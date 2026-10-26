#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""The night shift: work top backlog stories unattended at night, and govern it by day.

  night_shift.py nightly [--now] [--dry]     the nightly run (the launch agent starts it; --now for a manual run)
  night_shift.py security [--now]            the weekly deep security analysis (off until `set security true`)
  night_shift.py status                      knobs, quota, last runs, story branches
  night_shift.py pause | resume
  night_shift.py set <knob> <value>          e.g. set stories 2, set night_points 15, set codex false
  night_shift.py skip <KEY>                  never take this story
  night_shift.py reject <KEY> ["reason"]     you will not merge its branch: never retried, branch kept as night-archive/...
  night_shift.py retry <KEY> ["feedback"]    take it again; the feedback goes into the next attempt's brief
  night_shift.py merged <KEY>                you merged it (also detected by itself once main holds the branch)
  night_shift.py cleanup <KEY> [--force]     after review: the story's branch removed once main has it
  night_shift.py run-now [--dry]             start the nightly run through the launch agent now
  night_shift.py check-repos                 the morning check: fetch every checkout, alert if a sync is needed
  night_shift.py fail "<message>"            the wrapper's last resort: write a failure note

Hard rules the code enforces, not the prompts: the quota guard (quota.py) before every Claude session,
one run at a time (run_lock), a deadline on every child process (supervise.py), nothing pushed, nothing
written to Jira, nothing deleted.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import alert
import note
import quota
import sessions
import supervise
import workspace
from common import (
    CODEX_EXEC,
    DEFAULT_KNOBS,
    RUN_NOW_FILE,
    RUNS_DIR,
    SECURITY_REQUEST_FILE,
    STATE_DIR,
    Config,
    Json,
    at_time,
    knobs,
    load_config,
    log,
    read_json,
    run_lock,
    save_knobs,
    valid_key,
    write_json,
)

SKILLS = Path.home() / ".claude" / "skills"
WORK_SETTINGS = SKILLS / "night-shift-work" / "settings.json"
SECURITY_SETTINGS = SKILLS / "night-shift-work" / "settings-security.json"
UV = "uv run --quiet --no-project --script"
SCRIPTS = "~/.claude/skills/night-shift/scripts"
LAUNCH_LABEL = "com.dotfiles.night-shift"
FINAL = {"solved", "partial", "abandoned"}
FRESH_POLL_SECONDS = 300
# Session outcomes after which no further Claude session may start tonight.
STOP_NIGHT = {"usage_limit", "usage_limit_weekly", "gated", "deadline"}
RETRY_AFTER_DAYS = 7
CODEX_RECHECK_SECONDS = 600
MAX_DIFF_CHARS = 150_000

PICK_TOOLS = [
    "Skill", "ToolSearch", "Read", "Glob", "Grep",
    f"Bash({UV} {SCRIPTS}/attachment.py *)",
    f"Bash({UV} {SCRIPTS}/night_shift.py validate-plan *)",
    "Bash(command git -C * log *)", "Bash(command git -C * show *)", "Bash(command git -C * ls-files *)", "Bash(command git -C * grep *)",
    "Bash(command git -C * branch *)", "Bash(command git -C * for-each-ref *)", "Bash(command git -C * cat-file *)",
    "Bash(command git -C * rev-parse *)", "Bash(command ls *)",
    "mcp__plugin_atlassian_atlassian__getAccessibleAtlassianResources",
    "mcp__plugin_atlassian_atlassian__searchJiraIssuesUsingJql",
    "mcp__plugin_atlassian_atlassian__getJiraIssue",
    "mcp__plugin_atlassian_atlassian__searchConfluence",
    "mcp__plugin_atlassian_atlassian__getConfluenceContent",
    "mcp__plugin_atlassian_atlassian__search",
    "mcp__plugin_atlassian_atlassian__discover",
    "mcp__plugin_atlassian_atlassian__executeRead",
    "mcp__plugin_slack_slack__slack_search_public",
    "mcp__plugin_slack_slack__slack_search_public_and_private",
    "mcp__plugin_slack_slack__slack_read_channel",
    "mcp__plugin_slack_slack__slack_read_thread",
    "mcp__plugin_slack_slack__slack_read_file",
    "mcp__plugin_gitlab_gitlab__get_commit",
    "mcp__plugin_gitlab_gitlab__search",
]

OPINION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["workable", "primary_repo", "risk", "reason"],
    "properties": {
        "workable": {"type": "boolean"},
        "primary_repo": {"type": "string"},
        "risk": {"type": "string", "enum": ["low", "medium", "high"]},
        "reason": {"type": "string"},
    },
}
REVIEW_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "summary", "tests_weakened", "unneeded_changes", "findings"],
    "properties": {
        "verdict": {"type": "string", "enum": ["approve", "approve_with_nits", "request_changes"]},
        "summary": {"type": "string"},
        "tests_weakened": {"type": "boolean"},
        "unneeded_changes": {"type": "array", "items": {"type": "string"}},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["severity", "file", "issue", "suggestion"],
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "file": {"type": "string"},
                    "issue": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
            },
        },
    },
}
CHALLENGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["closes_finding", "could_break", "reviewer_checks", "summary"],
    "properties": {
        "closes_finding": {"type": "boolean"},
        "could_break": {"type": "array", "items": {"type": "string"}},
        "reviewer_checks": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
    },
}


# ---------- codex ----------

class Codex:
    """Codex as a second harness on its own quota: opinions, reviews, challenges, and fallback implementation."""

    def __init__(self, enabled: bool, log_dir: Path, deadline: datetime):
        self.enabled = enabled
        self.deadline = deadline
        self.log_dir = log_dir
        self.checked_at = 0.0
        self.available = enabled
        self.note = ""
        if enabled:
            doctor = self._call(["doctor"], timeout=180)
            if not doctor.get("ok"):
                self.available = False
                self.note = f"codex is off tonight: its CLI no longer matches the recipe ({doctor}). Run the codex-servant refresh."
            elif doctor.get("substitutes"):
                self.note = f"codex models substituted: {doctor['substitutes']}"

    def _call(self, args: list[str], timeout: float) -> Json:
        outcome = supervise.run(
            ["uv", "run", "--quiet", "--no-project", "--script", str(CODEX_EXEC), *args],
            cwd=Path.home(), seconds=max(timeout, 30), log_dir=self.log_dir, name=f"codex-call-{time.time_ns()}",
            env={"NIGHT_SHIFT_RUN_DIR": str(self.log_dir.parent)},
        )
        if outcome.timed_out:
            return {"status": "timeout"}
        try:
            return json.loads(outcome.stdout.strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return {"status": "error", "stderr_tail": outcome.stderr[-500:]}

    def ready(self) -> bool:
        """Is codex usable now? After a usage limit, check back at most every 10 minutes."""
        if not self.enabled:
            return False
        if self.available or time.time() - self.checked_at < CODEX_RECHECK_SECONDS:
            return self.available
        self.checked_at = time.time()
        self.available = self._call(["probe"], timeout=180).get("status") == "ok"
        return self.available

    def run(self, role: str, *, cd: Path, prompt: str, name: str, schema: Json | None = None, add_dirs: list[Path] = ()) -> Json:
        if not self.ready():
            return {"status": "unavailable"}
        self.log_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = self.log_dir / f"codex-{name}.prompt.md"
        prompt_file.write_text(prompt)
        out = self.log_dir / f"codex-{name}.md"
        args = ["run", "--role", role, "--cd", str(cd), "--prompt-file", str(prompt_file), "--out", str(out)]
        if schema:
            schema_file = self.log_dir / f"codex-{name}.schema.json"
            schema_file.write_text(json.dumps(schema))
            args += ["--schema", str(schema_file)]
        for directory in add_dirs:
            args += ["--add-dir", str(directory)]
        remaining = (self.deadline - datetime.now()).total_seconds()
        if remaining < 120:
            return {"status": "deadline"}
        result = self._call(args, timeout=remaining)
        if result.get("status") == "unavailable":
            self.available, self.checked_at = False, time.time()
        if result.get("status") == "ok" and out.exists():
            text = out.read_text()
            result["text"] = text
            if schema:
                try:
                    result["data"] = json.loads(text)
                except json.JSONDecodeError:
                    result["status"] = "error"
        return result


# ---------- helpers ----------

def browse_url(config: Config) -> str:
    return f"{config.jira_site}/browse/"


def session_settings(template: Path, *, target: Path, config: Config) -> Path:
    """The night rules, plus this machine's production boundaries from the untracked config.

    The session works like the user by day: no sandbox, auto mode's classifier reviews each action. What
    must never happen at night is named to the classifier as hard rules: production hosts and AWS accounts
    outside the allowed ones come from config.toml, so the public template stays generic.
    """
    settings = json.loads(template.read_text())
    hard = settings.setdefault("autoMode", {}).setdefault("hard_deny", ["$defaults"])
    if config.env_forbidden_hosts:
        hard.append("These hosts are production; never connect to them in any way: " + ", ".join(config.env_forbidden_hosts) + " (regular expressions).")
    if config.aws_allowed_accounts:
        hard.append("Use AWS only through profiles of these accounts, never any other account: " + ", ".join(config.aws_allowed_accounts) + ".")
    write_json(target, settings)
    return target


RECHECK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["workable", "reasons", "updated"],
    "properties": {"workable": {"type": "boolean"}, "reasons": {"type": "array", "items": {"type": "string"}}, "updated": {"type": "string"}},
}
RECHECK_TOOLS = ["ToolSearch", "mcp__plugin_atlassian_atlassian__getAccessibleAtlassianResources", "mcp__plugin_atlassian_atlassian__getJiraIssue"]


def jira_recheck(key: str, *, run_dir: Path, k: Json, deadline: datetime, morning: datetime) -> Json:
    """Right before work: is the story still unassigned, in the backlog, unflagged and not blocked by an open issue?

    A small haiku session reads it through the user's own Atlassian sign-in; no API token is involved.
    A check that does not finish is not a green light: the story is skipped, and a quota stop ends the night.
    """
    prompt = (
        f"Read Jira issue {key} with getJiraIssue (view evidence, so issue links are included). Answer: workable is false "
        "if it has an assignee, if its status category is not To Do, if it is flagged (Flagged or Impediment field), or if "
        "an 'is blocked by' link points to an issue that is not done; reasons lists each such finding in a few words; "
        "updated is the issue's updated timestamp. Read only; change nothing."
    )
    result = sessions.run(
        sessions.Spec(kind="recheck", key=key, prompt=prompt, cwd=run_dir, run_id=run_dir.name, log_dir=run_dir / "logs", model="haiku", effort="low",
                      cap_usd=0.5, minutes=5, permission_mode="dontAsk", allowed_tools=RECHECK_TOOLS, max_turns=8, json_schema=RECHECK_SCHEMA),
        knobs=k, deadline=deadline, morning=morning,
    )
    answer = result.data.get("structured_output") if result.status == "ok" else None
    if isinstance(answer, dict):
        return {**answer, "status": "ok"}
    return {"workable": False, "reasons": [f"the pre-work recheck did not finish ({result.status} {result.reason})".strip()], "status": result.status}


def progress(issue_dir: Path, text: str) -> None:
    with (issue_dir / "progress.md").open("a") as handle:
        handle.write(f"· {datetime.now():%H:%M} {text}\n")


def set_phase(issue_dir: Path, phase: str, **extra: object) -> None:
    current = read_json(issue_dir / "phase.json", {}) or {}
    write_json(issue_dir / "phase.json", {**current, "phase": phase, "at": time.time(), **extra})


def update_issue(key: str, **fields: object) -> None:
    with quota.transaction() as ledger:
        ledger["issues"][key] = {**ledger["issues"].get(key, {}), **fields, "date": datetime.now().isoformat(timespec="minutes")}


def sync_notes(config: Config) -> list[str]:
    """The user's word on a story note: archived (moved anywhere in the vault outside the night-shift folder) or
    deleted means the story is closed, ignored from now on, never picked again and never listed as waiting.
    Run notes carry no meaning. Notes are found by their id, so a rename or a move inside the folder changes nothing.

    The ledger records it, so the ledger never says what the vault contradicts. An archived note is the user's,
    not a source: nothing reads it after this.
    """
    closed = []
    notes = note.find_notes(note.vault_root(config.vault_folder))
    with quota.transaction() as ledger:
        for key, entry in ledger["issues"].items():
            if not entry.get("note_id") or entry.get("note_state") in ("archived", "deleted"):
                continue
            where = notes.get(entry["note_id"])
            if where and where.is_relative_to(config.vault_folder):
                entry["note"] = str(where.relative_to(config.vault_folder))
                continue
            state = "archived" if where else "deleted"
            entry.update(note_state=state, final=True, review=entry.get("review") if entry.get("review") in ("merged", "rejected") else "closed",
                         closed=datetime.now().isoformat(timespec="minutes"))
            closed.append(f"{key}: note {state}")
    return closed


def refresh_reviews(config: Config) -> None:
    """A story waiting for review is merged once main holds all of its branch's commits; the user merges and pushes."""
    with quota.transaction() as ledger:
        for key, entry in ledger["issues"].items():
            if entry.get("review") != "awaiting":
                continue
            branch = workspace.branch_name(key)
            repos = [config.repos[name] for name in entry.get("repos", []) if name in config.repos]
            present = [repo for repo in repos if workspace.git(repo.path, "branch", "--list", branch)]
            if present and all(not workspace.git(repo.path, "log", "--oneline", f"origin/main..{branch}") for repo in present):
                entry["review"] = "merged"


def awaiting_review() -> list[Json]:
    ledger = quota.load_ledger()
    return [{"key": key, **entry} for key, entry in sorted(ledger["issues"].items()) if entry.get("review") == "awaiting"]


def new_run_dir(name: str) -> Path:
    """A fresh directory for every run: a restart within the same second never reuses another run's files."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / name
    while True:
        try:
            path.mkdir()
            return path
        except FileExistsError:
            path = RUNS_DIR / f"{name}-{os.getpid()}-{time.time_ns() % 10_000}"


def reconcile(current_run: Path, config: Config) -> list[str]:
    """Stories a crashed or killed run left half-done: the user's checkout is released first, then the story is
    reported once as interrupted, never silently retried or deleted."""
    found = []
    for frame_file in sorted(RUNS_DIR.glob("*/*/frame-*.json")):
        frame = read_json(frame_file, {}) or {}
        if frame.get("released") or frame.get("repo") not in config.repos:
            continue
        result = workspace.release_frame(frame_file, repo=config.repos[frame["repo"]], log_dir=frame_file.parent / "logs")
        state = "restored" if result["ok"] else "NEEDS ATTENTION: " + "; ".join(result["problems"])
        found.append(f"{frame['repo']} checkout left on {frame['branch']} by run {frame_file.parent.parent.name}: {state}")
    for phase_file in sorted(RUNS_DIR.glob("*/*/phase.json")):
        if phase_file.parent.parent == current_run:
            continue
        phase = read_json(phase_file, {}) or {}
        if phase.get("phase") in ("reported", "reconciled"):
            continue
        key = phase_file.parent.name
        found.append(f"{key} (run {phase_file.parent.parent.name}) stopped during {phase.get('phase')}; its branch was kept as it was. `/night-shift retry {key}` to try again")
        update_issue(key, status="interrupted", final=True)
        set_phase(phase_file.parent, "reconciled")
    return found


def stale_checkouts(repos: list, k: Json) -> list[str]:
    return [problem for repo in repos if (problem := workspace.staleness(repo, int(k["fetch_max_workdays"])))]


def fetch_all(repos: list) -> list[str]:
    """One warning per distinct failure, naming every repository it hit."""
    failed: dict[str, list[str]] = {}
    for repo in repos:
        if reason := workspace.fetch(repo):
            failed.setdefault(reason, []).append(repo.name)
    return [f"git fetch failed for {', '.join(names)} ({reason}); the work is based on their last fetched origin/main." for reason, names in failed.items()]


def wait_until_fresh(repos: list, k: Json, until: datetime) -> list[str]:
    """No story starts on a stale checkout. The user gets a dialog; once they sync (or GitLab lets the fetch
    through again), the run goes on. What is still stale at `until` is returned."""
    problems = stale_checkouts(repos, k)
    if problems:
        log(f"stale checkouts, waiting until {until:%H:%M} for a sync: {problems}")
        alert.stale_repos(problems, tonight=True)
    while problems and datetime.now() + timedelta(seconds=FRESH_POLL_SECONDS) < until:
        time.sleep(FRESH_POLL_SECONDS)
        for repo in repos:
            if workspace.staleness(repo, int(k["fetch_max_workdays"])):
                workspace.fetch(repo)
        problems = stale_checkouts(repos, k)
    return problems


def deadlines(k: Json, now: datetime, manual: bool) -> tuple[datetime, datetime]:
    if manual:
        return now + timedelta(hours=4), now + timedelta(hours=2, minutes=30)
    return at_time(k["deadline"], base=now), at_time(k["last_start"], base=now)


def consume_run_now() -> Json | None:
    request = read_json(RUN_NOW_FILE, None)
    if not request or request.get("consumed"):
        return None
    write_json(RUN_NOW_FILE, {**request, "consumed": time.time()})
    return request


def context_for_picker(config: Config, k: Json, run_dir: Path, keys: list[str] | None = None) -> Path:
    ledger = quota.load_ledger()
    context = {
        "run_dir": str(run_dir),
        "stories_wanted": int(k["stories"]),
        "examine_max": 12,
        "jira_site": config.jira_site,
        "jira_project": config.jira_project,
        "browse_url": browse_url(config),
        "candidates": candidate_source(config, keys),
        "people": config.people,
        "slack_channels": config.slack_channels,
        "repos": {name: str(repo.path) for name, repo in config.repos.items()},
        "previous": ledger["issues"],
        "retry_after_days": RETRY_AFTER_DAYS,
        "today": datetime.now().date().isoformat(),
        "scripts": SCRIPTS,
    }
    path = run_dir / "context.json"
    write_json(path, context)
    return path


def candidate_source(config: Config, keys: list[str] | None = None) -> Json:
    """Where tonight's candidates come from, in the order the team ranks them.

    With a board configured, only the cards in its to-do column count: a team-managed board keeps a separate
    backlog list in the same status, and those items rank above the column without being chosen work.
    """
    if keys:
        return {"keys": keys}
    if config.jira_board_id:
        return {
            "board_id": config.jira_board_id,
            "column_jql": f'status = "{config.jira_board_column_status}" AND assignee is EMPTY AND issuetype != Epic AND Flagged is EMPTY',
            "exclude_backlog_list": True,
        }
    return {
        "jql": (
            f'project = {config.jira_project} AND assignee is EMPTY AND statusCategory = "To Do" AND status != Icebox '
            f"AND Flagged is EMPTY AND issuetype != Epic ORDER BY Rank ASC"
        )
    }


def validate_plan(run_dir: Path, config: Config) -> tuple[list[Json], list[Json], list[str]]:
    plan = read_json(run_dir / "plan.json", None)
    problems, stories = [], []
    if not isinstance(plan, dict):
        return [], [], ["plan.json is missing or not an object"]
    for story in plan.get("stories", []):
        key = str(story.get("key", ""))
        repos = [repo for repo in story.get("repos", []) if repo in config.repos]
        dossier = Path(str(story.get("dossier", ""))).expanduser()
        if not valid_key(key):
            problems.append(f"invalid key {key!r}")
        elif not repos or repos != story.get("repos"):
            problems.append(f"{key}: repos {story.get('repos')} are not all configured")
        elif not story.get("brief"):
            problems.append(f"{key}: empty brief")
        elif not dossier.resolve().is_relative_to(run_dir.resolve()):
            problems.append(f"{key}: dossier outside the run directory")
        else:
            stories.append({**story, "repos": repos, "dossier": str(dossier.resolve())})
    skipped = [item for item in plan.get("skipped", []) if valid_key(str(item.get("key", "")))]
    return stories, skipped, problems


# ---------- nightly ----------

def nightly(args: argparse.Namespace) -> None:
    config = load_config()
    k = knobs()
    now = datetime.now()
    request = consume_run_now()
    manual = args.now or request is not None
    dry = args.dry or bool(request and request.get("dry"))
    deadline, last_start = deadlines(k, now, manual)
    morning = quota.morning_after(now)
    candidate_keys = [key for key in (args.candidates or "").split(",") if key]
    if any(not valid_key(key) for key in candidate_keys):
        sys.exit(f"invalid key in --candidates: {args.candidates}")
    if manual:
        sessions.RUN_GATE.update(since=time.time(), points=float(k["night_points"]))
    run_dir = new_run_dir(now.strftime("%Y%m%d-%H%M%S"))
    kind = "Dry run" if dry else "Manual run" if manual else "Night run"
    night: Json = {"date": morning.date().isoformat(), "started": now.isoformat(), "kind": kind, "stories": [], "skipped": [], "warnings": [], "interrupted": [], "status": "done"}

    def finish(status: str | None = None, reason: str | None = None) -> None:
        if status:
            night["status"] = status
        if reason:
            night["reason"] = reason
        quota.current(max_age=0, label="night_end")
        night["quota"] = quota.describe(k, morning, sessions.RUN_GATE.get("since"), sessions.RUN_GATE.get("points"))
        path = note.night_note(folder=config.vault_folder, night=night, browse=browse_url(config))
        log(f"note: {path}")
        for story in night.get("stories", []):
            if story.get("note_id"):
                update_issue(story["key"], note=story["note"], note_id=story["note_id"], note_state="open")

    if not manual and not (now.hour < 12 and now <= last_start):
        log(f"started at {now:%H:%M}, outside the night window (until {k['last_start']}): nothing to do")
        return
    if not manual and morning.weekday() >= 5:
        if int(k["weekend_stories"]) <= 0:
            log("weekend night: weekend_stories is 0, nothing to do")
            return
        k = {**k, "stories": int(k["weekend_stories"]), "night_points": float(k["weekend_night_points"])}
    with run_lock("nightly"):
        night["interrupted"] = reconcile(run_dir, config)
        workspace.night_aws_config(config.aws_allowed_accounts)
        workspace.night_docker_config()
        quota.current(max_age=0, label="run_start" if manual else "night_start")
        verdict = quota.check(kind="pick", knobs=k, morning=morning, **sessions.RUN_GATE)
        if not verdict.allowed:
            return finish("skipped", f"Not started: {verdict.reason}")
        night["warnings"] += fetch_all(list(config.repos.values()))
        for change in sync_notes(config):
            log(change)
        refresh_reviews(config)
        night["awaiting"] = awaiting_review()
        codex = Codex(bool(k["codex"]), run_dir / "logs", deadline)
        if codex.note:
            night["warnings"].append(codex.note)

        context = context_for_picker(config, k, run_dir, candidate_keys)
        pick = sessions.run(
            sessions.Spec(
                kind="pick",
                prompt=f"Run the night-shift-pick skill with the context file {context}.",
                cwd=run_dir,
                run_id=run_dir.name,
                log_dir=run_dir / "logs",
                model="opus",
                effort="high",
                cap_usd=k["caps_usd"]["pick"],
                minutes=45,
                permission_mode="acceptEdits",
                allowed_tools=PICK_TOOLS,
                max_turns=200,
                env={"NIGHT_SHIFT_RUN_DIR": str(run_dir)},
            ),
            knobs=k,
            deadline=deadline,
            morning=morning,
        )
        if pick.status != "ok":
            return finish("failed" if pick.status == "error" else "skipped", f"The picker did not finish: {pick.status} {pick.reason}".strip())
        stories, skipped, problems = validate_plan(run_dir, config)
        night["skipped"] = [{"key": item["key"], "reason": item.get("reason", "")} for item in skipped]
        for item in skipped:
            update_issue(item["key"], status=item.get("kind", "not_workable"), final=False, reason=item.get("reason", ""), jira_updated=item.get("jira_updated"))
        night["warnings"] += [f"plan: {problem}" for problem in problems]
        stories = second_opinions(codex, stories, config, night, run_dir)
        if dry:
            night["stories"] = [{"key": story["key"], "summary": story.get("summary", ""), "status": "", "reason": "dry run: picked, not worked", "summary_text": story["brief"][:600]} for story in stories]
            return finish("dry-run")
        for index, story in enumerate(stories[: int(k["stories"])]):
            if datetime.now() > last_start:
                night["skipped"].append({"key": story["key"], "reason": f"not started: past the last start time {k['last_start']}"})
                break
            if stale := wait_until_fresh([config.repos[name] for name in story["repos"]], k, last_start):
                night["warnings"].append(f"Stopped before {story['key']}: its checkouts stayed stale ({'; '.join(stale)}). Sign in to GitLab and run /sync-gitlab-repos.")
                break
            recheck = jira_recheck(story["key"], run_dir=run_dir, k=k, deadline=deadline, morning=morning)
            if recheck["status"] in STOP_NIGHT:
                night["warnings"].append(f"Stopped before {story['key']}: {'; '.join(recheck['reasons'])}")
                break
            if not recheck.get("workable"):
                night["skipped"].append({"key": story["key"], "reason": "changed since picking: " + "; ".join(recheck["reasons"])})
                update_issue(story["key"], status="blocked", final=False, reason="; ".join(recheck["reasons"]), jira_updated=recheck.get("updated"))
                continue
            outcome = work_story(config, k, story, index, run_dir, codex, deadline, morning)
            night["stories"].append(outcome)
            for problem in outcome.get("release_problems", []):
                night["warnings"].insert(0, f"Your checkout after {story['key']} needs attention: {problem}")
            if outcome["status"] in STOP_NIGHT:
                night["warnings"].append(f"Stopped after {story['key']}: {outcome.get('reason')}")
                break
        finish()


def second_opinions(codex: Codex, stories: list[Json], config: Config, night: Json, run_dir: Path) -> list[Json]:
    """Codex reads each pick independently. A concrete 'not workable' moves the story to the back, not out."""
    if not codex.ready():
        return stories
    agreed, doubted = [], []
    for story in stories:
        primary = config.repos[story["repos"][0]]
        prompt = (
            "You are an independent senior engineer. Decide whether this Jira story can be worked unattended overnight by an "
            "AI agent in this repository, with no one to ask. Not workable: needs a product or design decision, external "
            "access, production data, or is too vague to test. Read the repository as needed; do not change anything.\n\n"
            f"Story {story['key']}: {story.get('summary', '')}\n\nBrief:\n{story['brief']}\n\nDossier directory (read it): {story['dossier']}\n"
        )
        result = codex.run("opinion", cd=primary.path, prompt=prompt, name=f"opinion-{story['key']}", schema=OPINION_SCHEMA, add_dirs=[])
        opinion = result.get("data")
        story["codex_opinion"] = opinion
        if opinion and not opinion["workable"]:
            night["warnings"].append(f"codex doubts {story['key']}: {opinion['reason']}")
            doubted.append(story)
        else:
            agreed.append(story)
    write_json(run_dir / "plan-opinions.json", stories)
    return agreed + doubted


def brief_text(story: Json, prepared: list[workspace.Prepared], issue_dir: Path, implementer: str, deadline: datetime) -> str:
    primary, *others = prepared
    lines = [
        f"# {story['key']}: {story.get('summary', '')}",
        "",
        f"- Checkout (your working directory): {primary.path}, on branch {primary.branch} from origin/main",
        *[f"- Also: {item.repo} checkout {item.path}, on branch {item.branch}" for item in others],
        "- The user's own work in these checkouts is set aside for the night and is not yours to see or touch.",
        f"- Run directory (result.json, progress.md): {issue_dir}",
        f"- Dossier (read it before touching code): {story['dossier']}",
        f"- Implementer: {implementer}",
        f"- Hard stop: {deadline:%H:%M}. Leave time for the report.",
        "",
        "## Brief from the picker",
        "",
        story["brief"],
    ]
    feedback = (quota.load_ledger()["issues"].get(story["key"]) or {}).get("feedback")
    if feedback:
        lines += ["", "## The user's feedback on an earlier attempt (follow it)", "", feedback]
    if story.get("codex_opinion"):
        lines += ["", "## Codex's independent read of the story", "", json.dumps(story["codex_opinion"], indent=2)]
    return "\n".join(lines) + "\n"


def session_name(story: Json) -> str:
    return f"night {story['key']}: {story.get('summary', '')}".strip().rstrip(":")[:80]


def work_story(config: Config, k: Json, story: Json, index: int, run_dir: Path, codex: Codex, deadline: datetime, morning: datetime) -> Json:
    """One story in the user's own checkouts: enter, work, review, fix, verify, check independence, release.

    The release runs whatever happens before it, so the user always gets their checkout back as it was.
    """
    key = story["key"]
    issue_dir = run_dir / key
    issue_dir.mkdir(parents=True, exist_ok=True)
    outcome: Json = {"key": key, "summary": story.get("summary", ""), "repos": [], "status": "", "progress": []}
    update_issue(key, status="started", final=False, run=run_dir.name)
    set_phase(issue_dir, "preparing")
    manual = bool(sessions.RUN_GATE)
    prepared: list[workspace.Prepared] = []
    try:
        try:
            for name in story["repos"]:
                repo = config.repos[name]
                workspace.preflight(repo, manual=manual, env_allowed_hosts=config.env_allowed_hosts, env_forbidden_hosts=config.env_forbidden_hosts)
                prepared.append(workspace.enter(repo, key, log_dir=issue_dir / "logs", deadline=deadline, frame_file=issue_dir / f"frame-{name}.json"))
        except workspace.SetupProblem as problem:
            outcome.update(status="setup_failed", reason=str(problem))
            update_issue(key, status="setup_failed", final=False)
            return outcome
        progress(issue_dir, f"on {key}'s branch: {', '.join(item.branch + ' in ' + item.repo for item in prepared)}")
        _work(config, k, story, index, run_dir, issue_dir, codex, deadline, morning, prepared, outcome)
        return outcome
    finally:
        releases = {}
        for item in reversed(prepared):
            releases[item.repo] = workspace.release(item, repo=config.repos[item.repo], log_dir=issue_dir / "logs", deadline=None)
        outcome["release"] = releases
        for repo in outcome["repos"]:
            repo["removed"] = bool((releases.get(repo["repo"]) or {}).get("removed_empty_branch"))
        bad = [f"{repo}: {'; '.join(result['problems'])}" for repo, result in releases.items() if not result["ok"]]
        if bad:
            outcome["release_problems"] = bad
        if prepared:
            progress(issue_dir, "your checkout restored" if not bad else "checkout restore NEEDS ATTENTION, see the note")
        outcome["progress"] = (issue_dir / "progress.md").read_text().splitlines() if (issue_dir / "progress.md").exists() else []
        set_phase(issue_dir, "reported")


def _work(config: Config, k: Json, story: Json, index: int, run_dir: Path, issue_dir: Path, codex: Codex, deadline: datetime, morning: datetime,
          prepared: list[workspace.Prepared], outcome: Json) -> None:
    key = story["key"]
    set_phase(issue_dir, "working")
    verdict = quota.check(kind="work", knobs=k, morning=morning, **sessions.RUN_GATE)
    seven = verdict.seven_day_percent or 0
    implementer = "codex-first" if codex.ready() and (index % 2 == 1 or seven > 40) else "claude"
    if not verdict.allowed and k.get("codex_fallback") and codex.ready():
        implementer = "codex-only"
    outcome["implementer"] = implementer
    (issue_dir / "brief.md").write_text(brief_text(story, prepared, issue_dir, implementer, deadline))
    primary = prepared[0]
    claude_session: sessions.Result | None = None
    if implementer == "codex-only":
        result = codex_only(codex, story, prepared, issue_dir)
        outcome.update(status=result["status"], reason=result.get("reason", ""))
    else:
        settings = session_settings(WORK_SETTINGS, target=issue_dir / "settings.json", config=config)
        session = sessions.run(
            sessions.Spec(
                kind="work",
                key=key,
                prompt=f"Run the night-shift-work skill for the story brief in {issue_dir / 'brief.md'}.",
                cwd=primary.path,
                run_id=run_dir.name,
                log_dir=issue_dir / "logs",
                model="fable",
                effort="high",
                cap_usd=k["caps_usd"]["work"],
                minutes=float(k["story_minutes"]),
                settings=settings,
                add_dirs=[item.path for item in prepared[1:]] + [issue_dir, Path(story["dossier"])],
                fallback_models=["opus"],
                env={"NIGHT_SHIFT_RUN_DIR": str(issue_dir), **workspace.tool_env(primary.path)},
                name=session_name(story),
            ),
            knobs=k,
            deadline=deadline,
            morning=morning,
        )
        outcome["cost"] = session.cost
        outcome["points"] = session.points
        outcome["session_id"] = session.session_id
        outcome["session_cwd"] = str(primary.path)
        claude_session = session if session.status == "ok" else None
        result = read_json(issue_dir / "result.json", {}) or {}
        if session.status == "ok" and result.get("status") in FINAL:
            outcome["status"] = result["status"]
        else:
            outcome["status"] = session.status if session.status != "ok" else "error"
            outcome["reason"] = session.reason or "the session ended without a result.json"
        outcome["summary_text"] = result.get("summary", "")
        outcome["open_questions"] = result.get("open_questions", [])
    # The review commits to REPORT.md, so it comes first: the gate then runs on the branch tip the user gets.
    set_phase(issue_dir, "reviewing")
    if any(workspace.commits_since(item.path, item.base_sha) for item in prepared) and codex.ready():
        outcome["review"] = codex_review(codex, story, prepared, issue_dir, config)
        if needs_fix(outcome["review"]) and claude_session is not None:
            set_phase(issue_dir, "fixing")
            fixed = fix_round(k, story, prepared, issue_dir, outcome["review"], claude_session, deadline, morning)
            outcome["cost"] = outcome.get("cost", 0.0) + fixed.cost
            if fixed.points is not None:
                outcome["points"] = round((outcome.get("points") or 0.0) + fixed.points, 1)
            outcome["fix_round"] = fixed.status if fixed.status != "ok" else "done"
            result = read_json(issue_dir / "result.json", {}) or {}
            if fixed.status == "ok" and result.get("status") in FINAL:
                outcome["status"] = result["status"]
                outcome["summary_text"] = result.get("summary", outcome.get("summary_text", ""))
                outcome["open_questions"] = result.get("open_questions", outcome.get("open_questions", []))
    set_phase(issue_dir, "verifying")
    for item in prepared:
        commits = workspace.commits_since(item.path, item.base_sha)
        verify = workspace.verify(config.repos[item.repo], item, key=key, log_dir=issue_dir / "logs", deadline=deadline) if commits else None
        independence = workspace.independence_problems(item.path, key) if commits else []
        if verify:
            progress(issue_dir, f"{item.repo} gate {'passed' if verify['passed'] else 'FAILED'} on {verify['final_sha'][:8]}")
        if independence:
            progress(issue_dir, f"{item.repo} branch not standalone: {'; '.join(independence)}")
        outcome["repos"].append({"repo": item.repo, "branch": item.branch, "checkout": str(item.path), "commits": commits, "verify": verify, "independence": independence})
    write_json(issue_dir / "verify.json", outcome["repos"])
    changed = [repo for repo in outcome["repos"] if repo["commits"]]
    if outcome["status"] == "solved" and not changed:
        outcome["status"], outcome["reason"] = "partial", "the model said solved, but no commit landed on the branch"
    elif outcome["status"] == "solved" and not all(repo["verify"]["passed"] for repo in changed):
        outcome["status"], outcome["reason"] = "partial", "the model said solved, but the repository gate failed on the branch tip"
    elif outcome["status"] == "solved" and any(repo["independence"] for repo in changed):
        outcome["status"], outcome["reason"] = "partial", "the branch does not stand alone: " + "; ".join(p for repo in changed for p in repo["independence"])
    worked = any(repo["commits"] for repo in outcome["repos"])
    update_issue(key, status=outcome["status"], final=outcome["status"] in FINAL, branch=primary.branch, repos=story["repos"],
                 review="awaiting" if worked else None, summary=story.get("summary", ""), session=outcome.get("session_id"))


def needs_fix(review: Json | None) -> bool:
    if not review:
        return False
    return review["verdict"] == "request_changes" or review["tests_weakened"] or any(finding["severity"] in ("high", "medium") for finding in review["findings"])


def fix_round(k: Json, story: Json, prepared: list[workspace.Prepared], issue_dir: Path, review: Json, session: sessions.Result,
              deadline: datetime, morning: datetime) -> sessions.Result:
    """One bounded round in the same Claude session, so it keeps everything it learned: act on codex's review."""
    minutes = min(float(k["fix_minutes"]), (deadline - datetime.now()).total_seconds() / 60 - 10)
    if minutes < 10:
        progress(issue_dir, "fix round skipped: not enough time before the deadline")
        return sessions.Result("skipped", "not enough time")
    findings = "\n".join(f"- [{f['severity']}] {f['file']}: {f['issue']} Suggestion: {f['suggestion']}" for f in review["findings"])
    unneeded = "\n".join(f"- {item}" for item in review["unneeded_changes"]) or "- (none)"
    prompt = (
        "An independent reviewer (codex) has read your branch. Its verdict and findings are below. Treat them as a "
        "colleague's review: verify each one against the code first. Fix every finding that holds, with a test where "
        "behavior changes, in the smallest change. Do not fix what does not hold; say why instead. Then run the "
        "repository's final gate again, update REPORT.md with a 'Review follow-up' section (one line per finding: fixed "
        "how, or not fixed and why), update result.json (status and done-list stay honest), add one progress checkpoint, "
        "and commit.\n\n"
        f"Verdict: {review['verdict']}. {review['summary']}\nTests weakened: {review['tests_weakened']}\n\n"
        f"Findings:\n{findings}\n\nParts of the diff the reviewer says the story does not need:\n{unneeded}\n"
    )
    primary = prepared[0]
    settings = issue_dir / "settings.json"
    result = sessions.run(
        sessions.Spec(
            kind="fix", key=story["key"], prompt=prompt, cwd=primary.path, run_id=issue_dir.parent.name, log_dir=issue_dir / "logs",
            model="fable", effort="high", cap_usd=k["caps_usd"]["fix"], minutes=minutes, settings=settings,
            add_dirs=[item.path for item in prepared[1:]] + [issue_dir, Path(story["dossier"])], fallback_models=["opus"],
            env={"NIGHT_SHIFT_RUN_DIR": str(issue_dir), **workspace.tool_env(primary.path)},
            resume_from=session.session_id, cost_before=float(session.data.get("total_cost_usd") or 0.0), max_turns=150, name=session_name(story),
        ),
        knobs=k, deadline=deadline, morning=morning,
    )
    progress(issue_dir, f"fix round after the review: {result.status}")
    return result


def codex_review(codex: Codex, story: Json, prepared: list[workspace.Prepared], issue_dir: Path, config: Config) -> Json | None:
    primary = prepared[0]
    diff = "\n".join(workspace.git(item.path, "diff", f"{item.base_sha}..HEAD") for item in prepared)[:MAX_DIFF_CHARS]
    tests = "\n".join(workspace.git(item.path, "diff", "--stat", f"{item.base_sha}..HEAD", "--", "*test*", "*spec*") for item in prepared)
    report = (primary.path / "REPORT.md").read_text() if (primary.path / "REPORT.md").exists() else "(no REPORT.md)"
    prompt = (
        "Review this change as an independent senior reviewer. Another agent wrote it overnight for the Jira story below; "
        "you have not seen its reasoning, and it will not see yours before a human reads both. Read any file in the "
        "repository you need. Judge: correctness, missed acceptance criteria, security, and minimality: list every part of "
        "the diff the story does not need. Say whether any test was deleted, skipped or weakened. Do not change files.\n\n"
        f"## Brief\n{(issue_dir / 'brief.md').read_text()}\n\n## REPORT.md\n{report}\n\n## Test files changed\n{tests or '(none)'}\n\n## Diff\n{diff}\n"
    )
    result = codex.run("review", cd=primary.path, prompt=prompt, name=f"review-{story['key']}", schema=REVIEW_SCHEMA)
    review = result.get("data")
    if not review:
        progress(issue_dir, f"codex review not done: {result.get('status')}")
        return None
    lines = ["", "## Independent review (codex)", "", f"Verdict: {review['verdict']}. {review['summary']}", ""]
    if review["tests_weakened"]:
        lines.append("**Tests were weakened, deleted or skipped.**\n")
    lines += [f"- [{f['severity']}] `{f['file']}`: {f['issue']} Suggestion: {f['suggestion']}" for f in review["findings"]]
    if review["unneeded_changes"]:
        lines += ["", "Not needed for the story:", *[f"- {item}" for item in review["unneeded_changes"]]]
    with (primary.path / "REPORT.md").open("a") as handle:
        handle.write("\n".join(lines) + "\n")
    workspace.commit_paths(primary.path, ["REPORT.md"], config.subject("Add the independent review", story["key"]))
    progress(issue_dir, f"codex review: {review['verdict']}, {len(review['findings'])} findings")
    return review


def codex_only(codex: Codex, story: Json, prepared: list[workspace.Prepared], issue_dir: Path) -> Json:
    """Claude's quota is closed for the night: codex does the whole story, the gate and a second codex pass judge it."""
    primary = prepared[0]
    skill = (SKILLS / "night-shift-work" / "SKILL.md").read_text()
    prompt = (
        "You work this Jira story alone, overnight, with nobody to ask. Follow these working rules, which were written "
        "for another agent; where they name a tool you do not have, do the same thing by hand.\n\n"
        f"{skill}\n\n## The story brief\n{(issue_dir / 'brief.md').read_text()}\n"
    )
    add_dirs = [item.path for item in prepared[1:]] + [issue_dir]
    result = codex.run("implement", cd=primary.path, prompt=prompt, name=f"implement-{story['key']}", add_dirs=add_dirs)
    progress(issue_dir, f"codex implemented alone: {result.get('status')}")
    data = read_json(issue_dir / "result.json", {}) or {}
    if result.get("status") != "ok":
        return {"status": "error", "reason": f"codex: {result.get('status')} {result.get('reason', '')}"}
    return {"status": data.get("status", "partial"), "reason": "worked by codex alone (Claude's quota guard was closed)"}


# ---------- security ----------

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def fingerprint(repo: str, finding: Json) -> str:
    import hashlib

    title = str(finding.get("title", "")).lower().strip()
    return f"{repo}:{finding.get('file')}:{finding.get('cwe_id')}:{hashlib.sha1(title.encode()).hexdigest()[:10]}"


TRASH_INSTEAD_OF_CLEAN = (
    "The user's rules forbid permanent deletion, so `git clean` is always denied here. Wherever the Claude Security "
    "recipe tells you to run `git clean -fd` (or any `clean`) in a scratch workspace, run instead, as a standalone "
    "command: uv run --quiet --no-project --script ~/.claude/skills/night-shift/scripts/trash_untracked.py <that "
    "scratch workspace path>. It does the same, with the macOS Trash. Never delete anything else. "
    "The user's shell wraps git, and a hook refuses a bare `git`: write every git command as `command git`, "
    "with the same arguments and environment variables."
)
WEEKDAY_NAMES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def next_weekday_time(spec: str, after: datetime) -> datetime:
    """`Sun 18:00` after a Saturday 00:37 start is the next day at 18:00."""
    day, hhmm = spec.split()
    hour, minute = (int(part) for part in hhmm.split(":"))
    moment = after.replace(hour=hour, minute=minute, second=0, microsecond=0)
    moment += timedelta(days=(WEEKDAY_NAMES.index(day[:3].lower()) - after.weekday()) % 7)
    return moment if moment > after else moment + timedelta(days=7)


def security(args: argparse.Namespace) -> None:
    config = load_config()
    k = knobs()
    if not k["security"] and not args.now:
        log("security is off (/night-shift set security true)")
        return
    if not SECURITY_REQUEST_FILE.is_file():
        log(f"no {SECURITY_REQUEST_FILE}: the scan needs your own request text with the cost acknowledgment")
        return
    now = datetime.now()
    deadline = next_weekday_time(k["security_deadline"], now)
    # The gate's "day work" morning is the next workday after the deadline.
    morning = quota.morning_after(deadline)
    while morning.weekday() >= 5:
        morning += timedelta(days=1)
    run_dir = new_run_dir(f"security-{now:%Y%m%d-%H%M%S}")
    report: Json = {"date": morning.date().isoformat(), "started": now.isoformat(), "warnings": [], "status": "done"}

    started = time.time()
    gate = {"since": started, "points": float(k["security_points"])}

    def finish(status: str, headline: str) -> None:
        report.update(status=status, headline=headline, quota=quota.describe(k, morning, **gate))
        log(f"note: {note.security_note(folder=config.vault_folder, report=report)}")

    with run_lock("security"):
        report["warnings"] += [f"interrupted earlier: {item}" for item in reconcile(run_dir, config)]
        workspace.night_aws_config(config.aws_allowed_accounts)
        workspace.night_docker_config()
        ledger = quota.load_ledger()
        names = [name for name, repo in config.repos.items() if repo.security_areas]
        if not names:
            return finish("skipped", "No repository has security_areas in config.toml")
        # The rotation lists a repository as often as it should come up, e.g. the backend most weeks.
        rotation = [name for name in config.security_rotation if name in names] or names
        turn = int(ledger["security"].get("rotation_index", 0))
        name = rotation[turn % len(rotation)]
        repo = config.repos[name]
        area_index = ledger["security"]["area_index"].get(name, 0) % len(repo.security_areas)
        area = repo.security_areas[area_index]
        report.update(repo=name, area=area, effort="medium")
        quota.current(max_age=0, label="run_start")
        report["warnings"] += fetch_all([repo])
        if stale := wait_until_fresh([repo], k, deadline - timedelta(hours=6)):
            return finish("skipped", f"Not started: the checkout stayed stale ({'; '.join(stale)}). Sign in to GitLab and run /sync-gitlab-repos.")
        key = f"SEC-{now:%Y%m%d}"
        journal = run_dir / key
        journal.mkdir()
        set_phase(journal, "preparing")
        try:
            workspace.preflight(repo, manual=bool(args.now), env_allowed_hosts=config.env_allowed_hosts, env_forbidden_hosts=config.env_forbidden_hosts)
            prepared = workspace.enter(repo, key, log_dir=run_dir / "logs", deadline=deadline, frame_file=journal / f"frame-{name}.json")
        except workspace.SetupProblem as problem:
            set_phase(journal, "reported")
            return finish("failed", f"Setup failed: {problem}")
        try:
            _security_in_checkout(config, k, repo, name, area, key, prepared, journal, run_dir, report, finish, now, deadline, morning, ledger, turn, area_index, gate)
        finally:
            released = workspace.release(prepared, repo=repo, log_dir=run_dir / "logs")
            if not released["ok"]:
                report["warnings"].insert(0, "Your checkout was not restored exactly: " + "; ".join(released["problems"]))


def _security_in_checkout(config: Config, k: Json, repo, name: str, area: str, key: str, prepared, journal: Path, run_dir: Path,
                          report: Json, finish, now: datetime, deadline: datetime, morning: datetime, ledger: Json, turn: int, area_index: int, gate: Json) -> None:
    if True:
        set_phase(journal, "scanning")
        report.update(commit=prepared.base_sha[:12], branch=prepared.branch, checkout=str(prepared.path))
        settings = session_settings(SECURITY_SETTINGS, target=run_dir / "settings.json", config=config)
        request = SECURITY_REQUEST_FILE.read_text().replace("{area}", area).replace("{repo}", name)
        started = time.time()
        common_spec = dict(
            cwd=prepared.path, run_id=run_dir.name, log_dir=run_dir / "logs", model="fable", effort="high", settings=settings,
            fallback_models=["opus"], max_turns=600, env={"NIGHT_SHIFT_RUN_DIR": str(run_dir), **workspace.tool_env(prepared.path)},
            append_system_prompt=TRASH_INSTEAD_OF_CLEAN, max_waits=int(k["security_max_waits"]),
            gate=gate,
        )
        scan = sessions.run(sessions.Spec(kind="scan", prompt=request, cap_usd=k["caps_usd"]["scan"], minutes=240, **common_spec), knobs=k, deadline=deadline, morning=morning)
        reports = sorted(path for path in prepared.path.glob("CLAUDE-SECURITY-*") if path.is_dir() and path.stat().st_mtime >= started)
        if scan.status != "ok" or not reports:
            set_phase(journal, "reported")
            return finish("failed", f"The scan did not produce a report ({scan.status} {scan.reason}). If the plugin asked for confirmation, the request text lacks its cost acknowledgment.")
        report_dir = reports[-1]
        report["report_dir"] = str(STATE_DIR / "security" / now.strftime("%Y-%m-%d"))
        findings = [json.loads(line) for line in (report_dir / "CLAUDE-SECURITY-RESULTS.jsonl").read_text().splitlines() if line.strip()] if (report_dir / "CLAUDE-SECURITY-RESULTS.jsonl").exists() else []
        counts: dict[str, int] = {}
        for finding in findings:
            counts[str(finding.get("severity", "?")).lower()] = counts.get(str(finding.get("severity", "?")).lower(), 0) + 1
        report["counts"] = ", ".join(f"{count} {level}" for level, count in sorted(counts.items(), key=lambda item: SEVERITY_RANK.get(item[0], 9))) or "no findings"
        coverage = report_dir / "CLAUDE-SECURITY-RESULTS.md"
        if coverage.exists():
            text = coverage.read_text()
            start = text.find("## Coverage")
            report["not_examined"] = text[start : start + 3000] if start >= 0 else ""
        seen = ledger["security"]["findings"]
        candidates = sorted(
            (finding for finding in findings if fingerprint(name, finding) not in seen),
            key=lambda finding: (SEVERITY_RANK.get(str(finding.get("severity", "")).lower(), 9), CONFIDENCE_RANK.get(str(finding.get("confidence", "")).lower(), 9)),
        )
        with quota.transaction() as fresh:
            fresh["security"]["last_repo"] = name
            fresh["security"]["rotation_index"] = turn + 1
            fresh["security"]["area_index"][name] = area_index + 1
        shutil.copytree(report_dir, Path(report["report_dir"]), dirs_exist_ok=True)
        if not candidates:
            set_phase(journal, "reported")
            return finish("done", f"No new findings in {name} {area}")
        finding = candidates[0]
        finding_id = str(finding.get("id") or finding.get("claudeSecurityPluginFindingId"))
        report["finding"] = finding
        set_phase(journal, "patching")
        patch = sessions.run(
            sessions.Spec(kind="patch", prompt=f"Run Claude Security suggest patches for {finding_id} from the report in {report_dir}.", cap_usd=k["caps_usd"]["patch"], minutes=90, **common_spec),
            knobs=k, deadline=deadline, morning=morning,
        )
        patch_file = report_dir / "patches" / f"{finding_id}.patch"
        patch_note = report_dir / "patches" / f"{finding_id}.md"
        status = "needs attention"
        if patch.status == "ok" and patch_file.exists():
            check = subprocess.run(["git", "-C", str(prepared.path), "apply", "--check", str(patch_file)], capture_output=True, text=True)
            if check.returncode == 0:
                subprocess.run(["git", "-C", str(prepared.path), "apply", str(patch_file)], check=True)
                codex = Codex(bool(k["codex"]), run_dir / "logs", deadline)
                challenge = codex.run(
                    "challenge", cd=prepared.path, name=f"challenge-{finding_id}", schema=CHALLENGE_SCHEMA,
                    prompt=f"A security finding and a patch for it are below; the patch is applied in this working tree. Does it close the finding? What could it break? What should a reviewer check? Read the code as needed; change nothing.\n\n## Finding\n{json.dumps(finding, indent=2)}\n\n## Patch note\n{patch_note.read_text() if patch_note.exists() else ''}\n\n## Patch\n{patch_file.read_text()}\n",
                ).get("data")
                report["challenge"] = json.dumps(challenge, indent=2) if challenge else "codex was not available"
                (prepared.path / "REPORT.md").write_text(
                    f"# Security fix for {finding.get('title')}\n\n```json\n{json.dumps(finding, indent=2)}\n```\n\n## Patch note\n\n{patch_note.read_text() if patch_note.exists() else ''}\n\n## Independent challenge (codex)\n\n{report['challenge']}\n"
                )
                workspace.commit_paths(prepared.path, ["."], config.subject(f"Fix security finding: {finding.get('title')}"))
                verify = workspace.verify(repo, prepared, key=key, log_dir=run_dir / "logs", deadline=deadline)
                closes = bool(challenge and challenge.get("closes_finding"))
                status = "review-ready" if verify["passed"] and closes else "needs attention"
                report["patch"] = f"Applied on `{prepared.branch}`; gate {'passed' if verify['passed'] else 'failed'}; codex says it {'closes' if closes else 'may not close'} the finding."
            else:
                report["patch"] = f"The patch no longer applies: {check.stderr.strip()[:300]}"
        else:
            report["patch"] = (patch_note.read_text()[:2000] if patch_note.exists() else f"No patch: {patch.status} {patch.reason}")
        with quota.transaction() as fresh:
            fresh["security"]["findings"][fingerprint(name, finding)] = {"date": now.date().isoformat(), "repo": name, "status": status}
        set_phase(journal, "reported")
        shutil.copytree(report_dir, Path(report["report_dir"]), dirs_exist_ok=True)
        finish(status, f"{finding.get('severity')} finding in {name}: {finding.get('title')} ({status})")


# ---------- governor ----------

def status(_: argparse.Namespace) -> None:
    k = knobs()
    lines = [f"knobs: {json.dumps(k)}", f"quota: {quota.describe(k, quota.morning_after(datetime.now()))}"]
    lock = STATE_DIR / "lock"
    if lock.exists() and lock.read_text().strip():
        lines.append(f"last lock holder: {lock.read_text().strip()}")
    runs = sorted(RUNS_DIR.glob("*"), key=lambda path: path.stat().st_mtime)[-3:] if RUNS_DIR.exists() else []
    try:
        config = load_config()
        lines += [f"closed now: {change}" for change in sync_notes(config)]
        for repo in config.repos.values():
            fetched = workspace.last_fetched(repo)
            stale = workspace.staleness(repo, int(k["fetch_max_workdays"]))
            lines.append(f"{repo.name}: last fetched {datetime.fromtimestamp(fetched):%a %d %b %H:%M}" + (" (STALE)" if stale else "") if fetched else f"{repo.name}: never fetched")
    except SystemExit:
        lines.append("config.toml missing: checkouts not listed")
    lines.append("recent runs: " + (", ".join(run.name for run in runs) or "none"))
    waiting = [item for item in awaiting_review()]
    lines.append(f"waiting for your review: {len(waiting)}")
    lines += [f"  {item['key']}: {item.get('status')} on {item.get('branch')} ({item.get('date')})" for item in waiting]
    agent = subprocess.run(["/bin/launchctl", "print", f"gui/{os.getuid()}/{LAUNCH_LABEL}"], capture_output=True, text=True)
    lines.append("launch agent: " + ("loaded" if agent.returncode == 0 else "not loaded"))
    print("\n".join(lines))


def set_knob(args: argparse.Namespace) -> None:
    name, raw = args.knob, args.value
    if name.startswith("caps_usd."):
        cap = name.split(".", 1)[1]
        if cap not in DEFAULT_KNOBS["caps_usd"]:
            sys.exit(f"unknown cap {cap}; caps: {sorted(DEFAULT_KNOBS['caps_usd'])}")
        caps = {**knobs()["caps_usd"], cap: float(raw)}
        print(json.dumps(save_knobs({"caps_usd": caps})["caps_usd"]))
        return
    if name not in DEFAULT_KNOBS or isinstance(DEFAULT_KNOBS[name], dict):
        sys.exit(f"unknown knob {name}; knobs: {sorted(DEFAULT_KNOBS)} and caps_usd.<kind>")
    default = DEFAULT_KNOBS[name]
    if isinstance(default, bool):
        value: object = raw.lower() in ("1", "true", "on", "yes")
    elif isinstance(default, int):
        value = int(raw)
    elif isinstance(default, float):
        value = float(raw)
    else:
        value = raw
    save_knobs({name: value})
    print(f"{name} = {knobs()[name]}")


def review(args: argparse.Namespace) -> None:
    """The user's decision on a story the night shift worked."""
    if not valid_key(args.key):
        sys.exit(f"invalid key {args.key}")
    text = " ".join(args.text).strip()
    if args.action == "reject":
        config = load_config()
        entry = quota.load_ledger()["issues"].get(args.key, {})
        kept = []
        for name in entry.get("repos", []) or list(config.repos):
            repo = config.repos.get(name)
            branch = workspace.branch_name(args.key)
            if repo and workspace.git(repo.path, "branch", "--list", branch):
                if workspace.git(repo.path, "branch", "--show-current") == branch:
                    sys.exit(f"{name}: you are on {branch}; switch away from it first")
                archive = f"night-archive/{args.key}-{datetime.now():%Y%m%d}"
                workspace.git(repo.path, "branch", "-m", branch, archive)
                kept.append(f"{name}: {archive}")
        update_issue(args.key, status="rejected", final=True, review="rejected", reason=text)
        print(f"{args.key}: rejected, never retried" + (f"; branch kept as {', '.join(kept)}" if kept else ""))
    elif args.action == "retry":
        with quota.transaction() as ledger:
            entry = ledger["issues"].get(args.key, {})
            ledger["issues"][args.key] = {"status": "retry", "final": False, "review": None, "feedback": text or None,
                                          "previous_status": entry.get("status"), "date": datetime.now().isoformat(timespec="minutes")}
        print(f"{args.key}: eligible again" + (" with your feedback" if text else ""))
    else:
        update_issue(args.key, review="merged")
        print(f"{args.key}: marked merged")


def mark(args: argparse.Namespace) -> None:
    if not valid_key(args.key):
        sys.exit(f"invalid key {args.key}")
    if args.action == "skip":
        update_issue(args.key, status="skipped_by_user", final=True)
    else:
        with quota.transaction() as ledger:
            ledger["issues"].pop(args.key, None)
    print(f"{args.key}: {args.action}")


def cleanup(args: argparse.Namespace) -> None:
    config = load_config()
    if not valid_key(args.key):
        sys.exit(f"invalid key {args.key}")
    # Never while a run is going: it may be working on that very branch.
    with run_lock("cleanup"):
        for repo in config.repos.values():
            if workspace.git(repo.path, "branch", "--list", workspace.branch_name(args.key)):
                print(workspace.cleanup(repo, args.key, force=args.force))


def run_now(args: argparse.Namespace) -> None:
    write_json(RUN_NOW_FILE, {"requested": time.time(), "dry": args.dry})
    result = subprocess.run(["/bin/launchctl", "kickstart", f"gui/{os.getuid()}/{LAUNCH_LABEL}"], capture_output=True, text=True)
    print("started; follow ~/Library/Logs/night-shift.log" if result.returncode == 0 else f"launchctl: {result.stderr.strip()}")


def check_repos(_: argparse.Namespace) -> None:
    """The morning check: tonight's run needs fresh checkouts, and only the user can renew GitLab's sign-in."""
    config = load_config()
    k = knobs()
    if k["paused"]:
        return
    problems = [f"{repo.name}: fetch failed ({failure})" for repo in config.repos.values() if (failure := workspace.fetch(repo))]
    problems += [stale for stale in stale_checkouts(list(config.repos.values()), k) if stale.split(":")[0] not in {p.split(":")[0] for p in problems}]
    if problems:
        log(f"alerting: {problems}")
        alert.stale_repos(problems, tonight=False)
    else:
        log("all checkouts fetched")


def fail(args: argparse.Namespace) -> None:
    config = load_config()
    night = {"date": quota.morning_after(datetime.now()).date().isoformat(), "kind": "Failed run", "status": "failed", "reason": args.message, "quota": quota.describe(knobs(), quota.morning_after(datetime.now()))}
    print(note.night_note(folder=config.vault_folder, night=night, browse=browse_url(config)))


def validate(args: argparse.Namespace) -> None:
    stories, skipped, problems = validate_plan(Path(args.run_dir), load_config())
    print(json.dumps({"stories": [story["key"] for story in stories], "skipped": len(skipped), "problems": problems}))
    sys.exit(1 if problems else 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("nightly")
    p.add_argument("--now", action="store_true")
    p.add_argument("--dry", action="store_true")
    p.add_argument("--candidates", help="comma-separated keys to use instead of the board, in this order (manual runs)")
    p.set_defaults(handler=nightly)
    p = sub.add_parser("security")
    p.add_argument("--now", action="store_true")
    p.set_defaults(handler=security)
    sub.add_parser("status").set_defaults(handler=status)
    sub.add_parser("check-repos").set_defaults(handler=check_repos)
    sub.add_parser("pause").set_defaults(handler=lambda _: print(f"paused = {save_knobs({'paused': True})['paused']}"))
    sub.add_parser("resume").set_defaults(handler=lambda _: print(f"paused = {save_knobs({'paused': False})['paused']}"))
    p = sub.add_parser("set")
    p.add_argument("knob")
    p.add_argument("value")
    p.set_defaults(handler=set_knob)
    p = sub.add_parser("skip")
    p.add_argument("key")
    p.set_defaults(handler=mark, action="skip")
    for action in ("reject", "retry", "merged"):
        p = sub.add_parser(action)
        p.add_argument("key")
        p.add_argument("text", nargs="*")
        p.set_defaults(handler=review, action=action)
    p = sub.add_parser("cleanup")
    p.add_argument("key")
    p.add_argument("--force", action="store_true")
    p.set_defaults(handler=cleanup)
    p = sub.add_parser("run-now")
    p.add_argument("--dry", action="store_true")
    p.set_defaults(handler=run_now)
    p = sub.add_parser("fail")
    p.add_argument("message")
    p.set_defaults(handler=fail)
    p = sub.add_parser("validate-plan")
    p.add_argument("run_dir")
    p.set_defaults(handler=validate)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
