"""Obsidian notes for the night shift: one per night, one per security run, in their own vault folder.

Each note starts with `read: false`; the folder's Base lists unread notes, as the recap's does.
The morning read must answer three questions fast: what is ready to review, how it got there, and what the
night cost. So the quota line comes first, each story gets a short checkpoint timeline, and the review
commands are copy-ready.
"""

import json
from datetime import date, datetime
from pathlib import Path

from common import Json

BASE_TEMPLATE = """filters:
  and:
    - file.inFolder("{folder}")
properties:
  file.name:
    displayName: Note
  note.read:
    displayName: Read
  note.headline:
    displayName: Headline
views:
  - type: table
    name: Unread
    filters:
      and:
        - read != true
    order:
      - file.name
      - read
      - headline
    sort:
      - property: file.name
        direction: DESC
  - type: table
    name: All
    order:
      - file.name
      - read
      - headline
    sort:
      - property: file.name
        direction: DESC
"""

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


def unique(folder: Path, stem: str) -> Path:
    """A later run the same morning (a restart, a dry run) gets its own note instead of replacing the first."""
    path = folder / f"{stem}.md"
    if not path.exists():
        return path
    return folder / f"{stem} ({datetime.now():%H.%M.%S}).md"


def ensure_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    base = folder / f"{folder.name}.base"
    if not base.exists():
        base.write_text(BASE_TEMPLATE.format(folder=folder.name))


def _yaml(value: object) -> str:
    return json.dumps(value, ensure_ascii=False) if isinstance(value, str) else str(value).lower() if isinstance(value, bool) else str(value)


def _frontmatter(properties: Json) -> str:
    return "---\n" + "".join(f"{key}: {_yaml(value)}\n" for key, value in properties.items()) + "---\n"


def _story(story: Json, browse: str) -> list[str]:
    key = story["key"]
    lines = [f"## [{key}]({browse}{key}) {story.get('summary', '')}", ""]
    label = STATUS_WORDS.get(story.get("status", ""), story.get("status", ""))
    lines.append((f"**{label}**" if label else "") + (f": {story['reason']}" if label and story.get("reason") else story.get("reason", "")))
    if story.get("summary_text"):
        lines += ["", story["summary_text"]]
    meta = []
    if story.get("implementer"):
        meta.append(f"implemented by {story['implementer']}")
    if story.get("cost") is not None:
        meta.append(f"Claude ≈ ${story['cost']:.2f}")
    if meta:
        lines += ["", "*" + ", ".join(meta) + "*"]
    if story.get("progress"):
        lines += ["", "**How it went**", ""] + [f"- {line[2:]}" if line.startswith("- ") else f"- *{line[2:]}*" for line in story["progress"]]
    for repo in story.get("repos", []):
        verify = repo.get("verify") or {}
        gate = "✅ gate passed" if verify.get("passed") else "❌ gate failed" if verify else "gate not run"
        lines += ["", f"**{repo['repo']}** · `{repo['branch']}` · {gate} · {len(repo.get('commits', []))} commits"]
        for command in verify.get("commands", []):
            if not command["ok"]:
                lines += ["", f"> [!failure]- `{command['command']}`", "> ```", *[f"> {tail}" for tail in command["tail"].splitlines()[-15:]], "> ```"]
        if verify.get("archived_uncommitted"):
            lines += ["", f"Uncommitted files were left; saved to `{verify['archived_uncommitted']}`."]
        lines += ["", "```sh", f"cd {repo['worktree']}", "git log --oneline origin/main..", "git diff origin/main...", "```"]
    review = story.get("review")
    if review:
        lines += ["", f"**Independent review (codex)**: {review.get('verdict', '?')}. {review.get('summary', '')}"]
        if story.get("fix_round"):
            lines.append(f"*Fix round after the review: {story['fix_round']}. Its replies are in REPORT.md under Review follow-up.*")
        for finding in review.get("findings", [])[:5]:
            lines.append(f"- [{finding.get('severity', '?')}] {finding.get('file', '')}: {finding.get('issue', '')}")
    if story.get("open_questions"):
        lines += ["", "**Open questions**", ""] + [f"- {question}" for question in story["open_questions"]]
    return lines + [""]


def night_note(*, folder: Path, night: Json, browse: str) -> Path:
    ensure_folder(folder)
    day = night.get("date") or date.today().isoformat()
    path = unique(folder, f"{day} Night shift")
    stories = night.get("stories", [])
    ready = sum(1 for story in stories if story.get("status") == "solved")
    headline = night.get("headline") or (f"{ready} of {len(stories)} stories ready to review" if stories else night.get("reason", "Nothing worked tonight"))
    body = [f"# Night shift, {day}", "", f"**{headline}**", "", f"Quota: {night.get('quota', 'unknown')}"]
    for warning in night.get("warnings", []):
        body.append(f"\n> [!warning] {warning}")
    body.append("")
    for story in stories:
        body += _story(story, browse)
    if night.get("skipped"):
        body += ["## Looked at, not worked", ""] + [f"- [{item['key']}]({browse}{item['key']}): {item['reason']}" for item in night["skipped"]] + [""]
    if night.get("interrupted"):
        body += ["## Interrupted earlier", ""] + [f"- {item}" for item in night["interrupted"]] + [""]
    properties = {"read": False, "status": night.get("status", "done"), "headline": headline, "stories": len(stories)}
    path.write_text(_frontmatter(properties) + "\n".join(body) + "\n")
    return path


def security_note(*, folder: Path, report: Json) -> Path:
    ensure_folder(folder)
    day = report.get("date") or date.today().isoformat()
    path = unique(folder, f"{day} Security")
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
        body += ["```sh", f"cd {report['worktree']}", "git show --stat HEAD", "```", ""]
    if report.get("not_examined"):
        body += ["## Not examined", "", report["not_examined"], ""]
    for warning in report.get("warnings", []):
        body.append(f"> [!warning] {warning}\n")
    path.write_text(_frontmatter({"read": False, "status": report.get("status", "done"), "headline": headline}) + "\n".join(body) + "\n")
    return path
