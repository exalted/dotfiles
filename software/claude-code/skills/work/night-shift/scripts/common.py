"""Shared by the night-shift scripts: configuration, knobs, state paths, the run lock, and small helpers.

The scripts run as `uv run --script`, which puts this directory on sys.path, so they import it directly.
Organization-specific values (Jira site, repos, people) live in untracked ~/.config/dotfiles/night-shift/,
never in this public repository.
"""

import fcntl
import json
import os
import re
import sys
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, NoReturn

type Json = dict[str, Any]

SCRIPTS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".config" / "dotfiles" / "night-shift"
CONFIG_FILE = CONFIG_DIR / "config.toml"
KNOBS_FILE = CONFIG_DIR / "knobs.json"
SECURITY_REQUEST_FILE = CONFIG_DIR / "security-request.txt"
# Not under a .claude/ folder: Claude Code asks before every write there, and nobody answers at night.
STATE_DIR = Path.home() / ".local" / "state" / "night-shift"
LEDGER_FILE = STATE_DIR / "ledger.json"
RUNS_DIR = STATE_DIR / "runs"
ARCHIVE_DIR = STATE_DIR / "archive"
LOCK_FILE = STATE_DIR / "lock"
RUN_NOW_FILE = STATE_DIR / "run-now"
FETCHED_FILE = STATE_DIR / "fetched.json"
ALERT_FILE = STATE_DIR / "alert.json"
TEAM_FILE = STATE_DIR / "team.json"
# Written by /pairing-candidates when the user records the week's tactical pairs.
TACTICAL_PAIRS_FILE = Path.home() / ".config" / "dotfiles" / "pairing-candidates" / "tactical.txt"
# Written by the user's status line script (software/claude-code/statusline-command.sh) during day sessions;
# a free reading when it is fresh, else the gate probes.
USAGE_SNAPSHOT = Path.home() / ".local" / "state" / "claude-usage" / "latest.json"
# Shared with the recap job, so the Jira site and project are configured once.
JIRA_BROWSE_FILE = Path.home() / ".config" / "dotfiles" / "jira"
RECAP_CONFIG_DIR = Path.home() / ".config" / "dotfiles" / "recap"
NIGHT_AWS_CONFIG = STATE_DIR / "aws-config"
NIGHT_DOCKER_CONFIG = STATE_DIR / "docker-config"
CODEX_EXEC = Path.home() / ".claude" / "skills" / "codex-servant" / "scripts" / "codex_exec.py"

KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
EXIT_SETUP_ERROR = 2

# Defaults for the values /night-shift may change. The user's knobs.json overrides them key by key.
DEFAULT_KNOBS: Json = {
    "paused": False,
    "stories": 1,
    # Ready stories waiting for the user's review, that nobody has picked up, count against `stories`.
    "hold_while_waiting": True,
    # The user's team this week (see team.py): tactical works only stories with config's tactical_label.
    "tactical": False,
    # Quota is in percent of the 7-day window. Day work keeps day_reserve_percent for each workday left before
    # the weekly reset (more if the ledger measured more); the night shift never goes above what is left, nor
    # above seven_day_ceiling_percent. One night may add at most night_points to the 7-day usage.
    "day_reserve_percent": 15,
    "seven_day_ceiling_percent": 90,
    "night_points": 10,
    "last_start": "03:00",
    "deadline": "05:00",
    "story_minutes": 75,
    "security": False,
    # The weekend security run: it may wait out usage resets until this weekday and time.
    "security_deadline": "Sun 18:00",
    "security_points": 15,
    "security_max_waits": 12,
    # Above 0, the nights before Saturday and Sunday run too, with this many stories and their own points.
    "weekend_stories": 0,
    "weekend_night_points": 15,
    # A checkout whose last successful fetch is this many workday starts old is stale: no story starts on it.
    "fetch_max_workdays": 2,
    "codex": True,
    "codex_fallback": False,
    # Runaway guards per session, in the only unit `claude --max-budget-usd` takes; the gate itself is in percent.
    "caps_usd": {"pick": 8.0, "work": 25.0, "fix": 10.0, "report": 5.0, "scan": 30.0, "patch": 15.0},
    # The fix round after codex's review starts only with at least this many minutes left before the deadline.
    "fix_minutes": 30,
}


def setup_error(message: str) -> NoReturn:
    print(f"SETUP ERROR: {message}", file=sys.stderr)
    sys.exit(EXIT_SETUP_ERROR)


def log(message: str) -> None:
    print(f"{datetime.now():%H:%M:%S} {message}", flush=True)


def write_json(path: Path, data: Any) -> None:
    """Write through a temporary name and rename, so a crash never leaves half a file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def valid_key(key: str) -> bool:
    return bool(KEY_PATTERN.match(key))


def knobs() -> Json:
    merged = json.loads(json.dumps(DEFAULT_KNOBS))
    for name, value in (read_json(KNOBS_FILE, {}) or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(name), dict):
            merged[name].update(value)
        else:
            merged[name] = value
    return merged


def save_knobs(changes: Json) -> Json:
    current = read_json(KNOBS_FILE, {}) or {}
    current.update(changes)
    write_json(KNOBS_FILE, current)
    return knobs()


@dataclass(frozen=True)
class Repo:
    name: str
    path: Path
    setup: list[list[str]]
    verify: list[Json]
    security_areas: list[str]


@dataclass(frozen=True)
class Config:
    jira_site: str
    jira_project: str
    vault_folder: Path
    repos: dict[str, Repo]
    people: list[Json]
    slack_channels: list[str] = field(default_factory=list)
    # The board whose to-do column is "the backlog" for the night shift, and the status that column shows.
    jira_board_id: int | None = None
    jira_board_column_status: str = ""
    env_allowed_hosts: list[str] = field(default_factory=list)
    env_forbidden_hosts: list[str] = field(default_factory=list)
    aws_allowed_accounts: list[str] = field(default_factory=list)
    security_rotation: list[str] = field(default_factory=list)
    # How the driver's own commits start, to pass the repositories' commit-msg hooks: {key} is the story key.
    commit_prefix: str = "{key}:"
    no_story_prefix: str = ""
    # A story that left To Do is cleaned up, unless it is in this status with the user as assignee or in this field.
    own_status: str = ""
    pair_field: str = ""
    # Stories with this label are tactical work; the others are strategic. Empty: no split.
    tactical_label: str = ""
    # The user's handle in /pairing-candidates' tactical pairs.
    pairing_handle: str = ""

    def subject(self, text: str, key: str | None = None) -> str:
        prefix = self.commit_prefix.format(key=key) if key else self.no_story_prefix
        return f"{prefix} {text}".strip()


def _jira_from_browse_file() -> tuple[str, str]:
    """The recap's `jira` file holds a browse URL such as https://<site>/browse/<KEY>-."""
    if not JIRA_BROWSE_FILE.is_file():
        return "", ""
    match = re.match(r"(https://[^/]+)/browse/([A-Z][A-Z0-9]+)-", JIRA_BROWSE_FILE.read_text().strip())
    return (match.group(1), match.group(2)) if match else ("", "")


def _default_vault_folder() -> Path | None:
    recap_folder = RECAP_CONFIG_DIR / "vault-folder"
    if recap_folder.is_file():
        return Path(recap_folder.read_text().strip()).expanduser().parent / "Night shift"
    return None


def load_config() -> Config:
    if not CONFIG_FILE.is_file():
        setup_error(f"{CONFIG_FILE} is missing. Copy config.example.toml from the night-shift skill and fill it in.")
    raw = tomllib.loads(CONFIG_FILE.read_text())
    site, project = _jira_from_browse_file()
    site = raw.get("jira_site", site).rstrip("/")
    project = raw.get("jira_project", project)
    if not site or not project:
        setup_error("Set jira_site and jira_project in config.toml (or keep ~/.config/dotfiles/jira, as the recap does).")
    vault = Path(raw["vault_folder"]).expanduser() if "vault_folder" in raw else _default_vault_folder()
    if vault is None:
        setup_error("Set vault_folder in config.toml.")
    if not any((parent / ".obsidian").is_dir() for parent in vault.parents):
        setup_error(f"{vault} is not inside an Obsidian vault (no .obsidian/ folder above it).")
    repos = {}
    for name, entry in (raw.get("repos") or {}).items():
        path = Path(entry["path"]).expanduser()
        if not (path / ".git").exists():
            setup_error(f"repos.{name}.path {path} is not a git checkout.")
        repos[name] = Repo(
            name=name,
            path=path,
            setup=[list(command) for command in entry.get("setup", [])],
            verify=[item if isinstance(item, dict) else {"command": list(item)} for item in entry.get("verify", [])],
            security_areas=list(entry.get("security_areas", [])),
        )
    if not repos:
        setup_error("config.toml has no [repos.<name>] table.")
    channels = raw.get("slack_channels")
    if channels is None and (RECAP_CONFIG_DIR / "channel").is_file():
        channels = [(RECAP_CONFIG_DIR / "channel").read_text().strip()]
    return Config(
        jira_site=site,
        jira_project=project,
        vault_folder=vault,
        repos=repos,
        people=list(raw.get("people") or []),
        slack_channels=list(channels or []),
        jira_board_id=int(raw["jira_board_id"]) if "jira_board_id" in raw else None,
        jira_board_column_status=str(raw.get("jira_board_column_status", "")),
        env_allowed_hosts=[str(pattern) for pattern in raw.get("env_allowed_hosts", [])],
        env_forbidden_hosts=[str(pattern) for pattern in raw.get("env_forbidden_hosts", [])],
        aws_allowed_accounts=[str(account) for account in raw.get("aws_allowed_accounts", [])],
        security_rotation=[str(name) for name in raw.get("security_rotation", []) if name in repos],
        commit_prefix=str(raw.get("commit_prefix", "{key}:")),
        no_story_prefix=str(raw.get("no_story_prefix", "")),
        own_status=str(raw.get("own_status", "")),
        pair_field=str(raw.get("pair_field", "")),
        tactical_label=str(raw.get("tactical_label", "")),
        pairing_handle=str(raw.get("pairing_handle", "")),
    )


WORKDAY_START_HOUR = 8


def workdays_between(start: float, end: float) -> int:
    """Workday starts (08:00, Monday to Friday) between two moments: the day work that happened between them."""
    count = 0
    day = datetime.fromtimestamp(start).date()
    while True:
        moment = datetime.combine(day, datetime.min.time()).replace(hour=WORKDAY_START_HOUR)
        if moment.timestamp() > end:
            return count
        if moment.timestamp() > start and day.weekday() < 5:
            count += 1
        day += timedelta(days=1)


def at_time(hhmm: str, *, base: datetime) -> datetime:
    """`hhmm` on the night `base` belongs to: a time before noon falls on the morning after an evening start."""
    hour, minute = (int(part) for part in hhmm.split(":"))
    moment = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if base.hour >= 12 and hour < 12:
        moment += timedelta(days=1)
    return moment


@contextmanager
def run_lock(kind: str) -> Iterator[None]:
    """One night-shift process at a time: nightly, security and manual runs share quota and state.

    flock releases the lock when the process dies, so a crashed run never leaves a stale lock behind.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    handle = LOCK_FILE.open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.seek(0)
        setup_error(f"another night-shift run holds {LOCK_FILE}: {handle.read().strip()}")
    handle.seek(0)
    handle.truncate()
    handle.write(f"{kind} pid {os.getpid()} since {datetime.now():%Y-%m-%d %H:%M}\n")
    handle.flush()
    try:
        yield
    finally:
        fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()
