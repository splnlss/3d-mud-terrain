# 07 — Keep agricultural patterns as tonal variation

## Goal

The valley floor shows restrained pivot circles and field boundaries, with no mapped roads or buildings visible.

## Scope

- **Bake:** ingest NAIP/Sentinel-2, derive and regrade a tonal/wetness mask into the reference palette; remove road/building cues while preserving pivot and field tone.
- **Tiles:** pack the tonal channel into each affected ~256² KTX2 tile mask and rebuild/validate tile assets.
- **Viewer:** apply that channel through the mud material and wetness control across streamed LODs.

## Acceptance criteria

- Fixed Alamosa/valley-floor screenshots show recognisable pivot circles and field edges only as tonal or wetness changes, without photographic imagery, road lines, or building shapes.
- The result retains **S2, S3, S7**: crust/granular placement and dust still dominate, and satellite signal stays within the muted model palette.
- The browser shows no mask pop or misregistration at tile and LOD seams.
- Bake manifest records source imagery and confirms no Google-derived asset entered the output.

## Blocked by

04, 02.

## Notes

This ticket may run after 06 in the main sequence, but its data path depends on the material mask, not water shimmer.

## Status

**Implemented; pivot legibility remains open.** The bake uses cloud-filtered Sentinel-2 reflectance for muted NDVI tone, blurs narrow mapped cues, and records scene IDs, dates and URLs in `manifest.json`. No Google-derived data enters the bake or runtime. [07-valley-fields.jpg](../evidence/07-valley-fields.jpg) is the fixed valley view. Distinct pivot circles and field boundaries are weak in that capture, so this acceptance criterion is not yet met visually. A full seam/misregistration inspection remains unverified.
