#!/usr/bin/env bash
# Fast-forward the GitLab repos directly under a root (default: ~/Developer) that are behind
# origin and hold no ongoing work, then print the report the sync-gitlab-repos skill shows.
#
# Usage: sync.sh [--apply] [root]
#   without --apply  fetch, classify and report what an apply run would do; no branch moves
#   --apply          also fast-forward, then check stash counts and dirty state
# Exit: 0 done; 2 a fetch failed, so nothing was updated; 3 a stash pop conflicted or a
# check after an update failed.
#
# A branch moves only by `merge --ff-only`. Nothing is pushed, committed or reset. The one
# stash it makes holds only a `.gitignore` whose sole change disables the `.claude` ignore
# rule, and it is popped right after the fast-forward.
set -u

apply=0
if [ "${1:-}" = "--apply" ]; then apply=1; shift; fi
root="${1:-$HOME/Developer}"
root="${root%/}"
[ -d "$root" ] || { echo "No such directory: $root" >&2; exit 1; }

git() { command git "$@"; }

rows=()          # "rank<TAB>sort key<TAB>emoji<TAB>status<TAB>repo<TAB>result<TAB>note"
details=()       # bullet lines after the table
fetch_errors=()
offer=()         # repos on hold for ongoing work: stash-and-fast-forward candidates
plan_dir=(); plan_kind=(); plan_behind=(); plan_note=(); plan_stash=(); plan_dirty=(); plan_untracked=()
total=0; updated=0; current=0; skipped=0; foreign=0; fetch_failed=0; stashed_any=0; status=0
display_root="$root"
case "$root" in "$HOME"/*) display_root="~${root#"$HOME"}" ;; esac

row() { local IFS=$'\t'; rows+=("$*"); }  # rank sort-key emoji status repo result note

# Plain text, not a Markdown table: a forked skill's output reaches the terminal unrendered.
# Only the first column holds an emoji, so padding the ASCII columns keeps them aligned.
print_table() {  # rows on stdin, sorted
  local rank key emoji status repo result note i emojis=() statuses=() repos=() results=() notes=()
  local w_status=6 w_repo=4 w_result=6
  while IFS=$'\t' read -r rank key emoji status repo result note; do
    emojis+=("$emoji"); statuses+=("$status"); repos+=("$repo"); results+=("$result"); notes+=("$note")
    [ "${#status}" -gt "$w_status" ] && w_status=${#status}
    [ "${#repo}" -gt "$w_repo" ] && w_repo=${#repo}
    [ "${#result}" -gt "$w_result" ] && w_result=${#result}
  done
  {
    printf '   %-*s  %-*s  %-*s  %s\n' "$w_status" Status "$w_repo" Repo "$w_result" Result Note
    for ((i = 0; i < ${#emojis[@]}; i++)); do
      printf '%s %-*s  %-*s  %-*s  %s\n' "${emojis[$i]}" "$w_status" "${statuses[$i]}" \
        "$w_repo" "${repos[$i]}" "$w_result" "${results[$i]}" "${notes[$i]}"
    done
  } | /usr/bin/sed 's/ *$//'
}
backticked() { /usr/bin/sed 's/^/`/; s/$/`/' | /usr/bin/paste -sd, - | /usr/bin/sed 's/,/, /g'; }
remote_label() {
  [ -n "$1" ] || { echo "no origin"; return; }
  printf '%s\n' "$1" | /usr/bin/sed -E 's#^[a-z+]+://##; s#^[^@/]+@##; s#:([^0-9])#/\1#; s#\.git$##'
}
stash_count() { git -C "$1" stash list | /usr/bin/wc -l | /usr/bin/tr -d ' '; }
tracked_changes() { git -C "$1" status --porcelain=v1 | command grep -v '^??'; }
untracked_count() { git -C "$1" status --porcelain=v1 | command grep -c '^??'; }

operation_in_progress() {
  local git_dir
  git_dir="$(git -C "$1" rev-parse --absolute-git-dir 2>/dev/null)" || return
  if [ -e "$git_dir/rebase-merge" ] || [ -e "$git_dir/rebase-apply" ]; then echo rebase
  elif [ -e "$git_dir/MERGE_HEAD" ]; then echo merge
  elif [ -e "$git_dir/CHERRY_PICK_HEAD" ]; then echo cherry-pick
  elif [ -e "$git_dir/REVERT_HEAD" ]; then echo revert
  elif [ -e "$git_dir/BISECT_LOG" ]; then echo bisect
  fi
}

# True when the only change to .gitignore disables the `.claude` ignore rule: lines
# `/.claude/` or `.claude` removed, or replaced by their commented-out form.
gitignore_only_unignores_claude() {
  local line removed=0
  while IFS= read -r line; do
    case "$line" in
      -*) printf '%s\n' "${line#-}" | command grep -qE '^[[:space:]]*/?\.claude/?[[:space:]]*$' || return 1
          removed=1 ;;
      +*) printf '%s\n' "${line#+}" | command grep -qE '^[[:space:]]*#[[:space:]]*/?\.claude/?[[:space:]]*$' || return 1 ;;
    esac
  done < <(git -C "$1" diff -U0 HEAD -- .gitignore | /usr/bin/sed -n '/^@@/,$p' | command grep -v '^@@')
  [ "$removed" -eq 1 ]
}

plan() {  # dir kind behind note
  plan_dir+=("$1"); plan_kind+=("$2"); plan_behind+=("$3"); plan_note+=("$4")
  plan_stash+=("$(stash_count "$1")"); plan_dirty+=("$(tracked_changes "$1")"); plan_untracked+=("$(untracked_count "$1")")
}

hold() {  # name result note detail
  row 3 0 ⏸️ "on hold" "$1" "$2" "$3"
  details+=("- \`$1\`: $4"); skipped=$((skipped + 1))
}

block() {  # name result note detail
  row 4 0 ⛔ blocked "$1" "$2" "$3"
  details+=("- \`$1\`: $4"); skipped=$((skipped + 1))
}

for path in "$root"/*/; do
  dir="${path%/}"; name="${dir##*/}"
  [ -e "$dir/.git" ] || continue
  total=$((total + 1))

  url="$(git -C "$dir" remote get-url origin 2>/dev/null)" || url=""
  case "$url" in
    *gitlab.com*) ;;
    *) row 5 0 🚫 "not GitLab" "$name" untouched "$(remote_label "$url")"; foreign=$((foreign + 1)); continue ;;
  esac

  if ! fetch_out="$(git -C "$dir" fetch --all --prune -q 2>&1)"; then
    row 0 0 ❌ "fetch failed" "$name" "not fetched" "see below"; fetch_failed=$((fetch_failed + 1))
    while IFS= read -r line; do fetch_errors+=("- $line"); done \
      < <(printf '%s\n' "$fetch_out" | command grep -E 'ERROR|fatal|SSO|https?://' | /usr/bin/sort -u)
    continue
  fi

  if ! upstream="$(git -C "$dir" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null)"; then
    branch="$(git -C "$dir" rev-parse --abbrev-ref HEAD 2>/dev/null)"
    block "$name" "no upstream" "branch \`$branch\`" "branch \`$branch\` has no upstream, so there is nothing to compare with"
    continue
  fi
  read -r behind ahead < <(git -C "$dir" rev-list --left-right --count '@{u}...HEAD')
  if [ "$behind" -eq 0 ]; then
    row 2 0 ✅ "was up-to-date" "$name" "nothing to pull" ""; current=$((current + 1))
    continue
  fi

  op="$(operation_in_progress "$dir")"
  if [ -n "$op" ]; then
    block "$name" "behind $behind" "$op in progress" "a $op is in progress; finish or abort it first"
    continue
  fi
  if [ "$ahead" -gt 0 ]; then
    block "$name" "ahead $ahead" "local commits not on origin" "$ahead local commit(s) not on \`$upstream\`, and $behind incoming; a fast-forward is impossible"
    continue
  fi

  changes="$(tracked_changes "$dir")"
  untracked_note=""
  [ "$(untracked_count "$dir")" -gt 0 ] && untracked_note="untracked files left alone"
  if [ -z "$changes" ]; then
    plan "$dir" ff "$behind" "$untracked_note"
  elif [ "$(printf '%s\n' "$changes" | /usr/bin/cut -c4-)" = ".gitignore" ] && gitignore_only_unignores_claude "$dir"; then
    incoming="$(git -C "$dir" log --format= --name-only 'HEAD..@{u}' -- .gitignore .claude | command grep -v '^$' | /usr/bin/sort -u)"
    if [ -n "$incoming" ]; then
      hold "$name" "behind $behind" "incoming changes touch \`.gitignore\` or \`.claude/\`" \
        "only \`.gitignore\` is modified (it un-ignores \`.claude\`), but incoming commits change $(printf '%s\n' "$incoming" | backticked)"
    else
      plan "$dir" stash "$behind" "\`.gitignore\` stashed → ff → popped"
    fi
  else
    files="$(printf '%s\n' "$changes" | /usr/bin/cut -c4- | backticked)"
    hold "$name" "behind $behind" "modified tracked files" "modified tracked files: $files"
    offer+=("\`$name\`")
  fi
done

if [ "$fetch_failed" -gt 0 ]; then
  printf '❌ GitLab repo sync · %s · nothing was updated\n\n' "$display_root"
  printf '%s\n' ${rows[@]+"${rows[@]}"} | command grep '^0'$'\t' | /usr/bin/sort -t$'\t' -k5,5 | print_table
  printf '\nA fetch failed, so the behind and ahead counts are stale and no repo was touched.\n'
  printf 'The usual cause is an expired GitLab SAML SSO session: open the `…/-/saml/sso?token=…` URL below in the browser, sign in, and run the sync again.\n'
  [ "${#fetch_errors[@]}" -eq 0 ] || { printf '\n'; printf '%s\n' "${fetch_errors[@]}" | /usr/bin/sort -u; }
  exit 2
fi

stopped=""
for ((i = 0; i < ${#plan_dir[@]}; i++)); do
  dir="${plan_dir[$i]}"; name="${dir##*/}"; behind="${plan_behind[$i]}"; note="${plan_note[$i]}"
  if [ "$apply" -eq 0 ]; then
    row 1 "-$behind" ⬇️ "would update" "$name" "$behind commits" "$note"; updated=$((updated + 1))
    continue
  fi
  if [ -n "$stopped" ]; then
    hold "$name" "behind $behind" "not run" "not run: the sync stopped at \`$stopped\`"
    continue
  fi

  if [ "${plan_kind[$i]}" = stash ]; then
    git -C "$dir" stash push -q -m "sync-gitlab-repos: temp stash .gitignore" -- .gitignore || {
      hold "$name" "behind $behind" "stash failed" "could not stash \`.gitignore\`; nothing changed"; continue; }
    stashed_any=1
  fi
  merge_out="$(git -C "$dir" merge --ff-only -q '@{u}' 2>&1)"; merge_rc=$?
  if [ "${plan_kind[$i]}" = stash ] && ! git -C "$dir" stash pop -q >/dev/null 2>&1; then
    hold "$name" "behind $behind" "stash pop conflicted" \
      "\`git stash pop\` conflicted after the fast-forward; the stash is kept, nothing was resolved. Stopped here."
    stopped="$name"; status=3
    continue
  fi
  if [ "$merge_rc" -ne 0 ]; then
    hold "$name" "behind $behind" "merge refused" "\`merge --ff-only\` refused: $(printf '%s\n' "$merge_out" | /usr/bin/head -1)"
    continue
  fi

  problems=()
  [ "$(stash_count "$dir")" = "${plan_stash[$i]}" ] || problems+=("stash count changed from ${plan_stash[$i]}")
  [ "$(tracked_changes "$dir")" = "${plan_dirty[$i]}" ] || problems+=("tracked changes differ from before")
  [ "$(untracked_count "$dir")" = "${plan_untracked[$i]}" ] || problems+=("untracked file count changed")
  if [ "${#problems[@]}" -gt 0 ]; then
    note="⚠️ ${problems[*]}"; status=3
    details+=("- \`$name\`: updated, but after the update: ${problems[*]}")
  fi
  row 1 "-$behind" ⬇️ updated "$name" "$behind commits" "$note"; updated=$((updated + 1))
done

stash_total=0
for path in "$root"/*/; do
  dir="${path%/}"
  case "$(git -C "$dir" remote get-url origin 2>/dev/null)" in
    *gitlab.com*) stash_total=$((stash_total + $(stash_count "$dir"))) ;;
  esac
done

if [ "$apply" -eq 1 ]; then
  printf '🔄 GitLab repo sync · %s · %s repos\n\n' "$display_root" "$total"
else
  printf '🔍 GitLab repo check, nothing changed · %s · %s repos\n\n' "$display_root" "$total"
fi
printf '%s\n' ${rows[@]+"${rows[@]}"} | /usr/bin/sort -t$'\t' -k1,1n -k2,2n -k5,5 | print_table
printf '\n📊 %s %s · %s up to date · %s skipped · %s non-GitLab\n' \
  "$updated" "$([ "$apply" -eq 1 ] && echo updated || echo 'would update')" "$current" "$skipped" "$foreign"
if [ "$stashed_any" -eq 1 ]; then
  printf '🧹 %s stash entries everywhere · pre-existing dirty state restored\n' "$stash_total"
else
  printf '🧹 %s stash entries everywhere\n' "$stash_total"
fi
if [ "${#details[@]}" -gt 0 ]; then
  printf '\n'; printf '%s\n' "${details[@]}"
fi
if [ "${#offer[@]}" -gt 0 ]; then
  printf '\nFor %s: want me to stash the ongoing work, fast-forward, and pop the stash back? I will not do it without your go-ahead.\n' \
    "$(printf '%s\n' "${offer[@]}" | /usr/bin/paste -sd, - | /usr/bin/sed 's/,/, /g')"
fi
exit "$status"
