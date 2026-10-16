#!/bin/sh
# Mirror the Claude Code docs as Markdown so a refresh reads whole pages from
# disk instead of fetching them one by one over WebFetch, which cuts a page at
# 100k characters (hooks.md alone is 270k) and forced a fetch cap on the run.
# The site is Mintlify-hosted with no public source repository, but every page
# is served as Markdown at its URL plus ".md".
#
# No single index is complete: llms.txt and the sitemap each lack pages the
# other has, and some pages (plugins, terminal-guide) are in neither and are
# only reachable by a link from another page. So the page list is the union of
# llms.txt, the English part of the sitemap, and every docs link found in the
# pages already mirrored, followed until no new page turns up.
#
# Usage: sync-docs.sh [mirror-dir]
# Default mirror: <dotfiles>/.claude/scratchpad.local/claude-code-levers/docs,
# the scratchpad of the repository this skill is checked out in. A doc URL maps
# to a mirror file by its path after "/docs/": .../docs/en/hooks.md is en/hooks.md.
# Files of pages that left the index are not removed; .pages in the mirror is
# the authoritative page list, .failed the pages that could not be fetched.
set -eu

site='https://code.claude.com/docs'
skill="$(cd "$(/usr/bin/dirname "$(/usr/bin/readlink -f "$0")")/.." && pwd)"
dotfiles="$(cd "$skill/../../../../.." && pwd)"
scratchpad="$dotfiles/.claude/scratchpad.local"
mirror="${1:-$scratchpad/claude-code-levers/docs}"

if [ -z "${1:-}" ] && [ ! -f "$scratchpad/.gitignore" ]; then
  /bin/mkdir -p "$scratchpad"
  printf '*\n' > "$scratchpad/.gitignore"
fi
/bin/mkdir -p "$mirror"

# Page paths are kept without ".md" and without anchors: "en/hooks".
normalize() {
  /usr/bin/sed -E "s#^$site/##; s/[#?].*//; s/\.md\$//; s#/\$##" | /usr/bin/grep -E '^en/[A-Za-z0-9_/.-]+$' | /usr/bin/sort -u
}

/usr/bin/curl -sSf -m 60 --retry 2 "$site/llms.txt" -o "$mirror/llms.txt"
/usr/bin/grep -oE "$site/[^ )]+\.md" "$mirror/llms.txt" | normalize > "$mirror/.pages-llms"
/usr/bin/curl -sSf -m 60 --retry 2 "$site/sitemap.xml" -o "$mirror/sitemap.xml"
/usr/bin/grep -oE '<loc>[^<]+</loc>' "$mirror/sitemap.xml" | /usr/bin/sed -E 's#</?loc>##g' | normalize > "$mirror/.pages-sitemap"
/usr/bin/sort -u "$mirror/.pages-llms" "$mirror/.pages-sitemap" > "$mirror/.pages"
: > "$mirror/.failed"

fetch_missing() {
  /usr/bin/xargs -P 8 -I{} /bin/sh -c '
    page=$1; mirror=$2; site=$3
    [ -f "$mirror/$page.md" ] && exit 0
    /bin/mkdir -p "$mirror/$(/usr/bin/dirname "$page")"
    /usr/bin/curl -sSf -m 60 --retry 2 "$site/$page.md" -o "$mirror/$page.md" || echo "$page" >> "$mirror/.failed"
  ' _ {} "$mirror" "$site"
}

# Links inside mirrored pages: relative "/docs/en/..." and absolute ones.
linked_pages() {
  /usr/bin/grep -rhoE "(\]\(|$site)/docs/en/[A-Za-z0-9_/.#?=-]+" "$mirror/en" 2>/dev/null \
    | /usr/bin/sed -E 's#^\]\(/docs/##; s#^'"$site"'/##' | normalize
}

# Pass 1 fetches the indexed pages, pass 2 the pages they link to, and so on
# until a pass finds nothing new. A few rounds suffice; the cap is a safety net.
# A linked page that does not exist stays in .failed and out of .pages.
round=0
fetch_missing < "$mirror/.pages"
while [ "$round" -lt 5 ]; do
  round=$((round + 1))
  /usr/bin/sort -u "$mirror/.failed" -o "$mirror/.failed"
  new="$(linked_pages | /usr/bin/comm -23 - "$mirror/.pages" | /usr/bin/comm -23 - "$mirror/.failed")"
  [ -n "$new" ] || break
  printf '%s\n' "$new" | fetch_missing
  printf '%s\n' "$new" | /usr/bin/sort -u - "$mirror/.pages" -o "$mirror/.pages"
done
/usr/bin/sort -u "$mirror/.failed" -o "$mirror/.failed"
/usr/bin/comm -23 "$mirror/.pages" "$mirror/.failed" | /usr/bin/sort -u -o "$mirror/.pages"

/bin/date '+%Y-%m-%dT%H:%M:%S%z' > "$mirror/.synced"
echo "mirror: $mirror"
echo "pages: $(/usr/bin/wc -l < "$mirror/.pages" | /usr/bin/tr -d ' ') (llms.txt $(/usr/bin/wc -l < "$mirror/.pages-llms" | /usr/bin/tr -d ' '), sitemap $(/usr/bin/wc -l < "$mirror/.pages-sitemap" | /usr/bin/tr -d ' '), link rounds $round) failed: $(/usr/bin/wc -l < "$mirror/.failed" | /usr/bin/tr -d ' ')"
[ ! -s "$mirror/.failed" ] || { echo "failed pages:"; /bin/cat "$mirror/.failed"; }
