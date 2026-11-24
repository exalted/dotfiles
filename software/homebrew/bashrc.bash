# ~/.bashrc sources this file by absolute path, so ${BASH_SOURCE[0]%/*} is this
# directory in the dotfiles repo. See shellenv.sh for why the probing is needed.
\. "${BASH_SOURCE[0]%/*}/shellenv.sh"

# `brew --prefix` is the authority, not an inherited $HOMEBREW_PREFIX: that can
# name a Homebrew other than the one on PATH (a terminal that kept the env of an
# older session, a second prefix under /usr/local). Resolved once here, with one
# fork: homebrew is in the BOOTSTRAP list, so ~/.bashrc sources this fragment
# before every other one, and they all read $HOMEBREW_PREFIX instead of running
# `brew --prefix` again. A formula's own files are under
# "$HOMEBREW_PREFIX/opt/<formula>" (what `brew --prefix <formula>` prints); etc/
# and var/ stay in "$HOMEBREW_PREFIX" itself.
#
# Assigned, not `: "${HOMEBREW_PREFIX:=$(brew --prefix)}"`: that leaves the
# variable set to the empty string when there is no brew, and empty-but-set
# silently defeats every `${HOMEBREW_PREFIX:-…}` fallback downstream. Unset is
# the honest answer, so those fallbacks still fire.
HOMEBREW_PREFIX="$(brew --prefix 2>/dev/null)"
if [ -n "$HOMEBREW_PREFIX" ]; then export HOMEBREW_PREFIX; else unset HOMEBREW_PREFIX; fi
