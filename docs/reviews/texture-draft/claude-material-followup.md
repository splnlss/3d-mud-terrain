**Verdict: the material pass improved.** Shadows now have fill, the plastic sheen is gone from dry crust, exposed clay no longer shows noisy grain, and the water reads as muted opaque silt with a modest glancing sheen. The overall tone is closer to the reference's grey-ochre, though the render still skews warmer and more orange than the canyon study.

**Completed material changes (confirmed in the render and in `material_refinement.py`):**
- Ambient fill raised, exposure fixed, roughness remapped to a matte dry range.
- Shore band at constant mid roughness, wetness-driven.
- Fine pore bump reduced and suppressed on exposed clay via the style field.
- Water base colour muted to taupe, roughness lowered only slightly.

**Two biggest remaining visual gaps:**

1. **Value and hue separation (material, remaining).** The reference splits into pale beige-grey silt matrix and distinctly dark, cool grey nodular crust, with warm ochre only on lit ridge tops. The render's aggregate is the same brown as the matrix, just darkened. The channel is also the lightest element in the reference, but in the render it sits darker than the shore rim, inverting that relationship. A cooler, darker aggregate albedo and a paler silt tone would address this without changing the water interpretation.

2. **Landform language (geometry and art direction, not material).** The render reads as uniform conical peaks with evenly sprinkled pebble clumps. The reference has layered, slumped flanks with vertical flow striations and runnels, crust massed on upper slopes, and a flat cracked silt bench beside the channel. Lighting is also flat and overcast where the reference uses low warm backlight with atmospheric depth.
