# `brew --prefix` is the authority, not an inherited $HOMEBREW_PREFIX: that can
# name a Homebrew other than the one on PATH (a terminal that kept the env of an
# older session, a second prefix under /usr/local). Resolved once here — one
# fork, ~10ms — and reused by everything below, including nvm-loader.sh.
#
# Assigned, not `: "${HOMEBREW_PREFIX:=$(brew --prefix)}"`: that leaves the
# variable set to the empty string when there is no brew, and empty-but-set
# silently defeats every `${HOMEBREW_PREFIX:-…}` fallback downstream. Unset is
# the honest answer, so those fallbacks still fire.
HOMEBREW_PREFIX="$(brew --prefix 2>/dev/null)"
[ -n "$HOMEBREW_PREFIX" ] || unset HOMEBREW_PREFIX

[ -n "${HOMEBREW_PREFIX:-}" ] && export PATH="$PATH:$HOMEBREW_PREFIX/opt/node/bin"

# make sure these comes after all the others, so that local binaries win
# export PATH="../../../../node_modules/.bin:$PATH"
# export PATH="../../../node_modules/.bin:$PATH"
# export PATH="../../node_modules/.bin:$PATH"
# export PATH="../node_modules/.bin:$PATH"
export PATH="node_modules/.bin:$PATH"

#
# Node Version Manager (see `brew info nvm`)
#
# ~/.bashrc sources this file by absolute path, so ${BASH_SOURCE[0]%/*} is this
# directory in the dotfiles repo.
\. "${BASH_SOURCE[0]%/*}/nvm-loader.sh"
[ -s "${HOMEBREW_PREFIX:-}/opt/nvm/etc/bash_completion.d/nvm" ] && \. "$HOMEBREW_PREFIX/opt/nvm/etc/bash_completion.d/nvm"  # This loads nvm bash_completion
