#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_SERVICE="backend"
POSTGRES_CONTAINER="booml-postgres"
DEFAULT_DUMP_NAME="booml.dump"

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
  dev                Start all docker services
  migrate            Run Django migrations in backend container
  makemigrations     Create Django migrations in backend container
  test               Run backend tests in backend container
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

command="${1:-}"
shift || true

case "$command" in
  dev)
    ${COMPOSE[@]} up --build
    ;;
  migrate)
    backend_exec python manage.py migrate
    ;;
  makemigrations)
    backend_exec python manage.py makemigrations
    ;;
  test)
    backend_exec python manage.py test -v 2  --noinput
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
