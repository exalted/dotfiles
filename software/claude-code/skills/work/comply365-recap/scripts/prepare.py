#!/usr/bin/env -S uv run --quiet --no-project --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Tidy the recap folder, then say whether a recap run is due. The launch agent runs this before Claude.

Tidying, done on every start so a tick takes effect at the next login or wake, not only the next recap:
- A catch-up note the user marked read marks every recap it covers as read, once.
- An unread catch-up note that covers fewer than the threshold of unread recaps is stale and goes to the Trash.

A run is due when no recap reaches the newest weekday run time yet. So a login or wake before the run time does
nothing, and one after a missed run time catches up at once, weekends included.

Exit 0: a run is due. Exit 3: nothing to do (the recap for the newest run time is already written). Exit 2: setup error.
"""

import sys
from datetime import datetime
from pathlib import Path

from common import (
    CATCH_UP_SUFFIX,
    CATCH_UP_THRESHOLD,
    RECAP_SUFFIX,
    is_read,
    last_run_slot,
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


def written_since(*, folder: Path, slot: datetime) -> bool:
    for recap in notes(folder=folder, suffix=RECAP_SUFFIX):
        window_end = read_properties(recap).get("window_end")
        if isinstance(window_end, str) and datetime.fromisoformat(window_end) >= slot:
            return True
    return False


def main() -> None:
    folder = read_folder()
    print(f"marked read through a catch-up: {propagate_catch_up_reads(folder)}")
    print(f"stale catch-up notes trashed: {drop_stale_catch_ups(folder)}")

    # Naive local time, like the window_end the notes store.
    slot = last_run_slot(datetime.now())
    if written_since(folder=folder, slot=slot):
        print(f"not due: the recap for {slot:%a %Y-%m-%d %H:%M} is already written")
        sys.exit(EXIT_NOT_DUE)
    print(f"due: the recap for {slot:%a %Y-%m-%d %H:%M}")


if __name__ == "__main__":
    main()
