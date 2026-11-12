# Local validation

Captured on 12 November 2026. [Machine-readable results](validation.json) include
browser, GPU renderer, resolution, capture method and the presentation baseline.
**No physical target phone has been measured.**

## Checks

- **36 Python and 8 TypeScript tests pass.** TypeScript typechecking now includes
  tests. Regressions cover negative-clod water banks, native polygon membership
  during LOD bed lowering, confluence profiles, narrow lake shores, broad material
  placement independent of clods, camera-side lighting, queued/failed texture
  loads, resource cleanup and verified tool downloads, as well as earlier geometry,
  coordinate, availability, water-island, orbit and trace checks.
- **Production build passes.** Vite retains a large JavaScript chunk warning.
- **341 GLBs, 335 with water:** meshopt decode, Khronos glTF validation, local
  implicit availability and decoded bounds checks passed with zero errors or
  warnings. GLBs across all LODs total **66,513,336 bytes**. This is not the initial
  transfer size and is not complete OGC conformance certification.
- The separate real 12 km diagnostic tile loaded in PlayCanvas. Full-scene browser
  checks verify orbit, child LOD requests, four fixed views and no runtime errors
  or failed requests on the successful path.
- A deliberately blocked root material request produced the public Retry view
  action. Unblocking the request and clicking it restored the fully loaded scene;
  no developer commands appeared in the visitor message.

## Final production diagnostics

Both runs used **Apple M3 Pro / ANGLE Metal**, Chrome 152 in a visible, focused
Paradev pane. Phone viewport emulation uses the same desktop GPU.

| Measurement | Desktop | Phone viewport on desktop |
|---|---:|---:|
| Render resolution | 2560 × 1440 | 1170 × 2532 |
| Capture length | 60 s | 60 s |
| Average fps | 120.0 | 120.0 |
| p95 / frame distribution | See exact JSON | See exact JSON |
| Peak draw calls | 22 | 9 |
| Peak GPU allocation estimate | 81.36 MB | 70.85 MB |
| Empty-cache initial transfer | 3.37 MB | 3.37 MB |

First-view navigation has cache disabled. **Screencasting stops and normal caching
is restored before timing.** Still/video capture is separate. The trace automates
small orbits, pans and zooms after touring the fixed views; it is not a worst-case
coverage test. GPU figures include PlayCanvas allocations and an estimated default
framebuffer, excluding browser/driver overhead.

### Why these do not qualify a phone

Earlier captures used screencasting to keep a hidden embedded pane rendering and
reported about 84 fps. After removing it, an early foreground run was about 23 fps.
A same-pane control reached 120 fps on a blank rAF loop but only 20 fps clearing an
empty WebGL2 canvas. Later foreground scene runs consistently reached 120 fps
without screencasting, including the two final runs above. The host presentation
conditions affected measurements. All these raw records remain in ignored `data/`;
the control is preserved in [validation.json](validation.json).

This evidence supports functional streaming, transfer, allocation and draw-count
checks. It does **not** establish performance on iPhone 12, Snapdragon 7-series, or
an independent standalone-browser benchmark. Use the UI recorder on those targets.

## Reproduce

Keep the browser pane visible and focused. With a production preview running:

```sh
node scripts/check-browser.mjs WORKSPACE PANE data/evidence-review-final-desktop \
  http://localhost:20001 --views --clip --trace
node scripts/check-browser.mjs WORKSPACE PANE data/evidence-review-final-mobile \
  http://localhost:20001 --mobile --views --trace
uv run python scripts/create-review-evidence.py data/evidence-review-final-desktop
```

The local comparison is `data/evidence-review-final-desktop/index.html`. It pairs
fixed native-canvas captures with the source photograph and includes a water clip,
fixed-region colour means and luminance percentiles. No target-colour search is
used. The script forces repeatable viewport sizes; native canvas images avoid the
embedded host cropping phone screenshots. Source image pixels are never changed.

## Acceptance open

1. On each physical target phone: 60-second recorder at native resolution,
   representative navigation, cold-cache transfer, memory, touch and mixed-LOD checks.
2. S1–S7 visual judgement against the saved photograph, especially sculpted clod
   morphology, pitted granular faces, sparse detail and shoreline contact.
3. Watch the water clip for restrained shimmer and a matte painted read.

[Claude's review and verified corrections](claude-review.md) record the independent
review; functional tests do not constitute reference-fidelity sign-off.
