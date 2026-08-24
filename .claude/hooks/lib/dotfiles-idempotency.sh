#!/usr/bin/env bash
# Runs this batch's software entry scripts TWICE against a throwaway $HOME and
# prints KEY=VALUE facts about the result. Answers "does `bin/dotfiles` break
# anything", minus the parts that need sudo or Homebrew.
#
# Safe to run any time: none of these scripts install anything (verified — only
# comments mention brew) and every path they touch is under $HOME, which here is
# a temp dir. bin/dotfiles itself is NOT run: it calls _keep_sudo_alive and the
# installers.
set -uo pipefail
repo="${1:?repo root required}"
cd "$repo" || exit 1

fake="$(mktemp -d)"; trap 'rm -rf "$fake"' EXIT
mkdir -p "$fake/.ssh" "$fake/.config/dotfiles"
# Entry scripts abort without a resolved profile — that is bin/dotfiles' first step.
echo work > "$fake/.config/dotfiles/profile"
# A config kept outside this repo, which a run must preserve rather than replace.
printf 'Host jump\n  HostName example.invalid\n' > "$fake/.ssh/config"
printf '# pre-existing zshenv\n' > "$fake/.zshenv"

SCRIPTS=(software/comply365/cortex.rb software/comply365/web-safety.rb
         software/comply365/zsh.rb software/ssh/ssh.rb)
failed=0
for _run in 1 2; do
  for s in "${SCRIPTS[@]}"; do
    HOME="$fake" ruby "$s" >/dev/null 2>&1 || failed=$((failed + 1))
  done
done
echo "script_failures=$failed"

# Idempotency: two runs must leave one source line per fragment.
dupes="$(command grep '^source ' "$fake/.bashrc.dotfiles" 2>/dev/null | command sort | command uniq -d | command wc -l | tr -d ' ')"
echo "duplicate_source_lines=$dupes"
echo "fragments_sourced=$(command grep -c '^source ' "$fake/.bashrc.dotfiles" 2>/dev/null || echo 0)"

# Non-destructive: content preserved, one Include, one backup, and a mode ssh accepts.
echo "ssh_include_lines=$(command grep -c '^Include' "$fake/.ssh/config")"
echo "ssh_preexisting_host=$(command grep -c 'Host jump' "$fake/.ssh/config")"
echo "ssh_backups=$(command ls -1 "$fake/.ssh" | command grep -c backup)"
echo "ssh_fragment_linked=$([ -L "$fake/.ssh/config.d/dotfiles" ] && echo yes || echo no)"
mode="$(command stat -f '%Lp' "$fake/.ssh/config")"
# ssh refuses a config that is group- or world-WRITABLE; 644 is fine, 66x is not.
echo "ssh_group_or_world_writable=$([ $(( 0$mode & 0022 )) -ne 0 ] && echo yes || echo no)"

# Same again with no pre-existing config: that path creates the file, and it must
# be created 600 regardless of the ambient umask.
fresh="$(mktemp -d)"; mkdir -p "$fresh/.ssh" "$fresh/.config/dotfiles"
echo work > "$fresh/.config/dotfiles/profile"
( umask 0002; HOME="$fresh" ruby software/ssh/ssh.rb >/dev/null 2>&1 )
echo "ssh_fresh_mode=$(command stat -f '%Lp' "$fresh/.ssh/config" 2>/dev/null || echo none)"
rm -rf "$fresh"

echo "zshenv_is_symlink=$([ -L "$fake/.zshenv" ] && echo yes || echo no)"
echo "zshenv_backup_preserved=$(command grep -qF 'pre-existing zshenv' "$fake/.zshenv.backup" 2>/dev/null && echo yes || echo no)"
