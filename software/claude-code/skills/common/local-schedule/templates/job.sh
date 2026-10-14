#!/bin/sh
# Entry point of the <label> launch agent: <one line on what the job does>.
#
# launchd runs this script directly, by the absolute path the installer rendered
# into the plist, with a bare environment: no shell profile, no Homebrew on PATH.
# So this script finds the dotfiles checkout from its own real path and puts
# Homebrew on PATH itself.

self="$(/usr/bin/readlink -f "$0")"
dotfiles="$(cd "$(/usr/bin/dirname "$self")/../.." && pwd)"
. "$dotfiles/software/homebrew/shellenv.sh"

log="$HOME/Library/Logs/<job>.log"
/bin/mkdir -p "$(/usr/bin/dirname "$log")"
exec >>"$log" 2>&1

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start"
cd "$dotfiles" || exit 1

status=0
<command> || status=$?

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') end exit=$status"
exit "$status"
