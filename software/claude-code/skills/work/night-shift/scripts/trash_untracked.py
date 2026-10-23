#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""`git clean -fd` for the Claude Security plugin's scratch workspaces, with the macOS Trash instead of deletion.

  trash_untracked.py <scratch workspace>

The user's rules deny every permanent deletion, `git clean` included. The plugin's patch recipe cleans its
scratch clones between attempts; the night security session runs this instead. It acts only on a directory
inside a `CLAUDE-SECURITY-<timestamp>/.claude-security-run/` tree of the current working directory, and
moves only the untracked, non-ignored files of that clone to the Trash, as `git clean -fd` would remove them.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPORT_DIR = re.compile(r"^CLAUDE-SECURITY-\d{8}-\d{6}$")


def fenced(path: Path) -> bool:
    parts = path.relative_to(Path.cwd().resolve()).parts if path.is_relative_to(Path.cwd().resolve()) else ()
    return len(parts) >= 3 and REPORT_DIR.match(parts[0]) is not None and parts[1] == ".claude-security-run"


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: trash_untracked.py <scratch workspace>")
    scratch = Path(sys.argv[1]).resolve()
    if scratch.is_symlink() or not fenced(scratch) or not (scratch / ".git").exists():
        sys.exit(f"trash_untracked.py: refusing {scratch}: not a scratch clone inside CLAUDE-SECURITY-*/.claude-security-run/ here")
    listing = subprocess.run(["git", "-C", str(scratch), "ls-files", "-z", "--others", "--exclude-standard", "--directory"], capture_output=True, check=True).stdout
    paths = [scratch / os.fsdecode(raw).rstrip("/") for raw in listing.split(b"\0") if raw]
    paths = [path for path in paths if path.resolve().is_relative_to(scratch)]
    for start in range(0, len(paths), 200):
        subprocess.run(["/usr/bin/trash", "--stopOnError", *map(str, paths[start : start + 200])], check=True)
    print(f"moved {len(paths)} untracked entries of {scratch.name} to the Trash")


if __name__ == "__main__":
    main()
