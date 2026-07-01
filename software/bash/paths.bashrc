##
## PATH
##

export PATH="$PATH:$HOME/bin"

export PATH="$PATH:$(dirname "${BASH_SOURCE[0]}")/bin"

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
