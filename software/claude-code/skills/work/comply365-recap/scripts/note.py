#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Write recap, catch-up and failure notes into the configured vault folder.

The note format lives here, not in the prompt, so every note has the same properties and layout.
Each note starts with `read: false`; the folder's Base lists unread notes and lets the user tick them.

Modes:
  --work-dir DIR   write the recap from DIR/collected.json and DIR/recap.json (exit 4 when invalid)
  --unread         print, as JSON, the unread recaps and whether a catch-up note is due
  --catch-up DIR   write the catch-up note from DIR/catch-up.json over the unread recaps (exit 4 when invalid)
  --error TEXT     write or update the single failure note
"""

import argparse
import json
import re
import sys
import urllib.parse
from datetime import date, datetime
from pathlib import Path
from typing import Any, NoReturn

from common import (
    CATCH_UP_SUFFIX,
    CATCH_UP_THRESHOLD,
    FAILED_SUFFIX,
    RECAP_SUFFIX,
    covered_workdays,
    note_name,
    notes,
    previous_workday,
    read_folder,
    read_properties,
    short_day,
    trash,
    unread_catch_ups,
    unread_recaps,
)

ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?")
EXIT_INVALID = 4
KINDS = {
    "new": "New",
    "improved": "Improved",
    "fixed": "Fixed",
    "under_the_hood": "Under the hood",
}

type Json = dict[str, Any]


def invalid(problems: list[str]) -> NoReturn:
    print("INVALID:\n" + "\n".join(f"- {problem}" for problem in problems), file=sys.stderr)
    sys.exit(EXIT_INVALID)


def commits_by_sha(collected: Json) -> dict[str, Json]:
    return {
        commit["sha"]: commit | {"repo": repo["name"], "product": repo["product"]}
        for repo in collected["repos"]
        for commit in repo["commits"]
    }


def resolve_sha(*, reference: str, commits: dict[str, Json]) -> str | None:
    matches = [sha for sha in commits if sha.startswith(reference)]
    return matches[0] if len(matches) == 1 else None


def commit_for(*, reference: str, commits: dict[str, Json]) -> Json:
    sha = resolve_sha(reference=reference, commits=commits)
    if sha is None:
        raise KeyError(f"validate() lets no unknown commit through, yet got {reference!r}")
    return commits[sha]


def validate(*, recap: Json, commits: dict[str, Json]) -> None:
    problems = []
    referenced = set()
    for item in recap.get("items", []):
        if item.get("kind") not in KINDS:
            problems.append(f"item {item.get('title')!r} has kind {item.get('kind')!r}; use one of {list(KINDS)}")
        for reference in item.get("commits", []):
            sha = resolve_sha(reference=reference, commits=commits)
            if sha is None:
                problems.append(f"item {item.get('title')!r} names unknown or ambiguous commit {reference!r}")
            else:
                referenced.add(sha)
    for reference in recap.get("minor_commits", []):
        sha = resolve_sha(reference=reference, commits=commits)
        if sha is None:
            problems.append(f"minor_commits names unknown or ambiguous commit {reference!r}")
        else:
            referenced.add(sha)
    for sha, commit in commits.items():
        if sha not in referenced:
            problems.append(
                f"commit {commit['short_sha']} ({commit['repo']}: {commit['subject']}) "
                "is in no item and not in minor_commits"
            )
    if problems:
        invalid(problems)


def link_target(name: str) -> str:
    return urllib.parse.quote(name)


def note_link(name: str) -> str:
    return f"[{name}]({link_target(name + '.md')})"


def table_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def yaml_scalar(value: Any) -> str:
    # Unquoted, so Obsidian types the property as a date and sorts on it.
    if isinstance(value, str) and ISO_DATE.fullmatch(value):
        return value
    # JSON scalars are valid YAML scalars, so json.dumps quotes every other string safely.
    return json.dumps(value, ensure_ascii=False)


def frontmatter(properties: Json) -> str:
    lines = ["---"]
    for key, value in properties.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            lines.extend(f"  - {yaml_scalar(entry)}" for entry in value)
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def document(*, properties: Json, blocks: list[str]) -> str:
    # The text starts right below the properties: an empty line there shows as an empty first line in Obsidian.
    return frontmatter(properties) + "\n" + "\n\n".join(blocks) + "\n"


def quoted(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def link_line(*, jira_keys: list[str], slack: list[Json], issues: Json, browse_url: str) -> str:
    links = []
    for key in jira_keys:
        status = issues.get(key, {}).get("status")
        links.append(f"[{key}]({browse_url}{key})" + (f" ({status})" if status else ""))
    links.extend(f"[{link['label']}]({link['url']})" for link in slack)
    return " · ".join(links)


def commit_table(commits: list[Json]) -> str:
    rows = ["| Commit | Project | Change | Author | Size |", "|---|---|---|---|---|"]
    for commit in commits:
        added = sum(change["added"] for change in commit["files"])
        deleted = sum(change["deleted"] for change in commit["files"])
        file_count = len(commit["files"]) + commit["files_not_listed"]
        rows.append(
            f"| [{commit['short_sha']}]({commit['url']}) | {commit['repo']} | {table_cell(commit['subject'])} "
            f"| {table_cell(commit['author'])} | {file_count} {'file' if file_count == 1 else 'files'} +{added} −{deleted} |"
        )
    return "\n".join(rows)


def render_item(*, item: Json, recap: Json, commits: dict[str, Json], browse_url: str) -> str:
    item_commits = [commit_for(reference=reference, commits=commits) for reference in item.get("commits", [])]
    products = sorted({commit["product"] for commit in item_commits})
    links = link_line(
        jira_keys=item.get("jira", []),
        slack=item.get("slack", []),
        issues=recap.get("jira_issues", {}),
        browse_url=browse_url,
    )
    meta = " · ".join(part for part in (" · ".join(f"*{product}*" for product in products), links) if part)
    parts = [f"### {item['title']}"]
    if meta:
        parts.append(meta)
    parts.append(item["summary"].strip())
    technical = []
    if item.get("details"):
        technical.append(item["details"].strip())
    if item.get("diagram"):
        technical.append(f"```mermaid\n{item['diagram'].strip()}\n```")
    if item_commits:
        technical.append(commit_table(item_commits))
    if technical:
        parts.append("> [!info]- Technical details\n" + quoted("\n\n".join(technical)))
    return "\n\n".join(parts)


def render_entries(*, heading: str, entries: list[Json], issues: Json, browse_url: str) -> str:
    blocks = [f"## {heading}"]
    for entry in entries:
        block = [f"### {entry['title']}"]
        links = link_line(
            jira_keys=entry.get("jira", []), slack=entry.get("slack", []), issues=issues, browse_url=browse_url
        )
        if links:
            block.append(links)
        block.append(entry["summary"].strip())
        if entry.get("recaps"):
            block.append("From " + ", ".join(note_link(name) for name in entry["recaps"]))
        blocks.append("\n\n".join(block))
    return "\n\n".join(blocks)


def previous_recap(*, folder: Path, day: date) -> str | None:
    earlier = [path.stem for path in notes(folder=folder, suffix=RECAP_SUFFIX) if path.name[:10] < day.isoformat()]
    return earlier[-1] if earlier else None


def related_line(*, folder: Path, day: date) -> str:
    previous = previous_recap(folder=folder, day=day)
    base = f"[All recaps]({link_target(folder.name + '.base')})"
    return f"Related: {note_link(previous)} · {base}" if previous else f"Related: {base}"


def render_recap(*, recap: Json, collected: Json, folder: Path, days: tuple[date, ...]) -> str:
    commits = commits_by_sha(collected)
    browse_url = collected["jira"]["browse_url"]
    start = datetime.fromisoformat(collected["window"]["start"])
    end = datetime.fromisoformat(collected["window"]["end"])
    items = recap.get("items", [])
    counts = {kind: sum(1 for item in items if item["kind"] == kind) for kind in KINDS}
    issues = recap.get("jira_issues", {})

    properties: Json = {
        "read": False,
        "headline": recap["headline"],
        # Where the next run starts; collect.py and prepare.py read it.
        "window_end": f"{end:%Y-%m-%dT%H:%M}",
    }

    glance = " · ".join(
        f"[{counts[kind]} {label.lower()}](#{link_target(label)})" for kind, label in KINDS.items() if counts[kind]
    )
    if recap.get("heading_next"):
        glance += (" · " if glance else "") + f"[coming up](#{link_target('Coming up')})"

    body = [f"# {recap['headline']}", recap["summary"].strip()]
    if glance:
        body.append(glance)
    if not items:
        body.append("Nothing reached main in this window.")
    for kind, label in KINDS.items():
        kind_items = [item for item in items if item["kind"] == kind]
        if kind_items:
            body.append(f"## {label}")
            body.extend(
                render_item(item=item, recap=recap, commits=commits, browse_url=browse_url) for item in kind_items
            )
    if recap.get("heading_next"):
        body.append(
            render_entries(heading="Coming up", entries=recap["heading_next"], issues=issues, browse_url=browse_url)
        )

    sources = [
        "## Sources",
        (
            f"Commits that reached `main` between {start:%a %-d %b %H:%M} and {end:%a %-d %b %H:%M}, "
            "matched with Jira stories and team Slack threads."
        ),
        "\n".join(
            f"- {repo['product']} (`{repo['name']}`): {len(repo['commits'])} commits, "
            f"main at [{repo['head']}]({repo['web_url']})"
            for repo in collected["repos"]
        ),
    ]
    minor = [commit_for(reference=reference, commits=commits) for reference in recap.get("minor_commits", [])]
    if minor:
        sources.append(
            "Left out as too small to mention: "
            + ", ".join(f"[{commit['short_sha']}]({commit['url']}) {commit['subject']}" for commit in minor)
        )
    if recap.get("notes"):
        sources.append("Gaps in this recap:\n" + "\n".join(f"- {note}" for note in recap["notes"]))
    body.append("\n\n".join(sources))
    body.append(related_line(folder=folder, day=days[0]))
    return document(properties=properties, blocks=body)


def write_recap(*, folder: Path, work_dir: Path) -> Path:
    collected = json.loads((work_dir / "collected.json").read_text())
    recap = json.loads((work_dir / "recap.json").read_text())
    validate(recap=recap, commits=commits_by_sha(collected))

    days = covered_workdays(
        start=datetime.fromisoformat(collected["window"]["start"]),
        end=datetime.fromisoformat(collected["window"]["end"]),
    )
    note = folder / f"{note_name(first=days[0], last=days[-1], suffix=RECAP_SUFFIX)}.md"
    note.write_text(render_recap(recap=recap, collected=collected, folder=folder, days=days))
    # A successful recap starts where the last one ended, so it covers whatever the failed runs missed.
    for failed in notes(folder=folder, suffix=FAILED_SUFFIX):
        trash(failed)
    return note


def write_failure(*, folder: Path, error: str, now: datetime) -> Path:
    """One failure note, however many runs fail in a row: it keeps its name, the first workday without a recap."""
    existing = notes(folder=folder, suffix=FAILED_SUFFIX)
    if existing:
        note = existing[0]
        for extra in existing[1:]:
            trash(extra)
    else:
        day = previous_workday(now.date())
        note = folder / f"{note_name(first=day, last=day, suffix=FAILED_SUFFIX)}.md"
    headline = f"Recaps missing since {short_day(date.fromisoformat(note.name[:10]))}"
    note.write_text(
        document(
            properties={"read": False, "headline": headline},
            blocks=[
                f"# {headline}",
                f"> [!warning] Latest error ({now:%a %-d %b %H:%M})\n{quoted(error.strip())}",
                (
                    "Nothing is lost: once the cause is fixed, the next run covers everything since the last "
                    "recap and moves this note to the Trash. It runs at 07:47 on weekdays and after you log in. "
                    "To run it now: `launchctl kickstart gui/$(id -u)/com.dotfiles.comply365-recap`. "
                    "Run log: `~/Library/Logs/recap.log`."
                ),
                related_line(folder=folder, day=date.fromisoformat(note.name[:10])),
            ],
        )
    )
    return note


def unread_report(folder: Path) -> Json:
    recaps = unread_recaps(folder)
    current = unread_catch_ups(folder)
    covered = set(read_properties(current[-1]).get("covers", [])) if current else set()
    names = [path.stem for path in recaps]
    return {
        "unread_recaps": [
            {"name": path.stem, "path": str(path), "headline": read_properties(path).get("headline")} for path in recaps
        ],
        "catch_up_due": len(recaps) >= CATCH_UP_THRESHOLD and covered != set(names),
        "threshold": CATCH_UP_THRESHOLD,
    }


def write_catch_up(*, folder: Path, work_dir: Path, browse_url: str) -> Path:
    catch_up = json.loads((work_dir / "catch-up.json").read_text())
    recaps = unread_recaps(folder)
    names = [path.stem for path in recaps]
    problems = [
        f"theme {theme.get('title')!r} names {name!r}, which is not an unread recap"
        for theme in catch_up.get("themes", [])
        for name in theme.get("recaps", [])
        if name not in names
    ]
    if len(recaps) < CATCH_UP_THRESHOLD:
        problems.append(f"only {len(recaps)} unread recaps; a catch-up needs {CATCH_UP_THRESHOLD}")
    if problems:
        invalid(problems)

    first = date.fromisoformat(recaps[0].name[:10])
    last_end = datetime.fromisoformat(str(read_properties(recaps[-1])["window_end"]))
    last = max(first, previous_workday(last_end.date()))
    name = note_name(first=first, last=last, suffix=CATCH_UP_SUFFIX)
    properties: Json = {
        "read": False,
        "headline": catch_up["headline"],
        # prepare.py removes it once it has passed the read tick on, so a recap unticked later stays unread.
        "covers": names,
    }
    issues = catch_up.get("jira_issues", {})
    body = [
        f"# {catch_up['headline']}",
        catch_up["summary"].strip(),
        (
            f"> [!tip] {len(recaps)} recaps in one page\n"
            "> Tick **read** on this note, and the next run (at 07:47, or when you log in) "
            "marks every recap below as read."
        ),
        render_entries(
            heading="What changed", entries=catch_up.get("themes", []), issues=issues, browse_url=browse_url
        ),
        "## The recaps in this catch-up\n\n"
        + "\n".join(
            f"- {note_link(path.stem)}: {read_properties(path).get('headline', '')}" for path in reversed(recaps)
        ),
        f"Related: [All recaps]({link_target(folder.name + '.base')})",
    ]
    note = folder / f"{name}.md"
    for stale in unread_catch_ups(folder):
        trash(stale)
    note.write_text(document(properties=properties, blocks=body))
    return note


BASE = """filters:
  and:
    - file.inFolder("{folder}")
formulas:
  pinned: 'if(file.name.contains("Catch-up"), 1, if(file.name.contains("failed"), 2, 3))'
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
        - "read != true"
    order:
      - file.name
      - read
      - headline
    sort:
      - property: formula.pinned
        direction: ASC
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


def ensure_base(folder: Path) -> None:
    base = folder / f"{folder.name}.base"
    if not base.exists():
        base.write_text(BASE.format(folder=folder.name))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--work-dir", type=Path)
    mode.add_argument("--unread", action="store_true")
    mode.add_argument("--catch-up", type=Path, metavar="WORK_DIR")
    mode.add_argument("--error")
    arguments = parser.parse_args()

    folder = read_folder()
    ensure_base(folder)

    if arguments.unread:
        print(json.dumps(unread_report(folder), indent=2))
    elif arguments.error:
        print(write_failure(folder=folder, error=arguments.error, now=datetime.now().astimezone()))
    elif arguments.catch_up:
        collected = json.loads((arguments.catch_up / "collected.json").read_text())
        print(write_catch_up(folder=folder, work_dir=arguments.catch_up, browse_url=collected["jira"]["browse_url"]))
    else:
        print(write_recap(folder=folder, work_dir=arguments.work_dir))


if __name__ == "__main__":
    main()
