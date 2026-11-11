#!/usr/bin/env bash
# Usage: ./.paradev/with-secrets.sh <command> [args...]
# Runs a command with this workspace's ports and, if configured, Doppler secrets.
# Workspace ports are applied last, so a PORT secret in Doppler cannot override them.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
load_project_env
[ "$#" -gt 0 ] || die "usage: $0 <command> [args...]"

env_lines="$(workspace_env_args)"
# shellcheck disable=SC2206 # KEY=number lines, no spaces
env_args=($env_lines)

if doppler_enabled; then
  command -v doppler >/dev/null 2>&1 || die "doppler CLI not found"
  exec doppler run --project "$DOPPLER_PROJECT" --config "$DOPPLER_CONFIG" -- env "${env_args[@]}" "$@"
fi
exec env "${env_args[@]}" "$@"
