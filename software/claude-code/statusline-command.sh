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

# Usage credits are not in the status line input for claude.ai accounts, and headless `/usage` omits them.
# This is the undocumented endpoint behind the interactive /usage screen, so expect it to break on a
# release: the credits bar then disappears once the cache is an hour old. Fetched in the background at
# most every five minutes, shared by all sessions, so the status line never waits on the network.
credits_cache="$usage_dir/credits.json"
credits_stamp="$usage_dir/credits.fetching"
mtime() { /usr/bin/stat -f %m "$1" 2>/dev/null || echo 0; }
now=$(/bin/date +%s)
if [ $(( now - $(mtime "$credits_cache") )) -ge 300 ] && [ $(( now - $(mtime "$credits_stamp") )) -ge 60 ]; then
  /bin/mkdir -p "$usage_dir"
  /usr/bin/touch "$credits_stamp"
  (
    token=$(/usr/bin/security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty')
    [ -n "$token" ] || exit 0
    /usr/bin/curl -sf -m 10 https://api.anthropic.com/api/oauth/usage \
      -H "Authorization: Bearer $token" -H "anthropic-beta: oauth-2025-04-20" \
      | jq -e '.extra_usage | select(.is_enabled == true)' > "$credits_cache.$$" \
      && /bin/mv "$credits_cache.$$" "$credits_cache"
  ) </dev/null >/dev/null 2>&1 &
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

# The cells are background-colored so the centered label can sit on top. Each
# label character takes the contrast of the cell under it: black on a filled
# cell, the threshold color on an empty one.
render_bar() {
  local pct=$1 label=${2:-$1%} fg bg
  if [ "$pct" -lt 20 ]; then
    fg="32"; bg="42"                       # green
  elif [ "$pct" -lt 50 ]; then
    fg="33"; bg="43"                       # yellow
  elif [ "$pct" -lt 80 ]; then
    fg="38;5;208"; bg="48;5;208"           # orange
  else
    fg="31"; bg="41"                       # red
  fi

  local bar_width=10
  [ $(( ${#label} + 2 )) -gt "$bar_width" ] && bar_width=$(( ${#label} + 2 ))
  local filled=$(( (pct * bar_width + 50) / 100 ))
  [ "$filled" -gt "$bar_width" ] && filled=$bar_width
  [ "$filled" -lt 0 ] && filled=0

  local label_start=$(( (bar_width - ${#label}) / 2 ))
  local bar="" i j ch
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
  printf "%b\e[0m" "$bar"
}

printf "\e[37m%s\e[0m" "${model} (${effort}) "
render_bar "$pct"
printf "\e[37m%s\e[0m" "$resets"

if [ -f "$credits_cache" ] && [ $(( now - $(mtime "$credits_cache") )) -lt 3600 ]; then
  # floor, not round: the /usage screen floors, and the two should agree.
  IFS=$'\t' read -r credits_pct used limit < <(jq -r '
    pow(10; .decimal_places // 2) as $unit
    | [(.utilization | floor), (.used_credits / $unit), (.monthly_limit / $unit)]
    | @tsv
  ' "$credits_cache" 2>/dev/null)
  if [ -n "$credits_pct" ]; then
    printf " \e[37m·\e[0m 💸 "
    render_bar "$credits_pct" "$(printf "%.2f/%.0f" "$used" "$limit")"
    # The endpoint gives no reset time; /usage shows credits resetting on the 1st of each month.
    today=$(/bin/date -j -f %Y-%m-%d "$(/bin/date +%Y-%m-%d)" +%s)
    first=$(/bin/date -j -f %Y-%m-%d "$(/bin/date -v1d -v+1m +%Y-%m-%d)" +%s)
    printf "\e[37m (-%dd)\e[0m" $(( (first - today + 43200) / 86400 ))
  fi
fi

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
