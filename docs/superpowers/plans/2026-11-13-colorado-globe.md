# Colorado Crown Implementation Plan

> **For agentic workers:** Use executing-plans inline. Steps use checkbox syntax.

**Goal:** A geographically grounded rounded mud globe cap for Colorado plus 200 miles.
**Architecture:** Cache public USGS DEM and named hydrography, author a single surface with the existing relief material recipe, bend map coordinates onto a sphere, export portable GLB and source scene, provide a dedicated PlayCanvas preview.
**Tech Stack:** Python, rasterio, scipy, Blender, PlayCanvas.
**Spec:** docs/superpowers/specs/2026-11-13-colorado-globe.md

## Global Constraints
- No LOD tree; no pointed low-poly summits.
- Processing and source caches on external drive.
- Geographical data and authored exaggerations recorded separately.

## Review Focus
- Buffer must include diagonal corner buffers as well as border midpoints.
- Rio Grande must cross 37 N near -105.7 longitude.
- Arkansas must cross -102.05 near 38 N latitude.
- Winding and axes must survive portable import.
- Snow must follow source elevation, not sphere height.

### Task 1: Geographic surface
- [x] Add failing tests for cap coverage, orientation and geographic river crossings.
- [x] Fetch and cache USGS DEM and river lines with source hashes.
- [x] Implement projection, spherical bending and rounded exaggerated relief using existing mud recipe.
- [x] Run geographic tests and save review overlay.

### Task 2: Portable model and preview
- [x] Export GLB, editable Blender source, manifest, hero and overhead renders.
- [x] Add standalone preview and bake command; document use.
- [x] Run tests/build, inspect actual renders, verify GLB import.

## Execution evidence

- Geographic tests were run before implementation and failed on the absent module;
  summit-rounding regression failed before extracting the tested shaping function.
- Actual NHD reaches verify Rio Grande (-105.718800866, 37) and Arkansas
  (-102.05, 38.032389737) crossings. Source overlay inspected.
- Source hero and overhead rendered; an initial pointed-summit render led to
  separate broad/fine exaggeration. Final source and imported-GLB hero inspected.
- GLB validator: 0 errors, 0 warnings. Portable/source render mean absolute pixel
  difference 0.00125 on a 0..1 scale (different sample counts).
- Browser verified model HTTP 200, horizon/map views and state outline toggle.
- Fresh independent review found a link outside the standalone deployment;
  removed it. Also fixed the map-view to orbit pitch discontinuity.
- Tests: 65 Python, 8 Node passing. Standalone build includes GLB and manifest.

Ruling: use the approved in-chat visual brief and proceed instruction as the
implementation authorization; record it here rather than request another approval.
Ruling: circular coverage includes extra land beyond the minimum 200-mile buffer,
allowing the sphere to meet the ground continuously without cropping the buffer.
