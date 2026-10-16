#!/bin/sh
# Entry point of the com.dotfiles.claude-code-levers-refresh launch agent: the
# weekly, unattended `/claude-code-levers refresh` (skills/common/claude-code-levers).
#
# launchd runs this script directly, by the absolute path the installer rendered
# into the plist, with a bare environment: no shell profile, no Homebrew on PATH.
# So this script finds the dotfiles checkout from its own real path and puts
# Homebrew (where `claude` lives) on PATH itself.

self="$(/usr/bin/readlink -f "$0")"
dotfiles="$(cd "$(/usr/bin/dirname "$self")/../.." && pwd)"
. "$dotfiles/software/homebrew/shellenv.sh"

skill="$dotfiles/software/claude-code/skills/common/claude-code-levers"
map="software/claude-code/skills/common/claude-code-levers/references/levers.md"
scratch="$dotfiles/.claude/scratchpad.local/claude-code-levers"
log="$HOME/Library/Logs/claude-code-levers-refresh.log"
/bin/mkdir -p "$(/usr/bin/dirname "$log")" "$scratch"
exec >>"$log" 2>&1

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start"
cd "$dotfiles" || exit 1

# The job commits the map by itself at the end. A map that is already dirty
# would get someone else's edits mixed into that commit, so note it now and
# leave the result uncommitted in that case.
map_was_clean=1
[ -z "$(command git status --porcelain -- "$map")" ] || map_was_clean=0

# The mirror lets the skill read whole pages from disk. If the sync fails, the
# skill falls back to WebFetch, which is allowed below, so the run still goes on.
"$skill/scripts/sync-docs.sh" || echo "docs sync failed; the skill falls back to WebFetch"

# Nobody is there to answer prompts: edits inside the checkout are accepted by
# the mode, everything else is denied unless pre-allowed here. Read and Grep,
# which the agent uses on the mirror, need no permission. The sync script is
# listed by every path the skill may spell it with, as are the single-page fetch
# the skill uses for a page the mirror lacks and the triage of the signals.
# Nobody is there to pick up side tasks: keep the todo hooks silent (see skills/common/todo).
export CLAUDE_TODO_HOOKS=0
status=0
summary="$scratch/run-summary.txt"
claude -p "/claude-code-levers refresh" \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "Agent,Skill,WebFetch,WebSearch,Bash(git status:*),Bash(git diff:*),Bash($skill/scripts/sync-docs.sh:*),Bash($HOME/.claude/skills/claude-code-levers/scripts/sync-docs.sh:*),Bash(~/.claude/skills/claude-code-levers/scripts/sync-docs.sh:*),Bash($skill/scripts/fetch-page.sh:*),Bash($HOME/.claude/skills/claude-code-levers/scripts/fetch-page.sh:*),Bash(~/.claude/skills/claude-code-levers/scripts/fetch-page.sh:*),Bash($skill/scripts/triage.sh:*),Bash($HOME/.claude/skills/claude-code-levers/scripts/triage.sh:*),Bash(~/.claude/skills/claude-code-levers/scripts/triage.sh:*)" \
  > "$summary" || status=$?
/bin/cat "$summary"

# Commit the map alone, by pathspec, so whatever else is staged or modified in
# the checkout stays exactly as it was. The run's summary becomes the commit
# body: it says why each row changed, which the diff alone would not.
#
# Then push, but only when that commit is the sole unpushed one on main: this
# machine is the one that refreshes the map, and the other machines take it from
# origin. Any other unpushed commit is the user's, and only the user pushes it.
if [ "$status" -eq 0 ] && [ "$map_was_clean" -eq 1 ] && ! command git diff --quiet -- "$map"; then
  message="$scratch/commit-message.txt"
  {
    echo "Refresh the Claude Code levers map ($(/bin/date '+%Y-%m-%d'))"
    echo
    /bin/cat "$summary"
  } > "$message"
  command git commit --quiet -F "$message" -- "$map" && echo "committed $(command git rev-parse --short HEAD)"

  command git fetch --quiet origin main || echo "fetch failed; push skipped"
  if [ "$(command git rev-parse --abbrev-ref HEAD)" != main ]; then
    echo "not on main; push skipped"
  elif [ "$(command git rev-parse HEAD~1)" != "$(command git rev-parse origin/main)" ]; then
    echo "main holds other unpushed commits, or origin moved on; push skipped"
  else
    command git push --quiet origin main && echo "pushed to origin/main"
  fi
elif [ "$map_was_clean" -eq 0 ]; then
  echo "the map had uncommitted changes before the run; result left uncommitted"
fi

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end exit=$status"
exit "$status"
