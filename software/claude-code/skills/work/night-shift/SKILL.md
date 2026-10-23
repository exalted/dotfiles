---
name: night-shift
description: Govern the unattended night shift, which works top Jira backlog stories overnight in git worktrees and leaves branches and an Obsidian note to review in the morning. Use for /night-shift, and when the user asks to pause or resume it, change how many stories it takes, change its quota limits, skip or retry a story, clean up after reviewing a branch, run it now, see its status, or turn the weekly security analysis or codex on or off.
argument-hint: "[status | pause | resume | stories <n> | set <knob> <value> | skip <KEY> | retry <KEY> | cleanup <KEY> [--force] | run-now [--dry] | security on|off | codex on|off | setup]"
---

# Night shift

The night shift is a launch agent (`com.dotfiles.night-shift`, Monday to Friday at 00:37) that runs
`scripts/night_shift.py nightly`. It picks the top unassigned, unblocked backlog stories, works each one on a
`night/<KEY>` branch in a git worktree of the right repository, checks the result with the repository's own
gate, has codex review it, and writes a note to the Obsidian folder. A second agent
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
| change the weekly limit | `set seven_day_max_percent P` or `set weekly_allowance_usd X` or `set night_allowance_usd X` |
| a story cap | `set caps_usd.work X` (also `pick`, `report`, `scan`, `patch`) |
| security analysis on / off | `set security true` / `set security false` |
| codex on / off, codex fallback | `set codex true|false`, `set codex_fallback true|false` |
| never take KEY | `skip KEY` |
| try KEY again | `retry KEY` |
| done reviewing KEY | `cleanup KEY` (add `--force` only when the user says to keep an unmerged branch as an archive) |
| run it now, test it | `run-now` (`--dry` picks stories and writes the note, works nothing) |

Say what changed in one line. For `status`, explain the quota line in plain words.

## After the work session

Codex reviews the branch. If it asks for changes, or reports a medium or high finding, the same Claude session
resumes for one fix round (cap `caps_usd.fix`, at most `fix_minutes`, only with time left before the deadline)
and answers each finding in REPORT.md. Then the repository's gate runs on the branch tip, outside the model,
including the Docker-backed suites marked `requires = "docker"` in `config.toml` when a Docker engine answers.

## The quota guard

The user's rule: the night shift never leaves them without quota for day work. `scripts/quota.py` enforces it
before every Claude session, failing closed:

- The 7-day usage from the status line snapshot (`~/.local/state/claude-usage/latest.json`, written by the
  user's status line script during day sessions) must be at or under `seven_day_max_percent` (60), and the
  snapshot at most `snapshot_max_age_hours` (12) old. No snapshot means no run.
- The ledger's estimated spend over 7 days plus the session's cap must fit `weekly_allowance_usd`, and the
  night's spend must fit `night_allowance_usd`. A session reserves its cap before it starts; a crashed one
  is charged in full.
- No story starts after `last_start` (03:00), and everything stops by `deadline` (05:00), so the 5-hour window
  the night opened is closed before the morning.
- A session limit with a reset that leaves time is waited out and the session resumed once; a weekly limit
  ends the night.

If the user's account gives the status line no `rate_limits`, the snapshot never appears and the gate stays
closed: there is no way around the snapshot. The night's allowance counts every run of the night, restarts
included. A story that a crashed run left behind waits for `retry KEY`.

## The weekly security analysis

Off until `set security true`. Each Saturday at 00:37 it takes the next repository from `security_rotation`
in `config.toml` and the next of its `security_areas`, scans that area with the Claude Security plugin at
medium effort in its own worktree (`night/SEC-<date>`), picks the most severe new finding, has the plugin
draft a patch, has codex challenge it, applies it on that branch and runs the repository's gate.

It may run all weekend: it waits out each usage-limit reset and resumes, up to `security_max_waits` times,
until `security_deadline` (Sunday 18:00). It has its own `security_allowance_usd`, the weekly allowance
still binds, and a weekly limit ends it. No day session refreshes the usage snapshot on a weekend, so it
accepts one up to `security_snapshot_max_age_hours` old.

The plugin removes its own scratch and run directories inside its report directory in that worktree. Where
its recipe would run `git clean`, the session moves the untracked files to the Trash instead
(`scripts/trash_untracked.py`, which refuses any path outside the plugin's scratch area).

## Setup (once per machine, work profile)

Check each item and tell the user only what is missing:

1. `~/.config/dotfiles/night-shift/config.toml` exists. Start from `config.example.toml` in this skill.
   It holds the repositories (path, setup, verify, files to copy into a worktree, security areas) and
   the people whose word counts, with their roles. Jira, Confluence, Slack and GitLab are read through the
   user's own plugin MCP sign-ins; no API tokens are stored.
2. Each file listed under `copy` exists. Env files are checked before they are copied: every host must be
   local, alpha, or match `env_allowed_hosts`, and none may match `env_forbidden_hosts` (production); keys in
   `env_drop_keys` are left out of the copy. Night processes read an AWS config with only the profiles of
   `aws_allowed_accounts`, so production profiles do not exist for them.
3. For the security analysis: `~/.config/dotfiles/night-shift/security-request.txt` in the user's own words.
   It must say they accept that the scan may take long and use many tokens (the plugin refuses otherwise),
   and may use `{repo}` and `{area}` placeholders.
4. `/night-shift status` shows the launch agent loaded and a fresh usage snapshot.

## Where things are

- Morning notes: the vault folder from `config.toml` (default: `Night shift` beside the recap folder).
- Per run: `~/.local/state/night-shift/runs/<date-time>/`: `plan.json`, one directory per story with
  `brief.md`, `dossier/`, `progress.md`, `result.json`, `verify.json`, and logs.
- Log: `~/Library/Logs/night-shift.log`.
- Uncommitted leftovers saved before verification or cleanup: `~/.local/state/night-shift/archive/`.
