#!/bin/sh
# Relief style for one real-terrain tile, one command per stage. See docs/relief-process.md.
# usage: scripts/relief_pipeline.sh CONFIG NAME [stage...]     stages: source fetch author check render boards (default: all)
#   CONFIG  configs/<tile>.json (centre, size, DEM, hydrography, water names)
#   NAME    tile name; writes data/<NAME>-package (source; override with PACKAGE=) and data/<NAME> (surface and renders)
# Set GOOGLE=1 to also fetch Google satellite imagery and 3D Tiles terrain (needs the Doppler key).
set -e
config=$1; name=$2; shift 2; stages=${*:-source fetch author check render boards}
package=${PACKAGE:-data/$name-package}; out=data/$name; run=""
[ -n "$GOOGLE" ] && run="doppler run -p misc_projects -c dev --"
for stage in $stages; do
  case $stage in
    source) [ -f "$package/source/dem.npy" ] || uv run python -m bake.style --config "$config" --output "$package" ;;
    fetch)  $run uv run python -m bake.style.fields --package "$package" --output "$out/reference"
            [ -n "$GOOGLE" ] && $run uv run python -m bake.style.google_tiles --package "$package" --output "$out/reference" ;;
    author) uv run python -m bake.style.relief_patch --package "$package" --output "$out" --resolution "${RESOLUTION:-3200}" ;;
    check)  uv run python -m bake.style.source_check --package "$package" --output "$out" ;;
    render) for camera in overhead elevated creek; do
              blender --background --python-exit-code 1 --python bake/style/blender_relief_study.py -- \
                --study "$out" --camera $camera --samples "${SAMPLES:-96}" --sharp 2>&1 | grep -E "Saved|Error|Traceback" || true
            done ;;
    boards) uv run python scripts/relief_boards.py ;;
    *) echo "unknown stage $stage" >&2; exit 2 ;;
  esac
done
