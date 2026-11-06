#!/bin/sh
# Claude Code installs a plugin's npm packages only into a cached copy, never into
# a plugin loaded in place, so this puts them in the plugin's data directory.
root="${CLAUDE_PLUGIN_ROOT:?}"
data="${CLAUDE_PLUGIN_DATA:?}"

mkdir -p "$data"
if cmp -s "$root/package-lock.json" "$data/package-lock.json" && [ -d "$data/node_modules" ]; then
  exit 0
fi

cp "$root/package.json" "$root/package-lock.json" "$data/" || exit 1
(cd "$data" && npm ci --silent --no-audit --no-fund) || { rm -f "$data/package-lock.json"; exit 1; }
