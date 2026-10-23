#!/usr/bin/env bash
input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "?"')
effort=$(echo "$input" | jq -r '.effort.level // "?"')
pct=$(echo "$input" | jq -r '(.rate_limits.five_hour.used_percentage // 0) | round')
resets_at=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
session_id=$(echo "$input" | jq -r '.session_id // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')

# The night shift's quota guard reads this snapshot (skills/work/night-shift/scripts/quota.py): the only
# place Claude Code hands out the plan's usage windows is the status line. Headless runs never call it, so
# day sessions keep it fresh. rate_limits arrives only after a session's first API response.
usage_dir="$HOME/.local/state/claude-usage"
if echo "$input" | jq -e '.rate_limits.seven_day' >/dev/null 2>&1; then
  /bin/mkdir -p "$usage_dir"
  echo "$input" | jq '{at: (now | floor), rate_limits}' > "$usage_dir/latest.json.$$" && /bin/mv "$usage_dir/latest.json.$$" "$usage_dir/latest.json"
elif echo "$input" | jq -e '.model' >/dev/null 2>&1 && [ ! -f "$usage_dir/latest.json" ]; then
  /bin/mkdir -p "$usage_dir"
  echo "$input" | jq '{at: (now | floor), keys: (keys)}' > "$usage_dir/seen-without-rate-limits.json"
fi

# --no-optional-locks: the status line refreshes often and must never contend
# with a git command the session itself is running.
branch=""
if [ -n "$cwd" ]; then
  branch=$(git --no-optional-locks -C "$cwd" branch --show-current 2>/dev/null)
  if [ -z "$branch" ]; then
    sha=$(git --no-optional-locks -C "$cwd" rev-parse --short HEAD 2>/dev/null)
    branch="$sha"
  fi
fi

# Format the reset time in 24h, local timezone (uses the system date, not any
# interactive-shell override, since this runs non-interactively).
resets=""
if [ -n "$resets_at" ]; then
  resets=" (resets $(/bin/date -r "$resets_at" +%H:%M))"
fi

if [ "$pct" -lt 20 ]; then
  fg="32"; bg="42"                       # green
elif [ "$pct" -lt 50 ]; then
  fg="33"; bg="43"                       # yellow
elif [ "$pct" -lt 80 ]; then
  fg="38;5;208"; bg="48;5;208"           # orange
else
  fg="31"; bg="41"                       # red
fi

bar_width=10
filled=$(( (pct * bar_width + 50) / 100 ))
[ "$filled" -gt "$bar_width" ] && filled=$bar_width
[ "$filled" -lt 0 ] && filled=0

# The cells are background-colored so the centered label can sit on top. Each
# label character takes the contrast of the cell under it: black on a filled
# cell, the threshold color on an empty one.
label="${pct}%"
label_start=$(( (bar_width - ${#label}) / 2 ))
bar=""
for ((i = 0; i < bar_width; i++)); do
  j=$(( i - label_start ))
  ch=" "
  [ "$j" -ge 0 ] && [ "$j" -lt "${#label}" ] && ch="${label:j:1}"
  if [ "$i" -lt "$filled" ]; then
    bar+="\e[30;${bg}m${ch}"
  else
    bar+="\e[${fg};48;5;238m${ch}"
  fi
done

prefix="${model} (${effort}) "

printf "\e[37m%s%b\e[0m\e[37m%s\e[0m" "$prefix" "$bar" "$resets"

# Session id dimmed and unlabeled, and "@" is a word boundary, so a
# double-click in the terminal selects exactly the id.
if [ -n "$session_id" ] || [ -n "$branch" ]; then
  printf " \e[37m·\e[0m "
  [ -n "$session_id" ] && printf "\e[2m%s\e[0m" "$session_id"
  [ -n "$session_id" ] && [ -n "$branch" ] && printf "\e[37m@\e[0m"
  [ -n "$branch" ] && printf "\e[37m%s\e[0m" "$branch"
fi

# Claude Code drops the whole status line when this script exits non-zero, and
# the `[ -n "$branch" ] && ...` above fails outside a git repo.
exit 0
