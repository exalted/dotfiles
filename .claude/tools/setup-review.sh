#!/usr/bin/env bash
# Has a work repo's setup/local-dev story moved since we last analyzed it?
#
# comply365 re-expresses what those repos' own setups install into rc files. That
# re-expression is only correct for the version of the setup it was written
# against, so when a repo's setup.sh, git hooks, runtime pins or local-dev docs
# change, our wiring has to be re-read against them.
#
# This script does NOT judge whether a change matters — a diff cannot tell an
# rc-file write from a reworded paragraph. It finds the delta and stops. The
# judgement is a human/agent reading, recorded back into the skill's tracked
# repos table (see `.claude/skills/comply365/SKILL.md`), which is also where the
# baseline commits live.
#
# Exit 0 = every tracked repo is analyzed and unchanged since. Exit 1 = at least
# one repo needs reading before its wiring can be trusted.
set -uo pipefail

# `--porcelain` prints one `STATUS<TAB>repo<TAB>detail` line per finding and
# nothing else. The Stop hook parses that instead of the human table: it first
# grepped this script's own guidance footer, matched the words DELTA and
# NEVER-ANALYZED in the prose, and reported a criterion as failing with a
# sentence of help text as its evidence. Machine output and prose must not share
# a stream.
PORCELAIN=no
[ "${1:-}" = --porcelain ] && PORCELAIN=yes

name='' base='' notes=() flags=()
# `flags` carry their own status keyword (`KEYWORD<TAB>text`) because they are a
# second, independent axis: a repo can be perfectly up to date AND have dead
# hooks, and those map to different criteria. `notes` are plain context.
emit() { # $1=status keyword  $2=detail
  local kw="$1" detail="$2" n f
  if [ "$PORCELAIN" = yes ]; then
    printf '%s\t%s\t%s\n' "$kw" "$name" "$detail"
    for f in ${flags+"${flags[@]}"}; do printf '%s\t%s\t%s\n' "${f%%$'\t'*}" "$name" "${f#*$'\t'}"; done
    for n in ${notes+"${notes[@]}"}; do printf '%s\t%s\t%s\n' NOTE "$name" "$n"; done
    return
  fi
  printf '%-14s %-10s %-15s %s\n' "$name" "${base:--}" "$kw" "$detail"
  for f in ${flags+"${flags[@]}"}; do printf '%26s%s — %s\n' '' "${f%%$'\t'*}" "${f#*$'\t'}"; done
  for n in ${notes+"${notes[@]}"}; do printf '%26s%s\n' '' "$n"; done
}

repo="$(git rev-parse --show-toplevel)"; cd "$repo"
# Both overridable so the branches below can be driven against fixture tables and
# throwaway clones. Every status this prints was verified that way; without the
# seam the only reachable branch is whatever the real repos happen to be in.
SKILL="${COMPLY365_SKILL:-.claude/skills/comply365/SKILL.md}"
DEV_ROOT="${DEV_ROOT:-$HOME/Developer}"
drift=0

# What can change the shell contract. Deliberately NOT the whole tree: a
# mechanism that fires on every upstream commit gets ignored, and an ignored
# gate is worse than none. `local` is included because that is where a repo
# keeps its local-dev environment; `.envrc` because direnv runs it on every `cd`.
# `package.json` and `pyproject.toml` are handled separately below.
WATCH_PATHS=(
  setup local .githooks .husky
  .envrc .nvmrc .node-version .tool-versions .python-version
  Brewfile Makefile README.md CLAUDE.md AGENTS.md
)

# package.json changes on nearly every commit, so diffing the file would make
# this tool cry wolf forever. Only these keys can alter what shell/runtime the
# repo expects; dependency churn is invisible here.
PKG_KEYS='engines packageManager volta scripts type'

pkg_keys_changed() { # $1=repo dir  $2=base rev  $3=tip rev  -> 0 when a key moved
  local dir="$1" base="$2" tip="$3" a b
  # No package.json at either end (a repo that has none, or one that gained or
  # lost it) is not a key change; the file itself appearing in the diff is what
  # WATCH_PATHS is for.
  git -C "$dir" cat-file -e "$base:package.json" 2>/dev/null || return 1
  git -C "$dir" cat-file -e "$tip:package.json"  2>/dev/null || return 1
  a="$(git -C "$dir" show "$base:package.json" 2>/dev/null)" || return 1
  b="$(git -C "$dir" show "$tip:package.json"  2>/dev/null)" || return 1
  [ "$(printf '%s' "$a" | pkg_slice)" != "$(printf '%s' "$b" | pkg_slice)" ]
}

pkg_slice() {
  python3 -c '
import json, sys, os
keys = os.environ["PKG_KEYS"].split()
try:
    d = json.load(sys.stdin)
except Exception:
    print("UNPARSEABLE"); sys.exit(0)
print(json.dumps({k: d.get(k) for k in keys}, sort_keys=True))
'
}
export PKG_KEYS

# pyproject.toml churns with dependency bumps the same way; only the interpreter
# range can change what a session expects. A line match, not a TOML parse: the
# stdlib parser needs a newer python3 than macOS ships, and a parse that falls
# back to the same placeholder at both ends would never report anything.
py_pin() { # $1=repo dir  $2=rev
  git -C "$1" show "$2:pyproject.toml" 2>/dev/null | command grep -E "^[[:space:]]*requires-python[[:space:]]*="
}

# The tracked repos table in SKILL.md is the record: column 1 the repo, column 3
# the commit its setup was last analyzed at. Kept there rather than in a
# generated file so the baseline and the reasoning behind it are read together.
rows="$(command awk -F'|' '
  /^\|[[:space:]]*repo[[:space:]]*\|/ { intable=1; next }
  intable && /^\|[[:space:]]*-/       { next }
  intable && !/^\|/                   { intable=0 }
  intable {
    gsub(/[`[:space:]]/, "", $2); gsub(/[`[:space:]]/, "", $4)
    if ($2 != "") print $2 "\t" $4
  }
' "$SKILL")"

if [ -z "$rows" ]; then
  echo "No tracked repos table found in $SKILL — nothing to check." >&2
  exit 1
fi

if [ "$PORCELAIN" = no ]; then
  printf '%-14s %-10s %s\n' REPO BASELINE STATUS
  printf '%-14s %-10s %s\n' -------------- ---------- ------
fi

while IFS="$(printf '\t')" read -r name base; do
  [ -n "$name" ] || continue
  dir="$DEV_ROOT/$name"
  # Reset before the first `continue`, not after it: these are loop-carried, and
  # resetting them further down leaked the previous repo's flags onto every
  # early-exit row — an uncloned repo was reported as having dead git hooks.
  notes=(); flags=()

  if [ ! -d "$dir/.git" ]; then
    emit NO-CLONE "not cloned at $dir; cannot analyze"
    continue
  fi

  head="$(git -C "$dir" rev-parse --short HEAD 2>/dev/null)"

  # A repo that ships .githooks/ but has core.hooksPath unset has INACTIVE
  # hooks — git silently falls back to .git/hooks, which holds only samples.
  # Every repo here sets it from its own setup.sh, so an unset value means that
  # setup never ran in this clone. Worth its own signal: the zsh/sh hook
  # reachability work (AC-19..23) is pointless for a repo whose hooks never
  # fire at all, and nothing else here would notice.
  if [ -d "$dir/.githooks" ] && [ -z "$(git -C "$dir" config --get core.hooksPath || true)" ]; then
    flags+=("HOOKS-INACTIVE"$'\t'"ships .githooks/ but core.hooksPath is unset, so its hooks never fire; run its setup.sh")
    drift=1
  fi

  case "$base" in
    ''|-|none|never)
      base='-'
      emit NEVER-ANALYZED "read its setup/README against our wiring, then record $head"
      drift=1
      continue
      ;;
  esac

  if ! git -C "$dir" cat-file -e "$base^{commit}" 2>/dev/null; then
    emit BASELINE-GONE "recorded commit absent from this clone (re-clone or force-push?); re-analyze at $head"
    drift=1
    continue
  fi

  # Diff against the newest commit this clone KNOWS about, not its checkout. A
  # clone sitting behind its remote would otherwise report "unchanged" while the
  # upstream setup has in fact moved — and origin/<branch> is a local ref, so
  # the answer is already here. No fetch: this is as fresh as your last pull.
  tip=HEAD; tipname="$head"; stale=''
  upstream="$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null || true)"
  if [ -n "$upstream" ]; then
    behind="$(git -C "$dir" rev-list --count "HEAD..$upstream" 2>/dev/null || echo 0)"
    if [ "${behind:-0}" -gt 0 ] 2>/dev/null; then
      tip="$upstream"
      tipname="$(git -C "$dir" rev-parse --short "$upstream" 2>/dev/null)"
      stale="clone is $behind commit(s) behind $upstream; comparing against that ref, not your checkout"
    fi
  fi

  changed="$(git -C "$dir" diff --name-only "$base" "$tip" -- "${WATCH_PATHS[@]}" 2>/dev/null)"
  pkg=''
  pkg_keys_changed "$dir" "$base" "$tip" && pkg='package.json (engines/packageManager/volta/scripts/type)'
  pyp=''
  [ "$(py_pin "$dir" "$base")" != "$(py_pin "$dir" "$tip")" ] && pyp='pyproject.toml (requires-python)'

  if [ -z "$changed" ] && [ -z "$pkg" ] && [ -z "$pyp" ]; then
    [ -n "$stale" ] && notes+=("$stale")
    emit OK "unchanged through $tipname"
    continue
  fi

  [ -n "$stale" ] && notes+=("$stale")
  emit DELTA "$base..$tipname touches:"
  { [ -n "$changed" ] && printf '%s\n' "$changed"; [ -n "$pkg" ] && printf '%s\n' "$pkg"; [ -n "$pyp" ] && printf '%s\n' "$pyp"; } \
    | while IFS= read -r f; do
        [ -z "$f" ] && continue
        if [ "$PORCELAIN" = yes ]; then printf 'PATH\t%s\t%s\n' "$name" "$f"; else printf '%30s%s\n' '' "$f"; fi
      done
  drift=1
done <<<"$rows"

# Porcelain is parsed, so it ends at the last status line — no summary, no
# guidance. Prose on the same stream is what made the hook match its own help
# text and report a criterion as failed on the strength of a sentence.
[ "$PORCELAIN" = yes ] && exit "$drift"

echo
if [ "$drift" = 0 ]; then
  echo "Every tracked repo's setup story is analyzed and unchanged since."
else
  cat <<'NEXT'
Something needs attention.

DELTA / NEVER-ANALYZED / BASELINE-GONE — the setup story has not been read at
this commit. A diff cannot tell an rc-file write from a reworded paragraph, so:
  1. Read the actual diff, not the file list:
       git -C ~/Developer/<repo> diff <baseline>..<tip> -- setup local .githooks .envrc .nvmrc README.md
  2. Judge it: does it write to an rc file, install or relocate a runtime
     manager, change a version pin, add or change a git hook (or its shebang),
     or change what a local-dev session expects on PATH?
  3. If it does NOT: record the new commit in the tracked repos table in
     .claude/skills/comply365/SKILL.md with a one-line verdict saying why it was
     irrelevant. Keep it generic — dotfiles is a public repo (AC-4).
  4. If it DOES: wire it (prefer widening one of the three generic mechanisms),
     add criteria to software/comply365/SPEC.md, and only then record the commit.

HOOKS-INACTIVE — nothing to read; the repo is simply not set up here. Run its
own setup.sh, or at minimum set what that script sets:
       git -C ~/Developer/<repo> config core.hooksPath .githooks

NO-CLONE is neither a pass nor a failure and never blocks: nothing can be read.
NEXT
fi
exit "$drift"
