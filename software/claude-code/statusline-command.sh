#!/usr/bin/env bash
input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "?"')
effort=$(echo "$input" | jq -r '.effort.level // "?"')
pct=$(echo "$input" | jq -r '(.rate_limits.five_hour.used_percentage // 0) | round')
resets_at=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
session_id=$(echo "$input" | jq -r '.session_id // empty')
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')

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

# Pick color + emoji by usage threshold.
if [ "$pct" -lt 20 ]; then
  emoji="🟢"; color="\e[32m"               # green text
elif [ "$pct" -lt 50 ]; then
  emoji="🟡"; color="\e[33m"               # yellow text
elif [ "$pct" -lt 80 ]; then
  emoji="🟠"; color="\e[30;48;5;208m"      # black on orange bg
else
  emoji="🔴"; color="\e[30;41m"            # black on red bg
fi

prefix="${model} (${effort}) "
status="${pct}%${resets}"

# Left-aligned (Claude Code's default). Emoji stays uncolored (no background
# bleed); only the status text gets $color.
printf "\e[37m%s%s ${color}%s\e[0m" "$prefix" "$emoji" "$status"

# Session id dimmed and unlabeled, and "@" is a word boundary, so a
# double-click in the terminal selects exactly the id.
if [ -n "$session_id" ] || [ -n "$branch" ]; then
  printf " \e[37m·\e[0m "
  [ -n "$session_id" ] && printf "\e[2m%s\e[0m" "$session_id"
  [ -n "$session_id" ] && [ -n "$branch" ] && printf "\e[37m@\e[0m"
  [ -n "$branch" ] && printf "\e[37m%s\e[0m" "$branch"
fi
