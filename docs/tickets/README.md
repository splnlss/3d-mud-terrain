# Vertical-slice task index

Each ticket ends with a visible browser result and touches bake inputs, 3D Tiles output, and viewer behaviour. Execute in numerical order unless dependencies permit parallel work. Do not start a horizontal-only infrastructure ticket.

| Order | Slice | Blocked by | Browser result |
|---|---|---|---|
| 01 | [First terrain tile](01-first-terrain-tile.md) | — | One flat-shaded San Luis DEM tile renders. |
| 02 | [Full extent and LOD](02-full-extent-lod.md) | 01 | Entire valley streams with seamless LOD. |
| 03 | [Remapped clod relief](03-remapped-clod-relief.md) | 02 | Rounded ridges and stronger low relief. |
| 04 | [Crust, granular, dust](04-crust-granular-dust.md) | 03 | Two-tone aged model material. |
| 05 | [Painted water extent](05-painted-water-extent.md) | 03, 04 | Flat rivers, reservoir, and acequias. |
| 06 | [Subtle water shimmer](06-subtle-water-shimmer.md) | 05 | Matte water with faint motion. |
| 07 | [Satellite tonal mask](07-satellite-tonal-mask.md) | 02, 04 | Pivots and fields as muted tone. |
| 08 | [Sparse model detail](08-sparse-model-detail.md) | 04, 07 | Tiny flecks and pale strands. |
| 09 | [Camera and diorama edge](09-camera-and-diorama-edge.md) | 02, 03, 05 | Bounded oblique view and sculpted edge. |
| 10 | [Mobile performance](10-mobile-performance-pass.md) | 06, 07, 08, 09 | Smooth, budget-compliant mobile scene. |
| 11 | [Reference fidelity sign-off](11-reference-fidelity-signoff.md) | 10 | Reviewed style match and final scene. |

```mermaid
flowchart LR
  T01[01 First tile] --> T02[02 Extent + LOD]
  T02 --> T03[03 Relief]
  T03 --> T04[04 Material]
  T03 --> T05[05 Water extent]
  T04 --> T05
  T05 --> T06[06 Shimmer]
  T02 --> T07[07 Tonal mask]
  T04 --> T07
  T04 --> T08[08 Micro-detail]
  T07 --> T08
  T02 --> T09[09 Camera + edge]
  T03 --> T09
  T05 --> T09
  T06 --> T10[10 Performance]
  T07 --> T10
  T08 --> T10
  T09 --> T10
  T10 --> T11[11 Fidelity]
```
