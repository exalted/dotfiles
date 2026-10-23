#!/usr/bin/python3
"""Ask before a `git rebase` that rewrites commits already on a remote branch.

A permission rule cannot tell a rebase of local-only commits from one that rewrites pushed
history, and a hook's "allow" cannot override an ask rule. So settings.json has no ask rule
for `git rebase`; this PreToolUse hook asks only when the rewritten range holds a commit that
a remote-tracking branch contains, or when it cannot work that range out. Otherwise it stays
silent and the permission mode decides: in auto mode, the classifier judges whether the user
asked for the rebase.

Runs on the system python, without uv, because it runs before every Bash call.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Optional

from shell_commands import Command, simple_commands

GIT_OPTIONS_WITH_ARGUMENT = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
GIT_OPTIONS_THAT_MOVE_THE_REPOSITORY = {"--git-dir", "--work-tree"}
REBASE_OPTIONS_WITH_ARGUMENT = {"--onto", "-s", "--strategy", "-X", "--strategy-option", "-x", "--exec"}
REBASE_ACTIONS_ON_A_STARTED_REBASE = {
    "--abort",
    "--continue",
    "--skip",
    "--quit",
    "--edit-todo",
    "--show-current-patch",
}


class Unresolved(Exception):
    """The hook cannot tell which commits the rebase rewrites."""


def split_git_command(arguments: list, directory: Optional[str]) -> tuple:
    """Return the git subcommand, its arguments, and the directory git runs in."""
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        option = arguments[index]
        if option in GIT_OPTIONS_THAT_MOVE_THE_REPOSITORY or option.split("=")[0] in GIT_OPTIONS_THAT_MOVE_THE_REPOSITORY:
            directory = None
        if option == "-C" and index + 1 < len(arguments):
            directory = resolve_directory(directory, arguments[index + 1])
        index += 2 if option in GIT_OPTIONS_WITH_ARGUMENT else 1
    if index >= len(arguments):
        return None, [], directory
    return arguments[index], arguments[index + 1 :], directory


def resolve_directory(base: Optional[str], path: str) -> Optional[str]:
    if base is None or "$" in path or "`" in path:
        return None
    return os.path.normpath(os.path.join(base, os.path.expanduser(path)))


def git(directory: str, *arguments: str) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "-C", directory, *arguments],
        capture_output=True,
        text=True,
        timeout=20,
    )
    if result.returncode != 0:
        raise Unresolved(result.stderr.strip() or f"`git {' '.join(arguments)}` failed")
    return result.stdout.strip()


def rewritten_range(rebase_arguments: list) -> Optional[list]:
    """Return the rev-list arguments for the commits the rebase rewrites, or None for none."""
    if any(argument in REBASE_ACTIONS_ON_A_STARTED_REBASE for argument in rebase_arguments):
        return None
    positional = []
    rebases_from_root = False
    index = 0
    while index < len(rebase_arguments):
        argument = rebase_arguments[index]
        if argument == "--root":
            rebases_from_root = True
        elif argument in REBASE_OPTIONS_WITH_ARGUMENT:
            index += 1
        elif not argument.startswith("-"):
            positional.append(argument)
        index += 1
    if rebases_from_root:
        if len(positional) > 1:
            raise Unresolved("unexpected arguments after `--root`")
        return [positional[0] if positional else "HEAD"]
    if len(positional) > 2:
        raise Unresolved("unexpected rebase arguments")
    upstream = positional[0] if positional else "@{upstream}"
    branch = positional[1] if len(positional) > 1 else "HEAD"
    return [branch, f"^{upstream}"]


def pushed_commit_count(directory: str, revisions: list) -> int:
    rewritten = int(git(directory, "rev-list", "--count", *revisions))
    local_only = int(git(directory, "rev-list", "--count", *revisions, "--not", "--remotes"))
    return rewritten - local_only


def rebase_concern(command: Command, directory: Optional[str]) -> Optional[str]:
    _, arguments, directory = split_git_command(command.argv[1:], directory)
    revisions = rewritten_range(arguments)
    if revisions is None:
        return None
    if directory is None:
        raise Unresolved("the repository directory is unknown")
    pushed = pushed_commit_count(directory, revisions)
    if pushed:
        return f"it rewrites {pushed} commit(s) that a remote branch already contains"
    return None


def concerns(command_line: str, working_directory: Optional[str]) -> list:
    try:
        commands = simple_commands(command_line)
    except ValueError:
        commands = []
    found = []
    directory = working_directory
    for command in commands:
        if command.name == "cd":
            directory = resolve_directory(directory, command.argv[1]) if len(command.argv) == 2 else None
            continue
        if command.name != "git":
            continue
        subcommand, _, _ = split_git_command(command.argv[1:], directory)
        if subcommand != "rebase":
            continue
        try:
            concern = rebase_concern(command, directory)
        except (Unresolved, ValueError, OSError, subprocess.SubprocessError) as error:
            concern = f"the hook cannot tell which commits it rewrites ({error})"
        if concern and concern not in found:
            found.append(concern)
    return found


def check(hook_input: dict[str, Any]) -> None:
    if hook_input.get("tool_name") != "Bash":
        return
    found = concerns(hook_input.get("tool_input", {}).get("command", ""), hook_input.get("cwd"))
    if found:
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "ask",
                    "permissionDecisionReason": f"git rebase: {'; '.join(found)}.",
                }
            },
            sys.stdout,
        )


if __name__ == "__main__":
    check(json.load(sys.stdin))
