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
# listed by every path the skill may spell it with.
status=0
summary="$scratch/run-summary.txt"
claude -p "/claude-code-levers refresh" \
  --permission-mode acceptEdits \
  --permission-prompts none \
  --allowedTools "Agent,Skill,WebFetch,WebSearch,Bash(git status:*),Bash(git diff:*),Bash($skill/scripts/sync-docs.sh:*),Bash($HOME/.claude/skills/claude-code-levers/scripts/sync-docs.sh:*),Bash(~/.claude/skills/claude-code-levers/scripts/sync-docs.sh:*)" \
  > "$summary" || status=$?
/bin/cat "$summary"

# Commit the map alone, by pathspec, so whatever else is staged or modified in
# the checkout stays exactly as it was. The run's summary becomes the commit
# body: it says why each row changed, which the diff alone would not.
if [ "$status" -eq 0 ] && [ "$map_was_clean" -eq 1 ] && ! command git diff --quiet -- "$map"; then
  message="$scratch/commit-message.txt"
  {
    echo "Refresh the Claude Code levers map ($(/bin/date '+%Y-%m-%d'))"
    echo
    /bin/cat "$summary"
  } > "$message"
  command git commit --quiet -F "$message" -- "$map" && echo "committed $(command git rev-parse --short HEAD)"
elif [ "$map_was_clean" -eq 0 ]; then
  echo "the map had uncommitted changes before the run; result left uncommitted"
fi

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end exit=$status"
exit "$status"
