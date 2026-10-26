#!/bin/sh
# Entry point of the com.dotfiles.bash-history-clean launch agent: strips a
# trailing `&& exit` (and its `;`/`||`, `exit N` and `logout` variants) from the
# bash history, so a command found again with Ctrl-r no longer closes the
# terminal. Lines that hold nothing but an exit are dropped.
#
# Takes the history file as an optional argument, for testing on a copy.

history_file="${1:-$HOME/.bash_history}"

log="$HOME/Library/Logs/bash-history-clean.log"
if [ ! -t 1 ]; then
  /bin/mkdir -p "$(/usr/bin/dirname "$log")"
  exec >>"$log" 2>&1
fi

echo "=== $(/bin/date '+%Y-%m-%dT%H:%M:%S%z') start $history_file"
[ -f "$history_file" ] || { echo "no history file"; exit 0; }

umask 077
before="$(/usr/bin/stat -f '%z %m' "$history_file")"
tmp="$history_file.clean.$$"

# Stripping can turn a line into a copy of an existing command. Of those copies,
# keep only the most recent one, as HISTCONTROL=erasedups would have.
result="$(/usr/bin/awk -v out="$tmp" '
  {
    orig = $0
    while (sub(/[[:space:]]*(&&|\|\||;)[[:space:]]*(exit([[:space:]]+[0-9]+)?|logout)[[:space:]]*$/, "")) {}
    if ($0 ~ /^[[:space:]]*(exit([[:space:]]+[0-9]+)?|logout)[[:space:]]*$/ || ($0 != orig && $0 ~ /^[[:space:]]*$/)) {
      drop[NR] = 1; n++
    } else if ($0 != orig) {
      stripped[$0] = 1; n++
    }
    line[NR] = $0
  }
  END {
    if (!n) { print "0 0"; exit }
    for (i = NR; i > 0; i--)
      if (!(i in drop) && line[i] in stripped) {
        if (line[i] in kept) drop[i] = 1
        kept[line[i]] = 1
      }
    for (i = 1; i <= NR; i++) if (i in drop) removed++; else print line[i] > out
    print n, removed
  }
' "$history_file")" || exit 1
changed="${result% *}"
removed="${result#* }"

if [ "$changed" -eq 0 ]; then
  echo "nothing to clean"
  exit 0
fi

# A shell that appended a command while we read would lose it on the rename.
# Skip instead; the next run cleans what is left.
if [ "$(/usr/bin/stat -f '%z %m' "$history_file")" != "$before" ]; then
  /usr/bin/trash "$tmp"
  echo "history changed during the run; skipped"
  exit 0
fi

/bin/mv "$tmp" "$history_file" && echo "cleaned $changed line(s), removed $removed line(s)"
