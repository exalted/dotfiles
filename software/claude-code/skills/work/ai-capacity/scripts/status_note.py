# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Rewrite one section of the living "AI status" note in the user's Obsidian vault.

  status_note.py <section> <markdown file>

The note's path is in ~/.config/dotfiles/ai-capacity/note (see note.example beside this skill). Each concern
owns one section between `<!-- <section>:start -->` and `<!-- <section>:end -->` and rewrites only that, so
other skills can add theirs to the same note. A missing note is created; a missing section is appended.
"""

import re
import sys
from datetime import datetime
from pathlib import Path

CONFIG = Path.home() / ".config" / "dotfiles" / "ai-capacity" / "note"


def main() -> None:
    if len(sys.argv) != 3 or not re.fullmatch(r"[a-z0-9-]+", sys.argv[1]):
        sys.exit("usage: status_note.py <section> <markdown file>")
    if not CONFIG.is_file():
        sys.exit(f"no note configured: write the note's absolute path into {CONFIG}")
    section, body = sys.argv[1], Path(sys.argv[2]).read_text().strip()
    note = Path(CONFIG.read_text().strip()).expanduser()
    start, end = f"<!-- {section}:start -->", f"<!-- {section}:end -->"
    block = f"{start}\n## {section} · {datetime.now():%Y-%m-%d}\n\n{body}\n{end}"
    text = note.read_text() if note.exists() else "# AI status\n"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    text = pattern.sub(lambda _: block, text) if pattern.search(text) else text.rstrip() + "\n\n" + block + "\n"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(text)
    print(note)


if __name__ == "__main__":
    main()
