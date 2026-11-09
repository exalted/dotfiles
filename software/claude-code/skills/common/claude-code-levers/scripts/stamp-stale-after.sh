#!/bin/sh
# Write stale_after into the map's frontmatter: last_verified plus the interval
# and margin in ../freshness.json. Every reader compares against this one date,
# so the freshness rule has one home. The margin covers the scheduled job's
# retry slot: a week whose run succeeds only on its last retry must not look
# stale.
set -eu
dir="$(command cd "$(/usr/bin/dirname "$0")/.." && pwd)"
map="$dir/references/levers.md"
days="$(/usr/bin/plutil -extract refresh_every_days raw "$dir/freshness.json")"
margin="$(/usr/bin/plutil -extract margin_days raw "$dir/freshness.json")"
verified="$(/usr/bin/sed -nE 's/^last_verified: *([0-9-]+).*/\1/p' "$map" | /usr/bin/head -1)"
stale="$(/bin/date -j -v+"$((days + margin))"d -f %Y-%m-%d "$verified" +%Y-%m-%d)"
if /usr/bin/grep -q '^stale_after:' "$map"; then
  /usr/bin/sed -i '' -E "s/^stale_after:.*/stale_after: $stale/" "$map"
else
  /usr/bin/sed -i '' -E "s/^(last_verified:.*)/\1\\
stale_after: $stale/" "$map"
fi
echo "stale_after: $stale"
