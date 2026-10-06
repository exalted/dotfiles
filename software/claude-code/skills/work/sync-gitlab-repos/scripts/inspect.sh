#!/usr/bin/env bash
# Prints one status block per GitLab repo directly under the given directory (default: ~/Developer).
# Read-only apart from `git fetch --all --prune`. Decides nothing; the skill decides from this output.
set -u
root="${1:-$HOME/Developer}"
cd "$root" || exit 1
fetch_failed=0

for d in */; do
  d="${d%/}"
  [ -d "$d/.git" ] || continue
  url="$(command git -C "$d" remote get-url origin 2>/dev/null || echo NO-ORIGIN)"
  case "$url" in
    *gitlab.com*) ;;
    *) printf '### %s\nSKIP: origin is not gitlab.com (%s)\n\n' "$d" "$url"; continue ;;
  esac

  fetch_out="$(command git -C "$d" fetch --all --prune -q 2>&1)"; fetch_rc=$?
  if [ "$fetch_rc" -ne 0 ]; then
    printf '### %s\nFETCH FAILED (exit %s): behind/ahead numbers below are STALE, do not act on them.\n' "$d" "$fetch_rc"
    printf '%s\n' "$fetch_out" | command grep -E 'ERROR|fatal|SSO|https?://' | /usr/bin/sed 's/^/fetch: /'
    fetch_failed=1
  else
    printf '### %s\n' "$d"
  fi

  branch="$(command git -C "$d" rev-parse --abbrev-ref HEAD 2>&1)"
  upstream="$(command git -C "$d" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>&1)"
  counts="$(command git -C "$d" rev-list --left-right --count '@{u}...HEAD' 2>/dev/null || echo 'n/a n/a')"
  behind="${counts%%[[:space:]]*}"; ahead="${counts##*[[:space:]]}"
  stash="$(command git -C "$d" stash list 2>/dev/null | /usr/bin/wc -l | /usr/bin/tr -d ' ')"
  op="$(/bin/ls "$d/.git" 2>/dev/null | command grep -E 'MERGE_HEAD|REBASE|CHERRY_PICK|BISECT|rebase-' | /usr/bin/tr '\n' ' ')"
  modified="$(command git -C "$d" status --porcelain=v1 2>/dev/null | command grep -v '^??' || true)"
  untracked="$(command git -C "$d" status --porcelain=v1 2>/dev/null | command grep '^??' || true)"

  printf 'branch: %s -> %s\nbehind: %s  ahead: %s  stash: %s  op-in-progress: %s\n' "$branch" "$upstream" "$behind" "$ahead" "$stash" "${op:-none}"
  if [ -n "$modified" ]; then printf 'modified/staged:\n%s\n' "$modified"; else printf 'modified/staged: none\n'; fi
  if [ -n "$untracked" ]; then printf 'untracked:\n%s\n' "$untracked"; else printf 'untracked: none\n'; fi
  if printf '%s' "$modified" | command grep -qE '^.M .gitignore$|^ M .gitignore$|^M  .gitignore$'; then
    printf -- '--- .gitignore diff ---\n'; command git -C "$d" diff -- .gitignore
    printf -- '--- incoming commits touching .gitignore or .claude/ ---\n'
    command git -C "$d" diff --name-only HEAD '@{u}' -- .gitignore .claude 2>/dev/null || true
  fi
  printf '\n'
done

if [ "$fetch_failed" -ne 0 ]; then
  printf '!!! At least one fetch failed. Fix access (usually: open the GitLab SSO URL above, sign in, re-run) before updating anything.\n'
  exit 2
fi
