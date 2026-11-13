#!/bin/sh
# Author the relief specimen and render the named review cameras.
# usage: scripts/relief_study.sh RESOLUTION SAMPLES camera[:flags]...
set -e
res=$1; samples=$2; shift 2
uv run python -m bake.style.relief_study --output data/relief-study --resolution "$res"
for view in "$@"; do
  camera=${view%%:*}; flags=""
  case "$view" in *:*) flags=$(echo "${view#*:}" | tr ':' ' ');; esac
  blender --background --python-exit-code 1 --python bake/style/blender_relief_study.py -- \
    --study data/relief-study --camera "$camera" --samples "$samples" $flags 2>&1 | grep -E "Saved|Error|Traceback" || true
done
