"""Obsidian notes for the night shift, in their own vault folder: one folder per day, named after the morning.

The day folder holds one run note per run (the nightly run, a restart, the security run): what the run did
as a whole, its quota, warnings and errors, and a link to each story note. Each story the run worked gets its
own note beside it, about that story only: status, how it went, branches, review, open questions.

The user keeps the folder tidy by hand: a story note archived (moved out of the folder) or deleted closes its
story. Each note carries a `night_shift_id`: Obsidian keeps frontmatter through a rename or a move, so the id, not the path,
tells where the user put a note (see find_notes).
"""

ID_PROPERTY = "night_shift_id"


import json
import uuid
from datetime import date, datetime
from pathlib import Path

from common import Json


STATUS_WORDS = {
    "solved": "Ready to review",
    "partial": "Partly done",
    "abandoned": "Stopped on purpose",
    "timeout": "Ran out of time",
    "usage_limit": "Stopped at a usage limit",
    "usage_limit_weekly": "Stopped at the weekly limit",
    "gated": "Not started: quota guard",
    "setup_failed": "Not started: setup failed",
    "error": "Session failed",
    "interrupted": "Interrupted",
    "blocked": "Blocked",
}


def run_stem(started: str | None, kind: str) -> str:
    """`2026-10-24 00.52 Night run`: the run's real start, so its runs sort first in the day folder, in order."""
    moment = datetime.fromisoformat(started) if started else datetime.now()
    return f"{moment:%Y-%m-%d %H.%M} {kind}"


def unique(folder: Path, stem: str) -> Path:
    """A later run the same morning (a restart, a dry run) gets its own note instead of replacing the first."""
    path = folder / f"{stem}.md"
    if not path.exists():
        return path
    return folder / f"{stem} ({datetime.now():%H.%M.%S}).md"


def day_folder(folder: Path, day: str) -> Path:
    path = folder / day
    path.mkdir(parents=True, exist_ok=True)
    return path


def _yaml(value: object) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)


def _callout(warning: str) -> str:
    """One line: a raw multi-line message would end the callout after its first line."""
    return f"> [!warning] {' '.join(warning.split())}"


def _frontmatter(properties: Json) -> str:
    properties = {ID_PROPERTY: uuid.uuid4().hex, **properties}
    return "---\n" + "".join(f"{key}: {_yaml(value)}\n" for key, value in properties.items()) + "---\n"


def note_id(path: Path) -> str | None:
    """The id from a note's frontmatter; only the frontmatter is read."""
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            if handle.readline().strip() != "---":
                return None
            for _, line in zip(range(40), handle):
                if line.strip() == "---":
                    return None
                if line.startswith(f"{ID_PROPERTY}:"):
                    return line.split(":", 1)[1].strip().strip('"') or None
    except OSError:
        return None
    return None


def find_notes(vault: Path) -> dict[str, Path]:
    """Every night-shift note in the vault by id. Obsidian's own trash counts as deleted."""
    found = {}
    for path in vault.rglob("*.md"):
        if {".obsidian", ".trash"} & set(path.relative_to(vault).parts):
            continue
        if identifier := note_id(path):
            found[identifier] = path
    return found


def vault_root(folder: Path) -> Path:
    return next(parent for parent in folder.parents if (parent / ".obsidian").is_dir())


def _label(story: Json) -> str:
    label = STATUS_WORDS.get(story.get("status", ""), story.get("status", ""))
    return (f"**{label}**" if label else "") + (f": {story['reason']}" if label and story.get("reason") else story.get("reason", ""))


def _story(story: Json, browse: str) -> list[str]:
    key = story["key"]
    lines = [f"# [{key}]({browse}{key}) {story.get('summary', '')}", ""]
    lines.append(_label(story))
    if story.get("summary_text"):
        lines += ["", story["summary_text"]]
    meta = []
    if story.get("implementer"):
        meta.append(f"implemented by {story['implementer']}")
    if story.get("points") is not None:
        meta.append(f"Claude used {story['points']:g} points of your 7-day limit")
    if meta:
        lines += ["", "*" + ", ".join(meta) + "*"]
    if story.get("session_id"):
        branch = next((repo["branch"] for repo in story.get("repos", []) if repo.get("commits")), f"night/{key}")
        lines += ["", "**Continue the night's Claude session** (from its checkout, on its branch):", "", "```sh",
                  f"cd {story['session_cwd']} && git switch {branch} && claude --resume {story['session_id']}", "```"]
    if story.get("progress"):
        lines += ["", "**How it went**", ""] + [f"- {line[2:]}" if line.startswith("- ") else f"- *{line[2:]}*" for line in story["progress"]]
    removed = [repo["repo"] for repo in story.get("repos", []) if not repo.get("commits") and repo.get("removed")]
    for repo in story.get("repos", []):
        if repo["repo"] in removed:
            continue
        verify = repo.get("verify") or {}
        gate = "✅ gate passed" if verify.get("passed") else "❌ gate failed" if verify else "gate not run"
        lines += ["", f"**{repo['repo']}** · `{repo['branch']}` · {gate} · {len(repo.get('commits', []))} commits"]
        for command in verify.get("commands", []):
            if not command["ok"]:
                lines += ["", f"> [!failure]- `{command['command']}`", "> ```", *[f"> {tail}" for tail in command["tail"].splitlines()[-15:]], "> ```"]
        if verify.get("archived_uncommitted"):
            lines += ["", f"Uncommitted files were left; saved to `{verify['archived_uncommitted']}`."]
        lines += ["", "```sh", f"git -C {repo['checkout']} log --oneline origin/main..{repo['branch']}", f"git -C {repo['checkout']} switch {repo['branch']}", "```"]
    review = story.get("review")
    if review:
        lines += ["", f"**Independent review (codex)**: {review.get('verdict', '?')}. {review.get('summary', '')}"]
        if story.get("fix_round"):
            lines.append(f"*Fix round after the review: {story['fix_round']}. Its replies are in REPORT.md under Review follow-up.*")
        for finding in review.get("findings", [])[:5]:
            lines.append(f"- [{finding.get('severity', '?')}] {finding.get('file', '')}: {finding.get('issue', '')}")
    if removed and len(removed) < len(story.get("repos", [])):
        lines += ["", f"*No change was needed in {', '.join(removed)}; its empty branch was removed.*"]
    elif removed:
        lines += ["", "*Nothing was committed; the empty branch was removed.*"]
    if story.get("open_questions"):
        lines += ["", "**Open questions**", ""] + [f"- {question}" for question in story["open_questions"]]
    return lines + [""]


def _repos_line(story: Json) -> str:
    parts = []
    for repo in story.get("repos", []):
        if repo.get("commits"):
            verify = repo.get("verify") or {}
            gate = "gate passed" if verify.get("passed") else "gate failed" if verify else "gate not run"
            parts.append(f"{repo['repo']}, {len(repo['commits'])} commits, {gate}")
    return " · ".join(parts)


def story_note(*, folder: Path, day: str, story: Json, browse: str, run_note: str) -> Path:
    path = unique(folder, f"{day} {story['key']}")
    properties = {"kind": "story", "story": story["key"], "status": story.get("status", "")}
    body = _story(story, browse) + [f"*Run: [[{run_note}]]*", ""]
    path.write_text(_frontmatter(properties) + "\n".join(body))
    return path


def night_note(*, folder: Path, night: Json, browse: str) -> Path:
    day = night.get("date") or date.today().isoformat()
    folder = day_folder(folder, day)
    path = unique(folder, run_stem(night.get("started"), night.get("kind", "Night run")))
    stories = night.get("stories", [])
    ready = sum(1 for story in stories if story.get("status") == "solved")
    headline = night.get("headline") or (f"{ready} of {len(stories)} stories ready to review" if stories else night.get("reason", "Nothing worked tonight"))
    body = [f"# Night shift, {day}", "", f"**{headline}**", "", f"Quota: {night.get('quota', 'unknown')}"]
    for warning in night.get("warnings", []):
        body.append("\n" + _callout(warning))
    body.append("")
    if stories:
        body += ["## Stories", ""]
    for story in stories:
        linked = story_note(folder=folder, day=day, story=story, browse=browse, run_note=path.stem)
        story["note"] = str(linked.relative_to(folder.parent))
        story["note_id"] = note_id(linked)
        details = " · ".join(part for part in (_label(story), _repos_line(story)) if part)
        body.append(f"- [[{linked.stem}|{story['key']}]] {story.get('summary', '')}: {details}")
    if stories:
        body.append("")
    if night.get("awaiting"):
        body += ["## Waiting for your review", ""]
        body += [f"- [{item['key']}]({browse}{item['key']}) {item.get('summary', '')}: {item.get('status')} on `{item.get('branch')}` since {item.get('date', '')[:10]}" for item in night["awaiting"]]
        body += ["", "Decide with `/night-shift merged KEY`, `/night-shift reject KEY \"why\"` or `/night-shift retry KEY \"what to change\"`.", ""]
    if night.get("skipped"):
        body += ["## Looked at, not worked", ""] + [f"- [{item['key']}]({browse}{item['key']}): {item['reason']}" for item in night["skipped"]] + [""]
    if night.get("interrupted"):
        body += ["## Interrupted earlier", ""] + [f"- {item}" for item in night["interrupted"]] + [""]
    properties = {"kind": "run", "status": night.get("status", "done")}
    path.write_text(_frontmatter(properties) + "\n".join(body) + "\n")
    return path


def security_note(*, folder: Path, report: Json) -> Path:
    day = report.get("date") or date.today().isoformat()
    path = unique(day_folder(folder, day), run_stem(report.get("started"), "Security run"))
    headline = report.get("headline", "Weekly security analysis")
    body = [f"# Security analysis, {day}", "", f"**{headline}**", "", f"Quota: {report.get('quota', 'unknown')}", ""]
    for label in ("repo", "area", "commit", "effort", "counts", "report_dir"):
        if report.get(label):
            body.append(f"- {label.replace('_', ' ')}: {report[label]}")
    finding = report.get("finding")
    if finding:
        body += ["", f"## {finding.get('title', 'Finding')}", "", f"Severity {finding.get('severity')}, confidence {finding.get('confidence')}, `{finding.get('file')}:{finding.get('line')}`", ""]
        for part in ("impact", "exploit_scenario", "recommendation"):
            if finding.get(part):
                body += [f"**{part.replace('_', ' ').capitalize()}**: {finding[part]}", ""]
    if report.get("patch"):
        body += ["## Patch", "", report["patch"], ""]
    if report.get("challenge"):
        body += ["## Independent challenge (codex)", "", report["challenge"], ""]
    if report.get("branch"):
        body += ["```sh", f"git -C {report['checkout']} show --stat {report['branch']}", "```", ""]
    if report.get("not_examined"):
        body += ["## Not examined", "", report["not_examined"], ""]
    for warning in report.get("warnings", []):
        body.append(_callout(warning) + "\n")
    path.write_text(_frontmatter({"kind": "run", "status": report.get("status", "done")}) + "\n".join(body) + "\n")
    return path
