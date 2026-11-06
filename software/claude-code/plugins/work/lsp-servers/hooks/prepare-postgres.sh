#!/bin/sh
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || exit 0

# The hook runs repository code (the migrator, the compose file), so each clone opts in with a
# marker under .git/, which no repository can ship: touch "$(git rev-parse --git-path lsp-servers-postgres)"
[ -f "$(git rev-parse --git-path lsp-servers-postgres 2>/dev/null)" ] || exit 0

# Before the snapshot import, applying every migration would break the local setup.
[ -f .local/setup-complete ] && [ -d database/migrations ] && [ -x database/migrator/migrator ] || exit 0

docker info >/dev/null 2>&1 || exit 0
docker compose --file local/docker-compose.yml up --detach --wait postgres >/dev/null 2>&1 || exit 0

POSTGRES_HOST=localhost \
POSTGRES_PORT=5432 \
POSTGRES_DB=cortex_db \
POSTGRES_USER=cortex_db_user \
POSTGRES_PASSWORD="$(sed -n 's/^ *POSTGRES_PASSWORD: *//p' local/docker-compose.yml | head -n 1)" \
  ./database/migrator/migrator database/migrations >/dev/null 2>&1

# The merge base, not the database: the branch's own new migrations must stay linted.
base="$(git merge-base HEAD origin/main 2>/dev/null)" || exit 0
after="$(git ls-tree --name-only "$base" database/migrations/ | sed -E 's|.*/||; s/_.*//' | sort -n | tail -n 1)"
[ -n "$after" ] || exit 0

printf '{"migrations":{"migrationsDir":"database/migrations","after":%s}}\n' "$after" > postgres-language-server.jsonc

exclude="$(git rev-parse --git-path info/exclude)"
grep -qxF postgres-language-server.jsonc "$exclude" 2>/dev/null || echo postgres-language-server.jsonc >> "$exclude"
