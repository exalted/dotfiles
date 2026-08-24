#!/usr/bin/env bash
# Prints the major version of the first `bash` on PATH after the repo's Homebrew
# shellenv has run. Its own interpreter is irrelevant — what matters is which
# bash a `#!/usr/bin/env bash` shebang would find. Kept as a file so the hook
# doesn't have to nest quotes inside `env -i ... bash -c '...'`.
cd "${1:?repo root required}" || exit 1
. software/homebrew/shellenv.sh
b="$(command -v bash)" || exit 1
exec "$b" -c 'printf %s "${BASH_VERSINFO[0]}"'
