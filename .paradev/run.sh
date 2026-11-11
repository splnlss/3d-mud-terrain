#!/usr/bin/env bash
# The Run button. DEV_CMD sees $PORT, $PORT_<NAME> and Doppler secrets.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_project_env
cd "$WORKSPACE_DIR"

dev_cmd="${DEV_CMD:-$(default_dev_cmd)}"
[ -n "$dev_cmd" ] || die "set DEV_CMD in .paradev/project.env"
log "run: $dev_cmd"
exec "$PARADEV_DIR/with-secrets.sh" sh -c "$dev_cmd"
