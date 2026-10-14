"""Split a Bash command line into the simple commands bash would run, for PreToolUse hooks.

A prefix match on the command text misses most of what bash runs. This module sees through
compound operators, subshells, command substitution, wrappers such as `sudo`, `env` and
`xargs`, `find -exec`, and nested shell strings (`bash -c`, `eval`), so a hook can judge each
command on its own. It is a heuristic, not a bash parser: it serves hooks that may miss an
obscure form but must not misread a common one.

Runs on the system python (3.9), without dependencies.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from typing import Optional

COMMAND_SEPARATORS = {
    ";",
    ";;",
    "&",
    "&&",
    "|",
    "||",
    "|&",
    "(",
    ")",
    "\n",
    "{",
    "}",
    "!",
}
COMMAND_PREFIX_KEYWORDS = {"if", "then", "else", "elif", "while", "until", "do", "time"}
HEREDOC_DELIMITER = re.compile(
    r"""(?<!<)<<-?(?!<)\s*['"]?([A-Za-z_][A-Za-z0-9_]*)['"]?"""
)
SHELL_PUNCTUATION = ";&|()<>\n"
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\[[^]]*\])?\+?=")

SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
TRANSPARENT_WRAPPERS = {"builtin", "exec", "nohup", "noglob", "time", "caffeinate", "stdbuf"}
# Options that take a separate argument, per wrapper, so the argument is not taken for the command.
OPTIONS_WITH_ARGUMENT = {
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-r", "-t", "-U", "-D", "-R", "-T"},
    "doas": {"-u", "-C"},
    "env": {"-u", "-C", "-P", "-S"},
    "xargs": {"-I", "-J", "-L", "-n", "-P", "-s", "-d", "-E", "-R", "-S", "-a"},
    "nice": {"-n"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
}
FIND_EXEC_ACTIONS = {"-exec", "-execdir", "-ok", "-okdir"}
MAX_NESTING = 5


@dataclass
class Command:
    """One simple command: its words after wrappers are removed, and its redirections."""

    argv: list
    redirects: list = field(default_factory=list)
    stdin: Optional[str] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.argv[0]) if self.argv else ""


def split_heredocs(command_line: str) -> tuple:
    """Return the command line without heredoc bodies, and the bodies in order of appearance."""
    kept_lines = []
    bodies = []
    pending_delimiters = []
    body_lines: list = []
    for line in command_line.split("\n"):
        if pending_delimiters:
            if line.strip() == pending_delimiters[0]:
                pending_delimiters.pop(0)
                bodies.append("\n".join(body_lines))
                body_lines = []
            else:
                body_lines.append(line)
            continue
        kept_lines.append(line)
        pending_delimiters.extend(HEREDOC_DELIMITER.findall(line))
    if pending_delimiters:
        bodies.append("\n".join(body_lines))
    return "\n".join(kept_lines), bodies


def strip_heredoc_bodies(command_line: str) -> str:
    """Drop heredoc bodies: they are data, and an apostrophe in prose would break tokenizing."""
    return split_heredocs(command_line)[0]


def tokenize(command_line: str) -> list:
    lexer = shlex.shlex(command_line, posix=True, punctuation_chars=SHELL_PUNCTUATION)
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    return list(lexer)


def is_operator(token: str) -> bool:
    return bool(token) and all(character in SHELL_PUNCTUATION for character in token)


def is_separator(token: str) -> bool:
    return token in COMMAND_SEPARATORS or (
        is_operator(token) and ("(" in token or ")" in token or not any(c in token for c in "<>"))
    )


def simple_commands(command_line: str, depth: int = 0) -> list:
    """Return every simple command in the line, nested ones included, in order.

    Raises ValueError when the top-level line does not tokenize, such as on an unbalanced quote.
    """
    if depth > MAX_NESTING:
        return []
    stripped, heredoc_bodies = split_heredocs(command_line)
    commands: list = []
    words: list = []
    redirects: list = []
    stdin: list = [None]

    def flush() -> None:
        if words or redirects:
            commands.extend(expand(list(words), list(redirects), stdin[0], depth))
        words.clear()
        redirects.clear()
        stdin[0] = None

    try:
        tokens = tokenize(stripped)
    except ValueError:
        # A nested string can hold quoting that only made sense to the outer shell.
        if depth == 0:
            raise
        return []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        for substitution in re.findall(r"\$\((.*)", token) + re.findall(r"`([^`]*)`", token):
            commands.extend(simple_commands(substitution, depth + 1))
        if is_separator(token):
            flush()
        elif is_operator(token):
            target = tokens[index + 1] if index + 1 < len(tokens) else ""
            if words and words[-1].isdigit():
                words.pop()
            if token in ("<<", "<<-") and heredoc_bodies:
                stdin[0] = heredoc_bodies.pop(0)
            elif token == "<<<":
                stdin[0] = target
            redirects.append((token, target))
            index += 1
        else:
            words.append(token)
        index += 1
    flush()
    return commands


def skip_options(words: list, wrapper: str) -> list:
    """Drop a wrapper's options and their arguments; return the wrapped command's words."""
    takes_argument = OPTIONS_WITH_ARGUMENT.get(wrapper, set())
    index = 0
    while index < len(words) and words[index].startswith("-") and words[index] != "-":
        if words[index] == "--":
            return words[index + 1 :]
        index += 2 if words[index] in takes_argument else 1
    return words[index:]


def expand(words: list, redirects: list, stdin: Optional[str], depth: int) -> list:
    while words and (words[0] in COMMAND_PREFIX_KEYWORDS or ASSIGNMENT.match(words[0])):
        words = words[1:]
    if not words:
        return [Command([], redirects, stdin)] if redirects else []
    name = os.path.basename(words[0])
    rest = words[1:]

    if name == "command" and rest[:1] not in (["-v"], ["-V"]):
        return expand(skip_options(rest, name), redirects, stdin, depth)
    if name in TRANSPARENT_WRAPPERS:
        return expand(skip_options(rest, name), redirects, stdin, depth)
    if name in ("sudo", "doas", "xargs", "nice"):
        return expand(skip_options(rest, name), redirects, stdin, depth)
    if name == "timeout":
        wrapped = skip_options(rest, name)
        return expand(wrapped[1:], redirects, stdin, depth)
    if name == "env":
        nested = []
        for index, word in enumerate(rest):
            if word in ("-S", "--split-string") and index + 1 < len(rest):
                nested = simple_commands(rest[index + 1], depth + 1)
        wrapped = skip_options(rest, name)
        while wrapped and ASSIGNMENT.match(wrapped[0]):
            wrapped = wrapped[1:]
        return nested + expand(wrapped, redirects, stdin, depth)
    if name == "eval":
        return [Command(words, redirects, stdin)] + simple_commands(" ".join(rest), depth + 1)
    if name in SHELLS:
        return [Command(words, redirects, stdin)] + shell_script_commands(rest, stdin, depth)
    if name == "find":
        return [Command(words, redirects, stdin)] + find_exec_commands(rest, depth)
    return [Command(words, redirects, stdin)]


def shell_script_commands(arguments: list, stdin: Optional[str], depth: int) -> list:
    """Commands of a nested shell: its `-c` string, or the heredoc it reads as its script."""
    for index, argument in enumerate(arguments):
        if argument.startswith("-") and not argument.startswith("--") and "c" in argument[1:]:
            if index + 1 < len(arguments):
                return simple_commands(arguments[index + 1], depth + 1)
            return []
        if not argument.startswith("-"):
            return []
    return simple_commands(stdin, depth + 1) if stdin else []


def find_exec_commands(arguments: list, depth: int) -> list:
    commands = []
    index = 0
    while index < len(arguments):
        if arguments[index] in FIND_EXEC_ACTIONS:
            end = index + 1
            while end < len(arguments) and arguments[end] not in (";", "+"):
                end += 1
            commands.extend(expand(arguments[index + 1 : end], [], None, depth + 1))
            index = end
        index += 1
    return commands
