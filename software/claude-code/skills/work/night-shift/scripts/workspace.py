"""Git worktrees for the night shift: create, set up, verify, commit the wrapper's own files, clean up.

Every git call the driver makes runs with core.hooksPath=/dev/null: the driver's own commits and checkouts
must not run repository hooks. The model's commits inside a worktree do run them, as in the user's day work.
Nothing here deletes a file: cleanup moves a worktree to the macOS Trash and keeps unmerged branches.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import supervise
from common import ARCHIVE_DIR, NIGHT_AWS_CONFIG, NIGHT_DOCKER_CONFIG, Json, Repo, log

EXCLUDE_LINE = ".claude/worktrees/"
SETUP_MINUTES = 15
VERIFY_MINUTES = 30
TAIL = 3000


class SetupProblem(Exception):
    pass


HOST_IN_VALUE = re.compile(r"(?:[a-z][a-z0-9+.-]*://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?=[:/\"'\s,}]|$)", re.IGNORECASE)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
# Hosts that are never a deployed environment, and names that mark a non-production one.
SAFE_HOST = re.compile(r"(^|\.)(localhost|alpha)(\.|$)|^127\.|\.local$|\.example\.com$|\balpha\b", re.IGNORECASE)


def production_hosts(env_file: Path, allowed: list[str], forbidden: list[str] = ()) -> list[str]:
    """Every host in an env file that is not local, not alpha, and not on the user's allowlist.

    The night shift must never reach production: a worktree's env file may point at local services or at
    alpha only. Anything else stops the story before the file is copied, so a guess never reaches a run.
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
    import json

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


def copy_env(source: Path, destination: Path, drop_keys: list[str]) -> None:
    """Copy an env file without the keys the night has no business holding, such as a personal Git token."""
    kept = [line for line in source.read_text().splitlines() if line.split("=", 1)[0].strip().removeprefix("export ") not in drop_keys]
    destination.write_text("\n".join(kept) + "\n")


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


def tool_env(worktree: Path) -> dict[str, str]:
    """The Node version the repository pins in .nvmrc, as the user's shell hook selects it by day.

    launchd's PATH has Homebrew's Node only, which may be a different major version than the repository's.
    """
    aws = {"AWS_CONFIG_FILE": str(NIGHT_AWS_CONFIG)} if NIGHT_AWS_CONFIG.exists() else {}
    if (NIGHT_DOCKER_CONFIG / "config.json").exists():
        aws["DOCKER_CONFIG"] = str(NIGHT_DOCKER_CONFIG)
    nvmrc = worktree / ".nvmrc"
    if not nvmrc.is_file():
        return aws
    version = nvmrc.read_text().strip().lstrip("v")
    node_bin = Path.home() / ".nvm" / "versions" / "node" / f"v{version}" / "bin"
    if not node_bin.is_dir():
        raise SetupProblem(f"{worktree.name}: .nvmrc asks for Node {version}, which nvm has not installed (nvm install {version})")
    return {**aws, "PATH": f"{node_bin}:{os.environ.get('PATH', '')}"}


def git(cwd: Path, *args: str, check: bool = True, timeout: int = 300) -> str:
    result = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(cwd), *args], capture_output=True, text=True, timeout=timeout)
    if check and result.returncode != 0:
        raise SetupProblem(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()[-500:]}")
    return result.stdout.strip()


def worktree_path(repo: Repo, key: str) -> Path:
    return repo.path / ".claude" / "worktrees" / f"night-{key}"


def branch_name(key: str) -> str:
    return f"night/{key}"


def fetch(repo: Repo) -> str | None:
    """Refresh origin/main. GitLab may refuse once its SSO session expired; the run then uses the last fetched main."""
    try:
        git(repo.path, "fetch", "--quiet", "origin", timeout=120)
        return None
    except (SetupProblem, subprocess.TimeoutExpired) as error:
        return f"{repo.name}: fetch failed, origin/main may be stale ({str(error)[:200]})"


def exclude_worktrees(repo: Repo) -> None:
    """Keep worktrees out of `git status` in the main checkout through the clone's own, untracked exclude file."""
    exclude = repo.path / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    lines = exclude.read_text().splitlines() if exclude.exists() else []
    if EXCLUDE_LINE not in lines:
        exclude.write_text("\n".join([*lines, EXCLUDE_LINE]) + "\n")


@dataclass(frozen=True)
class Prepared:
    repo: str
    path: Path
    branch: str
    base_sha: str
    reused: bool


def seconds_until(deadline: datetime) -> float:
    return (deadline - datetime.now()).total_seconds()


def prepare(repo: Repo, key: str, *, log_dir: Path, deadline: datetime, env_allowed_hosts: list[str], env_forbidden_hosts: list[str] = (), env_drop_keys: list[str] = ()) -> Prepared:
    for source, target in repo.copy:
        if Path(target).name.startswith(".env") and source.exists():
            if hosts := production_hosts(source, env_allowed_hosts, env_forbidden_hosts):
                raise SetupProblem(
                    f"{repo.name}: {source} names hosts that are not local or alpha: {', '.join(hosts)}. "
                    "If they are not production, add them to env_allowed_hosts in config.toml; nothing was copied."
                )
    exclude_worktrees(repo)
    path = worktree_path(repo, key)
    branch = branch_name(key)
    reused = path.exists()
    if not reused:
        exists = git(repo.path, "branch", "--list", branch)
        if exists:
            git(repo.path, "worktree", "add", str(path), branch)
        else:
            git(repo.path, "worktree", "add", "-b", branch, str(path), "origin/main")
    base_sha = git(path, "merge-base", "HEAD", "origin/main")
    for source, target in repo.copy:
        if not source.exists():
            raise SetupProblem(f"{repo.name}: {source} is missing (listed under copy in config.toml)")
        destination = path / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        if Path(target).name.startswith(".env"):
            copy_env(source, destination, list(env_drop_keys))
        else:
            shutil.copy2(source, destination)
    env = tool_env(path)
    for index, command in enumerate(repo.setup):
        if seconds_until(deadline) < 60:
            raise SetupProblem(f"{repo.name}: no time left before the deadline for setup")
        outcome = supervise.run(command, cwd=path, seconds=min(SETUP_MINUTES * 60, seconds_until(deadline)), env=env, log_dir=log_dir, name=f"setup-{repo.name}-{index}")
        if outcome.timed_out or outcome.returncode != 0:
            raise SetupProblem(f"{repo.name}: setup `{' '.join(command)}` failed: {(outcome.stderr or outcome.stdout)[-400:]}")
    return Prepared(repo.name, path, branch, base_sha, reused)


def head(path: Path) -> str:
    return git(path, "rev-parse", "HEAD")


def commits_since(path: Path, base: str) -> list[str]:
    out = git(path, "log", "--format=%h %s", f"{base}..HEAD")
    return out.splitlines() if out else []


def _git_bytes(cwd: Path, *args: str) -> bytes:
    """Raw output, untouched: a patch that loses its trailing newline no longer applies."""
    return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(cwd), *args], capture_output=True, check=True, timeout=300).stdout


def archive_dirty(path: Path, key: str) -> Path | None:
    """Save uncommitted work beside the state, so verification runs on committed code only and nothing is lost."""
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
    """Run the repository's own gate on the final commit, outside the model: Claude's "green" is confirmed or contradicted here."""
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


def commit_paths(path: Path, paths: list[str], message: str) -> bool:
    git(path, "add", "--", *paths)
    if not git(path, "diff", "--cached", "--name-only"):
        return False
    git(path, "commit", "--quiet", "-m", message, "--", *paths)
    return True


def cleanup(repo: Repo, key: str, *, force: bool) -> str:
    path = worktree_path(repo, key)
    branch = branch_name(key)
    # Merged means nothing on the branch is missing from main, local or pushed: the user merges and pushes.
    merged = not git(repo.path, "log", "--oneline", f"main..{branch}") or not git(repo.path, "log", "--oneline", f"origin/main..{branch}")
    if not merged and not force:
        return f"{repo.name}: {branch} has commits that are not in main; merge it first, or pass --force to keep it as an archive branch"
    if path.exists():
        archived = archive_dirty(path, key)
        subprocess.run(["/usr/bin/trash", "--stopOnError", str(path)], check=True)
        git(repo.path, "worktree", "prune")
        if archived:
            log(f"uncommitted files saved to {archived}")
    if merged:
        git(repo.path, "branch", "-D", branch)
        return f"{repo.name}: worktree to the Trash, merged branch {branch} removed"
    archive = f"night-archive/{key}-{datetime.now():%Y%m%d}"
    git(repo.path, "branch", "-m", branch, archive)
    return f"{repo.name}: worktree to the Trash, unmerged branch kept as {archive}"
