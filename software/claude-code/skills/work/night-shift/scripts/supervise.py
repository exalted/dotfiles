"""Run a child process in its own process group under a hard deadline, and leave nothing of it running.

An alarm on the parent alone leaves grandchildren running (test runners, package managers, subagents).
Each child gets its own session; when it ends, for any reason, whatever is left of its group gets SIGTERM,
then SIGKILL. Codex delegates start their own groups and record them in the run directory, so the driver
reaps those too.
"""

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

GRACE_SECONDS = 30
CODEX_GROUPS_FILE = "codex-pgids"


@dataclass(frozen=True)
class Outcome:
    returncode: int
    timed_out: bool
    stdout: str
    stderr: str


def run(command: list[str], *, cwd: Path, seconds: float, env: dict[str, str] | None = None, log_dir: Path, name: str) -> Outcome:
    log_dir.mkdir(parents=True, exist_ok=True)
    out_path, err_path = log_dir / f"{name}.out", log_dir / f"{name}.err"
    with out_path.open("w") as out, err_path.open("w") as err:
        process = subprocess.Popen(
            command, cwd=cwd, env=_child_env(env), stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True
        )
        timed_out = False
        end = time.monotonic() + max(seconds, 1)
        while process.poll() is None:
            if time.monotonic() >= end:
                timed_out = True
                _signal_group(process.pid, signal.SIGTERM)
                try:
                    process.wait(GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    pass
                break
            time.sleep(2)
        end_group(process.pid)
        if process.poll() is None:
            process.wait()
    return Outcome(process.returncode if process.returncode is not None else -1, timed_out, out_path.read_text(), err_path.read_text())


def _child_env(extra: dict[str, str] | None) -> dict[str, str]:
    """The driver runs inside uv's own script environment; its VIRTUAL_ENV must not leak into a repository's commands."""
    env = {key: value for key, value in os.environ.items() if key not in ("VIRTUAL_ENV", "UV_INTERNAL__PARENT_INTERPRETER")}
    return {**env, **(extra or {})}


def end_group(pgid: int) -> None:
    """Whatever is left of a process group after its leader ended: SIGTERM, a short grace, then SIGKILL."""
    if not _signal_group(pgid, signal.SIGTERM):
        return
    for _ in range(10):
        time.sleep(1)
        if not _signal_group(pgid, 0):
            return
    _signal_group(pgid, signal.SIGKILL)


def reap_codex(run_dir: Path) -> int:
    """End codex process groups recorded under this run that are still alive and still codex."""
    ended = 0
    for record in run_dir.rglob(CODEX_GROUPS_FILE):
        for line in record.read_text().split():
            pgid = int(line)
            listing = subprocess.run(["/bin/ps", "-A", "-o", "pgid=,command="], capture_output=True, text=True).stdout
            members = [line.split(None, 1)[1] for line in listing.splitlines() if line.split(None, 1)[0] == str(pgid)]
            if any("codex" in command for command in members):
                end_group(pgid)
                ended += 1
    return ended


def _signal_group(pgid: int, sig: int) -> bool:
    try:
        os.killpg(pgid, sig)
        return True
    except (ProcessLookupError, PermissionError):
        return False
