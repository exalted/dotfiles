##
## PATH
##

export PATH="$PATH:$HOME/bin"

# TODO: Is this necessary, or is it already being taken care by `software/homebrew/bashrc`
export PATH="$PATH:$(brew --prefix)/sbin"

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
CDPATH="$CDPATH:$HOME/Development/_downloads"
