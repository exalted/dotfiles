#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Append one checkpoint line to the story's progress file, for the morning note's timeline.

  progress.py "<what just happened, in one line>"          from the work session (at most 8 lines per story)
  progress.py --wrapper "<line>"                            from the night-shift driver (not counted)

The story's run directory comes from NIGHT_SHIFT_RUN_DIR, or --dir. Lines are cut at 120 characters.
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

MODEL_LINES = 8
WIDTH = 120


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--dir", default=os.environ.get("NIGHT_SHIFT_RUN_DIR"))
    parser.add_argument("--wrapper", action="store_true")
    args = parser.parse_args()
    if not args.dir:
        sys.exit("progress.py: no run directory (NIGHT_SHIFT_RUN_DIR is not set; pass --dir)")
    path = Path(args.dir) / "progress.md"
    lines = path.read_text().splitlines() if path.exists() else []
    marker = "·" if args.wrapper else "-"
    if not args.wrapper and sum(1 for line in lines if line.startswith("- ")) >= MODEL_LINES:
        print(f"Checkpoint limit ({MODEL_LINES}) reached: put further detail in REPORT.md instead.")
        return
    text = " ".join(args.text.split())
    if len(text) > WIDTH:
        text = text[: WIDTH - 1] + "…"
    with path.open("a") as handle:
        handle.write(f"{marker} {datetime.now():%H:%M} {text}\n")
    print("recorded")


if __name__ == "__main__":
    main()
