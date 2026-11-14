#!/bin/sh
# Build the Colorado viewer; bundle its portable model unless a remote root is supplied.
set -eu
npx tsc --noEmit
npx vite build --config vite.colorado.config.ts
if [ -z "${VITE_COLORADO_ROOT:-}" ]; then
  node scripts/validate-colorado-glb.mjs data/colorado-globe
  mkdir -p dist-colorado/colorado-globe
  cp data/colorado-globe/colorado-crown.glb data/colorado-globe/colorado-crown-web.glb data/colorado-globe/manifest.json dist-colorado/colorado-globe/
fi
