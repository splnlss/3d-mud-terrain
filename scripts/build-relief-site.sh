#!/bin/sh
# Build the relief preview as a static site in dist-relief/, reading tiles from VITE_RELIEF_BASE.
# usage: VITE_RELIEF_BASE=https://<public-host>/05_3D-tiles/san-luis-relief-sample scripts/build-relief-site.sh
set -e
[ -n "$VITE_RELIEF_BASE" ] || { echo "VITE_RELIEF_BASE is required" >&2; exit 2; }
npx tsc --noEmit
npx vite build --config vite.relief.config.ts
mkdir -p dist-relief/wasm/basis
cp public/wasm/basis/basis.js public/wasm/basis/basis.wasm.js public/wasm/basis/basis.wasm.wasm dist-relief/wasm/basis/
cp dist-relief/relief.html dist-relief/index.html
