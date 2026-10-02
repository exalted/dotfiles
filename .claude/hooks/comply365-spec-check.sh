#!/usr/bin/env bash
# Stop-hook verifier for software/comply365/SPEC.md.
#
# Runs only when this session actually touched the comply365 batch (see the gate
# below), so it stays silent in every other session in this repo.
#
# Two kinds of criterion:
#   [auto]  verified here, by behavior where possible rather than by grep
#   [eyes]  needs a human in a real terminal or GUI app — the hook prints the
#           steps and treats the criterion as failing until it is signed off
#           with comply365-signoff.sh. A sign-off expires when the files it
#           depends on change again.
#
# Blocks only when the set of problems has changed since the last block this
# session, so it can report something new but can never trap the session in a
# loop over a criterion that cannot be met.
#
# `$BASH` and `/usr/bin/env`, never bare `bash`/`env`: this repo's interactive
# shells alias some of those (`env` is `env | sort`), and a hook inherits them
# when the shell is initialized from the user's profile.
set -uo pipefail

input="$(cat)"
session_id="$(printf '%s' "$input" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("session_id","nosession"))' 2>/dev/null || echo nosession)"
latch="${TMPDIR:-/tmp}/claude-comply365-spec.${session_id}"

repo="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$repo" || exit 0

DIR=software/comply365
SPEC="$DIR/SPEC.md"
LEDGER=.claude/comply365-manual-signoff.json
WATCHED=("$DIR" software/bash/prompt-command.bashrc software/bash/prompt.bashrc software/node/nvm-loader.sh software/homebrew/shellenv.sh software/watch/bashrc software/git/bin/git-hist software/bash/pager.bashrc software/iterm2/bashrc profiles.rb .claude/tools/setup-review.sh .claude/skills/comply365/SKILL.md .claude/hooks/comply365-spec-check.sh .claude/hooks/comply365-signoff.sh .claude/hooks/lib .claude/tools/zsh-drift.sh)
# The verifier and the sign-off recorder are in WATCHED for the same reason the
# fragments are: a session that changes how the batch is checked has changed the
# batch's guarantees, and used to end without the checks running at all. They are
# deliberately NOT in batch_digest — they are tooling, not shell behavior, so
# editing them must not expire a human's terminal observations.

# ---- gate: did this batch move at all? -------------------------------------
base=origin/main
git rev-parse --verify --quiet "$base" >/dev/null || base=main
touched="$(git status --porcelain -- "${WATCHED[@]}"; git diff --name-only "$base"...HEAD -- "${WATCHED[@]}" 2>/dev/null)"
[ -n "$touched" ] || exit 0

# Digest of the ENTIRE batch, not just the files a criterion names. A sign-off is
# a statement about one state of the tree: we learned the hard way that a change
# in one file (the brew shellenv guard) breaks criteria that look unrelated at a
# glance (which bash wins, hence prompt rendering and `git hist`). So any change
# to any watched file re-opens every manual criterion.
batch_digest() {
  git -C "$repo" ls-files --cached --others --exclude-standard -- 'software/comply365/*.bashrc' 'software/comply365/*.rb' software/comply365/zshenv software/bash/prompt-command.bashrc software/bash/prompt.bashrc software/node/nvm-loader.sh software/node/bashrc software/homebrew/shellenv.sh software/homebrew/bashrc software/watch/bashrc software/git/bin/git-hist software/bash/pager.bashrc software/iterm2/bashrc profiles.rb 2>/dev/null \
    | command sort \
    | while read -r f; do command shasum -a 256 "$repo/$f"; done \
    | command shasum -a 256 | cut -c1-16
}

# Three buckets, not two. A manual criterion revoked by hand (the documented way
# to re-open one whose wording you have tightened) is neither an automated
# failure nor an untouched criterion: it needs a human to re-run it, exactly like
# `pending`, so it must carry its STEPS. Filing it under "automated criteria
# FAILED" and dropping the steps is the least useful thing this hook can do at
# precisely the moment they are needed.
fails=() ; pending=() ; revoked=()
# Consumes $? from the preceding command. Never put a `$(...)` in its arguments:
# it runs first and overwrites $? with its own (almost always zero) status, so
# the check can no longer fail. Read the value into a variable before the test.
check() {
  local rc=$? id="$1" desc="$2"
  [ "$rc" -eq 0 ] || fails+=("$id — $desc")
  return 0
}
BASH_BIN="${BASH:-/bin/bash}"
ENV_BIN=/usr/bin/env

# ---- AC-1  structure & registration ----------------------------------------
for f in cortex.rb web-safety.rb zsh.rb jira.rb; do
  [ -x "$DIR/$f" ]; check AC-1 "$DIR/$f is not executable (bin/dotfiles won't run it)"
  command grep -q "comply365/${f%.rb}" profiles.rb; check AC-1 "comply365/${f%.rb} is not registered in profiles.rb"
done
for f in cortex.bashrc web-safety.bashrc jira.bashrc zshenv SPEC.md; do
  [ ! -x "$DIR/$f" ]; check AC-1 "$DIR/$f is executable — _defined_software_names would treat it as a software entry"
done

# ---- AC-2  syntax, incl. stock ruby 2.6 for bootstrap ----------------------
"$BASH_BIN" -n "$DIR/cortex.bashrc" 2>/dev/null; check AC-2 "cortex.bashrc fails bash -n"
"$BASH_BIN" -n "$DIR/web-safety.bashrc" 2>/dev/null; check AC-2 "web-safety.bashrc fails bash -n"
"$BASH_BIN" -n "$DIR/jira.bashrc" 2>/dev/null; check AC-2 "jira.bashrc fails bash -n"
if command -v zsh >/dev/null; then
  zsh -n "$DIR/zshenv" 2>/dev/null; check AC-2 "zshenv fails zsh -n"
fi
for f in "$DIR"/*.rb; do
  /usr/bin/ruby -c "$f" >/dev/null 2>&1; check AC-2 "$f fails ruby -c under stock /usr/bin/ruby (bootstrap runs before rbenv)"
done

# ---- AC-3/4  wires config only; public-repo hygiene ------------------------
# `^[^#]*` on every content grep: these files explain their own reasoning at
# length, and a comment naming what they deliberately avoid is not a violation.
! command grep -qE '^[^#]*\bbrew\b' "$DIR"/*.rb; check AC-3 "a .rb installs via brew — the work repos' own setups own installing tools"
# Matches a repo path or a Jira site without naming the org, which would
# reintroduce the leak. A `<site>` placeholder does not match.
! command grep -rqE 'gitlab\.com[:/][A-Za-z0-9]|git@[a-z]|[A-Za-z0-9-]\.atlassian\.net' "$DIR"; check AC-4 "a GitLab repo path or Atlassian site leaked into $DIR — dotfiles is public"

# ---- AC-5/6/7  registration under the real load order ----------------------
# env -i means nvm does NOT exist while web-safety.bashrc is sourced — exactly
# the real order (comply365 sorts before node). Sourced twice for idempotency.
pc="$("$ENV_BIN" -i HOME="$HOME" PATH=/usr/bin:/bin "$BASH_BIN" --norc -c '
  cd "$1" || exit 1
  . software/bash/prompt-command.bashrc
  __prompt_command_prepend _direnv_hook
  . software/comply365/web-safety.bashrc
  . software/comply365/web-safety.bashrc
  printf "%s\n" "$PROMPT_COMMAND"
  declare -p PROMPT_COMMAND
' _ "$repo" 2>/dev/null)"
registered="$(printf '%s' "$pc" | head -1)"
n_reg="$(printf '%s' "$registered" | command grep -o '__comply365_auto_nvm_use' | command wc -l | tr -d ' ')"

[ -n "$registered" ]; check AC-5 "the nvm hook did not register when nvm was absent at load time (source-time guard regression)"
[ "$n_reg" = 1 ]; check AC-7 "the nvm hook is registered $n_reg times after two sources — not idempotent"
[[ "$registered" == *__comply365_auto_nvm_use ]]; check AC-6 "the nvm hook is not last in PROMPT_COMMAND — direnv's PATH restore will undo its nvm use"
"$BASH_BIN" -n <<<"$registered" 2>/dev/null; check AC-7 "the composed PROMPT_COMMAND does not parse: $registered"
! printf '%s' "$pc" | command grep -q 'declare -x PROMPT_COMMAND'; check AC-7 "PROMPT_COMMAND is exported — a --norc child inherits names without definitions"

# ---- AC-8/9/12  no $PWD gate, full cache key, own .nvmrc walk -------------
! command grep -qE '^[^#]*__comply365_nvm_on_chdir' "$DIR/web-safety.bashrc"; check AC-8 "the \$PWD-gated wrapper is back — an in-place .nvmrc rewrite goes unnoticed"
[ "$(command grep -cF '$__comply365_nvmrc|$__comply365_nvmrc_version|$PATH' "$DIR/web-safety.bashrc")" -ge 2 ]; check AC-9 "the cache key is no longer nvmrc|version|PATH in both the compare and the assignment"
! command grep -qE '^[^#]*nvm_find_nvmrc' "$DIR/web-safety.bashrc"; check AC-12 "nvm's private nvm_find_nvmrc is being called again"
command grep -qF '[ -n "$dir" ] || break' "$DIR/web-safety.bashrc"; check AC-12 "the walk no longer reaches /.nvmrc, so it disagrees with nvm about the same directory"

# ---- AC-10/11/13  hook behavior against a stub nvm ------------------------
# Warnings go to files, never through $(...): a command substitution forks, and
# the warn-once flag set in that subshell would be lost — making correct code
# look broken. In PROMPT_COMMAND the hook runs in the shell itself.
behavior="$("$ENV_BIN" -i HOME="$HOME" PATH=/usr/bin:/bin "$BASH_BIN" --norc -c '
  cd "$1" || exit 1
  tmp="$(mktemp -d)"; trap "rm -rf $tmp" EXIT
  mkdir -p "$tmp/pinned" "$tmp/plain" "$tmp/crlf" "$tmp/missing"
  printf "1.2.3\n"    > "$tmp/pinned/.nvmrc"
  printf "1.2.3\r\n"  > "$tmp/crlf/.nvmrc"
  printf "99.99.99\n" > "$tmp/missing/.nvmrc"

  nvm_use_fail=0
  nvm() {
    case "$1 ${2:-}" in
      "version default")            echo system ;;
      "version 1.2.3"|"version 4.5.6") echo "v$2" ;;
      "version "*)                  echo "N/A" ;;
      "current")                    echo "${STUB_CURRENT:-system}" ;;
      "use default")                [ "$nvm_use_fail" = 1 ] && return 1; STUB_CURRENT=system ;;
      "use "*)                      [ "$nvm_use_fail" = 1 ] && return 1; STUB_CURRENT="v$2" ;;
    esac
  }
  . software/bash/prompt-command.bashrc
  . software/comply365/web-safety.bashrc

  cd "$tmp/missing"
  __comply365_auto_nvm_use 2>"$tmp/w1" >/dev/null
  __comply365_auto_nvm_use 2>"$tmp/w2" >/dev/null
  echo "warn1=$([ -s "$tmp/w1" ] && echo yes || echo no) warn2=$([ -s "$tmp/w2" ] && echo yes || echo no) state_after_missing=${__comply365_nvm_state:-unset}"

  cd "$tmp/pinned"; __comply365_auto_nvm_use >/dev/null 2>&1
  echo "pinned=$STUB_CURRENT"
  printf "4.5.6\n" > .nvmrc; __comply365_auto_nvm_use >/dev/null 2>&1
  echo "rewritten=$STUB_CURRENT"
  cd "$tmp/plain"; __comply365_auto_nvm_use >/dev/null 2>&1
  echo "plain=$STUB_CURRENT"
  cd "$tmp/crlf"; __comply365_auto_nvm_use >/dev/null 2>&1
  echo "crlf=$STUB_CURRENT"

  cd "$tmp/pinned"; unset __comply365_nvm_state; STUB_CURRENT=system; nvm_use_fail=1
  __comply365_auto_nvm_use >/dev/null 2>&1
  echo "state_after_failed_use=${__comply365_nvm_state:-unset}"
' _ "$repo" 2>/dev/null)"

[[ "$behavior" == *"warn1=yes warn2=no"* ]]; check AC-10 "an uninstalled .nvmrc version does not warn exactly once per version"
[[ "$behavior" == *"state_after_missing=unset"* ]]; check AC-10 "state is cached for an uninstalled version — installing it elsewhere would never be picked up"
[[ "$behavior" == *"pinned=v1.2.3"* ]]; check AC-9 "entering a pinned project did not switch Node"
[[ "$behavior" == *"rewritten=v4.5.6"* ]]; check AC-8 "an in-place .nvmrc rewrite without a cd did not switch Node"
[[ "$behavior" == *"plain=system"* ]]; check AC-11 "leaving all projects did not revert to nvm's default"
[[ "$behavior" == *"crlf=v1.2.3"* ]]; check AC-12 "a CRLF .nvmrc did not resolve (trailing whitespace not stripped)"
[[ "$behavior" == *"state_after_failed_use=unset"* ]]; check AC-13 "a failed nvm use was cached as success, so it never retries"

# ---- AC-15/16  direnv wiring ----------------------------------------------
command grep -qF 'direnv hook bash' "$DIR/cortex.bashrc"; check AC-15 "cortex.bashrc no longer re-adds the direnv hook that bin/dotfiles wipes"
command grep -qF 'command -v direnv' "$DIR/cortex.bashrc"; check AC-15 "cortex.bashrc no longer guards on direnv being installed"
command grep -qE '^[^#]*\bwarn\b' "$DIR/cortex.rb"; check AC-16 "cortex.rb no longer warns when direnv is missing — the failure would be silent"

# ---- AC-19/20/21  zsh reachability ---------------------------------------
command grep -qF "link_to_home_relative 'zshenv', '.zshenv', backup: true" "$DIR/zsh.rb"; check AC-19 "zsh.rb no longer links ~/.zshenv with backup: true"
! command grep -qE '^[^#]*(\.zshrc|\.zprofile)' "$DIR"/*.rb; check AC-19 "a .rb touches ~/.zshrc or ~/.zprofile — those belong to the work repos' own setups"
command grep -qF '${${(%):-%x}:A:h}' "$DIR/zshenv"; check AC-20 "zshenv no longer resolves its own path through the symlink"
command grep -qF 'homebrew/shellenv.sh' "$DIR/zshenv"; check AC-20 "zshenv no longer sources the shared homebrew/shellenv.sh"
command grep -qF 'node/nvm-loader.sh' "$DIR/zshenv"; check AC-20 "zshenv no longer uses the shared nvm loader (second nvm copy risk)"
command grep -qF 'unfunction nvm' "$DIR/zshenv"; check AC-21 "the lazy nvm stub is gone — every zsh pays ~200ms again"

# ---- AC-22  a bare, GUI-like zsh finds the tools -------------------------
if command -v zsh >/dev/null; then
  missing="$("$ENV_BIN" -i HOME="$HOME" PATH=/usr/bin:/bin:/usr/sbin:/sbin zsh -f -c '
    . "$1"/software/comply365/zshenv
    for t in brew node pnpm nvm direnv; do command -v $t >/dev/null || print -n "$t "; done
  ' _ "$repo" 2>/dev/null)"
  [ -z "$missing" ]; check AC-22 "a GUI-like bare zsh cannot find: ${missing:-?} — web-safety's zsh git hooks will fail from Sourcetree"
fi

# ---- AC-24  Homebrew's bash must win, in both launch contexts ------------
# The stale-prefix case is the exact regression that made `git hist` fall back to
# bash 3.2: HOMEBREW_PREFIX inherited from a GUI app's cached environment while
# PATH does not actually contain its bin dir. A guard keyed on either proxy
# alone skips brew shellenv there and loses every Homebrew tool, `brew` included.
hb_prefix="$(command -v brew >/dev/null && brew --prefix 2>/dev/null || true)"
probe="$repo/.claude/hooks/lib/bash-major.sh"
gui_path=/usr/bin:/bin:/usr/sbin:/sbin

major_bare="$("$ENV_BIN" -i HOME="$HOME" PATH="$gui_path" "$BASH_BIN" "$probe" "$repo" 2>/dev/null)"
[ "${major_bare:-0}" -ge 4 ] 2>/dev/null
check AC-24 "in a bare GUI-like environment the first bash on PATH is major version ${major_bare:-none}, expected >= 4 — every #!/usr/bin/env bash shebang silently gets macOS bash 3.2"

if [ -n "$hb_prefix" ]; then
  major_stale="$("$ENV_BIN" -i HOME="$HOME" PATH="$gui_path" HOMEBREW_PREFIX="$hb_prefix" "$BASH_BIN" "$probe" "$repo" 2>/dev/null)"
  [ "${major_stale:-0}" -ge 4 ] 2>/dev/null
  check AC-24 "with HOMEBREW_PREFIX exported but its bin dir absent from PATH, bash resolves to major version ${major_stale:-none} — this is the emojify/git-hist regression"
fi

  major_late="$("$ENV_BIN" -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin:$hb_prefix/bin" HOMEBREW_PREFIX="$hb_prefix" "$BASH_BIN" "$probe" "$repo" 2>/dev/null)"
  [ "${major_late:-0}" -ge 4 ] 2>/dev/null
  check AC-24 "with HOMEBREW_PREFIX exported and its bin dir on PATH but BEHIND /usr/bin, bash resolves to major version ${major_late:-none} — this is what macOS's path_helper produces for every login shell, so terminals hit it"

# ---- AC-29/30/31/32  a `bin/dotfiles` run must be safe to repeat ---------
# The real run needs sudo and Homebrew, so it is AC-33 [eyes]. Everything that
# does not need them is checked here.
ruby -e '
require_relative "src/common"
Dir.glob("src/steps/*.rb").each { |f| require_relative f.sub(/\.rb\z/, "") }
_resolve_profile
_guard_profiles
' >/dev/null 2>&1; check AC-29 "_guard_profiles fails — a bin/dotfiles run would abort before configuring anything"

# The orphan half only warns, so it cannot fail the command above. Assert on its
# output instead, or a software/ entry configured in no profile goes unnoticed.
#
# Captures stdout as well as stderr on purpose: src/common.rb overrides `warn`
# to `puts`, so the warning lands on stdout. A stderr-only capture reads empty
# and the assertion silently becomes vacuous — which is exactly what it did.
guard_warnings="$(ruby -e '
require_relative "src/common"
Dir.glob("src/steps/*.rb").each { |f| require_relative f.sub(/\.rb\z/, "") }
_resolve_profile
_guard_profiles
' 2>&1)"
[ -z "$guard_warnings" ]
check AC-29 "_guard_profiles warns: $guard_warnings" 

idem="$("$BASH_BIN" "$repo/.claude/hooks/lib/dotfiles-idempotency.sh" "$repo" 2>/dev/null)"
fact() { printf '%s' "$idem" | command sed -n "s/^$1=//p"; }

f="$(fact script_failures)"
[ "$f" = 0 ]; check AC-30 "$f entry-script invocation(s) failed across two runs against a throwaway HOME"
f="$(fact duplicate_source_lines)"
[ "$f" = 0 ]; check AC-30 "a second run duplicated $f source line(s) in ~/.bashrc.dotfiles"
f="$(fact ssh_include_lines)"
[ "$f" = 1 ]; check AC-30 "~/.ssh/config ended up with $f Include lines after two runs, expected 1"
f="$(fact ssh_backups)"
[ "$f" = 1 ]; check AC-30 "two runs left $f ssh backup file(s), expected 1 — a second backup overwrites the first, losing the original"
[ "$(fact ssh_preexisting_host)" = 1 ]; check AC-31 "a Host entry kept outside this repo was lost from ~/.ssh/config"
[ "$(fact ssh_fragment_linked)" = yes ]; check AC-31 "the managed fragment is not linked at ~/.ssh/config.d/dotfiles"
[ "$(fact ssh_group_or_world_writable)" = no ]; check AC-31 "~/.ssh/config was left group- or world-writable — ssh refuses to use it"
f="$(fact ssh_fresh_mode)"
[ "$f" = 600 ]; check AC-31 "a freshly created ~/.ssh/config got mode $f under a permissive umask, expected 600"
[ "$(fact zshenv_is_symlink)" = yes ]; check AC-31 "~/.zshenv is not a symlink to the managed file"
[ "$(fact zshenv_backup_preserved)" = yes ]; check AC-31 "a pre-existing ~/.zshenv was clobbered instead of backed up"

# AC-32: the live generated file, in the order the fragments require.
rc="$HOME/.bashrc"
for frag in bash/prompt-command.bashrc bash/prompt.bashrc bash/history.bashrc bash/pager.bashrc node/bashrc homebrew/bashrc watch/bashrc comply365/cortex.bashrc comply365/web-safety.bashrc comply365/jira.bashrc; do
  count="$(command grep -c "software/$frag\$" "$rc" 2>/dev/null)"
  [ "$count" = 1 ]
  check AC-32 "~/.bashrc sources software/$frag ${count:-0} times, expected exactly 1 (re-run bin/dotfiles if a fragment is new)"
done
pcl="$(command grep -n 'bash/prompt-command.bashrc' "$rc" | cut -d: -f1 | head -1)"
for after in bash/history.bashrc bash/prompt.bashrc; do
  n="$(command grep -n "$after" "$rc" | cut -d: -f1 | head -1)"
  [ -n "$pcl" ] && [ -n "$n" ] && [ "$pcl" -lt "$n" ]
  check AC-32 "~/.bashrc sources $after (line ${n:-?}) before prompt-command.bashrc (line ${pcl:-?}) — the helpers it registers through do not exist yet"
done

# ---- AC-34  $LESS must survive being handed to less ----------------------
# A malformed option makes less reject the WHOLE variable, silently dropping
# -R (colors) and -F (quit on one screen) together.
pager_less="$("$ENV_BIN" -i HOME="$HOME" PATH=/usr/bin:/bin TERM=dumb "$BASH_BIN" --norc -c '
  cd "$1" || exit 1; . software/bash/pager.bashrc; printf "%s" "$LESS"' _ "$repo" 2>/dev/null)"
case "$pager_less" in *--RAW-CONTROL-CHARS*) true ;; *) false ;; esac
check AC-34 "\$LESS lacks --RAW-CONTROL-CHARS, so a pager strips ANSI colors"
case "$pager_less" in *--quit-if-one-screen*) true ;; *) false ;; esac
check AC-34 "\$LESS lacks --quit-if-one-screen, so a one-line result waits for q"
case "$pager_less" in *=[[:space:]]*|*=) false ;; *) true ;; esac
check AC-34 "\$LESS has an option with an empty value ($pager_less) — less rejects the entire variable"
! command grep -qE '^[^#]*\$\((tput|expr)' software/bash/pager.bashrc
check AC-34 "pager.bashrc computes an option value at shell startup; where TERM is unset that fails and poisons all of \$LESS"
# Not the exit status: less exits 0 even when it rejects the variable, and only
# complains on stderr. Empty stderr is the actual signal.
less_complaint="$(printf 'x\n' | LESS="$pager_less" less 2>&1 >/dev/null)"
[ -z "$less_complaint" ]
check AC-34 "less refuses the composed \$LESS ($less_complaint) — every option in it is then lost, colors and quit-on-one-screen included"

# ---- AC-36  iTerm2's integration must load only in iTerm2 -----------------
# Interactive (-i) because the integration bails out otherwise, which would make
# every case below look like a pass.
iterm2_loaded() { # $1..: extra env assignments
  "$ENV_BIN" -i HOME="$HOME" PATH=/usr/bin:/bin TERM=xterm-256color "$@" "$BASH_BIN" --norc -i -c '
    cd "$1" || exit 1
    . software/iterm2/bashrc
    printf "\nRESULT=%s\n" "${ITERM_SHELL_INTEGRATION_INSTALLED:-no}"' _ "$repo" 2>/dev/null \
    | command sed -n 's/.*RESULT=//p' | tail -1
}
[ "$(iterm2_loaded)" = Yes ]
check AC-36 "iTerm2's shell integration does NOT load in a plain terminal — shell marks and clickable paths are lost"
[ "$(iterm2_loaded ZED_TERM=true)" != Yes ]
check AC-36 "iTerm2's shell integration loads in Zed's terminal, where it garbles the prompt"
[ "$(iterm2_loaded TERMINAL_EMULATOR=JetBrains-JediTerm)" != Yes ]
check AC-36 "iTerm2's shell integration loads in IntelliJ's terminal — it exports an OSC-133 PS1 that comes back mojibaked"

# ---- AC-37  the work repos' own setups must not have moved unread ---------
# Only the non-OK rows go in the message: the full table is what the tool prints
# when run by hand, and a hook reason that reprints three passing rows buries the
# one that needs reading.
#
# SKILL.md holds the baselines but is NOT in batch_digest, on purpose — see
# AC-37 in SPEC.md. Recording "nothing relevant changed" must not expire ten
# manual sign-offs.
# --porcelain: `STATUS<TAB>repo<TAB>detail`, no header and no guidance prose.
# Parsed on the FIRST field only. Grepping the human output instead matched the
# script's own footer, and AC-37 "failed" quoting a line of its help text.
review_out="$("$BASH_BIN" "$repo/.claude/tools/setup-review.sh" --porcelain 2>&1)"
review_rc=$?
if [ "$review_rc" -ne 0 ]; then
  # Only the rows that need something. A hook reason that reprints three passing
  # rows buries the one that matters. HOOKS-INACTIVE is AC-38, the rest AC-37 —
  # split so the reason names the right criterion, since the two need completely
  # different actions (run a setup script vs. read a diff and record a verdict).
  bad_rows() { printf '%s' "$review_out" | command awk -F'\t' -v want="$1" \
    'BEGIN { n = split(want, w, "|"); for (i in w) sel[w[i]] = 1 }
     sel[$1] { printf "      %-14s %s: %s\n", $2, $1, $3 }'; }
  hooks_bad="$(bad_rows 'HOOKS-INACTIVE')"
  review_bad="$(bad_rows 'NEVER-ANALYZED|DELTA|BASELINE-GONE')"
  if [ -n "$review_bad" ]; then
    false
    check AC-37 "a tracked work repo's setup story has moved unread — read the diff and record a verdict in the skill's tracked repos table:
$review_bad"
  fi
  if [ -n "$hooks_bad" ]; then
    false
    check AC-38 "a tracked repo's git hooks are dead because core.hooksPath is unset — run that repo's setup.sh:
$hooks_bad"
  fi
  # Exit 1 with neither pattern present would mean the tool failed for a reason
  # this parser does not know about; surface it rather than passing silently.
  if [ -z "$review_bad" ] && [ -z "$hooks_bad" ]; then
    review_head="$(printf '%s' "$review_out" | command sed 's/^/      /' | head -20)"
    false
    check AC-37 "setup-review.sh exited $review_rc with no recognized status; run it by hand:
$review_head"
  fi
fi

# ---- AC-39  `jira` opens a story through `browse` -------------------------
# HOME is a throwaway, so the per-machine config is whatever this writes and
# never the real one; a stub `open` records what browse would have launched.
jira_out="$("$ENV_BIN" -i PATH=/usr/bin:/bin "$BASH_BIN" --norc -c '
  cd "$1" || exit 1
  export HOME="$(mktemp -d)"; trap "rm -rf $HOME" EXIT
  config="$HOME/.config/dotfiles/jira"
  mkdir -p "${config%/*}"; echo work > "${config%/*}/profile"
  . software/bash/commands.bashrc
  . software/comply365/jira.bashrc
  open() { printf "OPENED:%s\n" "$*"; }
  probe() { local out rc; out="$(jira "${@:2}" 2>&1)"; rc=$?; echo "$1=[$out] rc=$rc"; }
  rb() { echo "$1=[$(/usr/bin/ruby software/comply365/jira.rb 2>&1 | tr "\n" " ")]"; }

  rb rb_missing; probe no_config 472
  : > "$config"
  rb rb_empty; probe empty_config 472
  printf "https://example.invalid/browse/KEY-" > "$config"   # no trailing newline
  rb rb_set; probe ok 472
  probe no_args; probe full_key KEY-472; probe two_args 1 2; probe not_digits 47a
' _ "$repo" 2>&1)"
jfact() { printf '%s\n' "$jira_out" | command sed -n "s/^$1=//p"; }

j="$(jfact ok)"
[ "$j" = "[OPENED:https://example.invalid/browse/KEY-472] rc=0" ]; check AC-39 "jira 472 did not open <configured prefix>472 through browse: $j"
for c in no_config empty_config; do
  j="$(jfact $c)"
  [[ "$j" == *.config/dotfiles/jira*"rc=1" && "$j" != *OPENED* ]]; check AC-39 "jira with $c did not fail naming the file it reads: $j"
done
for c in no_args full_key two_args not_digits; do
  j="$(jfact $c)"
  [[ "$j" == *"Usage: jira"*"rc=1" && "$j" != *OPENED* ]]; check AC-39 "jira ($c) was not a usage error: $j"
done
for c in rb_missing rb_empty; do
  j="$(jfact $c)"
  [[ "$j" == *.config/dotfiles/jira* ]]; check AC-39 "jira.rb did not warn while the per-machine Jira config was ${c#rb_}: $j"
done
j="$(jfact rb_set)"
[ "$j" = "[]" ]; check AC-39 "jira.rb printed something with the per-machine Jira config in place: $j"

# ---- [eyes] criteria: unconfirmed until signed off ------------------------
# Each entry names the files its sign-off depends on; the digest of those files
# is what expires it, so editing the direnv wiring doesn't re-ask about zsh.
while IFS='|' read -r id _files steps; do
  [ -n "${id:-}" ] || continue
  digest="$(batch_digest)"
  recorded="$(python3 - "$LEDGER" "$id" 2>/dev/null <<'LEDGER_READ'
import json, sys
try:
    entries = json.load(open(sys.argv[1]))
except Exception:
    entries = {}
entry = entries.get(sys.argv[2]) or {}
print((entry.get("status") or "none") + ":" + (entry.get("digest") or "none"))
LEDGER_READ
)"
  case "$recorded" in
    "pass:$digest") ;;
    "fail:$digest") revoked+=("$id|$steps") ;;
    *)              pending+=("$id|$steps") ;;
  esac
done < <(sed -n '/<!-- manual-checks/,/-->/p' "$SPEC" | command grep -E '^AC-')

# ---- report ---------------------------------------------------------------
if [ "${#fails[@]}" -eq 0 ] && [ "${#pending[@]}" -eq 0 ] && [ "${#revoked[@]}" -eq 0 ]; then
  printf '{"systemMessage":"comply365 SPEC.md: all criteria pass (manual ones signed off for the current code)."}\n'
  exit 0
fi

{
  [ "${#fails[@]}" -gt 0 ] && { printf 'comply365 SPEC.md — %d automated criteria FAILED:\n' "${#fails[@]}"; printf '  - %s\n' "${fails[@]}"; printf 'Fix these by reading the actual code in software/comply365/, not a summary.\n\n'; }
  if [ "${#revoked[@]}" -gt 0 ]; then
    printf '%d manual criteria were REVOKED and need re-confirming by a human.\n' "${#revoked[@]}"
    printf 'A verdict of `fail` was recorded deliberately — usually because the criterion was\n'
    printf 'tightened. Nothing is broken in the code; it has to be re-run. Ask the user:\n'
    for p in "${revoked[@]}"; do printf '  - %s: %s\n' "${p%%|*}" "${p#*|}"; done
    printf '\n'
  fi
  if [ "${#pending[@]}" -gt 0 ]; then
    printf '%d criteria cannot be verified from a script and are NOT confirmed for the current code.\n' "${#pending[@]}"
    printf 'Ask the user to run each one and report back pass/fail. Do not claim the batch is done until they have.\n'
    for p in "${pending[@]}"; do printf '  - %s: %s\n' "${p%%|*}" "${p#*|}"; done
    printf '\n'
  fi
  { [ "${#revoked[@]}" -gt 0 ] || [ "${#pending[@]}" -gt 0 ]; } && \
    printf 'Record each answer with:  .claude/hooks/comply365-signoff.sh <AC-id> pass|fail\n'
} > "${TMPDIR:-/tmp}/comply365-report.$$"

report_digest="$(command shasum -a 256 "${TMPDIR:-/tmp}/comply365-report.$$" | cut -c1-16)"
mode=block
[ -f "$latch" ] && [ "$(cat "$latch")" = "$report_digest" ] && mode=advise
printf '%s' "$report_digest" > "$latch"

python3 -c '
import json,sys
body=open(sys.argv[1]).read()
if sys.argv[2]=="block":
    print(json.dumps({"decision":"block","reason":body}))
else:
    print(json.dumps({"systemMessage":body+"\n(unchanged since the last block this session — advisory only)"}))
' "${TMPDIR:-/tmp}/comply365-report.$$" "$mode"
rm -f "${TMPDIR:-/tmp}/comply365-report.$$"
exit 0
