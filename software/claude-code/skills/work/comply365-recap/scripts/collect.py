#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Collect the commits that reached each recap project's main branch during the recap window.

Reads the GitLab REST API, not local clones: GitLab refuses git fetch once the group's SAML SSO
session expires, which it often has by the time the job runs, while API access with a token keeps working.
Writes ~/.local/state/recap/work/<date>/collected.json and prints a summary.
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, NoReturn

from common import (
    CONFIG_DIR,
    RECAP_SUFFIX,
    RUN_TIME,
    covered_workdays,
    last_run_slot,
    notes,
    previous_workday,
    read_folder,
    read_properties,
    setup_error,
)

PROJECTS_FILE = CONFIG_DIR / "projects.txt"
CHANNEL_FILE = CONFIG_DIR / "channel"
JIRA_FILE = Path.home() / ".config" / "dotfiles" / "jira"
KEYCHAIN_SERVICE = "recap-gitlab-token"
BRANCH = "main"
# Not under a .claude/ folder: Claude Code asks before every write there, and nobody answers a scheduled run.
WORK_ROOT = Path.home() / ".local" / "state" / "recap" / "work"
MAX_FILES_PER_COMMIT = 40
MAX_BODY_CHARS = 2000
PAGE_SIZE = 100
EXIT_GITLAB_ERROR = 3

type Json = dict[str, Any]


@dataclass(frozen=True)
class ProjectConfig:
    web_url: str
    product: str

    @property
    def api_base(self) -> str:
        parts = urllib.parse.urlsplit(self.web_url)
        project = urllib.parse.quote(parts.path.strip("/"), safe="")
        return f"{parts.scheme}://{parts.netloc}/api/v4/projects/{project}"

    @property
    def name(self) -> str:
        return self.web_url.rstrip("/").rsplit("/", 1)[1]


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int
    deleted: int


@dataclass(frozen=True)
class Commit:
    sha: str
    short_sha: str
    author: str
    committed_at: str
    subject: str
    body: str
    story_keys: tuple[str, ...]
    no_id: bool
    url: str
    files: tuple[FileChange, ...]
    files_not_listed: int


@dataclass(frozen=True)
class ProjectResult:
    name: str
    product: str
    web_url: str
    head: str
    commits: tuple[Commit, ...]


@dataclass(frozen=True)
class JiraConfig:
    browse_url: str
    project_key: str


def gitlab_error(message: str) -> NoReturn:
    print(f"GITLAB ERROR: {message}", file=sys.stderr)
    sys.exit(EXIT_GITLAB_ERROR)


def read_projects() -> tuple[ProjectConfig, ...]:
    if not PROJECTS_FILE.is_file():
        setup_error(f"{PROJECTS_FILE} is missing. See One-time setup in the recap SKILL.md.")
    projects = []
    for line in PROJECTS_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        url, _, product = line.partition("|")
        url = url.strip().rstrip("/")
        if not re.fullmatch(r"https://[^/]+/.+/[^/]+", url):
            setup_error(f"{url!r} in {PROJECTS_FILE} is not a project URL like https://gitlab.com/<group>/<project>")
        projects.append(ProjectConfig(web_url=url, product=product.strip() or url.rsplit("/", 1)[1]))
    if not projects:
        setup_error(f"{PROJECTS_FILE} lists no projects.")
    return tuple(projects)


def read_jira() -> JiraConfig:
    if not JIRA_FILE.is_file():
        setup_error(f"{JIRA_FILE} is missing. It holds the browse URL prefix, e.g. https://<site>/browse/<KEY>-")
    match = re.fullmatch(r"(https://[^/]+/browse/)([A-Z][A-Z0-9]+)-", JIRA_FILE.read_text().strip())
    if not match:
        setup_error(f"{JIRA_FILE} must hold one line like https://<site>/browse/<KEY>-")
    return JiraConfig(browse_url=match.group(1), project_key=match.group(2))


def read_channel() -> str:
    if not CHANNEL_FILE.is_file():
        setup_error(f"{CHANNEL_FILE} is missing. It holds the team channel ID (C…).")
    return CHANNEL_FILE.read_text().strip()


def read_token() -> str:
    lookup = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if lookup.returncode != 0:
        setup_error(f"no Keychain item {KEYCHAIN_SERVICE!r}. See One-time setup in the recap SKILL.md.")
    return lookup.stdout.strip()


def last_recap_end(*, folder: Path, now: datetime) -> datetime | None:
    """The window end of the newest recap.

    Notes are named after the days they cover, not the day they were written, so this reads `window_end`.
    """
    ends = []
    for recap in notes(folder=folder, suffix=RECAP_SUFFIX):
        window_end = read_properties(recap).get("window_end")
        if isinstance(window_end, str):
            ends.append(datetime.fromisoformat(window_end).replace(tzinfo=now.tzinfo))
    return max(ends, default=None)


def resolve_window(*, last_end: datetime | None, now: datetime) -> Window:
    """From where the last recap ended, however long ago, so no commit is told twice or missed.

    The very first run, with no recap yet, starts at the run time one workday before the one it is due for.
    """
    if last_end is None:
        day = previous_workday(last_run_slot(now).date())
        return Window(start=datetime.combine(day, RUN_TIME, tzinfo=now.tzinfo), end=now)
    return Window(start=last_end, end=now)


class GitLab:
    def __init__(self, token: str) -> None:
        self.token = token

    def get(self, url: str) -> Any:
        request = urllib.request.Request(url, headers={"PRIVATE-TOKEN": self.token})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            if error.code in (401, 403):
                setup_error(f"GitLab refused the token ({error.code}): {detail}. Renew it, see One-time setup.")
            gitlab_error(f"{error.code} for {url}: {detail}")
        except urllib.error.URLError as error:
            gitlab_error(f"cannot reach {url}: {error.reason}")

    def pages(self, url: str) -> list[Json]:
        items: list[Json] = []
        page = 1
        while True:
            separator = "&" if "?" in url else "?"
            batch = self.get(f"{url}{separator}per_page={PAGE_SIZE}&page={page}")
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                return items
            page += 1


def file_change(*, path: str, diff: str) -> FileChange:
    lines = diff.splitlines()
    return FileChange(
        path=path,
        added=sum(1 for line in lines if line.startswith("+") and not line.startswith("+++")),
        deleted=sum(1 for line in lines if line.startswith("-") and not line.startswith("---")),
    )


def file_changes(*, gitlab: GitLab, project: ProjectConfig, sha: str) -> tuple[tuple[FileChange, ...], int]:
    diffs = gitlab.pages(f"{project.api_base}/repository/commits/{sha}/diff")
    changes = tuple(
        file_change(path=diff["new_path"], diff=diff.get("diff", "")) for diff in diffs[:MAX_FILES_PER_COMMIT]
    )
    return changes, max(0, len(diffs) - MAX_FILES_PER_COMMIT)


def collect_project(
    *, gitlab: GitLab, project: ProjectConfig, window: Window, key_pattern: re.Pattern[str]
) -> ProjectResult:
    query = urllib.parse.urlencode(
        {"ref_name": BRANCH, "since": window.start.isoformat(), "until": window.end.isoformat()}
    )
    commits = []
    for raw in gitlab.pages(f"{project.api_base}/repository/commits?{query}"):
        if len(raw["parent_ids"]) > 1:
            continue
        files, files_not_listed = file_changes(gitlab=gitlab, project=project, sha=raw["id"])
        subject, _, body = raw["message"].partition("\n")
        commits.append(
            Commit(
                sha=raw["id"],
                short_sha=raw["short_id"],
                author=raw["author_name"],
                committed_at=raw["committed_date"],
                subject=subject.strip(),
                body=body.strip()[:MAX_BODY_CHARS],
                story_keys=tuple(sorted(set(key_pattern.findall(raw["message"])))),
                no_id="[NO-ID]" in subject,
                url=raw["web_url"],
                files=files,
                files_not_listed=files_not_listed,
            )
        )
    # The newest commit, not the branches endpoint: a fine-grained token may read commits but not branches.
    newest = gitlab.get(
        f"{project.api_base}/repository/commits?{urllib.parse.urlencode({'ref_name': BRANCH})}&per_page=1"
    )
    head = newest[0]["short_id"] if newest else "(empty)"
    return ProjectResult(
        name=project.name, product=project.product, web_url=project.web_url, head=head, commits=tuple(commits)
    )


def work_directory(today: date) -> Path:
    directory = WORK_ROOT / today.isoformat()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def main() -> None:
    projects = read_projects()
    jira = read_jira()
    channel = read_channel()
    gitlab = GitLab(read_token())
    now = datetime.now().astimezone()
    window = resolve_window(last_end=last_recap_end(folder=read_folder(), now=now), now=now)
    workdays = covered_workdays(start=window.start, end=window.end)

    key_pattern = re.compile(rf"\b{jira.project_key}-\d+\b")
    results = tuple(
        collect_project(gitlab=gitlab, project=project, window=window, key_pattern=key_pattern) for project in projects
    )
    story_keys = sorted(
        {key for result in results for commit in result.commits for key in commit.story_keys},
        key=lambda key: int(key.rsplit("-", 1)[1]),
    )

    directory = work_directory(window.end.date())
    output = directory / "collected.json"
    output.write_text(
        json.dumps(
            {
                "generated_at": window.end.isoformat(),
                "window": {"start": window.start.isoformat(), "end": window.end.isoformat()},
                "workdays": [day.isoformat() for day in workdays],
                "jira": asdict(jira),
                "slack_channel": channel,
                "story_keys": story_keys,
                "repos": [asdict(result) for result in results],
            },
            indent=2,
        )
    )

    print(f"window: {window.start:%a %Y-%m-%d %H:%M} -> {window.end:%a %Y-%m-%d %H:%M %Z}, {len(workdays)} workdays")
    for result in results:
        print(f"{result.name} ({result.product}): {len(result.commits)} commits, {BRANCH} at {result.head}")
    print(f"story keys: {', '.join(story_keys) or '(none)'}")
    print(f"slack channel: {channel}")
    print(f"work dir: {directory}")


if __name__ == "__main__":
    main()
