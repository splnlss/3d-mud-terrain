# 09 — Frame the diorama and finish its edge

## Goal

Visitors stay in a close oblique model view; the square terrain fades into a sculpted mud edge rather than ending as a hard map cut.

## Scope

- **Bake:** apply stylised edge falloff to outer terrain tiles and recalculate geometry, skirts, and bounds.
- **Tiles:** publish the rebuilt edge GLBs and validate the quadtree border at every LOD.
- **Viewer:** clamp tilt/zoom, bound pan to the extent, set the default fixed camera, and optionally add desktop-only tilt-shift blur.

## Acceptance criteria

- At all orbit limits, the camera remains oblique with no horizon or ground-level view; pan cannot leave the diorama and zoom cannot clip through terrain.
- A fixed edge screenshot shows a continuous sculpted falloff with no square-wall cut, cracks, or streaming gaps.
- Default mountain and water screenshots still satisfy **S1, S4, S6** under the final camera and lighting.
- On mobile, optional blur is disabled and the same camera bounds work by touch.

## Blocked by

02, 03, 05.

## Notes

Keep controls minimal. Camera constraints are part of the intended photographic style, not an added exploration mode.

## Status

**Implemented; physical touch check remains open.** Orbit unit tests cover tilt, zoom, pan, portrait framing and repeated touch/wheel input; the saved browser smoke log records an orbit change. [09-overview.jpg](../evidence/09-overview.jpg) shows the fixed oblique composition and outer falloff. The edge and every LOD border have not been visually inspected at all orbit limits, and no physical phone gesture check is available. S1/S4 style limitations remain as recorded in tickets 03–06.
