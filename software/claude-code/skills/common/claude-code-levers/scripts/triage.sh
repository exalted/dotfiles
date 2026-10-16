#!/bin/sh
# Sort the configuration surfaces a text names into three bins: known (the map
# names it), documented-unmapped (a docs page names it, the map does not) and
# undocumented (neither does). The changelog and the blog are signals, not
# sources of truth: something can change without an entry, and an entry can
# name something the docs do not have yet. A text with nothing in the last two
# bins cannot change a row, whatever its title; at most it teaches how to use a
# mapped lever. A refresh hands this output to its agent, so the agent judges
# candidates, not whole texts.
#
# Usage: triage.sh [--since YYYY-MM-DD] [file ...]
# Without files: the changelog entries and the blog posts dated on or after
# --since, which defaults to last_verified in the map. With files: those texts.
set -eu

skill="$(cd "$(/usr/bin/dirname "$(/usr/bin/readlink -f "$0")")/.." && pwd)"
dotfiles="$(cd "$skill/../../../../.." && pwd)"
map="$skill/references/levers.md"
mirror="$dotfiles/.claude/scratchpad.local/claude-code-levers/docs"

since="$(/usr/bin/sed -nE 's/^last_verified: *([0-9-]+).*/\1/p' "$map" | /usr/bin/head -1)"
if [ "${1:-}" = "--since" ]; then since="$2"; shift 2; fi
[ -d "$mirror/en" ] || { echo "no mirror at $mirror; run sync-docs.sh first" >&2; exit 1; }

# A surface is a code span shaped like a slash command, a CLI flag, an env var,
# a camelCase settings key, a PascalCase event or tool name, a .claude path, or
# a config file name.
surfaces() {
  /usr/bin/grep -oE '`[^`]{2,80}`' | /usr/bin/tr -d '`' \
    | /usr/bin/grep -E '^(/[a-z][a-z0-9-]*|--[a-z][a-z0-9-]*|[A-Z][A-Z0-9_]{3,}|[a-z]+([A-Z][a-z0-9]*)+|([A-Z][a-z0-9]+){2,}|[^ ]*\.claude[^ ]*|[~.]?/?[A-Za-z0-9_./-]*\.(json|md|yaml|toml))$' \
    | /usr/bin/sort -u
}

# The changelog and the what's-new pages are signals themselves, so they do not
# count as documentation of a surface.
triage() {
  echo "== $1"
  surfaces | while IFS= read -r t; do
    if /usr/bin/grep -qF -- "$t" "$map"; then echo "known	$t"
    elif /usr/bin/grep -rqF --exclude=changelog.md --exclude-dir=whats-new --exclude='whats-new*' -- "$t" "$mirror/en"; then echo "documented-unmapped	$t"
    else echo "undocumented	$t"; fi
  done | /usr/bin/sort | /usr/bin/awk -F'\t' '
    { a[$1] = a[$1] " " $2 }
    END { n = split("undocumented documented-unmapped known", order, " "); for (i = 1; i <= n; i++) if (order[i] in a) print order[i] ":" a[order[i]] }'
}

if [ "$#" -gt 0 ]; then
  for f in "$@"; do triage "$f" < "$f"; done
  exit 0
fi

# Changelog entries are <Update label="2.1.299" description="October 14, 2026"> blocks.
/usr/bin/grep -nE '^<Update label="[^"]+" description="[^"]+">' "$mirror/en/changelog.md" \
  | while IFS= read -r line; do
      n="${line%%:*}"
      label="$(printf '%s' "$line" | /usr/bin/sed -E 's/.*label="([^"]+)".*/\1/')"
      day="$(printf '%s' "$line" | /usr/bin/sed -E 's/.*description="([^"]+)".*/\1/')"
      iso="$(/bin/date -j -f '%B %d, %Y' "$day" '+%Y-%m-%d' 2>/dev/null || echo 0000-00-00)"
      [ "$iso" \< "$since" ] && continue
      /usr/bin/awk -v s="$n" 'NR >= s { print; if (NR > s && /^<\/Update>/) exit }' "$mirror/en/changelog.md" \
        | triage "changelog $label ($iso)"
    done

# Posts carry "- Published: YYYY-MM-DD" in their Markdown header.
for f in "$mirror"/blog/*.md; do
  [ -f "$f" ] || continue
  pub="$(/usr/bin/sed -nE 's/^- Published: *([0-9-]+).*/\1/p' "$f" | /usr/bin/head -1)"
  [ -n "$pub" ] && [ "$pub" \< "$since" ] && continue
  triage "blog/$(/usr/bin/basename "$f") (${pub:-undated})" < "$f"
done
