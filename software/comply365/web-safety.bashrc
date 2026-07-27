# Bash equivalent of the zsh `chpwd` auto-`nvm use` hook that web-safety installs
# into ~/.zshrc (zsh-only, never fires in Bash). This adds the same
# auto-use-on-directory-change behavior for Bash.
#
# Note on ordering: `nvm` is a shell *function*, not a program. dotfiles loads it
# in software/node/bashrc, but that is sourced *after* this file (node sorts
# after comply365), and a repo — not dotfiles — might be what provides nvm. So we
# must NOT test for nvm now, at load time. Instead we check (and load nvm if
# needed) at runtime, inside the hook, which runs on the first prompt — by which
# point everything has loaded.

# Make sure nvm's function is available; load it if nothing else has yet.
__comply365_ensure_nvm() {
  command -v nvm >/dev/null 2>&1 && return 0

  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  local candidate
  for candidate in "$(brew --prefix 2>/dev/null)/opt/nvm/nvm.sh" "$NVM_DIR/nvm.sh"; do
    if [ -s "$candidate" ]; then
      \. "$candidate"
      break
    fi
  done

  command -v nvm >/dev/null 2>&1
}

__comply365_auto_nvm_use() {
  __comply365_ensure_nvm || return

  local nvmrc_path
  nvmrc_path="$(nvm_find_nvmrc 2>/dev/null)"

  if [ -n "$nvmrc_path" ]; then
    local resolved_version
    resolved_version="$(nvm version "$(command cat "$nvmrc_path")")"

    if [ "$resolved_version" = "N/A" ]; then
      nvm install
    elif [ "$resolved_version" != "$(nvm current)" ]; then
      nvm use >/dev/null
    fi
  elif [ "$(nvm current)" != "$(nvm version default)" ]; then
    # No .nvmrc in this tree: we've left a project, so revert to nvm's default
    # (which dotfiles sets to `system`). This goes beyond web-safety's own zsh
    # hook, which never reverts.
    nvm use default >/dev/null
  fi
}

# Mirror zsh's `chpwd`: act only when the directory actually changes, so this
# stays cheap on every prompt.
__comply365_nvm_on_chdir() {
  if [ "$PWD" != "${__comply365_last_pwd:-}" ]; then
    __comply365_last_pwd="$PWD"
    __comply365_auto_nvm_use
  fi
}

# Register LAST in PROMPT_COMMAND (append, don't prepend) so this runs *after*
# direnv's hook. When you leave a direnv project, direnv restores the PATH
# snapshot it captured on entry — which would otherwise undo our `nvm use` and
# leave the previous project's Node version active. Running last lets nvm have
# the final say on which version is on PATH. Registered once (idempotent).
case ";$PROMPT_COMMAND;" in
  *__comply365_nvm_on_chdir*) ;;
  *) PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }__comply365_nvm_on_chdir" ;;
esac
