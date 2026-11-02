#!/bin/sh
# Entry point of the com.dotfiles.ai-capacity-refresh launch agent: the weekly, unattended
# `/ai-capacity refresh` (skills/work/ai-capacity), then model-steward, which moves the introspective skills to
# the strongest model it found and commits that (skills/work/model-steward).
#
# launchd runs this script directly with a bare environment, so it starts itself again from the user's login
# profile, as the night shift does: the CLIs it asks then see what a terminal sees.

self="$(/usr/bin/readlink -f "$0")"
dotfiles="$(cd "$(/usr/bin/dirname "$self")/../.." && pwd)"
. "$dotfiles/software/homebrew/shellenv.sh"
if [ -z "${AI_CAPACITY_PROFILE:-}" ]; then
  export AI_CAPACITY_PROFILE=1
  exec bash -lc 'exec "$0" "$@"' "$self" "$@"
fi

state="$HOME/.local/state/ai-capacity"
log="$HOME/Library/Logs/ai-capacity-refresh.log"
/bin/mkdir -p "$state" "$(/usr/bin/dirname "$log")"
exec >>"$log" 2>&1
echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start"

# Claude's 7-day window resets on Wednesday morning, and the refresh wants that week complete; Wednesday 17:00
# is the first start after it that keeps the user's work day free. The slot ends Sunday 22:00.
. "$dotfiles/software/claude-code/work-hours-gate.sh"
gate_job ai-capacity-refresh wed 17 101 "Wed 17:23, Thu 17:23, Sat 09:23"

cd "$state" || exit 1

# Nobody is there to answer prompts or pick up side tasks. Auto mode's classifier reviews each command: the
# refresh has to try commands it has not seen before when a route moved. Its hard rules keep it read-only.
export CLAUDE_TODO_HOOKS=0
status=0
claude -p "/ai-capacity refresh" --model fable --effort high \
  --settings "$dotfiles/software/claude-code/skills/work/ai-capacity/refresh-settings.json" \
  --permission-mode auto \
  --permission-prompts none \
  --max-budget-usd 10 || status=$?

if [ "$status" -eq 0 ]; then
  uv run --quiet --no-project --script "$dotfiles/software/claude-code/skills/work/model-steward/scripts/steward.py" --commit || status=$?
fi

gate_done ai-capacity-refresh "$status"
echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end exit=$status"
exit "$status"
