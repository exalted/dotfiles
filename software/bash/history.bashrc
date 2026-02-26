export HISTSIZE=100000
# (Ref.: http://askubuntu.com/a/15929)
export HISTCONTROL=ignoreboth:erasedups
# # (Ref.: http://www.talug.org/events/20030709/cmdline_history.html)
# export HISTIGNORE="&:ls:[bf]g:exit"

# Immediately sync history across sessions
export PROMPT_COMMAND="history -a; history -c; history -r; $PROMPT_COMMAND"

# Append when the shell exits, rather than overwriting the history file
shopt -s histappend

# Only apply if the shell is interactive (e.g., Claude code running commands
# in non-interactive Bash sessions that doesn't support keyboard input).
if [[ $- == *i* ]]; then
    # History completion to what's already on the line
    # (Ref.: http://stackoverflow.com/a/1030206/11895)
    bind '"\e[A": history-search-backward'
    bind '"\e[B": history-search-forward'
fi
