# Shared helpers for the .paradev scripts. Sourced, not executed.

PARADEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$PARADEV_DIR/.." && pwd)"
WORKSPACE_ENV="$PARADEV_DIR/workspace.env"

# One shared registry for every repo on this machine, so blocks never overlap.
PORT_REGISTRY="${PARADEV_PORT_REGISTRY:-$HOME/.paradev/port-allocations.tsv}"

log() { printf '[paradev] %s\n' "$*"; }
warn() { printf '[paradev] warning: %s\n' "$*" >&2; }
die() { printf '[paradev] error: %s\n' "$*" >&2; exit 1; }

load_project_env() {
  DOPPLER_PROJECT="" DOPPLER_CONFIG="dev" PORT_NAMES="web"
  PORT_RANGE_START=20000 PORT_BLOCK_SIZE=10 PORT_BLOCK_COUNT=200
  INSTALL_CMD="" DEV_CMD=""
  # shellcheck source=/dev/null
  [ -f "$PARADEV_DIR/project.env" ] && . "$PARADEV_DIR/project.env"
  return 0
}

detect_package_manager() {
  local d="$WORKSPACE_DIR"
  if [ -f "$d/bun.lock" ] || [ -f "$d/bun.lockb" ]; then echo bun
  elif [ -f "$d/pnpm-lock.yaml" ]; then echo pnpm
  elif [ -f "$d/yarn.lock" ]; then echo yarn
  elif [ -f "$d/package-lock.json" ] || [ -f "$d/package.json" ]; then echo npm
  elif [ -f "$d/uv.lock" ]; then echo uv
  elif [ -f "$d/Cargo.toml" ]; then echo cargo
  fi
}

default_install_cmd() {
  case "$(detect_package_manager)" in
    bun) echo "bun install --frozen-lockfile" ;;
    pnpm) echo "pnpm install --frozen-lockfile" ;;
    yarn) echo "yarn install --immutable" ;;
    npm) if [ -f "$WORKSPACE_DIR/package-lock.json" ]; then echo "npm ci"; else echo "npm install"; fi ;;
    uv) echo "uv sync --frozen" ;;
    cargo) echo "cargo fetch" ;;
  esac
}

default_dev_cmd() {
  case "$(detect_package_manager)" in
    bun|pnpm|yarn|npm) echo "$(detect_package_manager) run dev" ;;
  esac
}

# Prints "KEY=value" lines from workspace.env, for `env`.
workspace_env_args() {
  [ -f "$WORKSPACE_ENV" ] || die "no $WORKSPACE_ENV; run ./.paradev/setup.sh first"
  grep -E '^[A-Z_][A-Z0-9_]*=' "$WORKSPACE_ENV"
}

# --- port registry: one "base<TAB>workspace path" line per block -------------

registry_lock() {
  mkdir -p "$(dirname "$PORT_REGISTRY")"
  local lock="$PORT_REGISTRY.lock" tries=0
  until mkdir "$lock" 2>/dev/null; do
    tries=$((tries + 1))
    # A lock older than a minute belongs to a script that died.
    if [ "$tries" -gt 100 ] || [ -n "$(find "$lock" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then
      rmdir "$lock" 2>/dev/null || true
    fi
    sleep 0.1
  done
  trap 'rmdir "$PORT_REGISTRY.lock" 2>/dev/null || true' EXIT
}

registry_unlock() {
  rmdir "$PORT_REGISTRY.lock" 2>/dev/null || true
  trap - EXIT
}

port_listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# Echoes this workspace's block base, reserving one if needed.
allocate_port_block() {
  local key="$WORKSPACE_DIR" base path line kept="" taken=" " count n i
  count=$(echo "$PORT_NAMES" | wc -w | tr -d ' ')
  [ "$count" -le "$PORT_BLOCK_SIZE" ] || die "PORT_NAMES has more names than PORT_BLOCK_SIZE"

  registry_lock
  touch "$PORT_REGISTRY"
  while IFS="$(printf '\t')" read -r base path; do
    [ -n "$base" ] || continue
    if [ "$path" = "$key" ]; then
      registry_unlock; echo "$base"; return 0
    fi
    # Drop blocks whose worktree is gone (teardown never ran).
    if [ -d "$path" ]; then
      kept="$kept$base	$path
"
      taken="$taken$base "
    fi
  done < "$PORT_REGISTRY"

  for n in $(seq 0 $((PORT_BLOCK_COUNT - 1))); do
    base=$((PORT_RANGE_START + n * PORT_BLOCK_SIZE))
    case "$taken" in *" $base "*) continue ;; esac
    line=ok
    for i in $(seq 0 $((count - 1))); do
      if port_listening $((base + i)); then line=busy; break; fi
    done
    [ "$line" = ok ] || continue
    printf '%s%s\t%s\n' "$kept" "$base" "$key" > "$PORT_REGISTRY.tmp"
    mv "$PORT_REGISTRY.tmp" "$PORT_REGISTRY"
    registry_unlock; echo "$base"; return 0
  done
  registry_unlock
  die "no free port block in $PORT_RANGE_START+ ($PORT_BLOCK_COUNT blocks of $PORT_BLOCK_SIZE)"
}

release_port_block() {
  local key="$WORKSPACE_DIR" base path
  [ -f "$PORT_REGISTRY" ] || return 0
  registry_lock
  while IFS="$(printf '\t')" read -r base path; do
    if [ -n "$base" ] && [ "$path" != "$key" ]; then printf '%s\t%s\n' "$base" "$path"; fi
  done < "$PORT_REGISTRY" > "$PORT_REGISTRY.tmp"
  mv "$PORT_REGISTRY.tmp" "$PORT_REGISTRY"
  registry_unlock
}

doppler_enabled() { [ -n "$DOPPLER_PROJECT" ]; }

doppler_reachable() {
  command -v doppler >/dev/null 2>&1 &&
    doppler secrets --project "$DOPPLER_PROJECT" --config "$DOPPLER_CONFIG" --only-names >/dev/null 2>&1
}
