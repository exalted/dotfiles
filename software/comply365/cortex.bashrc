# Enable direnv for Bash — the cortex repo's .envrc relies on it to auto-activate
# the uv .venv and load .env on `cd`. Guarded so we don't hook twice if direnv
# is somehow already wired into this shell (`direnv hook bash` defines
# `_direnv_hook` and appends itself to PROMPT_COMMAND).
if command -v direnv >/dev/null 2>&1 && ! declare -F _direnv_hook >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi
