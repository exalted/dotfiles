export HISTSIZE=100000
# (Ref.: http://askubuntu.com/a/15929)
export HISTCONTROL=ignoreboth:erasedups
# # (Ref.: http://www.talug.org/events/20030709/cmdline_history.html)
# export HISTIGNORE="&:ls:[bf]g:exit"

# Append when the shell exits, rather than overwriting the history file
shopt -s histappend

# History completion to what's already on the line
# (Ref.: http://stackoverflow.com/a/1030206/11895)
bind '"\e[A": history-search-backward'
bind '"\e[B": history-search-forward'
