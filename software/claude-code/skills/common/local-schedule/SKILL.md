---
name: local-schedule
description: Set up a recurring or one-off job that runs unattended on this Mac with access to local files, for example a weekly `claude -p` refresh, a nightly script, or a periodic check. Use when the user asks to run something on a schedule, periodically, every morning, weekly, as a cron job, or in the background on their machine, or asks how to schedule locally instead of a cloud routine. Default is a launchd agent owned by the dotfiles repo; Claude Code Desktop local scheduled tasks are the alternative when the user wants to watch runs in the app.
argument-hint: "<what to run> [how often]"
---

# Local schedule

Run a job on a schedule on this machine. Two mechanisms do this; one is the default.

## 1. Pick the mechanism

Default to **launchd**. Say in one line that a **Claude Code Desktop local scheduled task** exists and when it is the better pick. Proceed with launchd unless the user names a reason from the Desktop column.

| | launchd agent (default) | Desktop local scheduled task |
|---|---|---|
| Lives in | dotfiles repo: script + plist, installed by the tool's `.rb` | the Desktop app (schedule, folder, model); only the prompt is on disk |
| Reproducible on a new machine | yes, `bin/dotfiles` installs it | no, recreate it in the UI |
| Needs | machine awake | machine awake and the Desktop app open |
| Runs | any command, including headless `claude -p` | a Claude Code session in a chosen folder |
| Output | a log file; `git diff` for file changes | a session in the sidebar: transcript, run history, permission prompts you can answer later |
| Missed run while asleep | runs on wake (`StartCalendarInterval`) | one catch-up run for the most recent miss, within 7 days |
| Min interval | 1 minute (`StartInterval`) | 1 minute |

Valid reasons to pick Desktop: the user wants to read each run as a session, needs interactive permission prompts that cannot be pre-allowed, or does not want anything in dotfiles. Neither fits when no local files are needed: then a cloud routine via `/schedule` is simpler.

## 2. launchd: build it

Follow the worked example `software/claude-code/claude-code-levers-refresh.sh` and its plist in the dotfiles repo. Pieces, all in `software/<tool>/`:

1. **Wrapper script** `<job>.sh` from `templates/job.sh`. POSIX sh. It finds the dotfiles checkout from its own real path, sources `software/homebrew/shellenv.sh`, logs to `~/Library/Logs/<job>.log`, then runs the command. launchd gives a bare environment: no profile, no Homebrew on PATH.
2. **Plist** `<label>.plist` from `templates/label.plist`. Reverse-DNS label such as `com.dotfiles.<job>`. The script is the executable, with `@HOME@` in its path; the installer renders it. Pick a minute that is not `:00` or `:30`.
3. **Installer lines** in `software/<tool>/<tool>.rb`:
   ```ruby
   link_to_home_relative '<job>.sh', '.claude/<job>.sh'   # or another fixed $HOME path
   launch_agent_relative '<label>.plist'
   ```
   `launch_agent_relative` (in `src/helpers.rb`) renders `@HOME@`, copies the plist to `~/Library/LaunchAgents/`, and runs `launchctl bootstrap`. It reloads only when the rendered content changed or the job is not loaded.
4. **Install and test**:
   ```sh
   software/<tool>/<tool>.rb
   /bin/launchctl print "gui/$(id -u)/<label>" | grep -E "state|program|last exit"
   /bin/launchctl kickstart "gui/$(id -u)/<label>"
   tail -f ~/Library/Logs/<job>.log
   ```

For a Claude Code job, the command is headless and nobody answers prompts:

```sh
claude -p "/<skill> <args>" \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "Agent,Skill,WebFetch,WebSearch,Bash(git status:*),Bash(git diff:*)"
```

Pre-allow exactly the tools the job needs. Do not use `--bare`: it skips skills, hooks, CLAUDE.md, and the OAuth login. Leave file changes uncommitted unless the user asked for commits.

### Rules that came from real failures

- **The script, not `/bin/sh`, is the executable.** macOS names a background item after its executable in the "Background Items Added" notice and in Login Items. `/bin/sh -c ...` shows up as "sh". Check with `sudo sfltool dumpbtm` (look for `Name:` next to the label).
- **No `~` or `$HOME` in a plist.** launchd expands nothing. Keep the repo file generic with `@HOME@` and let the installer render it.
- **Copy the plist, do not symlink it.** launchd does not reliably load a symlinked plist; `brew services` copies for the same reason.
- **Reloading kills a running job.** `launchctl bootout` stops it mid-run. The helper skips the reload when nothing changed; wait for a run to end before reinstalling a changed plist.
- **Scripts follow the dotfiles CLAUDE.md rules:** `/usr/bin/<cmd>` or `command <cmd>` for tools the interactive shell wraps, and the repo is public, so no personal data or organization identifiers.
- **Sleep vs. power off.** A `StartCalendarInterval` time slept through runs on wake. A time passed while powered off is skipped.
- **A DarkWake counts as a wake.** With the lid closed, macOS wakes for about two seconds every quarter hour, and launchd starts the job then. A long job crawls for hours inside a closed Mac. Make the script wait until `/usr/bin/pmset -g systemstate` lists `Graphics` (a full wake), and run long work under `/usr/bin/caffeinate -i` with a time limit. See `comply365-recap.sh` for the pattern.
- **A job that edits a repo commits its own files only.** Note before the run whether its files are clean (`git status --porcelain -- <paths>`); afterwards commit by pathspec, `git commit -F <message> -- <paths>`, which records those paths from the working tree and leaves everything else staged, modified or untracked exactly as it was. Skip the commit when the run failed, nothing changed, or the files were dirty before. Put the run's own summary in the message body so the commit explains itself. See `claude-code-levers-refresh.sh` for the pattern.
- **A job that edits a shared file runs on one machine only.** Two machines that both commit the same file diverge. Gate the install in the `.rb` on the profile, and call `launch_agent_remove_relative` plus `trash` for the job's leftovers on every other profile, so a machine that installed the job before the gate drops it on its next run. If the job pushes, push only when its own commit is the sole unpushed commit on `main`; any other unpushed commit belongs to the user. See `claude-code.rb` and `claude-code-levers-refresh.sh`.

## 3. Desktop local scheduled task: set it up

The task is created in the app, not from the CLI. Give the user these values, or let them ask for the task in a Desktop session.

1. Open the Desktop app, **Code** tab, **Routines**, **New routine**, choose **Local**.
2. Fields: **Name** (becomes the folder name on disk), **Description**, **Instructions** (write it like a prompt; a skill invocation such as `/<skill> <args>` works), permission mode and model pickers, working folder (must be trusted), optional isolated worktree, **Schedule** (Manual, Hourly, Daily, Weekdays, Weekly; other intervals by asking Claude in a Desktop session).
3. Click **Run now** once and answer permission prompts with "always allow", so later runs do not stall.
4. The prompt lives at `~/.claude/scheduled-tasks/<name>/SKILL.md`; schedule, folder, model, and enabled state do not. Runs appear under **Scheduled** in the sidebar, with history, including skipped runs and why.

Docs: https://code.claude.com/docs/en/desktop-scheduled-tasks
