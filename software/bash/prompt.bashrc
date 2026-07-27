# (Ref.: https://support.apple.com/en-us/HT208050)
export BASH_SILENCE_DEPRECATION_WARNING=1

# We render our own "[venv: NAME]" segment (see PS1 below), so suppress the
# default "(NAME)" prefix that `source .venv/bin/activate` would prepend to PS1.
# (direnv's `layout python3` activates the venv via VIRTUAL_ENV + PATH but never
# touches PS1, so without this segment an active venv would be invisible.)
export VIRTUAL_ENV_DISABLE_PROMPT=1

__venv_ps1() {
  [ -n "${VIRTUAL_ENV:-}" ] || return 0

  # Prefer the venv's configured prompt name (pyvenv.cfg `prompt = …`, which uv
  # sets to the project name); fall back to the venv dir, then its parent when
  # the dir is a generic name like ".venv".
  local name
  name="$(command sed -n 's/^[[:space:]]*prompt[[:space:]]*=[[:space:]]*//p' "$VIRTUAL_ENV/pyvenv.cfg" 2>/dev/null | command head -n1)"
  if [ -z "$name" ]; then
    name="${VIRTUAL_ENV##*/}"
    case "$name" in
      .venv|venv|.env|env) name="${VIRTUAL_ENV%/*}"; name="${name##*/}" ;;
    esac
  fi

  printf ' [venv: %s]' "$name"
}

# TODO: consider moving `__git_ps1` to `PROMPT_COMMAND`, because;
#         1. it's slightly faster,
#         2. you can use `GIT_PS1_SHOWCOLORHINTS` in this mode.
#       (Check out `git-prompt.sh` for more details.)
#
# original: `export PS1="\h:\W \u\$ "`
export PS1="\[\e[34m\]\w \[\e[31m\]\$(__git_ps1 \"(%s)\")\[\e[36m\]\$(__venv_ps1)\n\[\e[32m\]❯ \[\e[0m\]"

# Put two blank lines before each prompt (except the very first, to avoid a gap
# at the top of a fresh terminal) so command output has room to breathe.
#
# This is an *additive* PROMPT_COMMAND entry. The previous version ran
# `unset PROMPT_COMMAND` after the first prompt, which also wiped out every other
# prompt hook — direnv, nvm auto-use, shared history — since they all live in
# PROMPT_COMMAND too. Appending (and preserving any existing value) lets them
# coexist and keep firing on every prompt.
# (Ref.: https://stackoverflow.com/a/48915032/11895)
__prompt_blank_lines() {
  if [ -n "${__prompt_seen:-}" ]; then
    printf '\n\n'
  else
    __prompt_seen=1
  fi
}
PROMPT_COMMAND="__prompt_blank_lines${PROMPT_COMMAND:+; $PROMPT_COMMAND}"
