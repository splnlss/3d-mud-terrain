#!/usr/bin/env bash
# Runs when Paradev deletes a workspace. Cleans up outside resources only.
set -uo pipefail
. "$(dirname "$0")/lib.sh"
load_project_env
cd "$WORKSPACE_DIR"

# Containers are namespaced by COMPOSE_PROJECT_NAME, so this only touches this workspace's.
if command -v docker >/dev/null 2>&1 && [ -f "$WORKSPACE_ENV" ] &&
  ls compose.y*ml docker-compose.y*ml >/dev/null 2>&1; then
  log "docker compose down"
  env $(workspace_env_args) docker compose down -v --remove-orphans || warn "docker compose down failed"
fi

release_port_block
log "released port block"
