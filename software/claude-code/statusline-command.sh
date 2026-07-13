#!/usr/bin/env bash
input=$(cat)

model=$(echo "$input" | jq -r '.model.display_name // "?"')
effort=$(echo "$input" | jq -r '.effort.level // "?"')
pct=$(echo "$input" | jq -r '(.rate_limits.five_hour.used_percentage // 0) | round')
resets_at=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')

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

prefix="${model} (${effort}) | "
status="${pct}%${resets}"

# Left-aligned (Claude Code's default). Emoji stays uncolored (no background
# bleed); only the status text gets $color.
printf "\e[37m%s%s ${color}%s\e[0m" "$prefix" "$emoji" "$status"
