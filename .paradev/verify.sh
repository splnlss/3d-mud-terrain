#!/usr/bin/env bash
# Usage: ./.paradev/verify.sh [--paradev]
# 1. Dry run: two throwaway worktrees from HEAD run setup in parallel, must get
#    different ports, then teardown must release both blocks.
# 2. --paradev: also create a real Paradev workspace from the current branch.
set -euo pipefail
. "$(dirname "$0")/lib.sh"
cd "$WORKSPACE_DIR"

git cat-file -e HEAD:.paradev/setup.sh 2>/dev/null ||
  die ".paradev/ is not committed; workspaces check out committed files, so commit first"

main_checkout="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
tmp="$(mktemp -d)"
cleanup() {
  for w in "$tmp"/a "$tmp"/b; do
    [ -d "$w" ] && git worktree remove --force "$w" 2>/dev/null
  done
  rm -rf "$tmp"
}
trap cleanup EXIT

run_setup() {
  git worktree add --quiet --detach "$tmp/$1" HEAD
  (cd "$tmp/$1" && SUPERSET_ROOT_PATH="$main_checkout" SUPERSET_WORKSPACE_NAME="verify-$1" \
    SUPERSET_WORKSPACE_PATH="$tmp/$1" ./.paradev/setup.sh) > "$tmp/$1.log" 2>&1
}

log "dry run: setup in two worktrees at once"
run_setup a & pa=$!
run_setup b & pb=$!
ok=1
wait "$pa" || { warn "setup a failed:"; cat "$tmp/a.log" >&2; ok=0; }
wait "$pb" || { warn "setup b failed:"; cat "$tmp/b.log" >&2; ok=0; }
[ "$ok" = 1 ] || die "setup failed"

port_a="$(grep '^PORT=' "$tmp/a/.paradev/workspace.env" | cut -d= -f2)"
port_b="$(grep '^PORT=' "$tmp/b/.paradev/workspace.env" | cut -d= -f2)"
[ -n "$port_a" ] && [ -n "$port_b" ] && [ "$port_a" != "$port_b" ] ||
  die "port collision: a=$port_a b=$port_b"
log "ports isolated: a=$port_a b=$port_b"

for w in a b; do (cd "$tmp/$w" && ./.paradev/teardown.sh) >> "$tmp/$w.log" 2>&1; done
if grep -q -F "$tmp/" "$PORT_REGISTRY" 2>/dev/null; then die "teardown left blocks in $PORT_REGISTRY"; fi
log "teardown released both blocks"

[ "${1:-}" = "--paradev" ] || { log "dry run passed. Re-run with --paradev to test a real workspace."; exit 0; }

command -v superset >/dev/null 2>&1 || die "superset CLI not found"
project_id="$(superset projects list --json | jq -r --arg p "$main_checkout" '.[] | select(.path == $p) | .id' | head -1)"
[ -n "$project_id" ] || die "no Paradev project at $main_checkout; add the repo in Paradev first"
branch="$(git branch --show-current)"
[ -n "$branch" ] || die "detached HEAD; check out the branch to test"

ws="$(superset workspaces create --local --project "$project_id" --name paradev-setup-test \
  --branch paradev-setup-test --skip-branch-prefix --base-branch "$branch" --quiet)"
log "created workspace $ws from $branch"
log "watch its 'Workspace Setup' terminal until it finishes cleanly, then clean up:"
log "  superset workspaces archive --local $ws && git branch -D paradev-setup-test"
