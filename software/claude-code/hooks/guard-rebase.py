#!/usr/bin/python3
"""Deny a `git rebase` that rewrites commits already on a remote branch.

Claude may rebase local-only commits, never pushed ones. A permission rule cannot tell the two
apart, and a hook's "allow" cannot override an ask rule, so settings.json has no rule for
`git rebase` and this PreToolUse hook decides:

- deny when the rewritten range holds a commit that a remote-tracking branch contains, checked
  after a fetch so that commits pushed from elsewhere count;
- ask when it cannot work that range out, cannot fetch, or the rebase runs `--exec` commands,
  which nothing else inspects;
- otherwise stay silent and let the permission mode decide: in auto mode, the classifier judges
  whether the user asked for the rebase.

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
FETCH_TIMEOUT_SECONDS = 40


class Unresolved(Exception):
    """The hook cannot tell which commits the rebase rewrites."""


def split_git_command(arguments: list, directory: Optional[str]) -> tuple:
    """Return the git subcommand, its arguments, and the directory git runs in."""
    index = 0
    while index < len(arguments) and arguments[index].startswith("-"):
        option = arguments[index]
        if option.split("=")[0] in GIT_OPTIONS_THAT_MOVE_THE_REPOSITORY:
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


def git(directory: str, *arguments: str, timeout: int = 20) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "-C", directory, *arguments],
        capture_output=True,
        text=True,
        timeout=timeout,
        # A credential prompt would hang the hook until its timeout.
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode != 0:
        raise Unresolved(result.stderr.strip() or f"`git {' '.join(arguments)}` failed")
    return result.stdout.strip()


def runs_exec_commands(rebase_arguments: list) -> bool:
    return any(
        argument in ("-x", "--exec") or argument.startswith("--exec=") or (argument.startswith("-x") and len(argument) > 2)
        for argument in rebase_arguments
    )


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
    try:
        git(directory, "fetch", "--quiet", "--all", timeout=FETCH_TIMEOUT_SECONDS)
    except (Unresolved, subprocess.TimeoutExpired) as error:
        raise Unresolved(f"cannot fetch, so commits pushed from elsewhere are unknown: {error}")
    rewritten = int(git(directory, "rev-list", "--count", *revisions))
    local_only = int(git(directory, "rev-list", "--count", *revisions, "--not", "--remotes"))
    return rewritten - local_only


def rebase_decision(command: Command, directory: Optional[str]) -> Optional[tuple]:
    """Return ("deny" or "ask", reason) for one git rebase command, or None to stay silent."""
    _, arguments, directory = split_git_command(command.argv[1:], directory)
    try:
        revisions = rewritten_range(arguments)
        if revisions is None:
            return None
        if directory is None:
            raise Unresolved("the repository directory is unknown")
        pushed = pushed_commit_count(directory, revisions)
    except (Unresolved, ValueError, OSError, subprocess.SubprocessError) as error:
        return "ask", f"the hook cannot tell which commits it rewrites ({error})"
    if pushed:
        return "deny", (
            f"it rewrites {pushed} commit(s) that a remote branch already contains. "
            "Rebase only local-only commits; never rewrite pushed history"
        )
    if runs_exec_commands(arguments):
        return "ask", "it runs `--exec` commands on each commit"
    return None


def decide(command_line: str, working_directory: Optional[str]) -> Optional[tuple]:
    try:
        commands = simple_commands(command_line)
    except ValueError:
        commands = []
    reasons: dict = {"deny": [], "ask": []}
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
        decision = rebase_decision(command, directory)
        if decision and decision[1] not in reasons[decision[0]]:
            reasons[decision[0]].append(decision[1])
    for verdict in ("deny", "ask"):
        if reasons[verdict]:
            return verdict, "; ".join(reasons[verdict])
    return None


def check(hook_input: dict[str, Any]) -> None:
    if hook_input.get("tool_name") != "Bash":
        return
    decision = decide(hook_input.get("tool_input", {}).get("command", ""), hook_input.get("cwd"))
    if decision:
        verdict, reason = decision
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": verdict,
                    "permissionDecisionReason": f"git rebase: {reason}.",
                }
            },
            sys.stdout,
        )


if __name__ == "__main__":
    check(json.load(sys.stdin))
