export GRC_ALIASES=true
# `brew --prefix`, not an inherited $HOMEBREW_PREFIX (see software/node/bashrc.bash),
# and not `brew --prefix grc`: Homebrew keeps etc/ in the shared prefix.
__grc_sh="$(brew --prefix 2>/dev/null)/etc/grc.sh"
[[ -f "$__grc_sh" ]] && \. "$__grc_sh"
unset __grc_sh

# grc's alias would hide the diff() function from software/diff/bashrc.bash.
unalias diff 2>/dev/null
