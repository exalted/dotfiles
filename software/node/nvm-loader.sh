# Locate and source nvm.sh, which is what defines the `nvm` shell function.
#
# Three places need nvm, and each used to carry its own copy of this search:
# software/node/bashrc (interactive Bash), software/comply365/zshenv (the zsh git
# hooks some work repos ship) and software/comply365/web-safety.bashrc (the
# auto-use-on-cd hook's fallback). This is the one copy, so there is a single
# place that knows where nvm lives. Kept to POSIX sh so zsh can source it too.
#
# Sourcing this is a no-op once nvm is loaded.
if ! command -v nvm >/dev/null 2>&1; then
  # Must stay $HOME/.nvm: that's where Homebrew's nvm.sh keeps user-installed
  # Node versions, so they survive `brew upgrade nvm`.
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"

  # Homebrew's copy is the one dotfiles installs (software/node); a
  # self-installed nvm under $NVM_DIR is the fallback. HOMEBREW_PREFIX comes from
  # `brew shellenv`, so neither prefix is baked in here.
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
