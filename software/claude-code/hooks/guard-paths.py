#!/usr/bin/python3
"""Keep Claude's files in the project, not in system temp directories or under ~/.claude.

The harness tells Claude to put scratch files in a session directory under /private/tmp, plans
in ~/.claude/plans and memories in ~/.claude/projects/<project>/memory. The user's rules put
all three in the project, where they survive a reboot and sit next to the work they belong to.
Prose loses that argument with the harness, so this PreToolUse hook denies the write instead:

  - file tools: a target path in one of those locations;
  - Bash: an output redirect, or `tee`, `mkdir`, `touch`, `mktemp`, `cp`, `mv`, `ln`,
    `install` with such a destination. Reads stay allowed. It misses some forms, by design.

Runs on the system python, without uv, because it runs before every Bash and file tool call.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Optional

from shell_commands import Command, simple_commands

HOME = os.path.expanduser("~")
CLAUDE_HOME = os.path.realpath(os.path.join(HOME, ".claude"))
TEMP_ROOTS = sorted(
    {
        os.path.realpath(path)
        for path in ("/tmp", "/private/tmp", "/var/folders", os.environ.get("TMPDIR", "/tmp"))
    }
)
AUTO_MEMORY = re.compile(re.escape(CLAUDE_HOME) + r"/projects/[^/]+/memory(/|$)")
PLANS = os.path.join(CLAUDE_HOME, "plans")

FILE_TOOL_PATH_FIELDS = {
    "Write": "file_path",
    "Edit": "file_path",
    "MultiEdit": "file_path",
    "NotebookEdit": "notebook_path",
}
CREATING_COMMANDS = {"mkdir", "touch"}
COPYING_COMMANDS = {"cp", "mv", "ln", "install", "rsync"}


def under(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def where_it_belongs(path: str, project: str) -> Optional[str]:
    """Say where a file at `path` belongs instead, or None when `path` is fine."""
    if any(under(path, root) for root in TEMP_ROOTS):
        return (
            f"`{path}` is in a system temp directory. Put temporary files in "
            f"`{project}/.claude/scratchpad.local/<work-name>/` instead."
        )
    if under(path, PLANS):
        return (
            f"`{path}` is in ~/.claude/plans. Save plans in `{project}/.claude/plans/` "
            "instead, named `YYYY-MM-DD_<description>.md`."
        )
    if AUTO_MEMORY.match(path):
        return (
            f"`{path}` is in the global auto-memory. Save memories in `{project}/.claude/memory/` "
            "instead, or in `.claude/memory.local/` when they are personal."
        )
    return None


def resolve(path: str, cwd: str) -> str:
    path = re.sub(r"^\$\{?HOME\}?(?=/|$)", HOME, path)
    path = re.sub(r"^\$\{?TMPDIR\}?(?=/|$)", os.environ.get("TMPDIR", "/tmp"), path)
    return os.path.realpath(os.path.join(cwd, os.path.expanduser(path)))


def operands(command: Command) -> list:
    return [word for word in command.argv[1:] if not word.startswith("-")]


def mktemp_target(command: Command) -> Optional[str]:
    """Where `mktemp` creates its file: $TMPDIR unless a directory or a path template is given."""
    arguments = command.argv[1:]
    for index, argument in enumerate(arguments):
        if argument in ("-p", "--tmpdir") and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith("--tmpdir="):
            return argument.split("=", 1)[1]
    templates = [argument for argument in arguments if not argument.startswith("-")]
    if "-t" in arguments or not templates:
        return os.environ.get("TMPDIR", "/tmp")
    return templates[-1] if "/" in templates[-1] else None


def write_targets(command: Command) -> list:
    targets = [
        target
        for operator, target in command.redirects
        if ">" in operator and target and not target.isdigit() and target != "-"
    ]
    name = command.name
    if name in CREATING_COMMANDS or name == "tee":
        targets += operands(command)
    elif name == "mktemp":
        target = mktemp_target(command)
        targets += [target] if target else []
    elif name in COPYING_COMMANDS:
        arguments = command.argv[1:]
        for index, argument in enumerate(arguments):
            if argument == "-t" and index + 1 < len(arguments):
                targets.append(arguments[index + 1])
            elif argument.startswith("--target-directory="):
                targets.append(argument.split("=", 1)[1])
        destinations = operands(command)
        if len(destinations) >= 2:
            targets.append(destinations[-1])
    return targets


def bash_violations(command_line: str, cwd: str, project: str) -> list:
    try:
        commands = simple_commands(command_line)
    except ValueError:
        return []
    violations = []
    for command in commands:
        if command.name == "cd" and len(command.argv) > 1:
            cwd = resolve(command.argv[1], cwd)
            continue
        for target in write_targets(command):
            reason = where_it_belongs(resolve(target, cwd), project)
            if reason and reason not in violations:
                violations.append(reason)
    return violations


def deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )


def check(hook_input: dict[str, Any]) -> None:
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    cwd = hook_input.get("cwd") or os.getcwd()
    project = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    if tool_name in FILE_TOOL_PATH_FIELDS:
        path = tool_input.get(FILE_TOOL_PATH_FIELDS[tool_name], "")
        reason = where_it_belongs(resolve(path, cwd), project) if path else None
        violations = [reason] if reason else []
    elif tool_name == "Bash":
        violations = bash_violations(tool_input.get("command", ""), cwd, project)
    else:
        return
    if violations:
        deny("\n".join(violations))


if __name__ == "__main__":
    check(json.load(sys.stdin))
