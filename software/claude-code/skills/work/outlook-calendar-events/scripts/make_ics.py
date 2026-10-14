"""Write an Outlook-importable .ics file from a JSON event list.

Usage: make_ics.py <events.json> <output.ics>

events.json:
{
  "timezone": "Europe/Rome",            # optional, default Europe/Rome
  "uid_prefix": "deploy-windows-v1",    # required; change it for every regenerated batch
  "events": [
    {"summary": "...", "start": "2026-10-08T10:00", "end": "2026-10-08T11:40",
     "description": "...", "free": true, "private": true}
  ]
}

Times are wall-clock times in `timezone`. `free` (default true) keeps the event from showing as busy;
`private` (default false) hides title and details from colleagues (Outlook shows a lock icon).
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Outlook resolves TZID against an embedded VTIMEZONE; without one it may shift the events.
VTIMEZONES = {
    "Europe/Rome": ["+0100", "+0200", "CET", "CEST"],
    "Europe/London": ["+0000", "+0100", "GMT", "BST"],
}


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics_time(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y%m%dT%H%M%S")


def vtimezone(name: str) -> list[str]:
    if name not in VTIMEZONES:
        raise SystemExit(f"Add a VTIMEZONE for {name} to VTIMEZONES first")
    standard_offset, daylight_offset, standard_name, daylight_name = VTIMEZONES[name]
    return [
        "BEGIN:VTIMEZONE", f"TZID:{name}",
        "BEGIN:DAYLIGHT", f"TZOFFSETFROM:{standard_offset}", f"TZOFFSETTO:{daylight_offset}", f"TZNAME:{daylight_name}",
        "DTSTART:19700329T020000", "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
        "BEGIN:STANDARD", f"TZOFFSETFROM:{daylight_offset}", f"TZOFFSETTO:{standard_offset}", f"TZNAME:{standard_name}",
        "DTSTART:19701025T030000", "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD",
        "END:VTIMEZONE",
    ]


def main() -> None:
    spec = json.loads(Path(sys.argv[1]).read_text())
    zone = spec.get("timezone", "Europe/Rome")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//claude-code//outlook-calendar-events//EN", "CALSCALE:GREGORIAN", *vtimezone(zone)]
    for index, event in enumerate(spec["events"], 1):
        free = event.get("free", True)
        lines += [
            "BEGIN:VEVENT",
            f"UID:{spec['uid_prefix']}-{index}@claude-code.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART;TZID={zone}:{ics_time(event['start'])}",
            f"DTEND;TZID={zone}:{ics_time(event['end'])}",
            f"SUMMARY:{escape(event['summary'])}",
            f"DESCRIPTION:{escape(event.get('description', ''))}",
            f"TRANSP:{'TRANSPARENT' if free else 'OPAQUE'}",
            f"X-MICROSOFT-CDO-BUSYSTATUS:{'FREE' if free else 'BUSY'}",
            f"CLASS:{'PRIVATE' if event.get('private', False) else 'PUBLIC'}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    output = Path(sys.argv[2])
    output.write_text("\r\n".join(lines) + "\r\n", newline="")
    print(output)


if __name__ == "__main__":
    main()
