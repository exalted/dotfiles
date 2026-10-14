#!/usr/bin/python3
"""Deny a Bash command that deletes files, wherever in the command line the deletion hides.

The user deletes with `trash` only, so every deletion stays recoverable. `permissions.deny`
in settings.json blocks the direct forms (`rm …`, `find … -delete`), but a permission rule
matches the command text, so `bash -c 'rm …'` or a `python -c` one-liner slips past it.
This PreToolUse hook looks inside: nested shell strings, `eval`, `sudo`, `env`, `xargs`,
`find -exec`, and code passed to an interpreter with `-c`/`-e` or as a heredoc.

Runs on the system python, without uv, because it runs before every Bash call.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Optional

from shell_commands import Command, simple_commands

DELETING_COMMANDS = {"rm", "rmdir", "unlink", "shred", "srm"}
INTERPRETER = re.compile(r"^(python[0-9.]*|pypy[0-9.]*|perl|ruby|node|nodejs|deno|bun|php)$")
INLINE_CODE_FLAGS = {"-c", "-e", "-E", "-p", "--eval", "--print", "-r", "--run"}
DELETING_CALL = re.compile(
    r"""
    \bos\s*\.\s*(remove|unlink|rmdir|removedirs)\b
    | \bshutil\s*\.\s*rmtree\b
    | \.\s*(unlink|rmdir|rmtree)\s*\(
    | \bfs(\s*\.\s*promises)?\s*\.\s*(rm|rmSync|unlink|unlinkSync|rmdir|rmdirSync)\b
    | \b(rmSync|unlinkSync|rmdirSync)\b
    | \bFileUtils\s*\.\s*(rm\w*|remove\w*|rmdir|rmtree)\b
    | \b(File|Dir|FileUtils)\s*\.\s*(delete|unlink|rmdir)\b
    | \b(unlink|rmdir|rmtree|remove_tree)\b\s*[($'"]
    | \bDeno\s*\.\s*remove\b
    | (?<![\w.-])(rm|rmdir|shred)\s+[-'"/~.$\w]
    | ['"](rm|rmdir|shred|unlink)['"]\s*,
    """,
    re.VERBOSE,
)
GIT_OPTIONS_WITH_ARGUMENT = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def git_subcommand(arguments: list) -> Optional[str]:
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        index += 2 if arguments[index] in GIT_OPTIONS_WITH_ARGUMENT else 1
    return arguments[index] if index < len(arguments) else None


def inline_code(command: Command) -> list:
    arguments = command.argv[1:]
    code = [
        arguments[index + 1]
        for index, argument in enumerate(arguments[:-1])
        if argument in INLINE_CODE_FLAGS or re.match(r"^-[a-zA-Z]*[ce]$", argument)
    ]
    reads_stdin = not any(not argument.startswith("-") for argument in arguments) or "-" in arguments
    if command.stdin and reads_stdin:
        code.append(command.stdin)
    return code


def deletion(command: Command) -> Optional[str]:
    name = command.name
    if name in DELETING_COMMANDS:
        return f"`{name}`"
    if name == "find" and "-delete" in command.argv:
        return "`find -delete`"
    if name == "git" and git_subcommand(command.argv[1:]) == "clean":
        return "`git clean`"
    if INTERPRETER.match(name):
        for code in inline_code(command):
            match = DELETING_CALL.search(code)
            if match:
                return f"`{match.group(0).strip()}` in `{name}` code"
    return None


def deletions(command_line: str) -> list:
    try:
        commands = simple_commands(command_line)
    except ValueError:
        return []
    found = []
    for command in commands:
        description = deletion(command)
        if description and description not in found:
            found.append(description)
    return found


def check(hook_input: dict[str, Any]) -> None:
    if hook_input.get("tool_name") != "Bash":
        return
    found = deletions(hook_input.get("tool_input", {}).get("command", ""))
    if found:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": (
                        f"This command deletes files ({', '.join(found)}). Never delete: move "
                        "the paths to the Trash with `command trash --stopOnError <path>`. "
                        "If trash cannot do it, stop and ask the user."
                    ),
                }
            },
            sys.stdout,
        )


if __name__ == "__main__":
    check(json.load(sys.stdin))
