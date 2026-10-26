"""Start Claude Code sessions for the night shift: gate, reserve, run, settle, and retry at a usage limit.

Every session runs headless with `--permission-prompts none`, so nothing ever waits for a person, and with
the user's own configuration (CLAUDE.md, settings, hooks, skills, plugins). The night rules come on top
through `--settings`. `autoContinueAtUsageLimit` is false there: this module decides whether to wait.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import quota
import supervise
from common import Json, log

LIMIT = re.compile(r"hit your (\w+) limit(?:\s*[·\-–]\s*resets\s+([0-9A-Za-z: ]+?(?:am|pm)))?", re.IGNORECASE)
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
# The shortest useful continuation after a reset; less than this before the deadline is not worth the wait.
MIN_CONTINUATION = timedelta(minutes=15)
# A run outside the night (a manual daytime run) sets its own points budget here, counted from its own start, so
# it neither takes the next night's points nor is blocked by the last one's. Its sessions mix with the user's own
# day work, so they teach the ledger nothing about what a session costs.
RUN_GATE: Json = {}
RESUME_PROMPT = (
    "Continue the task exactly where you stopped. The interruption was a usage limit, which has reset now. "
    "Re-read your progress file and result file first."
)


@dataclass
class Spec:
    kind: str
    prompt: str
    cwd: Path
    run_id: str
    log_dir: Path
    model: str
    effort: str
    cap_usd: float
    minutes: float
    key: str | None = None
    permission_mode: str = "auto"
    settings: Path | None = None
    add_dirs: list[Path] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    max_turns: int = 300
    fallback_models: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    json_schema: Json | None = None
    append_system_prompt: str | None = None
    # How many usage-limit resets this session may wait out. One for a night story; the weekend security run more.
    max_waits: int = 1
    # Overrides for quota.check (since, points), for a run with its own budget.
    gate: Json = field(default_factory=dict)
    # Continue an earlier session (its id) with this prompt instead of starting a new one; its cost so far.
    resume_from: str | None = None
    cost_before: float = 0.0
    # The display name /rename would set, so the user finds the session in `claude --resume`.
    name: str | None = None


@dataclass
class Result:
    status: str
    reason: str = ""
    data: Json = field(default_factory=dict)
    cost: float = 0.0
    session_id: str = ""
    stderr_tail: str = ""
    points: float | None = None


def _command(spec: Spec, *, session_id: str, model: str, resume: bool, prompt: str) -> list[str]:
    command = ["claude", "-p", prompt, "--model", model, "--effort", spec.effort]
    command += ["--permission-mode", spec.permission_mode, "--permission-prompts", "none", "--output-format", "json"]
    command += ["--max-turns", str(spec.max_turns), "--max-budget-usd", f"{spec.cap_usd:.2f}"]
    command += ["--resume", session_id] if resume else ["--session-id", session_id]
    if spec.settings:
        command += ["--settings", str(spec.settings)]
    for directory in spec.add_dirs:
        command += ["--add-dir", str(directory)]
    if spec.allowed_tools:
        command += ["--allowedTools", ",".join(spec.allowed_tools)]
    if spec.fallback_models:
        command += ["--fallback-model", ",".join(spec.fallback_models)]
    if spec.json_schema:
        command += ["--json-schema", json.dumps(spec.json_schema)]
    if spec.append_system_prompt:
        command += ["--append-system-prompt", spec.append_system_prompt]
    if spec.name:
        command += ["--name", spec.name]
    return command


def _result_json(stdout: str) -> Json:
    for line in reversed(stdout.strip().splitlines()):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def parse_reset(text: str, now: datetime) -> datetime | None:
    """`3:45pm` is the next such time from now; `Mon 12:00am` the next such weekday and time."""
    text = text.strip().lower()
    weekday = None
    if text[:3] in WEEKDAYS:
        weekday, text = WEEKDAYS.index(text[:3]), text[3:].strip()
    match = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)
    if not match:
        return None
    hour = int(match.group(1)) % 12 + (12 if match.group(3) == "pm" else 0)
    moment = now.replace(hour=hour, minute=int(match.group(2) or 0), second=0, microsecond=0)
    if weekday is not None:
        moment += timedelta(days=(weekday - now.weekday()) % 7)
    if moment <= now:
        moment += timedelta(days=7 if weekday is not None else 1)
    return moment


def run(spec: Spec, *, knobs: Json, deadline: datetime, morning: datetime) -> Result:
    session_id = spec.resume_from or str(uuid.uuid4())
    model = spec.model
    fallbacks = list(spec.fallback_models)
    resume = spec.resume_from is not None
    prompt = spec.prompt
    total_before = spec.cost_before
    total_cost = 0.0
    total_points: float | None = None
    waits = 0
    attempt = 0
    while True:
        remaining = (deadline - datetime.now()).total_seconds()
        if remaining < 120:
            return Result("deadline", "no time left before the run's deadline", cost=total_cost, session_id=session_id, points=total_points)
        verdict = quota.check(kind=spec.kind, knobs=knobs, morning=morning, **(spec.gate or RUN_GATE))
        if not verdict.allowed:
            return Result("gated", verdict.reason, cost=total_cost, session_id=session_id, points=total_points)
        entry = quota.reserve(kind=spec.kind, cap=spec.cap_usd, run=spec.run_id, key=spec.key, start=verdict.usage, learn=not RUN_GATE)
        seconds = min(spec.minutes * 60, remaining)
        log(f"{spec.kind}{' ' + spec.key if spec.key else ''}: {model} {spec.effort}, 7-day {verdict.usage.seven:.0f}% of {verdict.ceiling.percent:.0f}%, {seconds / 60:.0f} min{' (resume)' if resume else ''}")
        outcome = supervise.run(
            _command(spec, session_id=session_id, model=model, resume=resume, prompt=prompt),
            cwd=spec.cwd,
            seconds=seconds,
            env={
                "ENABLE_CLAUDEAI_MCP_SERVERS": "false",
                "CLAUDE_CODE_MCP_STARTUP_WAIT_MS": "60000",
                "CLAUDE_CODE_RETRY_WATCHDOG": "1",
                "CLAUDE_TODO_HOOKS": "0",
                "NIGHT_SHIFT_DEADLINE": str(int(time.time() + seconds)),
                **spec.env,
            },
            log_dir=spec.log_dir,
            name=f"{spec.kind}-{attempt}",
            watch=lambda: quota.over_ceiling(knobs, morning),
        )
        attempt += 1
        if run_dir := spec.env.get("NIGHT_SHIFT_RUN_DIR"):
            supervise.reap_codex(Path(run_dir))
        data = _result_json(outcome.stdout)
        # On --resume the figure is the whole conversation's total, earlier attempts included.
        reported = data.get("total_cost_usd")
        cost = None if reported is None else max(float(reported) - total_before, 0.0)
        if reported is not None:
            total_before = float(reported)
        total_cost += cost if cost is not None else spec.cap_usd
        limit = LIMIT.search("\n".join([outcome.stderr, str(data.get("result", ""))]))
        status = "gated" if outcome.stopped else "timeout" if outcome.timed_out else "usage_limit" if limit else "error" if data.get("is_error") or not data else "ok"
        points = quota.settle(entry, cost, status)
        if points is not None:
            total_points = (total_points or 0.0) + points
        tail = outcome.stderr[-1500:]
        if status != "usage_limit":
            reason = outcome.stopped or (data.get("subtype", "") if status == "error" else "")
            return Result(status, reason, data, total_cost, session_id, tail, total_points)
        which, reset_text = limit.group(1).lower(), limit.group(2) or ""
        if which == "weekly":
            return Result("usage_limit_weekly", f"weekly limit hit ({reset_text or 'no reset time'})", data, total_cost, session_id, tail, total_points)
        if which != "session":
            # A model-family limit: another family keeps working.
            if not fallbacks:
                return Result("usage_limit", f"{which} limit hit", data, total_cost, session_id, tail, total_points)
            model = fallbacks.pop(0)
            resume, prompt = True, RESUME_PROMPT
            continue
        reset = parse_reset(reset_text, datetime.now()) if reset_text else None
        if reset is None or waits >= spec.max_waits or reset + timedelta(minutes=1) + MIN_CONTINUATION > deadline:
            return Result("usage_limit", f"session limit hit, resets {reset_text or 'unknown'}: no safe retry before the deadline", data, total_cost, session_id, tail, total_points)
        waits += 1
        wait = (reset + timedelta(minutes=1) - datetime.now()).total_seconds()
        log(f"session limit: waiting {wait / 60:.0f} min for the reset at {reset:%H:%M} (wait {waits} of {spec.max_waits}), then resuming")
        time.sleep(max(wait, 0))
        resume, prompt = True, RESUME_PROMPT
