#!/bin/sh
# A venv that the repository tracks could ship its own "pyright", so only an untracked one is used.
for venv in .venv venv; do
  [ -x "$venv/bin/python" ] || continue
  [ -z "$(git ls-files -- "$venv" 2>/dev/null | head -n 1)" ] || continue
  VIRTUAL_ENV="$PWD/$venv"
  export VIRTUAL_ENV
  PATH="$VIRTUAL_ENV/bin:$PATH"
  export PATH
  break
done

exec pyright-langserver --stdio
