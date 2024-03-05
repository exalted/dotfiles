# (Ref.: https://support.apple.com/en-us/HT208050)
export BASH_SILENCE_DEPRECATION_WARNING=1

# NOTE: `unalias git` is added to remove our `git-wrapper` around the original
#       `git` command, so that `__git_ps1` can work properly (e.g., it wouldn't
#       `trap` ERR, etc.)
#
# TODO: consider moving `__git_ps1` to `PROMPT_COMMAND`, because;
#         1. it's slightly faster,
#         2. you can use `GIT_PS1_SHOWCOLORHINTS` in this mode.
#       (Check out `git-prompt.sh` for more details.)
#
# original: `export PS1="\h:\W \u\$ "`
export PS1="\[\e[34m\]\w \[\e[31m\]\$(unalias git && __git_ps1 \"(%s)\")\n\[\e[32m\]❯ \[\e[0m\]"

# (Ref.: https://stackoverflow.com/a/48915032/11895)
export PROMPT_COMMAND='(( PROMPT_CTR-- < 0 )) && {
  unset PROMPT_COMMAND PROMPT_CTR
  PS1="\n\n$PS1"
}'

# PROMPT_COMMAND="export PROMPT_COMMAND='echo; echo'"
# alias clear="clear; export PROMPT_COMMAND='export PROMPT_COMMAND='echo''"
