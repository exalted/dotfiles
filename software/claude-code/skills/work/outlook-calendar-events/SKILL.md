---
name: outlook-calendar-events
description: Read the user's Outlook calendar through the Microsoft 365 MCP connector and add events to it by generating an .ics file and importing it with the Outlook desktop app (the connector is read-only). Use when the user asks to add, block, mark or visualize something in their Outlook calendar, to find free time or windows for a task, or to replace events added earlier this way.
---

# Outlook calendar events (read via MCP, write via .ics import)

The `claude.ai Microsoft 365` connector can be **read-only** for the calendar: without the `Calendars.ReadWrite` permission (which needs admin consent in Microsoft Entra), it can search events but not create them. In that case, write by importing an `.ics` file into the Outlook desktop app.

## 1. Check the connector

1. If only `mcp__claude_ai_Microsoft_365__authenticate` is available, ask the user to run `/mcp` and select **claude.ai Microsoft 365**. The connector cannot start the sign-in itself.
2. Try `outlook_create_event` once with no attendees. If it succeeds, the write permission was granted: use the connector for writes from now on and skip steps 3–4. If it fails with `Missing scope 'Calendars.ReadWrite'`, continue with the `.ics` route. Do not retry.

## 2. Read

- Use `outlook_calendar_search` with `query: "*"`, `afterDateTime`/`beforeDateTime` and `order: "oldest"` for a day's events.
- Times come back as `{dateTime, timeZone}` in the mailbox time zone (often `UTC`). Convert before you talk about them. Ask which time zone the user and their team mean; do not assume one.
- Existing meetings are not always constraints: ask whether the user can do the task during them.
- Before you propose or rank time slots, read the user's private scheduling preferences in `~/.config/dotfiles/outlook-calendar-events/preferences.md`, if the file exists. Treat them as soft preferences: prefer slots that fit them, but never drop a slot only because of them when the hard constraints leave few options.
- Those preferences are private. Never copy them, or anything derived from them (for example "after lunch" or "before I stop working"), into shared places: Jira, Slack, calendar event titles or descriptions, commits, or this public repo. Explain a preference-based choice only to the user.

## 3. Write: generate the .ics

1. Write a JSON spec and run the bundled script:
   ```bash
   python3 ~/.claude/skills/outlook-calendar-events/scripts/make_ics.py <spec.json> <output.ics>
   ```
   The script's docstring describes the spec. Defaults: `free: true` (not busy), `private: false`.
2. Ask the user before you set `private: true` (lock icon) or `free: false` (shows as busy).
3. Use a new `uid_prefix` for every regenerated batch, so a re-import never collides with events from an earlier file.
4. Put the spec and the `.ics` in the project's scratch directory (see the user's CLAUDE.md), never in a system temp directory.
5. Validate before importing:
   ```bash
   uv run --no-project --with icalendar python -c "import icalendar,sys; c=icalendar.Calendar.from_ical(open(sys.argv[1],'rb').read()); [print(e['DTSTART'].dt.isoformat(), e['DTEND'].dt.strftime('%H:%M'), e['TRANSP'], e['SUMMARY']) for e in c.walk('VEVENT')]" <output.ics>
   ```

## 4. Write: import with the Outlook desktop app

1. Run `open -a "Microsoft Outlook" "<output.ics>"`.
2. Tell the user that Outlook shows an import or preview window, and that they must confirm each event into their own calendar. The import does not happen without their confirmation.
3. When the user confirms, verify with `outlook_calendar_search` (search by a word from the summary, limited to the event dates) that every event arrived exactly once.

## Changing or removing imported events

- The connector cannot change or delete events. Ask the user to delete the old events in Outlook first, then import a regenerated file with a new `uid_prefix`. Verify afterwards that only the new events remain.
- Colors are Outlook categories, which the import does not reliably keep. Tell the user to select the events, right-click, choose **Categorize** and pick a color.
- Never put work-scheduling details from these events into shared systems (Jira, Slack) unless the user asks.
