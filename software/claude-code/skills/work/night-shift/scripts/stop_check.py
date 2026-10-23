#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Stop hook of the night-shift-work skill: keep the session working until the story's done-list holds.

This is the essence of /goal: a check that the worker does not run decides whether the work is finished.
It never fights the driver's deadline, and it gives up after a few blocks so a session that cannot finish
still ends and reports. Outside a night-shift session (no NIGHT_SHIFT_RUN_DIR) it does nothing.
"""

import json
import os
import sys
import time
from pathlib import Path

DONE_ITEMS = ("tests_added", "repo_gate", "code_review", "simplify", "security_review", "report")
STATUSES = ("solved", "partial", "abandoned")
MAX_BLOCKS = 6
DEADLINE_MARGIN = 300


def allow() -> None:
    sys.exit(0)


def block(reason: str, run_dir: Path) -> None:
    counter = run_dir / "stop-blocks"
    counter.write_text(str(int(counter.read_text() or 0) + 1) if counter.exists() else "1")
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


def main() -> None:
    json.load(sys.stdin)
    run_dir = os.environ.get("NIGHT_SHIFT_RUN_DIR")
    if not run_dir:
        allow()
    run_dir = Path(run_dir)
    deadline = float(os.environ.get("NIGHT_SHIFT_DEADLINE") or 0)
    if deadline and time.time() > deadline - DEADLINE_MARGIN:
        allow()
    counter = run_dir / "stop-blocks"
    if counter.exists() and int(counter.read_text() or 0) >= MAX_BLOCKS:
        allow()
    result_path = run_dir / "result.json"
    if not result_path.exists():
        block(f"The story is not finished: write {result_path} as the night-shift-work skill describes (status, done-list, summary) before you stop.", run_dir)
    try:
        result = json.loads(result_path.read_text())
    except json.JSONDecodeError as error:
        block(f"{result_path} is not valid JSON ({error}). Fix it.", run_dir)
    status = result.get("status")
    if status not in STATUSES:
        block(f"result.json status must be one of {STATUSES}, not {status!r}.", run_dir)
    done = result.get("done") or {}
    if status == "solved":
        missing = [item for item in DONE_ITEMS if done.get(item) is not True]
        if missing:
            block(f"status is solved, but these done-list items are not true yet: {', '.join(missing)}. Do them, or set status to partial and say why.", run_dir)
    elif done.get("report") is not True or not result.get("summary"):
        block("For a partial or abandoned story, REPORT.md and the summary in result.json still explain what was done and why it stopped.", run_dir)
    allow()


if __name__ == "__main__":
    main()
