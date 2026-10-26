"""Which team the user is on this week. The team rotates weekly: on the tactical team the night shift works only
stories with the tactical label, otherwise only stories without it.

For the current ISO week the user's own answer (the Monday dialog, or `set tactical`) wins, then the tactical
pairs that /pairing-candidates recorded for the week. Without either, last week's answer carries over.
"""

import subprocess
import time
from datetime import datetime

from common import TACTICAL_PAIRS_FILE, TEAM_FILE, Config, Json, read_json, save_knobs, write_json


def iso_week(when: datetime) -> str:
    year, week, _ = when.isocalendar()
    return f"{year}-W{week:02d}"


def from_pairing(week: str, handle: str) -> bool | None:
    """Whether the user is in one of this week's tactical pairs, or None when the pairs are not recorded for this week."""
    if not handle or not TACTICAL_PAIRS_FILE.is_file():
        return None
    recorded, people = "", set()
    for line in TACTICAL_PAIRS_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("week "):
            recorded = line.removeprefix("week ").strip()
        elif "+" in line and not line.startswith("#"):
            people |= {part.strip().lower() for part in line.split("+")}
    return handle.lower() in people if recorded == week else None


def confirmed(week: str) -> bool:
    return (read_json(TEAM_FILE, {}) or {}).get("week") == week


def confirm(tactical: bool, week: str, source: str) -> None:
    save_knobs({"tactical": tactical})
    write_json(TEAM_FILE, {"week": week, "tactical": tactical, "source": source, "at": time.time()})


def current(k: Json, config: Config, when: datetime) -> tuple[bool, str]:
    """(tactical, why). Adopts the pairs' answer as the knob, so it carries over into a week nobody confirms."""
    week = iso_week(when)
    if confirmed(week):
        return bool(k["tactical"]), "you confirmed it for this week"
    paired = from_pairing(week, config.pairing_handle)
    if paired is not None:
        if paired != bool(k["tactical"]):
            save_knobs({"tactical": paired})
        return paired, "from this week's tactical pairs in /pairing-candidates"
    return bool(k["tactical"]), f"carried over: not confirmed for {week} yet"


def name(tactical: bool) -> str:
    return "tactical" if tactical else "strategic"


def label_clause(config: Config, tactical: bool) -> str:
    """The JQL that keeps the week's stories; empty when no tactical label is configured."""
    if not config.tactical_label:
        return ""
    label = f'"{config.tactical_label}"'
    return f" AND labels = {label}" if tactical else f" AND (labels is EMPTY OR labels != {label})"


def on_team(state: Json | None, config: Config, tactical: bool) -> bool:
    """Whether a story belongs to the week's team. Unknown (the Jira check did not finish) counts as on the team."""
    if state is None or not config.tactical_label:
        return True
    return (config.tactical_label in state.get("labels", [])) == tactical


DIALOG = """on run argv
    return button returned of (display alert (item 1 of argv) message (item 2 of argv) as critical buttons {"Strategic", "Tactical"} default button (item 3 of argv))
end run
"""


def ask(k: Json, week: str) -> bool | None:
    """Show the dialog and wait for the answer; None if it was closed some other way."""
    message = (
        f"Week {week}: are you on the tactical team?\n\nTactical: the night shift works only stories with the tactical "
        "label. Strategic: only stories without it.\n\nYour answer stays until you change it."
    )
    result = subprocess.run(
        ["/usr/bin/osascript", "-e", DIALOG, "Night shift: which team are you on this week?", message, "Tactical" if k["tactical"] else "Strategic"],
        capture_output=True, text=True,
    )
    answer = result.stdout.strip()
    return answer == "Tactical" if answer in ("Tactical", "Strategic") else None
