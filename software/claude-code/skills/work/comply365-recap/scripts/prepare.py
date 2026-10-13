#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Tidy the recap folder, then say whether a recap run is due. The launch agent runs this before Claude.

Tidying, done on every start so a tick takes effect at the next login or wake, not only the next recap:
- A catch-up note the user marked read marks every recap it covers as read, once.
- An unread catch-up note that covers fewer than the threshold of unread recaps is stale and goes to the Trash.

Exit 0: a run is due. Exit 3: nothing to do (a weekend, or today's recap is already written). Exit 2: setup error.
"""

import sys
from datetime import date, datetime
from pathlib import Path

from common import (
    CATCH_UP_SUFFIX,
    CATCH_UP_THRESHOLD,
    RECAP_SUFFIX,
    is_read,
    notes,
    read_folder,
    read_properties,
    remove_property,
    set_property,
    trash,
    unread_catch_ups,
    unread_recaps,
)

EXIT_NOT_DUE = 3


def propagate_catch_up_reads(folder: Path) -> int:
    marked = 0
    for catch_up in notes(folder=folder, suffix=CATCH_UP_SUFFIX):
        properties = read_properties(catch_up)
        if not is_read(properties) or "covers" not in properties:
            continue
        for name in properties.get("covers", []):
            recap = folder / f"{name}.md"
            if recap.exists() and not is_read(read_properties(recap)):
                set_property(path=recap, key="read", raw_value="true")
                marked += 1
        remove_property(path=catch_up, key="covers")
    return marked


def drop_stale_catch_ups(folder: Path) -> int:
    if len(unread_recaps(folder)) >= CATCH_UP_THRESHOLD:
        return 0
    stale = unread_catch_ups(folder)
    for catch_up in stale:
        trash(catch_up)
    return len(stale)


def written_today(*, folder: Path, today: date) -> bool:
    for recap in notes(folder=folder, suffix=RECAP_SUFFIX):
        window_end = read_properties(recap).get("window_end")
        if isinstance(window_end, str) and datetime.fromisoformat(window_end).date() == today:
            return True
    return False


def main() -> None:
    folder = read_folder()
    print(f"marked read through a catch-up: {propagate_catch_up_reads(folder)}")
    print(f"stale catch-up notes trashed: {drop_stale_catch_ups(folder)}")

    today = datetime.now().astimezone().date()
    if today.weekday() >= 5:
        print("not due: weekend")
        sys.exit(EXIT_NOT_DUE)
    if written_today(folder=folder, today=today):
        print("not due: today's recap is already written")
        sys.exit(EXIT_NOT_DUE)
    print("due")


if __name__ == "__main__":
    main()
