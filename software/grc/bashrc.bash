export GRC_ALIASES=true
[[ -f "$HOMEBREW_PREFIX/etc/grc.sh" ]] && \. "$HOMEBREW_PREFIX/etc/grc.sh"

# grc's alias would hide the diff() function from software/diff/bashrc.bash.
unalias diff 2>/dev/null
