# Enable direnv for Bash — the cortex repo's .envrc relies on it to auto-activate
# the uv .venv and load .env on `cd`. No-ops if direnv isn't installed (cortex.rb
# warns in that case). No duplicate-guard needed here: `direnv hook bash`'s own
# generated snippet already checks PROMPT_COMMAND for `_direnv_hook` before
# PREPENDING itself (`PROMPT_COMMAND="_direnv_hook${PROMPT_COMMAND:+;...}"`).
# That prepend is why _direnv_hook still runs first even though this file is
# sourced after software/bash's hooks — and why the nvm hook in web-safety.bashrc
# must register with __prompt_command_append to stay behind it.
if command -v direnv >/dev/null 2>&1; then
  eval "$(direnv hook bash)"
fi
