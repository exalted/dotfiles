#!/usr/bin/env bash
# What a work repo's setup.sh left behind, and whether Bash already has it.
#
# Run this AFTER running any repo's setup/setup.sh. Those scripts append to
# ~/.zshrc (zsh-only builtins, so inert for us) and sometimes to ~/.bashrc
# (which `bin/dotfiles` regenerates from scratch, so it is erased on the next
# run). Either way the behavior only becomes durable once it exists as a
# fragment in this repo.
#
# Exit 0 = nothing unaccounted for. Exit 1 = something needs a decision.
set -uo pipefail

repo="$(git rev-parse --show-toplevel)"; cd "$repo"
drift=0
# One "logical unit" per line, so a multi-line shell function or a
# marker-delimited block is classified once instead of line by line (its body
# would otherwise look like a dozen unmirrored fragments). Marker comments are
# kept deliberately — `# >>> nvm auto-use >>>` names the mechanism.
effective() {
  [ -f "$1" ] || return 0
  command awk '
    /^[[:space:]]*#[[:space:]]*>>>/ { if (!inm) { inm=1; print } ; next }
    /^[[:space:]]*#[[:space:]]*<<</ { inm=0; next }
    inm                             { next }
    /^[[:space:]]*#/                { next }
    /^[[:space:]]*$/                { next }
    inf                             { if ($0 ~ /^[[:space:]]*}/) inf=0; next }
    /^[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\(\)/ { inf=1; print; next }
                                    { print }
  ' "$1" 2>/dev/null
}

# Pattern => what in this repo already provides it for Bash.
#
# The separator is `=>`, not `|`: the patterns are ERE, so a `|` inside one made
# `${entry%%|*}` cut the pattern in half — `nvm (use|install|...)` became the
# unbalanced `nvm (use`, which bash rejected on every line and silently matched
# nothing.
MIRRORED=(
  'direnv hook=>software/comply365/cortex.bashrc (direnv hook, any .envrc repo)'
  'NVM_DIR=>software/node/bashrc + node/nvm-loader.sh — but note this line points at a curl-installed nvm; we standardize on Homebrew'"'"'s'
  'nvm\.sh=>software/node/bashrc + node/nvm-loader.sh'
  'bash_completion=>software/node/bashrc'
  'add-zsh-hook=>software/comply365/web-safety.bashrc (auto-nvm-use, any .nvmrc repo)'
  'auto_nvm_use=>software/comply365/web-safety.bashrc'
  'nvm auto-use=>software/comply365/web-safety.bashrc'
  'chpwd=>software/comply365/web-safety.bashrc (PROMPT_COMMAND is the Bash analog)'
  'nvm_find_nvmrc=>software/comply365/web-safety.bashrc (we do our own walk on purpose)'
  'nvm (use|install|current|version)=>software/comply365/web-safety.bashrc'
  'brew shellenv=>software/homebrew/shellenv.sh'
  'JetBrains=>not shell behavior (Toolbox PATH entry) — ignorable'
)

classify() { # prints the mirror note, or nothing when unmirrored
  local line="$1" entry
  for entry in "${MIRRORED[@]}"; do
    [[ "$line" =~ ${entry%%=>*} ]] && { printf '%s' "${entry#*=>}"; return 0; }
  done
  return 1
}

echo "=== ~/.bashrc — foreign lines (erased on the next \`bin/dotfiles\` run) ==="
# Generated content is only the header plus `source` lines. Anything else was
# appended from outside this repo.
foreign="$(effective "$HOME/.bashrc" | command grep -vE '^(source|\.) ' || true)"
if [ -z "$foreign" ]; then
  echo "  (none)"
else
  while IFS= read -r line; do
    if note="$(classify "$line")"; then
      printf '  TRANSIENT  %s\n             already durable via: %s\n' "$line" "$note"
    else
      printf '  UNMIRRORED %s\n             -> nothing in this repo provides this; it disappears on the next run\n' "$line"
      drift=1
    fi
  done <<<"$foreign"
fi

for f in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.zlogin"; do
  [ -f "$f" ] || continue
  echo
  echo "=== $f — zsh-only, inert for our Bash shells ==="
  seen=''
  while IFS= read -r line; do
    if note="$(classify "$line")"; then
      case "$seen" in *"|$note|"*) continue ;; esac   # one line per mechanism
      seen="$seen|$note|"
      printf '  MIRRORED   %s\n' "$note"
    else
      printf '  UNMIRRORED %s\n' "$line"
      drift=1
    fi
  done < <(effective "$f")
done

echo
if [ "$drift" = 0 ]; then
  echo "No drift: everything those setups installed has a durable Bash equivalent here."
else
  cat <<'NEXT'
Drift found. For each UNMIRRORED item:
  1. Decide whether it is shell *behavior* we need in Bash (a hook, a PATH
     entry, a runtime manager) or repo-local noise.
  2. If we need it, add it to an existing software/comply365 fragment when one
     of the three generic mechanisms already fits, or add a new
     software/comply365/<project>.rb (+ fragment) and register it in
     profiles.rb under `work`.
  3. Add acceptance criteria to software/comply365/SPEC.md — automated where
     possible, otherwise a manual entry in the manual-checks block.
  4. Run .claude/hooks/comply365-spec-check.sh and have the user confirm any
     [eyes] criteria the change could affect.
NEXT
fi
exit "$drift"
