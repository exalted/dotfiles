# ~/.bashrc sources this file by absolute path, so ${BASH_SOURCE[0]%/*} is this
# directory in the dotfiles repo. See shellenv.sh for why the probing is needed.
\. "${BASH_SOURCE[0]%/*}/shellenv.sh"

# shellenv.sh leaves HOMEBREW_PREFIX set to the one Homebrew a dotfiles machine
# has, and homebrew is in the BOOTSTRAP list, so ~/.bashrc sources this fragment
# before every other one. They read $HOMEBREW_PREFIX instead of asking brew: a
# formula's own files are under "$HOMEBREW_PREFIX/opt/<formula>" (what
# `brew --prefix <formula>` prints), while etc/ and var/ stay in the prefix itself.
