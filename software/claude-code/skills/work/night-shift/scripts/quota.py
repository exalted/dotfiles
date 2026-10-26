"""The quota guard: live 7-day usage in percent, a ceiling that keeps quota for the workdays left, and the
gate every Claude session passes first.

The user's rule is absolute: the night shift never leaves them without quota for day work. The plan is
measured in percent of a weekly window, so every limit here is in percent too. The gate fails closed: no
usage reading means no session, not a guess. A tiny headless probe reads the live figures (the stream's
rate_limit_event), so the gate no longer depends on the status line having run recently.

Every change to the ledger is one locked transaction: the running job's sessions and the user's
/night-shift commands may happen at the same moment.
"""

import fcntl
import json
import os
import statistics
import subprocess
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterator

from common import LEDGER_FILE, STATE_DIR, USAGE_SNAPSHOT, WORKDAY_START_HOUR, Json, read_json, workdays_between, write_json

WEEK = 7 * 24 * 3600
LEDGER_LOCK = LEDGER_FILE.with_name("ledger.lock")
PROBE_FILE = STATE_DIR / "usage.json"
# A reading this fresh is good enough for a gate; the watchdog asks for a fresh one.
READING_MAX_AGE = 300
# What a session of each kind adds to the 7-day usage, in points, until the ledger has measured enough of them.
# Upper bounds from the first nights: the most each kind cost in dollars, at the most points a dollar can have
# been (all of that week's usage counted as night work).
DEFAULT_POINTS = {"pick": 1.6, "recheck": 0.1, "work": 6.6, "fix": 0.8, "report": 0.5, "scan": 6.0, "patch": 2.0}
# The sessions of one story. A story starts only when all of them fit in the night's points; once started, they
# may finish it above the night's points, never above the ceiling.
STORY_KINDS = ("recheck", "work", "fix")
MIN_SAMPLES = 3


def _load() -> Json:
    ledger = read_json(LEDGER_FILE, None) or {}
    ledger.setdefault("sessions", [])
    ledger.setdefault("issues", {})
    ledger.setdefault("readings", [])
    ledger.setdefault("security", {"findings": {}, "last_repo": None, "area_index": {}})
    return ledger


@contextmanager
def transaction() -> Iterator[Json]:
    """Read, change and write the ledger under one lock; the change is saved when the block ends."""
    LEDGER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER_LOCK.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = _load()
        yield ledger
        cutoff = time.time() - 5 * WEEK
        ledger["sessions"] = [entry for entry in ledger["sessions"] if entry["at"] >= cutoff]
        ledger["readings"] = [entry for entry in ledger["readings"] if entry["at"] >= cutoff]
        write_json(LEDGER_FILE, ledger)


def load_ledger() -> Json:
    """A read-only copy; change the ledger only inside transaction()."""
    return _load()


# ---------- usage readings ----------

@dataclass(frozen=True)
class Usage:
    at: float
    seven: float
    seven_resets: float
    five: float | None
    five_resets: float | None
    source: str


def _from_snapshot() -> Usage | None:
    data = read_json(USAGE_SNAPSHOT, None)
    if not isinstance(data, dict) or not isinstance(data.get("rate_limits"), dict):
        return None
    seven = data["rate_limits"].get("seven_day") or {}
    five = data["rate_limits"].get("five_hour") or {}
    if "used_percentage" not in seven:
        return None
    return Usage(float(data.get("at", 0)), float(seven["used_percentage"]), float(seven.get("resets_at") or 0),
                 float(five["used_percentage"]) if "used_percentage" in five else None, float(five.get("resets_at") or 0) or None, "status line")


def _from_probe_file() -> Usage | None:
    data = read_json(PROBE_FILE, None)
    return Usage(**data) if isinstance(data, dict) else None


def probe() -> Usage | None:
    """One tiny headless turn whose stream carries the account's live rate-limit windows."""
    command = ["claude", "-p", "Reply with OK.", "--model", "haiku", "--output-format", "stream-json", "--verbose",
               "--max-turns", "1", "--max-budget-usd", "0.05", "--strict-mcp-config", "--permission-mode", "dontAsk"]
    env = {"CLAUDE_TODO_HOOKS": "0", "ENABLE_CLAUDEAI_MCP_SERVERS": "false"}
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        output = subprocess.run(command, cwd=STATE_DIR, env={**os.environ, **env}, capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "rate_limit_event":
            continue
        windows = (event.get("rate_limit_info") or {}).get("unifiedWindows") or {}
        seven, five = windows.get("seven_day"), windows.get("five_hour") or {}
        if not seven or "utilization" not in seven:
            return None
        usage = Usage(time.time(), round(float(seven["utilization"]) * 100, 1), float(seven.get("resetsAt") or 0),
                      round(float(five["utilization"]) * 100, 1) if "utilization" in five else None, float(five.get("resetsAt") or 0) or None, "probe")
        write_json(PROBE_FILE, usage.__dict__)
        return usage
    return None


def current(*, max_age: float = READING_MAX_AGE, label: str | None = None) -> Usage | None:
    """The newest reading no older than max_age, probing when there is none. Labeled readings go to the ledger."""
    known = [usage for usage in (_from_snapshot(), _from_probe_file()) if usage]
    newest = max(known, key=lambda usage: usage.at) if known else None
    if newest is None or time.time() - newest.at > max_age:
        newest = probe()
    if newest and label:
        with transaction() as ledger:
            ledger["readings"].append({"at": time.time(), "seven": newest.seven, "resets": newest.seven_resets, "label": label})
    return newest


# ---------- sessions ----------

def reserve(*, kind: str, cap: float, run: str, key: str | None, engine: str = "claude", start: Usage | None = None, learn: bool = True) -> str:
    entry_id = uuid.uuid4().hex[:12]
    with transaction() as ledger:
        ledger["sessions"].append({
            "id": entry_id, "run": run, "kind": kind, "key": key, "engine": engine, "cap_usd": cap, "cost": None, "at": time.time(),
            "start_seven": start.seven if start else None, "start_resets": start.seven_resets if start else None, "learn": learn,
        })
    return entry_id


def settle(entry_id: str, cost: float | None, status: str) -> float | None:
    """Record what a session cost, in dollars as reported and in points of the 7-day window as measured."""
    with transaction() as ledger:
        entry = next((entry for entry in ledger["sessions"] if entry["id"] == entry_id), None)
    if entry is None:
        return None
    points = None
    if entry.get("start_seven") is not None:
        end = current(max_age=0)
        if end and end.seven_resets == entry.get("start_resets"):
            points = round(max(end.seven - entry["start_seven"], 0.0), 1)
    with transaction() as ledger:
        for item in ledger["sessions"]:
            if item["id"] == entry_id:
                item["cost"] = cost
                item["status"] = status
                item["points"] = points
    return points


def estimate(kind: str, ledger: Json | None = None) -> float:
    """What a session of this kind usually adds: the 75th percentile of measured ones, or a default. A "story" is
    all of a story's sessions."""
    ledger = ledger or load_ledger()
    if kind == "story":
        return round(sum(estimate(part, ledger) for part in STORY_KINDS), 1)
    measured = [entry["points"] for entry in ledger["sessions"] if entry.get("kind") == kind and entry.get("learn", True) and entry.get("points") is not None]
    if len(measured) < MIN_SAMPLES:
        return DEFAULT_POINTS.get(kind, 2.0)
    return round(statistics.quantiles(measured, n=4)[-1] if len(measured) > 1 else measured[0], 1)


# ---------- the ceiling ----------

def workdays_before(reset: datetime, morning: datetime) -> list[date]:
    """The workdays from this morning on whose start comes before the weekly window resets."""
    days = []
    day = morning.date()
    while datetime.combine(day, datetime.min.time()).replace(hour=WORKDAY_START_HOUR) < reset:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return days


def day_use(ledger: Json) -> float | None:
    """A typical workday's use, learned: the rise between one night's end and the next night's start, per workday."""
    readings = sorted(ledger["readings"], key=lambda entry: entry["at"])
    samples = []
    for index, start in enumerate(readings):
        if start.get("label") != "night_start":
            continue
        ends = [entry for entry in readings[:index] if entry.get("label") == "night_end"]
        if not ends or ends[-1]["resets"] != start["resets"]:
            continue
        days = workdays_between(ends[-1]["at"], start["at"])
        if days:
            samples.append(max(start["seven"] - ends[-1]["seven"], 0.0) / days)
    samples = samples[-10:]
    if len(samples) < MIN_SAMPLES:
        return None
    return round(statistics.quantiles(samples, n=5)[-1], 1)


@dataclass(frozen=True)
class Ceiling:
    percent: float
    reserve: float
    workdays: int
    reset: datetime

    def explain(self) -> str:
        if not self.workdays:
            return f"ceiling {self.percent:.0f}%: the weekly window resets {self.reset:%a %H:%M}, before day work"
        return f"ceiling {self.percent:.0f}%: {self.reserve:.0f}% kept for each of {self.workdays} workday(s) before the reset {self.reset:%a %H:%M}"


def ceiling(usage: Usage, knobs: Json, morning: datetime, ledger: Json | None = None) -> Ceiling:
    ledger = ledger or load_ledger()
    reserve = max(float(knobs["day_reserve_percent"]), day_use(ledger) or 0.0)
    reset = datetime.fromtimestamp(usage.seven_resets) if usage.seven_resets else morning + timedelta(days=7)
    days = len(workdays_before(reset, morning))
    top = float(knobs["seven_day_ceiling_percent"])
    return Ceiling(max(min(top, 100.0 - reserve * days), 0.0), reserve, days, reset)


def baseline(since: float, usage: Usage, ledger: Json) -> float:
    """The 7-day usage when this night (or run) began; zero when the weekly window reset since then."""
    earlier = [entry for entry in ledger["readings"] if entry["at"] >= since and entry.get("label") in ("night_start", "run_start")]
    if not earlier:
        return usage.seven
    first = min(earlier, key=lambda entry: entry["at"])
    return first["seven"] if first["resets"] == usage.seven_resets else 0.0


def night_start(morning: datetime) -> float:
    """23:00 the evening before: every run of one night shares that night's points, restarts included."""
    return (morning - timedelta(hours=9)).timestamp()


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str
    usage: Usage | None = None
    ceiling: Ceiling | None = None

    @property
    def seven_day_percent(self) -> float | None:
        return self.usage.seven if self.usage else None


def check(*, kind: str, knobs: Json, morning: datetime, since: float | None = None, points: float | None = None, started_story: bool = False) -> Verdict:
    """May a session of this kind start now? Every rule must pass; the first failure is the reason.

    A night run counts its points from the night's start against night_points; a run with its own budget (a
    manual run, the security run) passes its own start and points. A session of a story already started skips
    the points rule: its story was admitted with room for all its sessions, and half a story helps nobody.
    """
    if knobs.get("paused"):
        return Verdict(False, "the night shift is paused (/night-shift resume)")
    usage = current()
    if usage is None:
        return Verdict(False, "could not read your 7-day usage (the headless probe failed); the gate stays closed")
    ledger = load_ledger()
    limit = ceiling(usage, knobs, morning, ledger)
    expected = estimate(kind, ledger)
    if usage.seven + expected > limit.percent:
        return Verdict(False, f"7-day usage {usage.seven:.0f}% + about {expected:g} for this {kind} would pass the {limit.explain()}", usage, limit)
    if usage.five is not None and usage.five_resets and usage.five_resets > morning.timestamp() and usage.five > 50:
        return Verdict(False, f"5-hour window at {usage.five:.0f}% stays open until {datetime.fromtimestamp(usage.five_resets):%H:%M}", usage, limit)
    if started_story:
        return Verdict(True, "ok", usage, limit)
    budget = float(points if points is not None else knobs["night_points"])
    used = usage.seven - baseline(since if since is not None else night_start(morning), usage, ledger)
    if used + expected > budget:
        return Verdict(False, f"this run used {used:.1f} of its {budget:g} points; a {kind} needs about {expected:g} more", usage, limit)
    return Verdict(True, "ok", usage, limit)


def over_ceiling(knobs: Json, morning: datetime) -> str | None:
    """For the watchdog of a running session: a reason to stop it, or None. Only the ceiling is hard."""
    usage = current(max_age=0)
    if usage is None:
        return None
    limit = ceiling(usage, knobs, morning)
    return f"7-day usage reached {usage.seven:.0f}%, the {limit.explain()}" if usage.seven >= limit.percent else None


def morning_after(start: datetime) -> datetime:
    """08:00 on the morning a night run belongs to: day work starts about then."""
    day = start.date() + (timedelta(days=1) if start.hour >= 12 else timedelta(0))
    return datetime.combine(day, datetime.min.time()).replace(hour=WORKDAY_START_HOUR)


def describe(knobs: Json, morning: datetime, since: float | None = None, points: float | None = None) -> str:
    usage = current()
    if usage is None:
        return "7-day usage unknown (the probe failed)"
    ledger = load_ledger()
    limit = ceiling(usage, knobs, morning, ledger)
    used = usage.seven - baseline(since if since is not None else night_start(morning), usage, ledger)
    budget = points if points is not None else knobs["night_points"]
    five = f", 5-hour {usage.five:.0f}%" if usage.five is not None else ""
    return f"7-day usage {usage.seven:.0f}%{five}; {limit.explain()}; {'this run' if since is not None else 'this night'} used {used:.1f} of {budget:g} points"
