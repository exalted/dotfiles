# Put Homebrew — and everything installed through it — on PATH, and export the
# HOMEBREW_* / INFOPATH / MANPATH values that go with it.
#
# Sourced by software/homebrew/bashrc (interactive Bash) and by
# software/comply365/zshenv (every zsh, including the git hooks GUI apps spawn),
# so both shells find Homebrew the same way. POSIX sh for that reason.
#
# `brew` itself isn't findable yet at this point — that's the whole problem this
# solves — so we probe for it, the way Homebrew's own installer-generated snippet
# does. Both supported prefixes are tried (Apple Silicon first, then Intel) so
# neither is baked in.
#
# Skipped only when *both* proxies agree Homebrew is already set up: an exported
# HOMEBREW_PREFIX that really holds a `brew`, and its bin directory somewhere on
# PATH. Either one alone was tried and each broke a real case — PATH-only skipped
# for a terminal-inherited PATH and left HOMEBREW_PREFIX unset; HOMEBREW_PREFIX-
# only skipped when a GUI app's cached environment carried the variable while
# PATH did *not* have the bin directory, leaving `brew` and every Homebrew tool
# including its own bash off PATH (macOS's stock /bin/bash was then the only bash
# found, which broke tools expecting a modern one). Requiring both agree rules
# out each of those.
#
# Re-running `brew shellenv` is not free of side effects, which is why the guard
# has to exist at all: it re-prepends its bin directory whenever that isn't
# already the head of PATH, demoting anything deliberately put in front — an
# `nvm use` version behind Homebrew's own node, say. That matters here because
# ~/.zshenv sources this file on *every* zsh, including hooks spawned from a
# shell that has already selected a version.
# "On PATH" is not enough: it has to be on PATH *ahead of the system
# directories*. macOS's path_helper runs from /etc/profile in every login shell
# — which is what terminals start — and rebuilds PATH with /usr/bin and /bin
# first, pushing an inherited Homebrew entry to the end. Homebrew is then still
# "on PATH" while /bin/bash (3.2) wins over Homebrew's bash 5, and every
# `#!/usr/bin/env bash` tool silently runs on 3.2 — the `git hist` / emojify
# failure. Checking presence alone declared that state ready and skipped the fix.
__brew_ready=''
if [ -n "${HOMEBREW_PREFIX:-}" ] && [ -x "$HOMEBREW_PREFIX/bin/brew" ]; then
  # Everything in PATH ahead of the first system bin directory. `%%` strips from
  # the earliest match onward, so taking it twice leaves the head that precedes
  # both; if neither appears, the whole of PATH is the head, which is correct —
  # there is nothing there to lose a name collision to.
  __path_head=":$PATH:"
  __path_head="${__path_head%%:/usr/bin:*}:"
  __path_head="${__path_head%%:/bin:*}:"
  case "$__path_head" in
    *":$HOMEBREW_PREFIX/bin:"*) __brew_ready=1 ;;
  esac
  unset __path_head
fi

if [ -z "$__brew_ready" ]; then
  for __brew in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [ -x "$__brew" ] || continue
    eval "$("$__brew" shellenv)"
    break
  done
  unset __brew
fi
unset __brew_ready
