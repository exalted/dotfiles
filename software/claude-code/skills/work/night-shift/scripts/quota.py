"""The quota guard: a spend ledger with reservations, and the gate every Claude session passes first.

The user's rule is absolute: the night shift never leaves them without quota for day work. So the gate fails
closed. No usage snapshot, a stale one, or one without the 7-day window means no session, not a guess.
Costs are Claude Code's client-side list-price estimates; they are proportional to what a seat allowance
measures, not a bill, which is why the allowances are tuned against /usage rather than taken as exact.

Every change to the ledger is one locked transaction: the running job's reservations and the user's
/night-shift commands may happen at the same moment.
"""

import fcntl
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator

from common import LEDGER_FILE, USAGE_SNAPSHOT, Json, read_json, write_json

WEEK = 7 * 24 * 3600
LEDGER_LOCK = LEDGER_FILE.with_name("ledger.lock")


def _load() -> Json:
    ledger = read_json(LEDGER_FILE, None) or {}
    ledger.setdefault("sessions", [])
    ledger.setdefault("issues", {})
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
        write_json(LEDGER_FILE, ledger)


def load_ledger() -> Json:
    """A read-only copy; change the ledger only inside transaction()."""
    return _load()


def charged(entry: Json) -> float:
    """A settled session costs what it reported; an open or crashed one costs its whole reservation."""
    return entry["cost"] if entry.get("cost") is not None else entry["reserved"]


def spend_since(ledger: Json, since: float, *, engine: str = "claude") -> float:
    return sum(charged(entry) for entry in ledger["sessions"] if entry["at"] >= since and entry.get("engine", "claude") == engine)


def night_start(morning: datetime) -> float:
    """23:00 the evening before: every run of one night shares that night's allowance, restarts included,
    while daytime and evening work (tests, a manual dry run) stays out of it. The weekly allowance counts both."""
    return (morning - timedelta(hours=9)).timestamp()


def reserve(*, kind: str, cap: float, run: str, key: str | None, engine: str = "claude") -> str:
    entry_id = uuid.uuid4().hex[:12]
    with transaction() as ledger:
        ledger["sessions"].append(
            {"id": entry_id, "run": run, "kind": kind, "key": key, "engine": engine, "reserved": cap, "cost": None, "at": time.time()}
        )
    return entry_id


def settle(entry_id: str, cost: float | None, status: str) -> None:
    """Record what a session cost. A session that returned no figure keeps its reservation as its cost."""
    with transaction() as ledger:
        for entry in ledger["sessions"]:
            if entry["id"] == entry_id:
                if cost is not None:
                    entry["cost"] = cost
                entry["status"] = status


@dataclass(frozen=True)
class Verdict:
    allowed: bool
    reason: str
    seven_day_percent: float | None = None
    five_hour_percent: float | None = None


def snapshot() -> Json | None:
    data = read_json(USAGE_SNAPSHOT, None)
    return data if isinstance(data, dict) and isinstance(data.get("rate_limits"), dict) else None


def check(*, cap: float, knobs: Json, morning: datetime, since: float | None = None, allowance: float | None = None, max_age_hours: float | None = None) -> Verdict:
    """May a session with this cost cap start now? Every rule must pass; the first failure is the reason.

    A night run counts its spend from the night's start against night_allowance_usd. The weekend security
    run passes its own start, allowance and snapshot age: no day session refreshes the snapshot on a weekend,
    and the weekly allowance still binds it.
    """
    if knobs.get("paused"):
        return Verdict(False, "the night shift is paused (/night-shift resume)")
    data = snapshot()
    if data is None:
        return Verdict(False, f"no usage snapshot at {USAGE_SNAPSHOT}; open one interactive session today so the status line writes it")
    age_hours = (time.time() - float(data.get("at", 0))) / 3600
    max_age = float(max_age_hours if max_age_hours is not None else knobs["snapshot_max_age_hours"])
    if age_hours > max_age:
        return Verdict(False, f"usage snapshot is {age_hours:.0f} h old (limit {max_age:.0f} h)")
    limits = data["rate_limits"]
    seven_day = limits.get("seven_day") or {}
    if "used_percentage" not in seven_day:
        return Verdict(False, "usage snapshot has no 7-day window")
    seven = float(seven_day["used_percentage"])
    if seven > float(knobs["seven_day_max_percent"]):
        return Verdict(False, f"7-day usage {seven:.0f}% is over {knobs['seven_day_max_percent']}%", seven)
    five = None
    five_hour = limits.get("five_hour") or {}
    if "used_percentage" in five_hour:
        five = float(five_hour["used_percentage"])
        resets = float(five_hour.get("resets_at") or 0)
        if resets > morning.timestamp() and five > 50:
            return Verdict(False, f"5-hour window at {five:.0f}% stays open until {datetime.fromtimestamp(resets):%H:%M}", seven, five)
    ledger = load_ledger()
    week = spend_since(ledger, time.time() - WEEK)
    if week + cap > float(knobs["weekly_allowance_usd"]):
        return Verdict(False, f"7-day estimated spend ${week:.2f} + this session's cap ${cap:.2f} exceeds ${knobs['weekly_allowance_usd']}", seven, five)
    night = spend_since(ledger, since if since is not None else night_start(morning))
    limit = float(allowance if allowance is not None else knobs["night_allowance_usd"])
    if night + cap > limit:
        return Verdict(False, f"this run's estimated spend ${night:.2f} + cap ${cap:.2f} exceeds ${limit:.0f}", seven, five)
    return Verdict(True, "ok", seven, five)


def morning_after(start: datetime) -> datetime:
    """08:00 on the morning a night run belongs to: day work starts about then."""
    day = start.date() + (timedelta(days=1) if start.hour >= 12 else timedelta(0))
    return datetime.combine(day, datetime.min.time()).replace(hour=8)


def describe(knobs: Json, morning: datetime, since: float | None = None) -> str:
    ledger = load_ledger()
    data = snapshot()
    parts = []
    if data:
        limits = data["rate_limits"]
        seven = (limits.get("seven_day") or {}).get("used_percentage")
        five = (limits.get("five_hour") or {}).get("used_percentage")
        age = (time.time() - float(data.get("at", 0))) / 3600
        parts.append(f"usage snapshot {age:.1f} h old: 7-day {seven}%, 5-hour {five}%")
    else:
        parts.append("no usage snapshot")
    parts.append(f"7-day estimated spend ${spend_since(ledger, time.time() - WEEK):.2f} of ${knobs['weekly_allowance_usd']}")
    label = "this run" if since is not None else "this night"
    parts.append(f"{label} ${spend_since(ledger, since if since is not None else night_start(morning)):.2f} of ${knobs['night_allowance_usd']}")
    return "; ".join(parts)
