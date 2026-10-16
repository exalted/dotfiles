#!/bin/sh
# Fetch one doc page as Markdown into the mirror, whole. WebFetch cuts a page at
# about 100k characters, and the hooks, env-vars, MCP, skills and subagents
# references are longer than that, so a page the mirror lacks is fetched with
# this script, never with WebFetch, as long as curl can reach the site.
#
# Usage: fetch-page.sh <url> [mirror-dir]
# Accepts the page URL with or without ".md" and prints the mirror file's path.
# The mirror default is the same as sync-docs.sh's.
set -eu

url="${1:?usage: fetch-page.sh <url> [mirror-dir]}"
skill="$(cd "$(/usr/bin/dirname "$(/usr/bin/readlink -f "$0")")/.." && pwd)"
dotfiles="$(cd "$skill/../../../../.." && pwd)"
mirror="${2:-$dotfiles/.claude/scratchpad.local/claude-code-levers/docs}"

case "$url" in
  https://code.claude.com/docs/*) ;;
  *) echo "not a Claude Code docs URL: $url" >&2; exit 2 ;;
esac
url="${url%.md}.md"
path="${url#https://code.claude.com/docs/}"

/bin/mkdir -p "$mirror/$(/usr/bin/dirname "$path")"
/usr/bin/curl -sSf -m 60 --retry 2 "$url" -o "$mirror/$path"
echo "$mirror/$path"
