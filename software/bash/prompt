# original: `export PS1="\h:\W \u\$ "`
# TODO: consider moving `__git_ps1` to `PROMPT_COMMAND`, because;
#         1. it's slightly faster,
#         2. you can use `GIT_PS1_SHOWCOLORHINTS` in this mode.
PS1="\[\e[34m\]\w \[\e[31m\]\$(__git_ps1 \"(%s)\")\n\[\e[32m\]❯ \[\e[0m\]"

# (Ref.: https://stackoverflow.com/a/48915032/11895)
PROMPT_COMMAND='(( PROMPT_CTR-- < 0 )) && {
  unset PROMPT_COMMAND PROMPT_CTR
  PS1="\n\n$PS1"
}'
