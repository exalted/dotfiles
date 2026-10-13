"""Shared by the recap scripts: configuration, workday arithmetic, note names and note properties.

The scripts run as `uv run --script`, which puts this directory on sys.path, so they import it directly.
"""

import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import NoReturn

# Machine-local configuration, kept out of the public dotfiles repo this skill lives in.
CONFIG_DIR = Path.home() / ".config" / "dotfiles" / "recap"
VAULT_FOLDER_FILE = CONFIG_DIR / "vault-folder"
EXIT_SETUP_ERROR = 2

RECAP_SUFFIX = "Recap"
FAILED_SUFFIX = "Recap failed"
CATCH_UP_SUFFIX = "Catch-up"
CATCH_UP_THRESHOLD = 3
# Fixed English month names: %b follows the locale, and note names must not change with it.
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
NOTE_DATE = re.compile(r"(\d{4}-\d{2}-\d{2}) \([^)]+\) ")

type Properties = dict[str, str | list[str]]


def setup_error(message: str) -> NoReturn:
    print(f"SETUP ERROR: {message}", file=sys.stderr)
    sys.exit(EXIT_SETUP_ERROR)


def read_folder() -> Path:
    if not VAULT_FOLDER_FILE.is_file():
        setup_error(f"{VAULT_FOLDER_FILE} is missing. It holds the absolute path of the vault folder for the notes.")
    folder = Path(VAULT_FOLDER_FILE.read_text().strip()).expanduser()
    if not any((parent / ".obsidian").is_dir() for parent in folder.parents):
        setup_error(f"{folder} is not inside an Obsidian vault (no .obsidian/ folder above it).")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def previous_workday(day: date) -> date:
    day -= timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def covered_workdays(*, start: datetime, end: datetime) -> tuple[date, ...]:
    """The workdays a recap is about: a Monday run covers Friday, a catch-up run several days."""
    days = []
    day = start.date()
    while day < end.date():
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return tuple(days) or (start.date(),)


def short_day(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.day}"


def note_name(*, first: date, last: date, suffix: str) -> str:
    if first == last:
        label = short_day(first)
    elif first.month == last.month:
        label = f"{short_day(first)}–{last.day}"
    else:
        label = f"{short_day(first)}–{short_day(last)}"
    return f"{first.isoformat()} ({label}) {suffix}"


def note_date(path: Path) -> date | None:
    match = NOTE_DATE.match(path.name)
    return date.fromisoformat(match.group(1)) if match else None


def notes(*, folder: Path, suffix: str) -> list[Path]:
    """The notes of one kind, oldest first."""
    return sorted(path for path in folder.glob(f"*) {suffix}.md") if note_date(path) is not None)


def _scalar(text: str) -> str:
    return json.loads(text) if text.startswith('"') else text


def read_properties(path: Path) -> Properties:
    """The frontmatter as the recap scripts write it: scalars, and lists of `  - ` lines."""
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}
    properties: Properties = {}
    current: list[str] | None = None
    for line in text[4 : text.index("\n---", 3)].splitlines():
        if line.startswith("  - ") and current is not None:
            current.append(_scalar(line[4:]))
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value:
            properties[key] = _scalar(value)
            current = None
        else:
            current = []
            properties[key] = current
    return properties


def remove_property(*, path: Path, key: str) -> None:
    """Drop a property, list entries included."""
    text = path.read_text()
    end = text.index("\n---", 3)
    frontmatter = re.sub(rf"^{re.escape(key)}:.*\n(  - .*\n)*", "", text[:end] + "\n", count=1, flags=re.MULTILINE)
    path.write_text(frontmatter.rstrip("\n") + text[end:])


def set_property(*, path: Path, key: str, raw_value: str) -> None:
    text = path.read_text()
    end = text.index("\n---", 3)
    frontmatter = re.sub(rf"^{re.escape(key)}: .*$", f"{key}: {raw_value}", text[:end], count=1, flags=re.MULTILINE)
    path.write_text(frontmatter + text[end:])


def is_read(properties: Properties) -> bool:
    return properties.get("read") == "true"


def unread_recaps(folder: Path) -> list[Path]:
    return [path for path in notes(folder=folder, suffix=RECAP_SUFFIX) if not is_read(read_properties(path))]


def unread_catch_ups(folder: Path) -> list[Path]:
    return [path for path in notes(folder=folder, suffix=CATCH_UP_SUFFIX) if not is_read(read_properties(path))]


def trash(path: Path) -> None:
    if path.exists():
        subprocess.run(["/usr/bin/trash", str(path)], check=True, capture_output=True)
