# Locate and source nvm.sh, which is what defines the `nvm` shell function.
#
# Sourced by software/node/bashrc.bash (interactive Bash), so a single place knows
# where nvm lives. Kept to POSIX sh so any other shell can source it too.
#
# Sourcing this is a no-op once nvm is loaded.
if ! command -v nvm >/dev/null 2>&1; then
  # Must stay $HOME/.nvm: that's where Homebrew's nvm.sh keeps user-installed
  # Node versions, so they survive `brew upgrade nvm`.
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

  # Homebrew's copy is the one dotfiles installs (software/node); a
  # self-installed nvm under $NVM_DIR is the fallback. HOMEBREW_PREFIX comes from
  # software/homebrew/shellenv.sh; a shell that did not source it falls back to
  # asking brew. Either way, no prefix is baked in here.
  for __nvm_sh in \
    "${HOMEBREW_PREFIX:-$(brew --prefix 2>/dev/null)}/opt/nvm/nvm.sh" \
    "$NVM_DIR/nvm.sh"
  do
    if [ -s "$__nvm_sh" ]; then
      \. "$__nvm_sh"
      break
    fi
  done
  unset __nvm_sh
fi
