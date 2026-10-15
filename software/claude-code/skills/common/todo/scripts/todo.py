#!/usr/bin/python3
"""Side tasks per body of work, and ideas per project.

One program owns the file formats so the `todo` and `idea` skills and the three hooks
(SessionStart, Stop, SessionEnd) never disagree. See the skill's SKILL.md for the behavior
and `.claude/plans/2026-10-14_task-command-and-ideas.md` in the dotfiles repo for the why.

Files, all under the main worktree of the current git repo:

  .claude/scratchpad.local/todos.md          one `## <section>` per body of work, one
                                             `- [ ] text  (fields)` line per open task
  .claude/scratchpad.local/todos.state/      listing.<session>.json, offered.<session>,
                                             last-session.json, lock

Runs on the system python, without dependencies, because hooks call it on every session
start and every turn end.
"""

from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CONFIG_DIR = Path(os.path.expanduser("~/.config/dotfiles/todo"))
IDEAS_NOTE_FILE = CONFIG_DIR / "ideas-note"
HOOKS_OFF_VAR = "CLAUDE_TODO_HOOKS"
MAX_LINES_IN_HOOK_OUTPUT = 30

TASK_LINE = re.compile(r"^- \[ \] (?P<text>.*?)  \((?P<fields>.*)\)$")
SECTION_LINE = re.compile(r"^## (?P<name>.+?)\s*$")
STORY_KEY = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")

STANDING_RULE = (
    "When the user's current request is resolved, and before you stop, list the open side "
    "tasks of the current section and ask which to pick up. Do not start one on your own. "
    "Use the `todo` skill for every add, list or close."
)


class TodoError(Exception):
    pass


# ---- git context -------------------------------------------------------------


def git(cwd: Path, *args: str) -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


class Repo:
    def __init__(self, cwd: Path):
        common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
        toplevel = git(cwd, "rev-parse", "--show-toplevel")
        if not common or not toplevel:
            raise TodoError(f"{cwd} is not inside a git repository; side tasks need a project.")
        self.main_worktree = Path(common).parent
        self.worktree = Path(toplevel)
        self.project = self.main_worktree.name
        self.branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"

    @property
    def default_branch(self) -> str:
        head = git(self.main_worktree, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")
        if head:
            return head.rsplit("/", 1)[-1]
        configured = git(self.main_worktree, "config", "--get", "init.defaultBranch")
        if configured:
            return configured
        for name in ("main", "master"):
            if git(self.main_worktree, "rev-parse", "-q", "--verify", f"refs/heads/{name}") is not None:
                return name
        return "main"

    @property
    def branch_section(self) -> Optional[str]:
        """The section name the branch dictates, or None on the default branch or detached."""
        if self.branch in ("HEAD", self.default_branch):
            return None
        return self.branch.replace("/", "-")

    @property
    def worktree_relative(self) -> Optional[str]:
        if self.worktree == self.main_worktree:
            return None
        return os.path.relpath(self.worktree, self.main_worktree)

    @property
    def story_from_branch(self) -> Optional[str]:
        match = STORY_KEY.search(self.branch)
        return match.group(1) if match else None

    @property
    def scratchpad(self) -> Path:
        return self.main_worktree / ".claude" / "scratchpad.local"

    @property
    def todos_file(self) -> Path:
        return self.scratchpad / "todos.md"

    @property
    def state_dir(self) -> Path:
        return self.scratchpad / "todos.state"

    def ensure_dirs(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        gitignore = self.scratchpad / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")


# ---- the todos file ----------------------------------------------------------


class Task:
    def __init__(self, section: str, text: str, fields: List[Tuple[str, str]]):
        self.section = section
        self.text = text
        self.fields = fields

    @property
    def line(self) -> str:
        rendered = "; ".join(f"{key} {value}" if value else key for key, value in self.fields)
        return f"- [ ] {self.text}  ({rendered})"

    def field(self, key: str) -> Optional[str]:
        for name, value in self.fields:
            if name == key:
                return value
        return None

    @staticmethod
    def parse(section: str, line: str) -> Optional["Task"]:
        match = TASK_LINE.match(line)
        if not match:
            return None
        fields: List[Tuple[str, str]] = []
        for part in match.group("fields").split("; "):
            key, _, value = part.partition(" ")
            fields.append((key, value))
        return Task(section, match.group("text"), fields)


class TodoFile:
    """Reads and rewrites todos.md, keeping every line it does not own as it is."""

    def __init__(self, path: Path):
        self.path = path
        self.lines: List[str] = path.read_text().splitlines() if path.exists() else []

    def sections(self) -> List[str]:
        return [m.group("name") for m in map(SECTION_LINE.match, self.lines) if m]

    def tasks(self) -> List[Task]:
        found: List[Task] = []
        section = ""
        for line in self.lines:
            heading = SECTION_LINE.match(line)
            if heading:
                section = heading.group("name")
                continue
            task = Task.parse(section, line)
            if task and section:
                found.append(task)
        return found

    def _section_span(self, name: str) -> Optional[Tuple[int, int]]:
        start = None
        for index, line in enumerate(self.lines):
            heading = SECTION_LINE.match(line)
            if heading is None:
                continue
            if start is not None:
                return start, index
            if heading.group("name") == name:
                start = index
        return (start, len(self.lines)) if start is not None else None

    def add(self, task: Task) -> None:
        span = self._section_span(task.section)
        if span is None:
            if self.lines and self.lines[-1] != "":
                self.lines.append("")
            self.lines.extend([f"## {task.section}", task.line, ""])
            return
        start, end = span
        insert_at = end
        while insert_at > start + 1 and self.lines[insert_at - 1] == "":
            insert_at -= 1
        self.lines.insert(insert_at, task.line)

    def remove(self, task: Task) -> bool:
        span = self._section_span(task.section)
        if span is None:
            return False
        start, end = span
        for index in range(start + 1, end):
            if self.lines[index] == task.line:
                del self.lines[index]
                break
        else:
            return False
        if not any(Task.parse(task.section, line) for line in self.lines[start + 1 : end - 1]):
            del self.lines[start : end - 1]
            while start < len(self.lines) and self.lines[start] == "":
                del self.lines[start]
            while self.lines and self.lines[-1] == "" and (len(self.lines) < 2 or self.lines[-2] == ""):
                del self.lines[-1]
        return True

    def write(self) -> None:
        content = "\n".join(self.lines).rstrip("\n")
        if not content:
            if self.path.exists():
                self.path.unlink()
            return
        atomic_write(self.path, content + "\n")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


class Lock:
    def __init__(self, path: Path):
        self.path = path

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = open(self.path, "w")
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        return self

    def __exit__(self, *_: object) -> None:
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()


# ---- listings and per-session state ------------------------------------------


def open_set_hash(tasks: List[Task]) -> str:
    return hashlib.sha1("\n".join(f"{t.section}\t{t.line}" for t in tasks).encode()).hexdigest()


def order_sections(todo: TodoFile, current: Optional[str]) -> List[str]:
    names = todo.sections()
    if current in names:
        names.remove(current)
        names.insert(0, current)
    return names


def render_listing(
    todo: TodoFile, current: Optional[str], *, everything: bool, cap: Optional[int] = None
) -> Tuple[str, List[Dict[str, str]]]:
    """Numbered listing text plus the number-to-line map that `remove` resolves against."""
    tasks = todo.tasks()
    if not tasks:
        return "No open side tasks.", []
    numbered: List[Dict[str, str]] = []
    out: List[str] = []
    others: List[str] = []
    shown_lines = 0
    for section in order_sections(todo, current):
        in_section = [t for t in tasks if t.section == section]
        if not in_section:
            continue
        if not everything and section != current and current is not None:
            others.append(f"{section} ({len(in_section)})")
            continue
        out.append(section if section != current else f"{section}  (current)")
        for task in in_section:
            if cap is not None and shown_lines >= cap:
                continue
            numbered.append({"n": str(len(numbered) + 1), "section": section, "line": task.line})
            by = task.field("by") or "user"
            out.append(f"  {len(numbered)}. {task.text}  [by {by}, {task.field('added')}]")
            shown_lines += 1
    hidden = len(tasks) - len(numbered)
    if hidden > 0 and cap is not None:
        out.append(f"  … {hidden} more, run the `todo` skill's list for all")
    if others:
        out.append("Other open sections: " + ", ".join(others))
    if current is None and not everything:
        out.insert(0, "No section matches the current branch; showing every open section.")
    return "\n".join(out), numbered


def listing_cache(repo: Repo, session: str) -> Path:
    return repo.state_dir / f"listing.{session}.json"


def offered_file(repo: Repo, session: str) -> Path:
    return repo.state_dir / f"offered.{session}"


def marker_file(repo: Repo) -> Path:
    return repo.state_dir / "last-session.json"


def now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


# ---- subcommands -------------------------------------------------------------


def cmd_add(args: argparse.Namespace, repo: Repo) -> int:
    section = repo.branch_section or args.section
    if not section:
        raise TodoError(
            f"On the default branch ({repo.branch}) pass --section <work-name>: the scratchpad "
            "work-name of this body of work, or YYYY-MM-DD_<description>."
        )
    session_value = args.session
    if args.title:
        session_value += f' "{args.title}"'
    fields: List[Tuple[str, str]] = [("by", args.by), ("added", now()), ("session", session_value), ("branch", repo.branch)]
    if repo.worktree_relative:
        fields.append(("worktree", repo.worktree_relative))
    story = args.story or repo.story_from_branch
    if story:
        fields.append(("story", story))
    fields.append(("while", args.while_doing))
    task = Task(section, args.text.strip(), fields)
    repo.ensure_dirs()
    with Lock(repo.state_dir / "lock"):
        todo = TodoFile(repo.todos_file)
        todo.add(task)
        todo.write()
    print(f"Added to section {section} of {repo.todos_file}:\n{task.line}")
    return 0


def cmd_list(args: argparse.Namespace, repo: Repo) -> int:
    todo = TodoFile(repo.todos_file)
    text, numbered = render_listing(todo, repo.branch_section, everything=args.all)
    if numbered:
        repo.ensure_dirs()
        atomic_write(listing_cache(repo, args.session), json.dumps(numbered))
    print(text)
    return 0


def cmd_remove(args: argparse.Namespace, repo: Repo) -> int:
    cache = listing_cache(repo, args.session)
    if not cache.exists():
        raise TodoError("No listing in this session yet; run `list` first, then remove by its number.")
    numbered = json.loads(cache.read_text())
    entry = next((e for e in numbered if e["n"] == str(args.number)), None)
    with Lock(repo.state_dir / "lock"):
        todo = TodoFile(repo.todos_file)
        task = None
        if entry:
            task = next((t for t in todo.tasks() if t.section == entry["section"] and t.line == entry["line"]), None)
        if task is None:
            text, fresh = render_listing(todo, repo.branch_section, everything=True)
            atomic_write(cache, json.dumps(fresh))
            raise TodoError(f"Number {args.number} is stale; the file changed since the last listing. Fresh listing:\n{text}")
        todo.remove(task)
        todo.write()
    remaining = [e for e in numbered if e is not entry]
    atomic_write(cache, json.dumps(remaining))
    print(f"Removed from section {task.section}:\n{task.line}")
    return 0


def ideas_note_path() -> Path:
    if not IDEAS_NOTE_FILE.is_file():
        raise TodoError(
            f"{IDEAS_NOTE_FILE} is missing. Create it with the absolute path of the ideas note "
            "inside your Obsidian vault, for example <vault>/Ideas.md."
        )
    note = Path(IDEAS_NOTE_FILE.read_text().strip()).expanduser()
    if not any((parent / ".obsidian").is_dir() for parent in note.parents):
        raise TodoError(f"{note} is not inside an Obsidian vault (no .obsidian/ folder above it).")
    return note


def append_idea(note: Path, project: str, text: str) -> str:
    lines = note.read_text().splitlines() if note.exists() else ["# Ideas", ""]
    bullet = f"- {dt.date.today().isoformat()}: {text.strip()}"
    headings = [(i, m.group("name")) for i, m in enumerate(map(SECTION_LINE.match, lines)) if m]
    names = [name for _, name in headings]
    if project in names:
        start = headings[names.index(project)][0]
        end = next((i for i, _ in headings if i > start), len(lines))
        insert_at = end
        while insert_at > start + 1 and lines[insert_at - 1] == "":
            insert_at -= 1
        lines.insert(insert_at, bullet)
    else:
        later = next(((i, name) for i, name in headings if name.lower() > project.lower()), None)
        block = [f"## {project}", "", bullet, ""]
        if later is None:
            if lines and lines[-1] != "":
                lines.append("")
            lines.extend(block)
        else:
            lines[later[0] : later[0]] = block
    atomic_write(note, "\n".join(lines).rstrip("\n") + "\n")
    return bullet


def cmd_idea(args: argparse.Namespace, repo: Optional[Repo]) -> int:
    note = ideas_note_path()
    project = repo.project if repo else "General"
    lock_dir = (repo.state_dir if repo else CONFIG_DIR)
    lock_dir.mkdir(parents=True, exist_ok=True)
    with Lock(lock_dir / "ideas.lock"):
        bullet = append_idea(note, project, args.text)
    print(f"Added under ## {project} in {note}:\n{bullet}")
    return 0


# ---- hooks -------------------------------------------------------------------


def hook_input() -> Dict[str, object]:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}
    return data if isinstance(data, dict) else {}


def hooks_off() -> bool:
    return os.environ.get(HOOKS_OFF_VAR) == "0"


def emit(event: str, context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": context}}))


def repo_for_hook(data: Dict[str, object]) -> Optional[Repo]:
    cwd = Path(str(data.get("cwd") or os.getcwd()))
    try:
        return Repo(cwd)
    except TodoError:
        return None


def cmd_session_start(_: argparse.Namespace, __: Optional[Repo]) -> int:
    if hooks_off():
        return 0
    data = hook_input()
    repo = repo_for_hook(data)
    if repo is None:
        return 0
    session = str(data.get("session_id") or "default")
    todo = TodoFile(repo.todos_file)
    tasks = todo.tasks()
    marker = marker_file(repo)
    parts: List[str] = []
    if marker.exists():
        try:
            last = json.loads(marker.read_text())
        except json.JSONDecodeError:
            last = {}
        marker.unlink()
        if last.get("open"):
            who = last.get("title") or str(last.get("session", ""))[:8]
            parts.append(
                f"The last session on this project ({who}, {last.get('ended')}) ended with "
                f"{last['open']} open side task(s). Ask the user which to pick up, drop, or turn into ideas."
            )
    if not tasks and not parts:
        return 0
    parts.append(f"Side tasks for this project are in {repo.todos_file}. This session's id is {session}.")
    parts.append(STANDING_RULE)
    if tasks:
        text, _ = render_listing(todo, repo.branch_section, everything=True, cap=MAX_LINES_IN_HOOK_OUTPUT)
        parts.append(
            "Open side tasks by section; judge which sections belong to the current work and "
            "mention the others in one line:\n" + text
        )
    repo.ensure_dirs()
    atomic_write(offered_file(repo, session), open_set_hash(tasks))
    emit("SessionStart", "\n\n".join(parts))
    return 0


def cmd_stop(_: argparse.Namespace, __: Optional[Repo]) -> int:
    if hooks_off():
        return 0
    data = hook_input()
    if data.get("stop_hook_active"):
        return 0
    repo = repo_for_hook(data)
    if repo is None:
        return 0
    session = str(data.get("session_id") or "default")
    todo = TodoFile(repo.todos_file)
    tasks = todo.tasks()
    current = open_set_hash(tasks)
    offered = offered_file(repo, session)
    previous = offered.read_text() if offered.exists() else None
    if previous == current or (previous is None and not tasks):
        return 0
    repo.ensure_dirs()
    atomic_write(offered, current)
    if not tasks:
        emit("Stop", "No open side tasks remain. If this reply already said so, add nothing.")
        return 0
    text, _ = render_listing(todo, repo.branch_section, everything=False, cap=MAX_LINES_IN_HOOK_OUTPUT)
    emit(
        "Stop",
        "The open side tasks changed:\n"
        + text
        + "\n\nIf this reply already reported the change, add at most one short line. "
        "Otherwise offer the open tasks when the request is resolved. Do not start one on your own.",
    )
    return 0


def notify(message: str) -> None:
    script = f'display notification {json.dumps(message)} with title "Claude Code"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=1.2, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pass


def cmd_session_end(_: argparse.Namespace, __: Optional[Repo]) -> int:
    if hooks_off():
        return 0
    data = hook_input()
    repo = repo_for_hook(data)
    if repo is None:
        return 0
    tasks = TodoFile(repo.todos_file).tasks()
    marker = marker_file(repo)
    if not tasks:
        if marker.exists():
            marker.unlink()
        return 0
    per_section: Dict[str, int] = {}
    for task in tasks:
        per_section[task.section] = per_section.get(task.section, 0) + 1
    repo.ensure_dirs()
    atomic_write(
        marker,
        json.dumps(
            {
                "session": data.get("session_id"),
                "title": data.get("session_title"),
                "ended": now(),
                "reason": data.get("reason"),
                "open": len(tasks),
                "sections": per_section,
            }
        ),
    )
    if data.get("reason") in ("prompt_input_exit", "logout", "other"):
        summary = ", ".join(f"{name} ({count})" for name, count in per_section.items())
        notify(f"{len(tasks)} open side task(s) left in {repo.project}: {summary}")
    return 0


# ---- entry point -------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cwd", default=os.getcwd(), help="directory to resolve the project from")
    parser.add_argument(
        "--session",
        default=os.environ.get("CLAUDE_CODE_SESSION_ID", "default"),
        help="session id; defaults to $CLAUDE_CODE_SESSION_ID",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add a side task to the current section")
    add.add_argument("--by", choices=("user", "claude"), required=True)
    add.add_argument("--text", required=True)
    add.add_argument("--while", dest="while_doing", required=True, help="what the session was doing")
    add.add_argument("--section", help="work-name, required on the default branch")
    add.add_argument("--story", help="Jira key when the branch name does not carry it")
    add.add_argument("--title", help="session title, when the session has one")
    add.set_defaults(func=cmd_add, needs_repo=True)

    lst = sub.add_parser("list", help="list open side tasks with numbers")
    lst.add_argument("--all", action="store_true", help="every section in full")
    lst.set_defaults(func=cmd_list, needs_repo=True)

    rm = sub.add_parser("remove", help="remove a task by its number from the last listing")
    rm.add_argument("number", type=int)
    rm.set_defaults(func=cmd_remove, needs_repo=True)

    idea = sub.add_parser("idea", help="append an idea to the project's section of the ideas note")
    idea.add_argument("--text", required=True)
    idea.set_defaults(func=cmd_idea, needs_repo=False)

    for name, func in (("session-start", cmd_session_start), ("stop", cmd_stop), ("session-end", cmd_session_end)):
        hook = sub.add_parser(name, help=f"{name} hook; reads the hook JSON on stdin")
        hook.set_defaults(func=func, needs_repo=False, is_hook=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if getattr(args, "is_hook", False):
            return args.func(args, None)
        cwd = Path(args.cwd)
        if args.needs_repo:
            return args.func(args, Repo(cwd))
        try:
            repo: Optional[Repo] = Repo(cwd)
        except TodoError:
            repo = None
        return args.func(args, repo)
    except TodoError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
