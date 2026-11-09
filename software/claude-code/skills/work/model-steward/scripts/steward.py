# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Run the scheduled jobs of every introspective skill on the strongest Claude model, at its own default effort.

  steward.py [--commit]

The strongest model comes from ai-capacity's `capacity.json` (`claude.strongest`). An introspective skill
says `introspective: true` in its frontmatter. The `--model` and `--effort` of every scheduled job that runs
it (`claude -p "/<skill> …"` in software/claude-code/*.sh) are set; its own `model:` and `effort:` are
removed, because an interactive lookup must stay on the session's model: the weekly refresh is where the
strongest model pays off, and a lookup pinned to it cost a tenth of a week's usage. The effort is written out
on purpose: without it the user's own `modelSettings` override would apply, and the rule is the model's own
default.

With --commit, the changed files are committed by pathspec, and only when each was unmodified before, so the
user's other work never rides along. Nothing is pushed.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DOTFILES = Path(__file__).resolve().parents[6]
SKILLS = DOTFILES / "software" / "claude-code" / "skills"
JOBS = DOTFILES / "software" / "claude-code"
CAPACITY = Path.home() / ".local" / "state" / "ai-capacity" / "capacity.json"
EFFORTS = ("low", "medium", "high", "xhigh", "max")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(DOTFILES), *args], capture_output=True, text=True, check=True).stdout


def strongest() -> tuple[str, str]:
    if not CAPACITY.is_file():
        sys.exit(f"no {CAPACITY}: run /ai-capacity refresh first; nothing changed")
    data = json.loads(CAPACITY.read_text())
    best = (data.get("claude") or {}).get("strongest") or {}
    alias, effort = best.get("alias", ""), best.get("default_effort", "")
    stale_after = datetime.fromisoformat(data.get("stale_after", "1970-01-01T00:00:00+00:00"))
    if datetime.now(stale_after.tzinfo) > stale_after:
        sys.exit(f"capacity.json went stale on {stale_after:%Y-%m-%d}; nothing changed")
    if not re.fullmatch(r"[a-z0-9.\[\]-]+", alias) or effort not in EFFORTS:
        sys.exit(f"capacity.json names no verified strongest model ({best!r}); nothing changed")
    if alias not in claude_aliases():
        sys.exit(f"Claude Code does not offer the alias {alias!r} that capacity.json names; nothing changed")
    return alias, effort


def claude_aliases() -> set[str]:
    """The aliases Claude Code itself lists, so a model session's mistake, or a page it read, cannot put any
    other name into a commit. `/model` is local: it runs no model turn."""
    done = subprocess.run(["claude", "-p", "/model", "--output-format", "json", "--max-turns", "1", "--max-budget-usd", "0.01"],
                          capture_output=True, text=True, timeout=120, cwd=CAPACITY.parent, env={**os.environ, "CLAUDE_TODO_HOOKS": "0"})
    try:
        listed = json.loads(done.stdout).get("result", "")
    except json.JSONDecodeError:
        return set()
    match = re.search(r"Available:\s*(.+)", listed)
    return {name.strip(" .") for name in match.group(1).split(",")} if match else set()


def frontmatter(text: str) -> tuple[str, str] | None:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    return (match.group(1), text[match.end():]) if match else None


def drop_key(head: str, key: str) -> str:
    return re.sub(rf"^{key}:.*\n?", "", head, flags=re.MULTILINE).rstrip("\n")


def introspective() -> list[Path]:
    found = []
    for skill in sorted(SKILLS.glob("*/*/SKILL.md")):
        parts = frontmatter(skill.read_text())
        if parts and re.search(r"^introspective:\s*true\s*$", parts[0], re.MULTILINE):
            found.append(skill)
    return found


def unpin_skill(path: Path) -> bool:
    text = path.read_text()
    head, body = frontmatter(text)
    new = f"---\n{drop_key(drop_key(head, 'model'), 'effort')}\n---\n{body}"
    if new != text:
        path.write_text(new)
    return new != text


def update_jobs(names: list[str], alias: str, effort: str) -> list[Path]:
    changed = []
    for job in sorted(JOBS.glob("*.sh")):
        text = job.read_text()
        new = text
        for name in names:
            pattern = re.compile(rf'^(\s*claude -p "/{re.escape(name)}\b[^"]*")((?:\s+--(?:model|effort) \S+)*)', re.MULTILINE)
            new = pattern.sub(lambda match: f"{match.group(1)} --model {alias} --effort {effort}", new)
        if new != text:
            job.write_text(new)
            changed.append(job)
    return changed


def main() -> None:
    commit = sys.argv[1:] == ["--commit"]
    if sys.argv[1:] not in ([], ["--commit"]):
        sys.exit("usage: steward.py [--commit]")
    alias, effort = strongest()
    skills = introspective()
    names = [skill.parent.name for skill in skills]
    candidates = skills + sorted(JOBS.glob("*.sh"))
    dirty = {line[3:] for line in git("status", "--porcelain", "--", *map(str, candidates)).splitlines()}
    changed = [skill for skill in skills if unpin_skill(skill)] + update_jobs(names, alias, effort)
    relative = [str(path.relative_to(DOTFILES)) for path in changed]
    print(f"strongest: {alias} at {effort}; introspective skills: {', '.join(names) or 'none'}")
    print("changed: " + (", ".join(relative) or "nothing"))
    if not commit or not changed:
        return
    if blocked := [path for path in relative if path in dirty]:
        print("not committed: these files had uncommitted changes before the run: " + ", ".join(blocked))
        return
    git("commit", "--quiet", "-m", f"Run the introspective skills' scheduled jobs on {alias} at {effort} effort",
        "-m", f"ai-capacity found {alias} to be the strongest model, and {effort} its own default effort.", "--", *relative)
    print("committed " + git("rev-parse", "--short", "HEAD").strip())


if __name__ == "__main__":
    main()
