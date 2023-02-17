##
## PATH
##

export PATH="$HOME/bin:$PATH"

# TODO: Is this necessary, or is it already being taken care by `software/homebrew/bashrc`
export PATH="$(brew --prefix)/sbin:$PATH"

# TODO: remove hard-coded path
export PATH="$PATH:$HOME/Development/dotfiles/software/bash/bin"

##
## MANPATH
##

MANPATH="$MANPATH:/usr/share/man"

##
## CDPATH
##

# TODO: remove hard-coded path
CDPATH="$CDPATH:."
CDPATH="$CDPATH:$HOME"
CDPATH="$CDPATH:$HOME/Development"
CDPATH="$CDPATH:$HOME/Development/balsamiq"
CDPATH="$CDPATH:$HOME/Development/_balsamiq-others"
CDPATH="$CDPATH:$HOME/Development/_experiments"
CDPATH="$CDPATH:$HOME/Development/_forks"
CDPATH="$CDPATH:$HOME/Development/_downloads"
