# Bash equivalent of the zsh `chpwd` auto-`nvm use` hook that web-safety installs
# into ~/.zshrc (zsh-only, never fires in Bash). This adds the same
# auto-use behavior for Bash — on every prompt rather than on `chpwd`, because
# what governs the version can change without the directory changing (see the
# registration at the bottom).
#
# Note on ordering: `nvm` is a shell *function*, not a program. dotfiles loads it
# in software/node/bashrc, but that is sourced *after* this file (node sorts
# after comply365), and a repo — not dotfiles — might be what provides nvm. So we
# must NOT test for nvm now, at load time. Instead we check (and load nvm if
# needed) at runtime, inside the hook, which runs on the first prompt — by which
# point everything has loaded.

# Make sure nvm's function is available; load it if nothing else has yet.
# ${BASH_SOURCE[0]} inside a function is the file the function was defined in,
# i.e. this one, so this reaches the loader inside the dotfiles repo.
__comply365_ensure_nvm() {
  command -v nvm >/dev/null 2>&1 && return 0
  \. "${BASH_SOURCE[0]%/*}/../node/nvm-loader.sh"
  command -v nvm >/dev/null 2>&1
}

# Walk up from $PWD to the nearest .nvmrc, which is what nvm's own
# `nvm_find_nvmrc` does. We deliberately don't call that function: it's private
# to nvm.sh, so relying on it means this hook misbehaves the moment `nvm` is a
# lazy-loading wrapper — `command -v nvm` succeeds, nvm.sh was never sourced,
# `nvm_find_nvmrc` doesn't exist, its 127 gets swallowed, and every project then
# looks like it has no .nvmrc, so we'd `nvm use default` on *entering* a pinned
# repo. Doing the walk ourselves also means we don't need nvm loaded at all to
# discover there's nothing to do.
#
# The answers go into globals instead of stdout, because a command substitution
# would fork — and this runs on every directory change.
__comply365_find_nvmrc() {
  __comply365_nvmrc=''
  __comply365_nvmrc_version=''

  local dir="$PWD"
  while :; do
    if [ -f "$dir/.nvmrc" ]; then
      __comply365_nvmrc="$dir/.nvmrc"

      # First line only, like nvm, but via a builtin instead of `$(cat …)`.
      # Trailing whitespace is dropped for the same reason nvm pipes through
      # `tr -d '\r'`: we hand this version to `nvm use` ourselves, so a CRLF
      # .nvmrc would otherwise resolve to N/A and look uninstalled.
      read -r __comply365_nvmrc_version < "$__comply365_nvmrc"
      __comply365_nvmrc_version="${__comply365_nvmrc_version%"${__comply365_nvmrc_version##*[![:space:]]}"}"

      return 0
    fi

    # "" is what `${dir%/*}` leaves once dir is a top-level entry, and the
    # iteration it stands for is `/.nvmrc` — which nvm's own lookup does check,
    # so skipping it would have the two disagree about the same directory.
    [ -n "$dir" ] || break
    dir="${dir%/*}"
  done

  return 1
}

__comply365_auto_nvm_use() {
  __comply365_find_nvmrc

  # Bail out when neither the governing .nvmrc nor PATH has moved since we last
  # acted — the overwhelmingly common case, and one that costs no forks at all:
  # the walk above is builtins only, and this is a string compare. That is what
  # pays for running on every prompt rather than only on a directory change.
  # Previously every `cd` outside a project still ran `nvm current` (which execs
  # `node --version`) and `nvm version default` just to learn they matched.
  #
  # The pinned version is part of the key, not just the .nvmrc path: a
  # `git checkout` that rewrites .nvmrc in place changes neither $PWD nor the
  # path, so keying on the path alone left the previous branch's Node active for
  # the rest of the session.
  #
  # PATH is part of the key on purpose too: leaving a direnv project makes direnv
  # restore the PATH snapshot it took on entry, undoing our `nvm use`, and that
  # has to be redone.
  [ "$__comply365_nvmrc|$__comply365_nvmrc_version|$PATH" = "${__comply365_nvm_state:-}" ] && return 0

  __comply365_ensure_nvm || return

  if [ -n "$__comply365_nvmrc" ]; then
    local resolved_version
    resolved_version="$(nvm version "$__comply365_nvmrc_version")"

    if [ "$resolved_version" = "N/A" ]; then
      # Don't `nvm install` automatically: that's an unattended, possibly
      # multi-minute download with no failure handling, triggered by nothing
      # more than a `cd` (offline/proxied, it fails silently and the previous
      # Node version stays active with no indication anything is wrong). Surface
      # the version instead, and let the user opt in explicitly.
      #
      # Keyed on the version, not on the state below: PATH is in that key, and
      # direnv mutates PATH both entering and leaving a managed subdirectory, so
      # every `cd` within an uninstalled-version project would reprint this.
      if [ "$__comply365_nvmrc_version" != "${__comply365_nvm_warned:-}" ]; then
        __comply365_nvm_warned="$__comply365_nvmrc_version"
        printf 'nvm: no installed Node matches %s (run `nvm install`)\n' "$__comply365_nvmrc_version" >&2
      fi

      # Deliberately no state: installing the missing version from another
      # terminal changes nothing this key can see, so recording it here would
      # pin *this* shell to the wrong Node for the rest of its life, silently
      # (the warning is once-per-version). The price is one `nvm version` fork
      # per prompt while sitting in a project whose Node isn't installed — a
      # state we're actively telling the user to fix.
      return
    fi

    if [ "$resolved_version" != "$(nvm current)" ]; then
      # Named explicitly rather than a bare `nvm use`, which would redo the
      # .nvmrc lookup with nvm's own walk and could land on a different file.
      nvm use "$__comply365_nvmrc_version" >/dev/null || return
    fi
  elif [ "$(nvm current)" != "$(nvm version default)" ]; then
    # No .nvmrc in this tree: we've left a project, so revert to nvm's default
    # (which dotfiles sets to `system`). This goes beyond web-safety's own zsh
    # hook, which never reverts.
    nvm use default >/dev/null || return
  fi

  # Only ever reached once the Node on PATH is the one this directory asked for,
  # so a failed switch is retried on the next prompt instead of being cached as
  # if it had worked.
  __comply365_nvm_state="$__comply365_nvmrc|$__comply365_nvmrc_version|$PATH"
}

# Register LAST in PROMPT_COMMAND (append, don't prepend) so this runs *after*
# direnv's hook. When you leave a direnv project, direnv restores the PATH
# snapshot it captured on entry — which would otherwise undo our `nvm use` and
# leave the previous project's Node version active. Running last lets nvm have
# the final say on which version is on PATH.
#
# Every prompt, not only on a directory change (zsh `chpwd`-style): a
# `git checkout` that rewrites .nvmrc in place moves neither $PWD nor the file's
# path, and gating on $PWD made the version in the cache key above dead weight.
# The cached case is builtins only, so this costs no forks.
__prompt_command_append __comply365_auto_nvm_use
