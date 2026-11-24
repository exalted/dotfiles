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
