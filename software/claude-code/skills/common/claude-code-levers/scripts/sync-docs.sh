#!/bin/sh
# Mirror the Claude Code docs as Markdown so a refresh reads whole pages from
# disk instead of fetching them one by one over WebFetch, which cuts a page at
# 100k characters (hooks.md alone is 270k) and forced a fetch cap on the run.
# The site is Mintlify-hosted with no public source repository, but every page
# is served as Markdown at its URL plus ".md", and llms.txt lists them all.
#
# Usage: sync-docs.sh [mirror-dir]
# Default mirror: <dotfiles>/.claude/scratchpad.local/claude-code-levers/docs,
# the scratchpad of the repository this skill is checked out in. A doc URL maps
# to a mirror file by its path after "/docs/": .../docs/en/hooks.md is en/hooks.md.
# Files of pages that left the index are not removed; llms.txt in the mirror is
# the authoritative page list.
set -eu

index_url='https://code.claude.com/docs/llms.txt'
skill="$(cd "$(/usr/bin/dirname "$(/usr/bin/readlink -f "$0")")/.." && pwd)"
dotfiles="$(cd "$skill/../../../../.." && pwd)"
scratchpad="$dotfiles/.claude/scratchpad.local"
mirror="${1:-$scratchpad/claude-code-levers/docs}"

if [ -z "${1:-}" ] && [ ! -f "$scratchpad/.gitignore" ]; then
  /bin/mkdir -p "$scratchpad"
  printf '*\n' > "$scratchpad/.gitignore"
fi
/bin/mkdir -p "$mirror"

/usr/bin/curl -sSf -m 60 --retry 2 "$index_url" -o "$mirror/llms.txt"
/usr/bin/grep -oE 'https://code\.claude\.com/docs/[^ )]+\.md' "$mirror/llms.txt" \
  | /usr/bin/sort -u > "$mirror/.pages"
: > "$mirror/.failed"

/usr/bin/xargs -P 8 -I{} /bin/sh -c '
  url=$1; mirror=$2
  path="${url#https://code.claude.com/docs/}"
  /bin/mkdir -p "$mirror/$(/usr/bin/dirname "$path")"
  /usr/bin/curl -sSf -m 60 --retry 2 "$url" -o "$mirror/$path" || echo "$url" >> "$mirror/.failed"
' _ {} "$mirror" < "$mirror/.pages"

/bin/date '+%Y-%m-%dT%H:%M:%S%z' > "$mirror/.synced"
echo "mirror: $mirror"
echo "pages: $(/usr/bin/wc -l < "$mirror/.pages" | /usr/bin/tr -d ' ') failed: $(/usr/bin/wc -l < "$mirror/.failed" | /usr/bin/tr -d ' ')"
[ ! -s "$mirror/.failed" ] || { echo "failed pages:"; /bin/cat "$mirror/.failed"; }
