#!/usr/bin/python3
"""Deny rewriting git history on a default branch, and ask before rewriting it anywhere else.

Covers `git rebase`, force pushes, `git reset --hard` and `git commit --amend`. Permission rules
match command text, so `/usr/bin/git push -f` or `git -c k=v push -f` slips past a rule written for
`git push -f`, and no rule can see which commits are pushed or which branch a push lands on. This
hook reads the parsed command and the repository instead:

- `git rebase`: silent when it rewrites only local commits, so the permission mode decides; deny
  when a rewritten commit is on a remote's default branch; ask when the rewritten commits are pushed
  only to feature branches, naming them, or when the rebase runs `--exec` commands.
- force push (`-f`, `--force`, `--force-with-lease`, `--force-if-includes`, `+refspec`, `--mirror`):
  deny when it lands on a default branch or on every branch; ask otherwise.
- `git commit --amend`: deny when HEAD is on a remote's default branch; ask otherwise.
- `git reset --hard`: always ask, since it discards uncommitted work wherever it runs.

Whenever the hook cannot work out what a command rewrites, it asks. It fetches before judging
pushed commits, so that commits pushed from another machine count.

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
PUSH_OPTIONS_WITH_ARGUMENT = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
PUSH_FORCE_OPTIONS = {"-f", "--force", "--force-if-includes", "--mirror"}
PUSH_EVERY_BRANCH_OPTIONS = {"--mirror", "--all", "--branches"}
# Used only when a remote does not name its default branch through refs/remotes/<remote>/HEAD.
FALLBACK_DEFAULT_BRANCHES = ("main", "master")
FETCH_TIMEOUT_SECONDS = 40


class Unresolved(Exception):
    """The hook cannot tell what the command rewrites."""


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


def fetch(directory: str) -> None:
    try:
        git(directory, "fetch", "--quiet", "--all", timeout=FETCH_TIMEOUT_SECONDS)
    except (Unresolved, subprocess.TimeoutExpired) as error:
        raise Unresolved(f"cannot fetch, so commits pushed from elsewhere are unknown: {error}")


def ref_exists(directory: str, ref: str) -> bool:
    try:
        git(directory, "rev-parse", "--verify", "--quiet", ref)
    except Unresolved:
        return False
    return True


def default_branch_names(directory: str, remote: str) -> set:
    try:
        return {git(directory, "symbolic-ref", "--quiet", "--short", f"refs/remotes/{remote}/HEAD").split("/", 1)[1]}
    except (Unresolved, IndexError):
        return set(FALLBACK_DEFAULT_BRANCHES)


def default_branch_refs(directory: str) -> list:
    """Return the remote-tracking refs of every remote's default branch, such as `origin/main`."""
    refs = []
    for remote in git(directory, "remote").split():
        for name in sorted(default_branch_names(directory, remote)):
            if ref_exists(directory, f"refs/remotes/{remote}/{name}"):
                refs.append(f"{remote}/{name}")
    return refs


def remote_branches_containing(directory: str, commit: str) -> list:
    output = git(directory, "for-each-ref", "--contains", commit, "--format=%(refname:short)", "refs/remotes")
    return [ref for ref in output.splitlines() if "/" in ref and not ref.endswith("/HEAD")]


def commit_count(directory: str, *revisions: str) -> int:
    return int(git(directory, "rev-list", "--count", *revisions))


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


def rebase_decision(arguments: list, directory: str) -> Optional[tuple]:
    revisions = rewritten_range(arguments)
    if revisions is None:
        return None
    fetch(directory)
    rewritten = commit_count(directory, *revisions)
    pushed = rewritten - commit_count(directory, *revisions, "--not", "--remotes")
    if pushed:
        default_refs = default_branch_refs(directory)
        if default_refs and commit_count(directory, *revisions, "--not", *default_refs) != rewritten:
            return "deny", f"it rewrites commits that {', '.join(default_refs)} already contains. Never rewrite a default branch's history"
        # A branch that holds any pushed commit of a linear range also holds the oldest one.
        oldest_pushed = git(directory, "rev-list", "--reverse", *revisions, "--remotes").splitlines()[0]
        branches = ", ".join(remote_branches_containing(directory, oldest_pushed)) or "a remote branch"
        return "ask", (
            f"it rewrites {pushed} pushed commit(s) on {branches}, which no default branch contains. "
            "Approve only if the user asked for this rebase"
        )
    if runs_exec_commands(arguments):
        return "ask", "it runs `--exec` commands on each commit"
    return None


def push_destination(directory: str) -> list:
    """Return the remote and branch a bare `git push` updates, from `@{push}`."""
    return git(directory, "rev-parse", "--abbrev-ref", "@{push}").split("/", 1)


def push_decision(arguments: list, directory: str) -> Optional[tuple]:
    positional = []
    forces = False
    every_branch = False
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in PUSH_OPTIONS_WITH_ARGUMENT:
            index += 1
        elif argument in PUSH_FORCE_OPTIONS or argument.startswith("--force-with-lease"):
            forces = True
        elif argument.startswith("-") and not argument.startswith("--") and "f" in argument[1:]:
            forces = True
        elif not argument.startswith("-"):
            positional.append(argument)
        every_branch = every_branch or argument in PUSH_EVERY_BRANCH_OPTIONS
        index += 1
    refspecs = positional[1:]
    forces = forces or any(refspec.startswith("+") for refspec in refspecs)
    if not forces:
        return None
    if every_branch:
        return "deny", "it force-pushes every branch, the default branch included"

    remote = positional[0] if positional else push_destination(directory)[0]
    targets = []
    for refspec in refspecs or ["HEAD"]:
        destination = refspec.lstrip("+").split(":")[-1]
        if destination in ("", "HEAD"):
            destination = push_destination(directory)[1]
        if destination.startswith("refs/heads/"):
            destination = destination[len("refs/heads/") :]
        targets.append(destination)
    protected = sorted(set(targets) & default_branch_names(directory, remote))
    if protected:
        return "deny", f"it force-pushes to {remote}/{', '.join(protected)}, a default branch"
    return "ask", f"it force-pushes to {remote}/{', '.join(targets)}. Approve only if the user asked for it"


def amend_decision(directory: str) -> tuple:
    fetch(directory)
    pushed_to = remote_branches_containing(directory, "HEAD")
    on_default = [ref for ref in pushed_to if ref in default_branch_refs(directory)]
    if on_default:
        return "deny", f"HEAD is already on {', '.join(on_default)}. Never rewrite a default branch's history"
    where = f"pushed to {', '.join(pushed_to)}" if pushed_to else "local only"
    return "ask", f"it rewrites HEAD ({where}). Approve only if the user asked for it"


def git_decision(command: Command, directory: Optional[str]) -> Optional[tuple]:
    """Return ("deny" or "ask", reason) for one git command, or None to stay silent."""
    subcommand, arguments, directory = split_git_command(command.argv[1:], directory)
    if subcommand == "reset" and "--hard" in arguments:
        return "ask", "git reset --hard: it discards uncommitted changes and can drop commits. Approve only if the user asked for it"
    if subcommand == "rebase":
        decide_for = lambda directory: rebase_decision(arguments, directory)  # noqa: E731
    elif subcommand == "push":
        decide_for = lambda directory: push_decision(arguments, directory)  # noqa: E731
    elif subcommand == "commit" and "--amend" in arguments:
        decide_for = amend_decision
    else:
        return None
    try:
        if directory is None:
            raise Unresolved("the repository directory is unknown")
        decision = decide_for(directory)
    except (Unresolved, ValueError, IndexError, OSError, subprocess.SubprocessError) as error:
        return "ask", f"git {subcommand}: the hook cannot tell what it rewrites ({error})"
    if decision is None:
        return None
    verdict, reason = decision
    return verdict, f"git {subcommand}: {reason}"


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
        decision = git_decision(command, directory)
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
                    "permissionDecisionReason": f"{reason}.",
                }
            },
            sys.stdout,
        )


if __name__ == "__main__":
    check(json.load(sys.stdin))
