#!/bin/sh
for venv in .venv venv; do
  if [ -x "$venv/bin/python" ]; then
    VIRTUAL_ENV="$PWD/$venv"
    export VIRTUAL_ENV
    PATH="$VIRTUAL_ENV/bin:$PATH"
    export PATH
    break
  fi
done

exec pyright-langserver --stdio
