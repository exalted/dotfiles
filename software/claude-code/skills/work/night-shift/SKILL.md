---
name: night-shift
description: Govern the unattended night shift, which works top Jira backlog stories overnight, one at a time, on a branch per story in the user's own checkout, and leaves those branches and an Obsidian note to review in the morning. Use for /night-shift, and when the user asks to pause or resume it, change how many stories it takes, change its quota limits, skip or retry a story, clean up after reviewing a branch, run it now, see its status, or turn the weekly security analysis or codex on or off.
argument-hint: "[status | pause | resume | stories <n> | set <knob> <value> | skip <KEY> | retry <KEY> | cleanup <KEY> [--force] | run-now [--dry] | security on|off | codex on|off | setup]"
---

# Night shift

The night shift is a launch agent (`com.dotfiles.night-shift`, Monday to Friday at 00:37) that runs
`scripts/night_shift.py nightly`. It picks the top unassigned, unblocked backlog stories, works each one on a
`night/<KEY>` branch from `origin/main` in the user's own checkout of the right repository, checks the result with the repository's own
gate, has codex review it, and writes notes to the Obsidian folder: one folder per day, with a run note and
one note per story. A second agent
(`com.dotfiles.night-shift-security`, Saturday at 00:37) runs the weekly security analysis when it is on.

Nothing it does reaches `main`, the remote, or Jira: the user reviews, merges locally, and pushes.

## Governing it

Run the driver for every change; never edit `knobs.json` or `ledger.json` by hand:

```bash
uv run --quiet --no-project --script ~/.claude/skills/night-shift/scripts/night_shift.py <command>
```

| The user says | Command |
|---|---|
| status, how is it doing, what did it cost | `status` |
| pause it, not tonight | `pause` |
| resume it | `resume` |
| work on N stories | `set stories N` |
| keep more for day work | `set day_reserve_percent P` (percent kept per workday left before the weekly reset) |
| let a night use more or less | `set night_points N` (points of the 7-day window per night) |
| the absolute ceiling | `set seven_day_ceiling_percent P` |
| a runaway guard per session | `set caps_usd.work X` (also `pick`, `fix`, `report`, `scan`, `patch`) |
| how stale a checkout may be | `set fetch_max_workdays N` |
| security analysis on / off | `set security true` / `set security false` |
| codex on / off, codex fallback | `set codex true|false`, `set codex_fallback true|false` |
| never take KEY | `skip KEY` |
| won't merge KEY's branch | `reject KEY "why"` (never retried; branch kept as `night-archive/KEY-<date>`) |
| try KEY again | `retry KEY "what to change"` (the feedback goes into the next attempt's brief) |
| merged KEY | `merged KEY` (also detected by itself once main holds the branch) |
| stories on weekend nights | `set weekend_stories N` (0 turns weekend nights off), `set weekend_night_points N` |
| done reviewing KEY | `cleanup KEY` (add `--force` only when the user says to keep an unmerged branch as an archive) |
| run it now, test it | `run-now` (`--dry` picks stories and writes the note, works nothing) |

Say what changed in one line. For `status`, explain the quota line in plain words, in percent, never in dollars.

## The user's checkout, at night

The night shift works in the user's own checkouts under `~/Developer/`, one story at a time. Before a story,
it records the checkout's branch, HEAD, status and stash list, sets the user's uncommitted work aside with
`git stash` (also kept under `refs/night-shift/backup/`), and creates `night/<KEY>` from `origin/main`. After
the story, whatever happens, it saves anything left uncommitted to the archive, switches back, restores the
user's work exactly (staged stays staged), re-runs the repository's setup, and checks that branch, HEAD,
status and stash list match the record. A mismatch goes to the top of the note. A crashed run is released
at the next start. A manual run leaves a checkout alone when a file in it changed in the last 10 minutes.

Each story's branch must stand on its own: the gate runs with nothing but `origin/main` plus the story, and
the driver checks the branch is based on current `origin/main`, shares no commit with another `night/*`
branch, and merges into main without a conflict. Otherwise the story is partial.

## After the work session

Codex reviews the branch. If it asks for changes, or reports a medium or high finding, the same Claude session
resumes for one fix round (cap `caps_usd.fix`, at most `fix_minutes`, only with time left before the deadline)
and answers each finding in REPORT.md. Then the repository's gate runs on the branch tip, outside the model,
including the Docker-backed suites marked `requires = "docker"` in `config.toml` when a Docker engine answers.

## Stories it already worked

A story the night shift worked is never picked again on its own. With commits on its branch it waits for
the user's review, and every morning note lists it under "Waiting for your review" until one of these:
`merged` (also detected once `origin/main` holds all of the branch's commits), `reject` (never retried), or
`retry` (eligible again, with the user's feedback in the next brief). Blocked or unworkable stories are
looked at again only after they change in Jira.

The user also decides through the Obsidian notes. Each note carries a `night_shift_id` in its frontmatter,
and the night shift finds notes by it across the vault, so renaming or moving a note inside the night-shift
folder changes nothing. A story note moved anywhere outside that folder (archived, kept for the user's own
memory) or deleted (also into Obsidian's trash) closes the story: from the next run on it is never picked
again and never listed as waiting, and the ledger records `note_state` and `review: closed` so it never
contradicts the vault. The night shift never reads an archived note. Deleting a run note, or a whole day
folder, is only cleanup; for story notes in it, it closes them too. `retry KEY` reopens a closed story.

## What a night session may do

The same as the user by day: auto mode, no sandbox. It edits files in the checkout, creates scratch files,
installs the project's dependencies, and runs any of the project's commands, tests and tools. It must never
touch production or start a deployment, enforced in layers:

- deny rules: every `git push` (both `git` and `command git` forms), `glab`, and the GitLab, Jira, Confluence
  and Slack write tools;
- auto mode `hard_deny` rules: no production system, no push or pipeline, plus the production hosts
  (`env_forbidden_hosts`) and the allowed AWS accounts (`aws_allowed_accounts`) from `config.toml`;
- night processes see only the AWS profiles of `aws_allowed_accounts`;
- a checkout whose `.env` names a production host is left alone.

## The quota guard

The user's rule: the night shift never leaves them without quota for day work. Every limit is in percent of
the 7-day window, the unit the plan measures in. `scripts/quota.py` enforces them before every Claude session,
failing closed:

- The live 7-day usage comes from a tiny headless probe (its stream's `rate_limit_event`), or from the status
  line snapshot when that is under 5 minutes old. No reading means no session.
- The ceiling keeps `day_reserve_percent` (15) for each workday left before the weekly window resets; if the
  ledger measured more day use (the rise between one night's end and the next night's start), it keeps that.
  It never goes above `seven_day_ceiling_percent` (90). The night before the reset can therefore use more.
- A session starts only if the usage plus what that kind of session usually adds (measured, else a default)
  stays under the ceiling, and the night's rise stays within `night_points` (10; `weekend_night_points` on
  weekend nights). The night's points count every run of the night, restarts included.
- A running session is stopped when the usage reaches the ceiling (checked every 10 minutes).
- `caps_usd` are only runaway guards per session, in the one unit `claude --max-budget-usd` accepts.
- No story starts after `last_start` (03:00), and everything stops by `deadline` (05:00), so the 5-hour window
  the night opened is closed before the morning.
- A session limit with a reset that leaves time is waited out and the session resumed once; a weekly limit
  ends the night.

A story that a crashed run left behind waits for `retry KEY`.

## Fresh checkouts

A story never starts on a stale checkout: one whose last successful fetch is `fetch_max_workdays` (2) workday
starts old. Weekends do not count, so a Thursday fetch is fresh enough for the weekend nights. GitLab refuses
`git fetch` once the user's SSO session has expired; only the user can renew it. So:

- every workday morning at 09:00 (or at the next wake) `com.dotfiles.night-shift-check` fetches every
  checkout and, if GitLab refuses, shows a dialog that stays until answered. "Sync now" opens iTerm with
  `/sync-gitlab-repos`;
- at night, a stale checkout shows the same dialog, and the run waits (fetching every 5 minutes) until the
  user syncs or `last_start` passes. The security run does the same.

`status` lists each checkout's last fetch.

## Continuing a story by hand

Each story note has the command to continue the night's Claude session: `claude --resume <session id>` in the
story's main checkout, on its branch. The fix round resumes the same session, so it holds the whole night's
work on the story.

## Branches

A branch the night created and left without a commit (a repository the story did not need, a story that never
started) is removed when the night releases the checkout. The user reviews only branches with work on them.

## The weekly security analysis

Off until `set security true`. Each Saturday at 00:37 it takes the next repository from `security_rotation`
in `config.toml` and the next of its `security_areas`, scans that area with the Claude Security plugin at
medium effort on its own branch (`night/SEC-<date>`), picks the most severe new finding, has the plugin
draft a patch, has codex challenge it, applies it on that branch and runs the repository's gate.

It may run all weekend: it waits out each usage-limit reset and resumes, up to `security_max_waits` times,
until `security_deadline` (Sunday 18:00). It has its own `security_points`, the ceiling still binds, and a
weekly limit ends it.

The plugin removes its own scratch and run directories inside its report directory in that checkout. Where
its recipe would run `git clean`, the session moves the untracked files to the Trash instead
(`scripts/trash_untracked.py`, which refuses any path outside the plugin's scratch area).

## Setup (once per machine, work profile)

Check each item and tell the user only what is missing:

1. `~/.config/dotfiles/night-shift/config.toml` exists. Start from `config.example.toml` in this skill.
   It holds the repositories (path, setup, verify, security areas) and
   the people whose word counts, with their roles. Jira, Confluence, Slack and GitLab are read through the
   user's own plugin MCP sign-ins; no API tokens are stored.
2. Each checkout's `.env` is checked before a run: every host must be local, alpha, or match
   `env_allowed_hosts`, and none may match `env_forbidden_hosts` (production); otherwise the night shift
   leaves that repository alone. Night processes read an AWS config with only the profiles of
   `aws_allowed_accounts`, so production profiles do not exist for them.
3. For the security analysis: `~/.config/dotfiles/night-shift/security-request.txt` in the user's own words.
   It must say they accept that the scan may take long and use many tokens (the plugin refuses otherwise),
   and may use `{repo}` and `{area}` placeholders.
4. `/night-shift status` shows the launch agent loaded, a 7-day usage reading and each checkout's last fetch.

## Where things are

- Morning notes: the vault folder from `config.toml` (default: `Night shift` beside the recap folder), one
  folder per day (named after the morning) with a run note per run and a note per story.
- Per run: `~/.local/state/night-shift/runs/<date-time>/`: `plan.json`, one directory per story with
  `brief.md`, `dossier/`, `progress.md`, `result.json`, `verify.json`, and logs.
- Log: `~/Library/Logs/night-shift.log`.
- Uncommitted leftovers saved before verification or cleanup: `~/.local/state/night-shift/archive/`.
