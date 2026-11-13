#!/bin/sh
# Build the relief preview as a static site in dist-relief/, reading tile sets from VITE_RELIEF_ROOT.
# usage: VITE_RELIEF_ROOT=https://<public-host>/05_3D-tiles scripts/build-relief-site.sh
# Optional VITE_GOOGLE_MAPS_KEY adds the Google 3D Tiles view; the key is then visible in the page, so restrict it
# to the site's address in the Google Cloud console.
set -e
[ -n "$VITE_RELIEF_ROOT" ] || { echo "VITE_RELIEF_ROOT is required" >&2; exit 2; }
npx tsc --noEmit
npx vite build --config vite.relief.config.ts
mkdir -p dist-relief/wasm/basis
cp public/wasm/basis/basis.js public/wasm/basis/basis.wasm.js public/wasm/basis/basis.wasm.wasm dist-relief/wasm/basis/
if [ -n "$VITE_GOOGLE_MAPS_KEY" ]; then mkdir -p dist-relief/wasm/draco; cp public/wasm/draco/draco.wasm.js public/wasm/draco/draco.wasm.wasm dist-relief/wasm/draco/; fi
cp dist-relief/relief.html dist-relief/index.html
