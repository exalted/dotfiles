#!/bin/sh
if [ -n "${POSTGRES_HOST:-}" ]; then
  export PGHOST="$POSTGRES_HOST"
  export PGPORT="${POSTGRES_PORT:-5432}"
  export PGUSER="${POSTGRES_USER:-}"
  export PGPASSWORD="${POSTGRES_PASSWORD:-}"
  export PGDATABASE="${POSTGRES_DB:-}"
elif [ -f local/docker-compose.yml ]; then
  # A session started outside direnv still gets the local stack's database.
  export PGHOST=localhost PGPORT=5432 PGUSER=cortex_db_user PGDATABASE=cortex_db
  PGPASSWORD="$(sed -n 's/^ *POSTGRES_PASSWORD: *//p' local/docker-compose.yml | head -n 1)"
  export PGPASSWORD
fi

server="${CLAUDE_PLUGIN_DATA:?}/node_modules/.bin/postgres-language-server"
[ -x "$server" ] || sh "$(dirname "$0")/hooks/install-node-modules.sh" >&2 || exit 1

exec "$server" lsp-proxy
