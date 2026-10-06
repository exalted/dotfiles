---
name: pairing-candidates
description: Read-only check of which teammates (devs, ML/AI engineers) are free to pair on Tuple right now, combining Tuple presence (online / busy in a call / offline) with Slack presence, status, DND and local time. Use when the user asks who they can pair with, who is available or free for pairing, who is online on Tuple, or wants a pairing partner. Never calls, messages or joins anyone.
---

# Pairing candidates

List the teammates the user can reach out to for pairing on Tuple right now.

**This skill is read-only.** Never start a Tuple call, join a room, send a Slack message or DM, react, or change any status, even when a candidate is obvious. Report the list and stop. The user decides whom to contact.

This skill is user-scoped and works from any working directory. Do not `cd`.

## 1. Run the check

```bash
uv run --quiet --no-project --script ~/.claude/skills/pairing-candidates/scripts/check.py
```

The script reads:

- **Roster:** only the Slack handles in `~/.config/dotfiles/pairing-candidates/roster.txt`, looked up in the team channel whose ID is in `~/.config/dotfiles/pairing-candidates/channel`. `[pairing]` holds the real pairing candidates (devs, ML/AI engineers). `[on request]` holds people the user contacts only when needed (designer, PMs). Everyone else is ignored. Slack and Tuple people are matched by email.
- **Tuple** (`tuple contacts list`, `tuple contacts show`): `online`/`available`, `busy` (in a Tuple call, with whom) or `offline`.
- **Slack** (Web API, user token from the macOS Keychain): presence (`active` / `away`), status emoji and text, scheduled DND, and local time from the profile timezone.

## 2. Handle errors

- **Exit 2, `SETUP ERROR`:** stop. Show the message and point the user to **One-time setup** below. For a `missing_scope` error, name the missing scope. Do not fall back to the Slack MCP or to guessing.
- **`tuple ... failed`:** the Tuple app is probably not running or not signed in. Ask the user to open Tuple, then run the check again.
- **Exit 1, `ERROR`:** a network or Slack API problem. Show it and stop.

## 3. Report

The focus is who the user **can** pair with. Print the script output verbatim in a fenced code block and add nothing else: no rephrased lists, no summary, no ranking, no offer to contact anyone. The only exception: if `Can pair now` is `(0)`, add one line that says so.

The script already keeps the output short. The three sections cover `[pairing]` people only:

- **Can pair now:** Tuple online, not in a call, Slack active, no occupied or OOO status, not in DND, 09:00–18:00 their time. Each line is the name and handle, plus their status and their local time only when these add information.
- **Maybe** (shown only when not empty): Tuple online, but Slack away, a meeting/huddle/focus/lunch status, scheduled DND, or outside working hours. Each line names the signal.
- **Not available:** one line per reason, names only. Tuple calls show as groups (`A + B`), so you can see who pairs with whom. `someone` is a call participant who is not in the user's Tuple contacts.
- **Also around (on request):** one line with the `[on request]` people who can be reached now, with their role. Not shown when nobody qualifies.
- **Not found in #<channel>:** a roster handle that matches nobody (a typo, a renamed handle, or someone who left the channel). If it shows, tell the user to fix `roster.txt`.

## Configuration

- **Add, move or remove a person:** edit `~/.config/dotfiles/pairing-candidates/roster.txt`. Write one Slack handle per line, then an optional role, under `[pairing]` or `[on request]`. The role shows only on the "Also around" line. `#` starts a comment.
- **Team channel:** its ID (`C…`) is the only line of `~/.config/dotfiles/pairing-candidates/channel`.
- **Working hours, Keychain service name:** constants at the top of `scripts/check.py`.
- **Status keywords:** `OUT_OF_OFFICE_STATUS` (blocks) and `OCCUPIED_STATUS` (Maybe) in `scripts/check.py`.

## One-time setup

The roster names real colleagues and the channel ID is internal, so both live on this machine only, never in the public dotfiles repo this skill is tracked in:

```bash
mkdir -p ~/.config/dotfiles/pairing-candidates
cp ~/.claude/skills/pairing-candidates/roster.example.txt ~/.config/dotfiles/pairing-candidates/roster.txt
echo C0123456789 > ~/.config/dotfiles/pairing-candidates/channel
```

Then replace the example handles, and the example channel ID with the team channel's ID (Slack: channel details → About, at the bottom).

The Slack MCP cannot read presence, so the script uses its own read-only Slack **user** token.

1. Open https://api.slack.com/apps and select **Create New App → From a manifest**. Choose the Comply365 workspace.
2. Paste `~/.claude/skills/pairing-candidates/slack-app-manifest.yaml`. It asks only for the user scopes `channels:read`, `users:read`, `users:read.email` and `dnd:read`.
3. Select **Install to Workspace**. If the workspace needs admin approval, request it and wait.
4. Copy the **User OAuth Token** (`xoxp-…`) from **OAuth & Permissions**.
5. Store it in the Keychain. Run this in the prompt; it asks for the token, so it never lands in shell history:

   ```bash
   ! security add-generic-password -U -a "$USER" -s pairing-candidates-slack-token -w
   ```

To rotate the token, run the same command again (`-U` updates the item).
