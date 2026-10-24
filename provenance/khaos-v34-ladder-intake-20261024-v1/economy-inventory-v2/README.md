# Published 40-map static economy inventory (corrected v2)

Run `node inventory.mjs` from the repository root. The native map decoder yields canonical team-A storage. The script verifies the exact published40 map inventory hashes, then expands mirrored camps and cardinal camp groups with existing `Grid.allCamps()` and `Grid.groups()`. Centerline camps and self-mirrored groups are deduplicated. Group rewards use the existing group member sums. `SOURCE-PINS.json` records the parser, rules, and map-manifest hashes; `CROSSCHECK.md` checks three existing replay map extracts.

Counts and ordinary rewards cover the whole native map and include mirrors; ordinary totals exclude any group containing a monolith. They are not per-team accessible resources. Accessibility, vision, capture control, and weighted-selector eligibility are not inferred. Existing mapgen geometry summaries are included where available.

`economy-inventory-v1` is preserved as the original canonical-half attempt and is superseded by this corrected v2. Do not use v1 counts.
