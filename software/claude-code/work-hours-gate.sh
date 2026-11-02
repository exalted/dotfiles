# Sourced by the weekly unattended Claude jobs (claude-code-levers-refresh.sh, ai-capacity-refresh.sh).
# POSIX sh; expects $dotfiles to be set.
#
# The user's weekday 10:00-17:00 is theirs. The plan's 5-hour window starts at the first use, rounded down to
# the hour, so a job that starts Mon-Fri from 05:00 to 16:59 still holds that window at 10:00. Each job owns a
# weekly slot instead: it starts at <weekday> <hour> and stays open for <span> hours. Several launchd triggers
# fall inside the slot, so a trigger slept through (which launchd fires on wake, perhaps in work hours) is
# retried by the next one; the first success closes the slot until next week.
#
#   gate_job <job> <weekday: mon..sun> <hour> <span hours> <triggers, for the note>
#   gate_done <job> <exit status>
#
# <job> is also the basename of the job's log in ~/Library/Logs/.
#
# A run that is skipped or fails puts one line in the "scheduled-jobs" section of the AI status note; the
# job's next success removes it. A trigger in a slot that already succeeded exits quietly: that is no news.

gate_state="$HOME/.local/state/scheduled-jobs"

gate_note() {
  /bin/mkdir -p "$gate_state"
  body="$gate_state/note-section.md"
  /bin/cat "$gate_state"/*.line 2>/dev/null > "$body"
  [ -s "$body" ] || echo "Nothing needs you." > "$body"
  uv run --quiet --no-project --script \
    "$dotfiles/software/claude-code/skills/work/ai-capacity/scripts/status_note.py" scheduled-jobs "$body" \
    >/dev/null || echo "could not update the AI status note"
}

# A DarkWake (lid closed) also fires launchd triggers; decide only once the Mac is really awake, so the
# decision is made at the time the run would actually start.
gate_wait_for_full_wake() {
  until /usr/bin/pmset -g systemstate | /usr/bin/grep -q Graphics; do /bin/sleep 60; done
}

gate_job() {
  gate_name=$1 gate_triggers=$5
  gate_wait_for_full_wake
  now=$(/bin/date +%s)
  start=$(/bin/date -v-"$2" -v"$3"H -v0M -v0S +%s)
  [ "$start" -le "$now" ] || start=$((start - 7 * 86400))
  end=$((start + $4 * 3600))
  stamp="$gate_state/$gate_name.ok"
  last=$(/usr/bin/stat -f %m "$stamp" 2>/dev/null || echo 0)
  dow=$(/bin/date +%u) hour=$(/bin/date +%H)
  hour=${hour#0}
  when=$(/bin/date '+%a %d %b %H:%M')

  if [ "$last" -ge "$start" ]; then
    echo "already done this week; nothing to do"
    exit 0
  elif [ "$now" -ge "$end" ]; then
    gate_skip "$gate_name: no run this week. It was skipped at $when, after its slot had closed (the Mac was likely asleep at every trigger). Next tries: $gate_triggers."
  elif [ "$dow" -le 5 ] && [ "$hour" -ge 5 ] && [ "$hour" -lt 17 ]; then
    gate_skip "$gate_name: skipped at $when, inside your weekday hours. It retries at its next trigger: $gate_triggers."
  fi
}

gate_skip() {
  echo "skipped: $1"
  /bin/mkdir -p "$gate_state"
  echo "- $1" > "$gate_state/$gate_name.line"
  gate_note
  exit 0
}

gate_done() {
  /bin/mkdir -p "$gate_state"
  if [ "$2" -eq 0 ]; then
    /usr/bin/touch "$gate_state/$1.ok"
    [ -s "$gate_state/$1.line" ] || return 0
    : > "$gate_state/$1.line"
  else
    echo "- $1: failed at $(/bin/date '+%a %d %b %H:%M') (exit $2); see ~/Library/Logs/$1.log. It retries at its next trigger: $gate_triggers." > "$gate_state/$1.line"
  fi
  gate_note
}
