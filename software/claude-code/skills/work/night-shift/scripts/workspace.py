"""The night shift works in the user's own checkout, one story at a time, on a plain branch per story.

The user's state comes first. Before a story starts, `enter()` records the checkout's branch, HEAD, status and
stash list, sets the user's uncommitted work aside with `git stash` (kept twice: in the stash list and under
a private backup ref), and switches to `night/<KEY>` from `origin/main`, or, when an earlier attempt left the branch,
rebases it onto `origin/main`. `release()` always runs afterwards:
it saves whatever the story left uncommitted, returns to the user's branch, puts their work back exactly
(staged stays staged), and compares the result with the record. A branch the night created and left without
a commit is removed then: the user reviews only branches that hold work. The frame is written to disk, so a
crashed run is released at the next start.

The driver's own git calls run with core.hooksPath=/dev/null; the model's commits run the repository's hooks,
as in the user's day work. Nothing here deletes a file: leftovers are saved first, then moved to the Trash.
"""

import json
import os
import re
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import supervise
from common import ARCHIVE_DIR, FETCHED_FILE, NIGHT_AWS_CONFIG, Json, Repo, log, read_json, workdays_between, write_json

GATE_MINUTES = 60
TAIL = 3000
# A file the user changed this recently means they are working in the checkout: a manual run leaves it alone.
ACTIVE_MINUTES = 10
BACKUP_REF = "refs/night-shift/backup"


# Moves a checkout's dependencies and generated files from one commit to another: (checkout, from, to, label).
Setup = Callable[[Path, str, str, str], None]


class SetupProblem(Exception):
    pass


HOST_IN_VALUE = re.compile(r"(?:[a-z][a-z0-9+.-]*://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?=[:/\"'\s,}]|$)", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
# Hosts that are never a deployed environment, and names that mark a non-production one.
SAFE_HOST = re.compile(r"(^|\.)(localhost|alpha)(\.|$)|^127\.|\.local$|\.example\.com$|\balpha\b", re.IGNORECASE)


def production_hosts(env_file: Path, allowed: list[str], forbidden: list[str] = ()) -> list[str]:
    """Every host in an env file that is not local, not alpha, and not on the user's allowlist.

    The night shift must never reach production: the checkout's env file may point at local services or at
    alpha only. Anything else keeps the night shift out of that repository.
    """
    found = set()
    for line in env_file.read_text().splitlines():
        if line.lstrip().startswith("#") or "=" not in line:
            continue
        value = EMAIL.sub("", line.split("=", 1)[1])
        for host in HOST_IN_VALUE.findall(value):
            host = host.lower()
            if any(re.fullmatch(pattern, host) for pattern in forbidden):
                found.add(host)
                continue
            if SAFE_HOST.search(host) or any(re.fullmatch(pattern, host) for pattern in allowed):
                continue
            found.add(host)
    return sorted(found)


def night_aws_config(allowed_accounts: list[str]) -> Path:
    """The user's AWS config with only the profiles of allowed (non-production) accounts.

    By day the user picks a production profile on purpose. At night no command may even name one, so every
    night process reads this copy through AWS_CONFIG_FILE; SSO sessions and the token cache stay shared.
    """
    source = Path.home() / ".aws" / "config"
    blocks, current = [], []
    for line in (source.read_text().splitlines() if source.exists() else []):
        if line.startswith("[") and current:
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    kept = []
    for block in blocks:
        header = block[0].strip()
        accounts = [line.split("=", 1)[1].strip() for line in block if line.strip().startswith("sso_account_id")]
        is_profile = header.startswith("[profile ") or header == "[default]"
        if not is_profile or (accounts and all(account in allowed_accounts for account in accounts)) or (header == "[default]" and not accounts):
            kept.append("\n".join(block))
    NIGHT_AWS_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    NIGHT_AWS_CONFIG.write_text("\n\n".join(kept) + "\n")
    return NIGHT_AWS_CONFIG


def tool_env(checkout: Path) -> dict[str, str]:
    """The environment a terminal opened in the checkout has by day, so the night keeps no copy of the user's shell.

    The user's hooks (direnv, the .nvmrc Node) run before a prompt, and no prompt ever shows at night: the
    profile shell runs them once, explicitly. The night's AWS config goes on top.
    """
    shell = subprocess.run(["bash", "-lc", 'cd "$1" && { eval "$PROMPT_COMMAND"; } >&2 && /usr/bin/env -0', "tool-env", str(checkout)],
                           capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
    errors = shell.stderr.decode(errors="replace")
    if shell.returncode != 0 or "is blocked" in errors or "no installed Node matches" in errors:
        raise SetupProblem(f"{checkout.name}: the shell profile did not set up the checkout: {errors.strip()[-400:]}")
    env = dict(item.split("=", 1) for item in shell.stdout.decode(errors="replace").split("\0") if "=" in item)
    for name in ("PWD", "OLDPWD", "SHLVL", "_"):
        env.pop(name, None)
    if NIGHT_AWS_CONFIG.exists():
        env["AWS_CONFIG_FILE"] = str(NIGHT_AWS_CONFIG)
    return env


def git(cwd: Path, *args: str, check: bool = True, timeout: int = 300) -> str:
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(cwd), *args], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise SetupProblem(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()[-500:]}")
    return result.stdout.strip()


def _git_bytes(cwd: Path, *args: str) -> bytes:
    """Raw output, untouched: a patch that loses its trailing newline no longer applies."""
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(cwd), *args], capture_output=True, check=True, timeout=300).stdout


def branch_name(key: str) -> str:
    return f"night/{key}"


def fetch(repo: Repo) -> str | None:
    """Refresh origin/main; on failure, the remote's one-line reason. GitLab refuses once the user's SSO session
    expired; the run then uses the last fetched main."""
    try:
        git(repo.path, "fetch", "--quiet", "origin", timeout=120)
    except (SetupProblem, subprocess.TimeoutExpired) as error:
        lines = [line.removeprefix("remote:").strip() for line in str(error).splitlines()]
        return next((line for line in lines if "ERROR" in line), " ".join(lines)[-200:])
    fetched = read_json(FETCHED_FILE, {}) or {}
    write_json(FETCHED_FILE, {**fetched, repo.name: datetime.now().timestamp()})
    return None


def last_fetched(repo: Repo) -> float | None:
    """When origin was last fetched with success, by the night shift or by the user.

    A failed fetch truncates FETCH_HEAD, so only a non-empty one dates a success; the night shift's own record
    and origin/main's reflog cover the rest.
    """
    moments = [float((read_json(FETCHED_FILE, {}) or {}).get(repo.name) or 0)]
    fetch_head = Path(git(repo.path, "rev-parse", "--path-format=absolute", "--git-path", "FETCH_HEAD"))
    if fetch_head.is_file() and fetch_head.stat().st_size:
        moments.append(fetch_head.stat().st_mtime)
    reflog = git(repo.path, "reflog", "show", "--format=%ct", "-n", "1", "refs/remotes/origin/main", check=False)
    if reflog.isdigit():
        moments.append(float(reflog))
    return max(moments) or None


def staleness(repo: Repo, max_workdays: int) -> str | None:
    """Why this checkout's origin/main is too old to start a story on, or None. Weekends do not age it:
    the team rarely pushes then."""
    fetched = last_fetched(repo)
    if fetched is None:
        return f"{repo.name}: never fetched"
    days = workdays_between(fetched, datetime.now().timestamp())
    if days < max_workdays:
        return None
    return f"{repo.name}: last fetched {datetime.fromtimestamp(fetched):%a %d %b %H:%M}, {days} workdays ago"


def seconds_until(deadline: datetime) -> float:
    return (deadline - datetime.now()).total_seconds()


# ---------- the user's state ----------

@dataclass
class UserState:
    branch: str | None
    head: str
    status: str
    stash_list: str
    stash_sha: str | None = None
    backup_ref: str | None = None


def _state(path: Path) -> UserState:
    branch = git(path, "branch", "--show-current") or None
    return UserState(
        branch=branch,
        head=git(path, "rev-parse", "HEAD"),
        status=git(path, "status", "--porcelain=v1", "--untracked-files=all"),
        stash_list=git(path, "stash", "list", "--format=%H"),
    )


def _git_dir_marker(path: Path, name: str) -> bool:
    return (Path(git(path, "rev-parse", "--absolute-git-dir")) / name).exists()


def preflight(repo: Repo, *, manual: bool, env_allowed_hosts: list[str], env_forbidden_hosts: list[str]) -> None:
    """Reasons to leave a repository alone tonight. Every one is reported in the note."""
    path = repo.path
    for marker, what in (("rebase-merge", "a rebase"), ("rebase-apply", "a rebase or am"), ("MERGE_HEAD", "a merge"), ("CHERRY_PICK_HEAD", "a cherry-pick"), ("REVERT_HEAD", "a revert"), ("index.lock", "another git process")):
        if _git_dir_marker(path, marker):
            raise SetupProblem(f"{repo.name}: {what} is in progress in your checkout; the night shift left it alone")
    env_file = path / ".env"
    if env_file.exists() and (hosts := production_hosts(env_file, env_allowed_hosts, env_forbidden_hosts)):
        raise SetupProblem(f"{repo.name}: .env names hosts that are not local or alpha: {', '.join(hosts)}")
    if manual:
        cutoff = datetime.now().timestamp() - ACTIVE_MINUTES * 60
        for line in git(path, "status", "--porcelain=v1", "--untracked-files=all").splitlines():
            changed = path / line[3:].split(" -> ")[-1]
            if changed.exists() and changed.stat().st_mtime > cutoff:
                raise SetupProblem(f"{repo.name}: you changed {line[3:]} in the last {ACTIVE_MINUTES} minutes; a manual run does not take over a checkout in use")


# ---------- the frame around one story ----------

@dataclass
class Prepared:
    repo: str
    path: Path
    branch: str
    base_sha: str
    reused: bool
    user: UserState = field(default_factory=lambda: UserState(None, "", "", ""))
    frame_file: Path | None = None
    # Commits an earlier attempt left on the branch, and a rebase onto origin/main that stopped at a conflict.
    earlier: int = 0
    conflict: str = ""


def _follow(setup: Setup, path: Path, before: str, label: str) -> None:
    """The checkout moved between commits; its dependencies and generated files follow, if anything changed at all."""
    after = head(path)
    if git(path, "diff", "--name-only", before, after):
        setup(path, before, after, label)


def enter(repo: Repo, key: str, *, frame_file: Path, setup: Setup) -> Prepared:
    """Set the user's work aside and switch the checkout to the story's branch."""
    path = repo.path
    user = _state(path)
    branch = branch_name(key)
    if user.branch == branch:
        raise SetupProblem(f"{repo.name}: your checkout is already on {branch}; switch away from it first")
    if user.status:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        git(path, "stash", "push", "--include-untracked", "--message", f"night-shift: your work, set aside for {key} at {stamp}")
        user.stash_sha = git(path, "rev-parse", "stash@{0}")
        user.backup_ref = f"{BACKUP_REF}/{stamp}-{key}"
        git(path, "update-ref", user.backup_ref, user.stash_sha)
    reused = bool(git(path, "branch", "--list", branch))
    start = git(path, "rev-parse", branch if reused else "origin/main")
    earlier = len(commits_since(path, "origin/main", branch)) if reused else 0
    conflict = ""
    frame_file.parent.mkdir(parents=True, exist_ok=True)
    frame = {"repo": repo.name, "path": str(path), "branch": branch, "created": not reused, "start": start, "user": asdict(user)}
    frame_file.write_text(json.dumps(frame, indent=2))
    try:
        if reused:
            git(path, "switch", "--quiet", branch)
            conflict = _rebase_onto_main(path)
        else:
            git(path, "switch", "--quiet", "-c", branch, "origin/main")
        _follow(setup, path, user.head, "night")
    except Exception:
        release_frame(frame_file, setup=setup)
        raise
    return Prepared(repo.name, path, branch, git(path, "merge-base", "HEAD", "origin/main"), reused, user, frame_file, earlier, conflict)


def _rebase_in_progress(path: Path) -> bool:
    return _git_dir_marker(path, "rebase-merge") or _git_dir_marker(path, "rebase-apply")


def _rebase_onto_main(path: Path) -> str:
    """A branch must stand on current origin/main. A conflict stays in progress for the work session to resolve;
    the conflicting files are returned."""
    git(path, "-c", "core.editor=true", "rebase", "--quiet", "origin/main", check=False)
    if not _rebase_in_progress(path):
        return ""
    return git(path, "diff", "--name-only", "--diff-filter=U") or "unknown files"


def abort_unfinished_rebase(path: Path) -> bool:
    """Only the night can have a rebase in progress: preflight leaves a checkout with one alone."""
    if not _rebase_in_progress(path):
        return False
    git(path, "rebase", "--abort")
    return True


def continue_rebase(path: Path) -> tuple[bool, str]:
    """The work session's one way to move a conflicted rebase of its night branch on, after it resolved the files."""
    if not _rebase_in_progress(path):
        return False, "no rebase is in progress"
    head = (Path(git(path, "rev-parse", "--absolute-git-dir")) / "rebase-merge" / "head-name")
    if not head.exists() or not head.read_text().strip().startswith("refs/heads/night/"):
        return False, "the rebase in progress is not of a night branch"
    if unresolved := git(path, "diff", "--name-only", "--diff-filter=U"):
        return False, f"still unresolved: {unresolved}; edit and `git add` them, then run this again"
    result =subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.editor=true", "-C", str(path), "rebase", "--continue"], check=False,
                            capture_output=True, text=True, timeout=300)
    if _rebase_in_progress(path):
        unmerged = git(path, "diff", "--name-only", "--diff-filter=U")
        return False, f"the next commit conflicts too: resolve {unmerged or 'the files git names'}, stage them, and run this again\n{result.stdout}{result.stderr}"
    return result.returncode == 0, (result.stdout + result.stderr).strip() or "the branch is on origin/main now"


def _clear_leftovers(path: Path, key: str) -> Path | None:
    """What the story left uncommitted: saved to the archive, then the tracked part reset and the rest trashed."""
    archived = archive_dirty(path, key)
    if archived:
        git(path, "reset", "--quiet", "--hard")
        untracked = [os.fsdecode(raw) for raw in _git_bytes(path, "ls-files", "-z", "--others", "--exclude-standard").split(b"\0") if raw]
        for start in range(0, len(untracked), 200):
            subprocess.run(["/usr/bin/trash", "--stopOnError", *[str(path / item) for item in untracked[start : start + 200]]], check=True)
    return archived


def release_frame(frame_file: Path, *, setup: Setup) -> Json:
    """Return the checkout to the user exactly as recorded. Safe to run twice, and after a crash."""
    frame = json.loads(frame_file.read_text())
    if frame.get("released"):
        return frame["released"]
    path = Path(frame["path"])
    user = UserState(**frame["user"])
    key = frame["branch"].removeprefix("night/")
    problems: list[str] = []
    archived = None
    night_head = head(path)
    if abort_unfinished_rebase(path):
        log(f"{frame['repo']}: the rebase of {frame['branch']} onto origin/main was not finished; aborted")
    current = git(path, "branch", "--show-current")
    if current == frame["branch"]:
        archived = _clear_leftovers(path, key)
    if user.branch:
        if current != user.branch:
            git(path, "switch", "--quiet", user.branch)
    else:
        git(path, "switch", "--quiet", "--detach", user.head)
    if user.stash_sha:
        top = git(path, "rev-parse", "--verify", "--quiet", "stash@{0}", check=False)
        if top == user.stash_sha:
            popped = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(path), "stash", "pop", "--index", "--quiet"], capture_output=True, text=True)
            if popped.returncode != 0:
                problems.append(f"your set-aside work did not apply cleanly ({popped.stderr.strip()[-200:]}); it is still in the stash and under {user.backup_ref}")
        else:
            problems.append(f"your set-aside work is no longer on top of the stash list; it is safe under {user.backup_ref}")
    try:
        _follow(setup, path, night_head, "user")
    except SetupProblem as problem:
        problems.append(f"re-running setup for your branch failed: {problem}")
    after = _state(path)
    if after.branch != user.branch or after.head != user.head:
        problems.append(f"checkout is on {after.branch or after.head[:12]}, was {user.branch or user.head[:12]}")
    if after.status != user.status:
        problems.append("your uncommitted files differ from before the night")
    if after.stash_list != user.stash_list:
        problems.append("your stash list differs from before the night")
    removed = _remove_if_empty(path, frame)
    if user.backup_ref and not problems:
        # The work is back exactly as it was, so its safety copy has done its job.
        git(path, "update-ref", "-d", user.backup_ref)
    result = {"ok": not problems, "problems": problems, "archived_leftovers": str(archived) if archived else None, "backup_ref": user.backup_ref,
              "removed_empty_branch": removed}
    frame["released"] = result
    frame_file.write_text(json.dumps(frame, indent=2))
    if problems:
        log(f"{frame['repo']}: release problems: {problems}")
    return result


def _remove_if_empty(path: Path, frame: Json) -> bool:
    """A branch this night created and left with no commit of its own holds nothing to review."""
    branch = frame["branch"]
    if not frame.get("created") or not frame.get("start") or not git(path, "branch", "--list", branch):
        return False
    if git(path, "rev-list", f"{frame['start']}..{branch}") or git(path, "branch", "--show-current") == branch:
        return False
    git(path, "branch", "-D", branch)
    return True


def release(prepared: Prepared, *, setup: Setup) -> Json:
    return release_frame(prepared.frame_file, setup=setup)


def head(path: Path) -> str:
    return git(path, "rev-parse", "HEAD")


def commits_since(path: Path, base: str, ref: str = "HEAD") -> list[str]:
    out = git(path, "log", "--format=%h %s", f"{base}..{ref}")
    return out.splitlines() if out else []


def archive_dirty(path: Path, key: str) -> Path | None:
    """Save uncommitted work beside the state, so nothing is lost before the checkout is cleared or verified."""
    status = git(path, "status", "--porcelain")
    if not status:
        return None
    target = ARCHIVE_DIR / key / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target.mkdir(parents=True, exist_ok=True)
    (target / "status.txt").write_text(status + "\n")
    (target / "unstaged.diff").write_bytes(_git_bytes(path, "diff", "--binary", "--full-index"))
    (target / "staged.diff").write_bytes(_git_bytes(path, "diff", "--cached", "--binary", "--full-index"))
    for raw in _git_bytes(path, "ls-files", "-z", "--others", "--exclude-standard").split(b"\0"):
        if not raw:
            continue
        relative = os.fsdecode(raw)
        source, destination = path / relative, target / "untracked" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_symlink():
            os.symlink(os.readlink(source), destination)
        elif source.is_file():
            shutil.copy2(source, destination)
    return target


def pre_push_hook(path: Path) -> Path | None:
    """The hook git itself runs on a push, wherever the repository's core.hooksPath points."""
    found = subprocess.run(["git", "-C", str(path), "rev-parse", "--git-path", "hooks/pre-push"], capture_output=True, text=True, check=True, timeout=30)
    hook = Path(found.stdout.strip())
    hook = hook if hook.is_absolute() else path / hook
    return hook if hook.is_file() and os.access(hook, os.X_OK) else None


def hook_scripts(hook: Path, path: Path) -> list[str]:
    """The repository files a hook names, such as `${GIT_ROOT}/setup/check-ci.sh`: read from its text, so a guess."""
    code = "\n".join(line for line in hook.read_text(errors="replace").splitlines() if not line.lstrip().startswith("#"))
    named = re.findall(r"(?:\$\{?GIT_ROOT\}?/|\./)?((?:[\w.-]+/)+[\w.-]+)", code)
    return sorted({name for name in named if (path / name).is_file()})


def verify(repo: Repo, prepared: Prepared, *, key: str, log_dir: Path, deadline: datetime) -> Json:
    """Run the repository's own pre-push hook on the story's last commit, outside the model: the gate the user
    clears before every push, so the night keeps no copy of it.

    The checkout holds exactly origin/main plus this story's commits (the user's work is set aside), so a
    passing gate means the branch is deployable on its own. Uncommitted leftovers are archived and stashed
    first, so only committed code is judged and the hook's clean-tree check holds.
    """
    archived = archive_dirty(prepared.path, key)
    stashed = False
    if archived:
        git(prepared.path, "stash", "push", "--include-untracked", "--message", "night-shift-verify")
        stashed = True
    try:
        final_sha = head(prepared.path)
        hook = pre_push_hook(prepared.path)
        # The gate must not be one the story wrote: a branch that edits the hooks is not checked by them.
        hooks_changed = hook and hook.is_relative_to(prepared.path) and git(prepared.path, "diff", "--name-only", f"{prepared.base_sha}..{final_sha}", "--", str(hook.parent.relative_to(prepared.path)))
        if not hook:
            result = {"command": "pre-push hook", "ok": False, "timed_out": False, "tail": "not run: the repository has no active pre-push hook"}
        elif hooks_changed:
            result = {"command": "pre-push hook", "ok": False, "timed_out": False, "tail": f"not run: the branch changes the repository's git hooks ({hooks_changed.replace(chr(10), ', ')})"}
        elif seconds_until(deadline) < 60:
            result = {"command": "pre-push hook", "ok": False, "timed_out": True, "tail": "not run: no time left before the deadline"}
        else:
            remote = git(prepared.path, "remote", "get-url", "origin", check=False)
            ref = f"refs/heads/{prepared.branch}"
            outcome = supervise.run([str(hook), "origin", remote], cwd=prepared.path, seconds=min(GATE_MINUTES * 60, seconds_until(deadline)),
                                    env=tool_env(prepared.path), log_dir=log_dir, name=f"verify-{repo.name}", stdin=f"{ref} {final_sha} {ref} {'0' * 40}\n")
            ok = outcome.returncode == 0 and not outcome.timed_out
            result = {"command": f"{hook.relative_to(prepared.path) if hook.is_relative_to(prepared.path) else hook} origin", "ok": ok,
                      "timed_out": outcome.timed_out, "tail": (outcome.stdout + outcome.stderr)[-TAIL:]}
    finally:
        if stashed:
            git(prepared.path, "stash", "pop", check=False)
    scripts = hook_scripts(hook, prepared.path) if hook else []
    scripts_changed = git(prepared.path, "diff", "--name-only", f"{prepared.base_sha}..{final_sha}", "--", *scripts).splitlines() if scripts else []
    return {"repo": repo.name, "passed": result["ok"], "final_sha": final_sha, "base_sha": prepared.base_sha, "archived_uncommitted": str(archived) if archived else None,
            "commands": [result], "gate_scripts_changed": scripts_changed}


def independence_problems(path: Path, key: str) -> list[str]:
    """A story branch must stand alone: on current origin/main, sharing no commit with another night branch,
    and merging into main without a conflict. Checked on refs only; nothing is checked out."""
    branch = branch_name(key)
    problems = []
    if git(path, "merge-base", branch, "origin/main") != git(path, "rev-parse", "origin/main"):
        problems.append("is not based on the current origin/main")
    own = set(git(path, "rev-list", f"origin/main..{branch}").split())
    for other in git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads/night/").split():
        if other != branch and own & set(git(path, "rev-list", f"origin/main..{other}").split()):
            problems.append(f"shares commits with {other}")
    merge = subprocess.run(["git", "-C", str(path), "merge-tree", "--write-tree", "origin/main", branch], capture_output=True, text=True)
    if merge.returncode != 0:
        problems.append("conflicts with main")
    return problems


def commit_paths(path: Path, paths: list[str], message: str) -> bool:
    git(path, "add", "--", *paths)
    if not git(path, "diff", "--cached", "--name-only"):
        return False
    git(path, "commit", "--quiet", "-m", message, "--", *paths)
    return True


def cleanup(repo: Repo, key: str, *, force: bool) -> str:
    """After review: remove a story's branch once main holds its work, or with force even if it does not."""
    branch = branch_name(key)
    if not git(repo.path, "branch", "--list", branch):
        return f"{repo.name}: no branch {branch}"
    if git(repo.path, "branch", "--show-current") == branch:
        return f"{repo.name}: you are on {branch}; switch away from it first"
    # Merged means nothing on the branch is missing from main, local or pushed: the user merges and pushes.
    merged = not git(repo.path, "log", "--oneline", f"main..{branch}") or not git(repo.path, "log", "--oneline", f"origin/main..{branch}")
    if merged:
        git(repo.path, "branch", "-D", branch)
        return f"{repo.name}: merged branch {branch} removed"
    if not force:
        return f"{repo.name}: {branch} has commits that are not in main; merge it first, or pass --force to remove it anyway"
    git(repo.path, "branch", "-D", branch)
    return f"{repo.name}: unmerged branch {branch} removed"
