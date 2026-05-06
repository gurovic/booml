#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_SERVICE="backend"
POSTGRES_CONTAINER="booml-postgres"
DB_NAME="${DB_NAME:-booml}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
ROLE_NAME="${ROLE_NAME:-booml_user}"
ROLE_PASSWORD="${ROLE_PASSWORD:-booml_pass}"
DUMP_DIR_HOST="${ROOT_DIR}/data/db_dumps"
DEFAULT_DUMP_NAME="booml.dump"
DEFAULT_RESTORE_NAME="booml_prod.dump"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "docker compose not found" >&2
  exit 1
fi

usage() {
  cat <<'USAGE'
Usage: ./run.sh <command> [args]

Commands:
  dev                    Start all docker services
  migrate                Run Django migrations in backend container
  makemigrations         Create Django migrations in backend container
  test                   Run backend tests in backend container
  db-dump [name]         Create a DB dump from Postgres (default: booml.dump)
  db-restore [path|name] Restore DB from dump (default: data/db_dumps/booml_prod.dump)
USAGE
}

ensure_dump_dir() {
  mkdir -p "$DUMP_DIR_HOST"
}

backend_running() {
  local id
  id="$(${COMPOSE[@]} ps -q "$BACKEND_SERVICE" 2>/dev/null || true)"
  if [ -z "$id" ]; then
    return 1
  fi
  [ "$(docker inspect -f '{{.State.Running}}' "$id" 2>/dev/null || true)" = "true" ]
}

backend_exec() {
  if backend_running; then
    ${COMPOSE[@]} exec -T "$BACKEND_SERVICE" "$@"
  else
    ${COMPOSE[@]} run --rm "$BACKEND_SERVICE" "$@"
  fi
}

postgres_running() {
  local id
  id="$(docker ps -q -f "name=${POSTGRES_CONTAINER}" 2>/dev/null || true)"
  [ -n "$id" ]
}

ensure_postgres_running() {
  if postgres_running; then
    return 0
  fi
  echo "Postgres container '${POSTGRES_CONTAINER}' is not running." >&2
  echo "Run: ${COMPOSE[*]} up -d postgres" >&2
  exit 1
}

db_dump() {
  local name path
  name="${1:-$DEFAULT_DUMP_NAME}"
  ensure_dump_dir
  ensure_postgres_running
  if [[ "$name" == */* ]]; then
    path="$name"
  else
    path="$DUMP_DIR_HOST/$name"
  fi
  echo "[db-dump] Writing to $path"
  docker exec -i "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -F c -d "$DB_NAME" > "$path"
  echo "[db-dump] Done."
}

db_restore() {
  local name path
  name="${1:-$DEFAULT_RESTORE_NAME}"
  if [[ "$name" == */* ]]; then
    path="$name"
  else
    path="$DUMP_DIR_HOST/$name"
  fi
  if [ ! -f "$path" ]; then
    echo "Dump file not found: $path" >&2
    exit 1
  fi
  ensure_postgres_running
  echo "[db-restore] Restoring from $path"
  docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS ${DB_NAME};"
  docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c "CREATE DATABASE ${DB_NAME};"
  docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -c \
    "DO \$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${ROLE_NAME}') THEN CREATE ROLE ${ROLE_NAME} LOGIN PASSWORD '${ROLE_PASSWORD}'; END IF; END \$\$;"
  docker exec -i "$POSTGRES_CONTAINER" pg_restore -U "$POSTGRES_USER" -d "$DB_NAME" --no-owner < "$path"
  echo "[db-restore] Done."
}

command="${1:-}"
shift || true

case "$command" in
  dev)
    (cd "$ROOT_DIR/backend" && python3 docker/docker_build.py)
    ${COMPOSE[@]} up --build
    ;;
  migrate)
    backend_exec python manage.py migrate
    ;;
  makemigrations)
    backend_exec python manage.py makemigrations
    ;;
  test)
    backend_exec python manage.py test -v 2 --noinput
    ;;
  db-dump)
    db_dump "${1:-}"
    ;;
  db-restore)
    db_restore "${1:-}"
    ;;
  ""|help|-h|--help)
    usage
    ;;
  *)
    echo "Unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
