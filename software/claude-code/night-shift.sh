#!/bin/sh
# Entry point of the night-shift launch agents (skills/work/night-shift): the nightly backlog run, or with
# `security` the weekly deep security analysis. The Python driver does the work and enforces the quota
# guard, the deadlines and the one-run-at-a-time lock; this script only gives it a sane environment.
#
# launchd runs this script directly with a bare environment: no shell profile, no Homebrew on PATH.

self="$(/usr/bin/readlink -f "$0")"
dotfiles="$(cd "$(/usr/bin/dirname "$self")/../.." && pwd)"
. "$dotfiles/software/homebrew/shellenv.sh"

job="${1:-nightly}"
log="$HOME/Library/Logs/night-shift.log"
/bin/mkdir -p "$(/usr/bin/dirname "$log")"
exec >>"$log" 2>&1

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start $job"

# A lid-closed DarkWake starts launch agents for two seconds at a time; only a full wake has Graphics.
fully_awake() {
  /usr/bin/pmset -g systemstate | /usr/bin/grep -q Graphics
}
if ! fully_awake; then
  echo "waiting for a full wake"
  until fully_awake; do /bin/sleep 60; done
  echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') fully awake"
fi

state="$HOME/.local/state/night-shift"
/bin/mkdir -p "$state"
cd "$state" || exit 1

driver="$HOME/.claude/skills/night-shift/scripts/night_shift.py"

# Installed before it is configured: nothing to do, and nothing to report as a failure.
if [ ! -f "$HOME/.config/dotfiles/night-shift/config.toml" ]; then
  echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end $job: not configured (see /night-shift setup)"
  exit 0
fi

# The driver keeps its own deadlines; this outer alarm only catches a driver that hangs itself.
case "$job" in
  # The weekend security run waits out usage resets until its Sunday deadline (the security_deadline knob).
  security) limit_hours=44 ;;
  *) limit_hours=6 ;;
esac

status=0
/usr/bin/caffeinate -i \
  /usr/bin/perl -e 'alarm shift; exec @ARGV or die "exec $ARGV[0]: $!\n"' "$((limit_hours * 3600))" \
  uv run --quiet --no-project --script "$driver" "$job" < /dev/null || status=$?

if [ "$status" -eq 142 ]; then
  uv run --quiet --no-project --script "$driver" fail "The $job run hit its $limit_hours-hour outer limit. See ~/Library/Logs/night-shift.log"
elif [ "$status" -ne 0 ]; then
  uv run --quiet --no-project --script "$driver" fail "The $job run stopped: the driver exited with $status. See ~/Library/Logs/night-shift.log"
fi

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end $job exit=$status"
exit "$status"
