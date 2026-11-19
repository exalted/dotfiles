#!/usr/bin/env bash
# Hook for the Stop and Notification events: macOS banner plus sound.
# Usage: notify.sh <stop|attention>. Reads the hook JSON on stdin.
set -euo pipefail

kind="${1:?usage: notify.sh <stop|attention>}"
input="$(command cat)"
project="$(command jq -r '.cwd // empty | split("/") | last' <<<"$input")"

zed_is_frontmost() {
  command lsappinfo info -only bundleid "$(command lsappinfo front)" | command grep -q 'bundleID="dev\.zed\.Zed'
}

case "$kind" in
  stop)
    # Zed in front means you watched the turn end, so a notification adds only noise.
    zed_is_frontmost && exit 0
    message="Turn finished"
    sound="Glass"
    ;;
  attention)
    # idle_prompt repeats the Stop banner of the same turn about 60 s later.
    [[ "$(command jq -r '.notification_type // empty' <<<"$input")" == idle_prompt ]] && exit 0
    message="$(command jq -r '.message // "Needs your attention"' <<<"$input")"
    sound="Sosumi"
    ;;
  *)
    exit 2
    ;;
esac

# Arguments go through argv, so quotes in the message cannot break the script.
command osascript \
  -e 'on run argv' \
  -e 'display notification (item 1 of argv) with title (item 2 of argv) sound name (item 3 of argv)' \
  -e 'end run' \
  -- "$message" "Claude Code${project:+ · $project}" "$sound" >/dev/null
