#!/usr/bin/python3
"""Deny a Jira, Confluence or Slack write, or a git commit, whose text says "ticket".

The team calls a Jira work item a "story". CLAUDE.md says so, but that is advice; this
PreToolUse hook makes it hold. It denies instead of rewriting the text itself, so Claude
rephrases the sentence and keeps the grammar right (articles, plurals, capitals).
It also blocks quoted or inherited text: the user chose no exceptions.

For a git commit it checks the whole command line, which holds the `-m` text and any
heredoc, and the file that `-F` names.

Runs on the system python, without uv, because it runs before every Bash call.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Iterator, Optional

from shell_commands import Command, simple_commands

TICKET = re.compile(r"\btickets?\b", re.IGNORECASE)
GIT_OPTIONS_WITH_ARGUMENT = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def commit_arguments(command: Command) -> Optional[tuple]:
    """Return the `git commit` arguments and the `-C` directory, or None for any other command."""
    if command.name != "git":
        return None
    arguments = command.argv[1:]
    directory = None
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        if arguments[index] == "-C" and index + 1 < len(arguments):
            directory = arguments[index + 1]
        index += 2 if arguments[index] in GIT_OPTIONS_WITH_ARGUMENT else 1
    if index >= len(arguments) or arguments[index] != "commit":
        return None
    return arguments[index + 1 :], directory


def message_files(arguments: list) -> list:
    files = []
    for index, argument in enumerate(arguments):
        if argument in ("-F", "--file") and index + 1 < len(arguments):
            files.append(arguments[index + 1])
        elif argument.startswith("--file="):
            files.append(argument[len("--file=") :])
        elif argument.startswith("-F") and len(argument) > 2:
            files.append(argument[2:])
    return [path for path in files if path != "-"]


def read(path: str) -> str:
    try:
        with open(os.path.expanduser(path), encoding="utf-8", errors="replace") as file:
            return file.read()
    except OSError:
        return ""


def commit_texts(command_line: str, cwd: str) -> list:
    try:
        commands = simple_commands(command_line)
    except ValueError:
        return []
    texts = []
    for command in commands:
        commit = commit_arguments(command)
        if commit is None:
            continue
        arguments, directory = commit
        base = os.path.join(cwd, os.path.expanduser(directory)) if directory else cwd
        texts.append(command_line)
        texts.extend(read(os.path.join(base, path)) for path in message_files(arguments))
    return texts


def check(hook_input: dict[str, Any]) -> None:
    tool_input = hook_input.get("tool_input", {})
    if hook_input.get("tool_name") == "Bash":
        texts = commit_texts(tool_input.get("command", ""), hook_input.get("cwd") or os.getcwd())
    else:
        texts = list(strings(tool_input))
    if not any(TICKET.search(text) for text in texts):
        return
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "This text says 'ticket'. Call a Jira work item a 'story' ('stories'), "
                    "also in quoted or existing text. Rewrite the text and call the tool again."
                ),
            }
        },
        sys.stdout,
    )


if __name__ == "__main__":
    check(json.load(sys.stdin))
