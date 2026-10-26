---
name: pairing-candidates
description: Read-only check of which teammates (devs, ML/AI engineers) are free to pair on Tuple right now, combining Tuple presence (online / busy in a call / offline) with Slack presence, status, DND and local time, and flags teammates whose request for a pair in the team channel is still unanswered. Use when the user asks who they can pair with, who is available or free for pairing, who is online on Tuple, or wants a pairing partner. Never calls, messages or joins anyone.
model: haiku
argument-hint: "[tactical A+B [C+D] | tactical none]"
---

# Pairing candidates

List the teammates the user can reach out to for pairing on Tuple right now.

**This skill is read-only.** Never start a Tuple call, join a room, send a Slack message or DM, react, or change any status, even when a candidate is obvious. Report the list and stop. The user decides whom to contact.

This skill is user-scoped and works from any working directory. Do not `cd`.

## 1. Run the check

```bash
uv run --quiet --no-project --script ~/.claude/skills/pairing-candidates/scripts/check.py
```

If the user gave `tactical …` as arguments (for example `/pairing-candidates tactical dastan+drazen`), add `--tactical` with the pairs to the command:

1. Map each name to a `[pairing]` handle, as in step 2 of **Exit 3** below.
2. `--tactical` replaces this week's pairs. To keep a pair that is already recorded, read `~/.config/dotfiles/pairing-candidates/tactical.txt`. If its `week` line is this ISO week and a recorded pair shares no person with the new pairs, pass that pair too.
3. `tactical none` records that the team did not split this week.

The script reads:

- **Roster:** only the Slack handles in `~/.config/dotfiles/pairing-candidates/roster.txt`, looked up in the team channel whose ID is in `~/.config/dotfiles/pairing-candidates/channel`. `[pairing]` holds the real pairing candidates (devs, ML/AI engineers). `[on request]` holds people the user contacts only when needed (designer, PMs). Everyone else is ignored. Slack and Tuple people are matched by email.
- **Tactical pairs:** each week, four `[pairing]` people work on tactical stories in two fixed pairs; the others do strategic work. `~/.config/dotfiles/pairing-candidates/tactical.txt` holds the pairs for one ISO week (Monday to Sunday). The script writes it, never edit it by hand.
- **Tuple** (`tuple contacts list`, `tuple contacts show`): `online`/`available`, `busy` (in a Tuple call, with whom) or `offline`.
- **Slack** (Web API, user token from the macOS Keychain): presence (`active` / `away`), status emoji and text, scheduled DND, and local time from the profile timezone. It also reads today's top-level messages in the team channel (from 00:00 in each sender's timezone) and keeps the unanswered ones from roster people. A message is answered when somebody other than the sender replies in its thread, reacts with `:tuple:`, `:pear:`, `:pair:` or `:tuple-pear:`, or @-mentions the sender in a later channel message.

## 2. Handle errors

- **Exit 3, `TACTICAL PAIRS NEEDED`:** the pairs for this week are not recorded yet (the first run of a new week), or the pairs you gave were wrong. Then:
  1. Ask the user: "Who are the two tactical pairs this week?" Show the `[pairing]` handles from the message. Tell the user to answer `none` if the team did not split this week.
  2. Map the names in the answer to handles from the message. Use the user's own handle when they say "me". If a name matches no handle or more than one, ask again.
  3. Run the check again with the pairs: `... check.py --tactical first.dev+second.dev third.dev+fourth.dev`, or `--tactical none`.
  4. If it exits 3 again, show the message and go back to step 1.

  Do not ask again later in the same week: the script asks only when the week changes.
- **Exit 2, `SETUP ERROR`:** stop. Show the message and point the user to **One-time setup** in `~/.claude/skills/pairing-candidates/SETUP.md`. For a `missing_scope` error, name the missing scope. Do not fall back to the Slack MCP or to guessing.
- **`tuple ... failed`:** the Tuple app is probably not running or not signed in. Ask the user to open Tuple, then run the check again.
- **Exit 1, `ERROR`:** a network or Slack API problem. Show it and stop.

## 3. Report

The focus is who the user **can** pair with. Print the script output in a fenced code block and add nothing else: no rephrased lists, no summary, no ranking, no offer to contact anyone. Change the output only in these ways:

- **Unanswered messages to judge:** this section is input for you, not for the user. For each message, decide whether it explicitly asks for a pair now or later today (for example "anyone free to pair?", "can someone tuple with me on the migration?"). A message that only mentions pairing ("paired with Alex this morning", "the pair session was good") is not a request. Then:
  1. For each person with at least one request, add ` · 🍐 asking for a pair (54 min ago)` to their line, with the relative age of their latest request copied from the script (`54 min ago`, `2 h 5 min ago`). On a `Not available` line, write `Name (🍐 asking for a pair, 54 min ago)`. If the person has no line, add `🍐 Asking for a pair: Name (54 min ago)` as the last line.
  2. Remove the whole `Unanswered messages to judge` section.
- **Zero candidates:** if `Can pair now` is `(0)`, add one line after the code block that says so.

The script already keeps the output short. The three tier sections cover strategic `[pairing]` people only:

- **Your tactical partner** (shown only when the user is tactical this week): the partner's tier and status, before the other candidates.
- **Can pair now:** Tuple online, not in a call, Slack active, no occupied or OOO status, not in DND, 09:00–18:00 their time. Each line is the name and handle, plus their status and their local time only when these add information.
- **Maybe** (shown only when not empty): Tuple online, but Slack away, a meeting/huddle/focus/lunch status, scheduled DND, or outside working hours. Each line names the signal.
- **Not available:** one line per reason, names only. Tuple calls show as groups (`A + B`), so you can see who pairs with whom. `someone` is a call participant who is not in the user's Tuple contacts.
- **Tactical this week:** the two tactical pairs. Tactical people are left out of the three sections above, and their pair requests are dropped, except the user's own partner's.
- **Also around (on request):** one line with the `[on request]` people who can be reached now, with their role. Not shown when nobody qualifies.
- **Pair requests not checked:** the token lacks `channels:history`. Keep the line and point the user to **Add a scope** in `~/.claude/skills/pairing-candidates/SETUP.md`.
- **Not found in #<channel>:** a roster handle that matches nobody (a typo, a renamed handle, or someone who left the channel). If it shows, tell the user to fix `roster.txt`.

## Configuration

- **Add, move or remove a person:** edit `~/.config/dotfiles/pairing-candidates/roster.txt`. Write one Slack handle per line, then an optional role, under `[pairing]` or `[on request]`. The role shows only on the "Also around" line. `#` starts a comment.
- **Change this week's tactical pairs:** `/pairing-candidates tactical A+B C+D` (or `tactical none`), which runs the check with `--tactical`.
- **Team channel:** its ID (`C…`) is the only line of `~/.config/dotfiles/pairing-candidates/channel`.
- **Working hours, Keychain service name:** constants at the top of `scripts/check.py`.
- **Status keywords:** `OUT_OF_OFFICE_STATUS` (blocks) and `OCCUPIED_STATUS` (Maybe) in `scripts/check.py`.
