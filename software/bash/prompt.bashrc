# (Ref.: https://support.apple.com/en-us/HT208050)
export BASH_SILENCE_DEPRECATION_WARNING=1

# We render our own "[venv: NAME]" segment (see PS1 below), so suppress the
# default "(NAME)" prefix that `source .venv/bin/activate` would prepend to PS1.
# (direnv's `layout python3` activates the venv via VIRTUAL_ENV + PATH but never
# touches PS1, so without this segment an active venv would be invisible.)
export VIRTUAL_ENV_DISABLE_PROMPT=1

__venv_ps1_resolve() {
  local name=''

  # Prefer the venv's configured prompt name. `{…;q;}` stops at the first match,
  # so this is one fork instead of `sed | head`.
  if [ -r "$VIRTUAL_ENV/pyvenv.cfg" ]; then
    name="$(command sed -n '/^[[:space:]]*prompt[[:space:]]*=/{ s/^[^=]*=[[:space:]]*//; p; q; }' "$VIRTUAL_ENV/pyvenv.cfg")"
  fi

  # Drop trailing whitespace — notably the CR of a CRLF pyvenv.cfg, which would
  # otherwise be printed into PS1 and park the cursor at column 0.
  name="${name%"${name##*[![:space:]]}"}"

  # CPython's stdlib venv writes the value quoted (`prompt = 'name'`); uv writes
  # it bare. Without this, a stdlib venv renders as [venv: 'name'].
  case "$name" in
    \'*\'|\"*\") name="${name:1:${#name}-2}" ;;
  esac

  # No usable name: fall back to the venv dir, then its parent when the dir is a
  # generic name like ".venv".
  if [ -z "$name" ]; then
    name="${VIRTUAL_ENV##*/}"
    case "$name" in
      .venv|venv|.env|env) name="${VIRTUAL_ENV%/*}"; name="${name##*/}" ;;
    esac
  fi

  __venv_ps1_name="$name"
  __venv_ps1_resolved_for="$VIRTUAL_ENV"
}

# $VIRTUAL_ENV is the whole cache key: pyvenv.cfg is written once, when the venv
# is created, so the name can only change when the venv itself does. Without the
# cache the prompt re-parsed an immutable file on every keystroke-to-prompt
# cycle, on top of whatever __git_ps1 costs.
__venv_ps1_update() {
  [ -n "${VIRTUAL_ENV:-}" ] || return 0
  [ "$VIRTUAL_ENV" = "${__venv_ps1_resolved_for:-}" ] || __venv_ps1_resolve
}

__venv_ps1() {
  [ -n "${VIRTUAL_ENV:-}" ] || return 0

  # Priming the cache from here alone would never work: PS1 calls this through
  # `$(…)`, which Bash runs in a forked subshell, so the assignments die with
  # that subshell and the parse repeats on every prompt. Hence the PROMPT_COMMAND
  # registration below — this call is only the fallback for the prompt where the
  # hook hasn't run yet (a venv activated by direnv earlier in the same cycle).
  __venv_ps1_update

  printf ' [venv: %s]' "$__venv_ps1_name"
}

# Appended, so it runs after direnv's hook: `layout python3` is what sets
# VIRTUAL_ENV in the first place.
__prompt_command_append __venv_ps1_update

# TODO: consider moving `__git_ps1` to `PROMPT_COMMAND`, because;
#         1. it's slightly faster,
#         2. you can use `GIT_PS1_SHOWCOLORHINTS` in this mode.
#       (Check out `git-prompt.sh` for more details.)
#
# original: `export PS1="\h:\W \u\$ "`
#
# One prompt, set once, identical in every terminal — no per-terminal branching
# and no PROMPT_COMMAND rebuild.
#
# There used to be both, to work around `❯` arriving garbled in IntelliJ's
# terminal. Two theories drove that and both were wrong: that the literal `\n`
# below was the trigger, and that IntelliJ sets TERMINAL_EMULATOR too late to
# branch on. The actual cause was software/iterm2/'s shell integration being
# loaded in IntelliJ's terminal by a guard that excluded only Zed; it `export`s a
# PS1 wrapped in OSC 133 markers, and that came back byte-corrupted (`❯`, E2 9D
# AF, read as Latin-1 and re-encoded). Fixed where it belongs — see
# software/iterm2/bashrc — after which `❯` renders correctly in all three
# terminals with this plain assignment.
#
# So: do not reintroduce a rebuild here. It costs a prompt hook and silently
# reverts anything else that decorates PS1 (`conda activate`, an ad-hoc `PS1=`)
# one prompt later.
PS1="\[\e[34m\]\w \[\e[31m\]\$(__git_ps1 \"(%s)\")\[\e[36m\]\$(__venv_ps1)\n\[\e[32m\]❯ \[\e[0m\]"

# Put two blank lines before each prompt (except the very first, to avoid a gap
# at the top of a fresh terminal) so command output has room to breathe.
#
# This is an *additive* PROMPT_COMMAND entry. The previous version ran
# `unset PROMPT_COMMAND` after the first prompt, which also wiped out every other
# prompt hook — direnv, nvm auto-use, shared history — since they all live in
# PROMPT_COMMAND too. Registering alongside them (see prompt-command.bashrc) lets
# them coexist and keep firing on every prompt.
# (Ref.: https://stackoverflow.com/a/48915032/11895)
__prompt_blank_lines() {
  if [ -n "${__prompt_seen:-}" ]; then
    printf '\n\n'
  else
    __prompt_seen=1
  fi
}
__prompt_command_prepend __prompt_blank_lines
