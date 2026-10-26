"""The night shift works in the user's own checkout, one story at a time, on a plain branch per story.

The user's state comes first. Before a story starts, `enter()` records the checkout's branch, HEAD, status and
stash list, sets the user's uncommitted work aside with `git stash` (kept twice: in the stash list and under
a private backup ref), and switches to `night/<KEY>` from `origin/main`. `release()` always runs afterwards:
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
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import supervise
from common import ARCHIVE_DIR, FETCHED_FILE, NIGHT_AWS_CONFIG, NIGHT_DOCKER_CONFIG, Json, Repo, log, read_json, workdays_between, write_json

SETUP_MINUTES = 15
VERIFY_MINUTES = 30
TAIL = 3000
# A file the user changed this recently means they are working in the checkout: a manual run leaves it alone.
ACTIVE_MINUTES = 10
BACKUP_REF = "refs/night-shift/backup"


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


def night_docker_config() -> Path:
    """The user's Docker client config without its credential store: nothing at night may open the keychain.

    A keychain prompt waits for a password nobody types at night, and the test run hangs until its time limit.
    Images the suites use must already be on the machine (day work keeps them there); a missing private image
    then fails fast instead. Contexts stay shared, so the same engine answers.
    """
    source = Path.home() / ".docker" / "config.json"
    config = json.loads(source.read_text()) if source.exists() else {}
    for key in ("credsStore", "credHelpers", "auths"):
        config.pop(key, None)
    NIGHT_DOCKER_CONFIG.mkdir(parents=True, exist_ok=True)
    (NIGHT_DOCKER_CONFIG / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    contexts = NIGHT_DOCKER_CONFIG / "contexts"
    if not contexts.exists() and (Path.home() / ".docker" / "contexts").exists():
        contexts.symlink_to(Path.home() / ".docker" / "contexts")
    return NIGHT_DOCKER_CONFIG


def docker_socket() -> str | None:
    """The socket of the Docker engine in use (Docker Desktop, Colima, ...), or None when none answers."""
    try:
        env = {**os.environ, "DOCKER_CONFIG": str(NIGHT_DOCKER_CONFIG)} if (NIGHT_DOCKER_CONFIG / "config.json").exists() else None
        info = subprocess.run(["docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"], capture_output=True, text=True, timeout=20, env=env)
        alive = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=30, env=env)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    host = info.stdout.strip()
    return host.removeprefix("unix://") if alive.returncode == 0 and host.startswith("unix://") else None


def tool_env(checkout: Path) -> dict[str, str]:
    """The Node version the repository pins in .nvmrc, as the user's shell hook selects it by day.

    launchd's PATH has Homebrew's Node only, which may be a different major version than the repository's.
    """
    env = {"AWS_CONFIG_FILE": str(NIGHT_AWS_CONFIG)} if NIGHT_AWS_CONFIG.exists() else {}
    if (NIGHT_DOCKER_CONFIG / "config.json").exists():
        env["DOCKER_CONFIG"] = str(NIGHT_DOCKER_CONFIG)
    nvmrc = checkout / ".nvmrc"
    if not nvmrc.is_file():
        return env
    version = nvmrc.read_text().strip().lstrip("v")
    node_bin = Path.home() / ".nvm" / "versions" / "node" / f"v{version}" / "bin"
    if not node_bin.is_dir():
        raise SetupProblem(f"{checkout.name}: .nvmrc asks for Node {version}, which nvm has not installed (nvm install {version})")
    return {**env, "PATH": f"{node_bin}:{os.environ.get('PATH', '')}"}


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


def _run_setup(repo: Repo, path: Path, *, log_dir: Path, deadline: datetime, label: str) -> None:
    """The repository's own setup commands (dependencies, generated binaries) for the branch now checked out."""
    env = tool_env(path)
    for index, command in enumerate(repo.setup):
        if seconds_until(deadline) < 60:
            raise SetupProblem(f"{repo.name}: no time left before the deadline for setup")
        outcome = supervise.run(command, cwd=path, seconds=min(SETUP_MINUTES * 60, seconds_until(deadline)), env=env, log_dir=log_dir, name=f"setup-{label}-{repo.name}-{index}")
        if outcome.timed_out or outcome.returncode != 0:
            raise SetupProblem(f"{repo.name}: setup `{' '.join(command)}` failed: {(outcome.stderr or outcome.stdout)[-400:]}")


def enter(repo: Repo, key: str, *, log_dir: Path, deadline: datetime, frame_file: Path) -> Prepared:
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
    frame_file.parent.mkdir(parents=True, exist_ok=True)
    frame = {"repo": repo.name, "path": str(path), "branch": branch, "created": not reused, "start": start, "user": asdict(user)}
    frame_file.write_text(json.dumps(frame, indent=2))
    try:
        if reused:
            git(path, "switch", "--quiet", branch)
        else:
            git(path, "switch", "--quiet", "-c", branch, "origin/main")
        _run_setup(repo, path, log_dir=log_dir, deadline=deadline, label="night")
    except Exception:
        release_frame(frame_file, repo=repo, log_dir=log_dir)
        raise
    return Prepared(repo.name, path, branch, git(path, "merge-base", "HEAD", "origin/main"), reused, user, frame_file)


def _clear_leftovers(path: Path, key: str) -> Path | None:
    """What the story left uncommitted: saved to the archive, then the tracked part reset and the rest trashed."""
    archived = archive_dirty(path, key)
    if archived:
        git(path, "reset", "--quiet", "--hard")
        untracked = [os.fsdecode(raw) for raw in _git_bytes(path, "ls-files", "-z", "--others", "--exclude-standard").split(b"\0") if raw]
        for start in range(0, len(untracked), 200):
            subprocess.run(["/usr/bin/trash", "--stopOnError", *[str(path / item) for item in untracked[start : start + 200]]], check=True)
    return archived


def release_frame(frame_file: Path, *, repo: Repo, log_dir: Path, deadline: datetime | None = None) -> Json:
    """Return the checkout to the user exactly as recorded. Safe to run twice, and after a crash."""
    frame = json.loads(frame_file.read_text())
    if frame.get("released"):
        return frame["released"]
    path = Path(frame["path"])
    user = UserState(**frame["user"])
    key = frame["branch"].removeprefix("night/")
    problems: list[str] = []
    archived = None
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
        _run_setup(repo, path, log_dir=log_dir, deadline=deadline or datetime.max, label="user")
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


def release(prepared: Prepared, *, repo: Repo, log_dir: Path, deadline: datetime | None = None) -> Json:
    return release_frame(prepared.frame_file, repo=repo, log_dir=log_dir, deadline=deadline)


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


def verify(repo: Repo, prepared: Prepared, *, key: str, log_dir: Path, deadline: datetime) -> Json:
    """Run the repository's own gate on the story's last commit, outside the model.

    The checkout holds exactly origin/main plus this story's commits (the user's work is set aside), so a
    passing gate means the branch is deployable on its own. Uncommitted leftovers are archived and stashed
    first, so only committed code is judged.
    """
    archived = archive_dirty(prepared.path, key)
    stashed = False
    if archived:
        git(prepared.path, "stash", "push", "--include-untracked", "--message", "night-shift-verify")
        stashed = True
    results, passed = [], True
    try:
        final_sha = head(prepared.path)
        docker = docker_socket()
        for index, item in enumerate(repo.verify):
            command = item["command"]
            if seconds_until(deadline) < 60:
                passed = False
                results.append({"command": " ".join(command), "ok": False, "timed_out": True, "tail": "not run: no time left before the deadline"})
                continue
            if item.get("requires") == "docker" and not docker:
                passed = False
                results.append({"command": " ".join(command), "ok": False, "timed_out": False, "tail": "not run: no Docker engine answered"})
                continue
            outcome = supervise.run(command, cwd=prepared.path, seconds=min(VERIFY_MINUTES * 60, seconds_until(deadline)), env=tool_env(prepared.path), log_dir=log_dir, name=f"verify-{repo.name}-{index}")
            ok = outcome.returncode == 0 and not outcome.timed_out
            passed &= ok
            results.append({"command": " ".join(command), "ok": ok, "timed_out": outcome.timed_out, "tail": (outcome.stdout + outcome.stderr)[-TAIL:]})
    finally:
        if stashed:
            git(prepared.path, "stash", "pop", check=False)
    return {"repo": repo.name, "passed": passed and bool(results), "final_sha": final_sha, "base_sha": prepared.base_sha, "archived_uncommitted": str(archived) if archived else None, "commands": results}


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
