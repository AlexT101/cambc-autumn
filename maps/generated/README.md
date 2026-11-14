# Generated map suites

Four suites from [tools/mapgen](../../tools/mapgen/), seed 2026, one per mix. Each folder's `index.json` records every map's family, preset or mutation, spec and metrics.

| folder | maps | mix |
|---|---|---|
| `ladder-v4/` | 340 | nearest the ladder: `ladder-v2` plus maps in the style of the `05*` ladder maps and the full-pool fit |
| `ladder-v2/` | 256 | calibration 3: ladder-like presets and mutated ladder maps |
| `paradigms/` | 256 | 12 layouts the ladder mixes don't draw (ring roads, isles, corridors, ...) |
| `varied/` | 256 | the stress plan: designed, exotic and quirk maps, reweighed per seed |

Remake one with `node tools/mapgen/mapgen.mjs suite --mix MIX --seed 2026 --out maps/generated/MIX`. Mutated maps draw their source from the ladder maps in `maps/`, so they come out the same only while `maps/` holds the same ladder maps. Play one with `cambc run --map maps/generated/MIX/FILE.map26a`, or a whole suite with `py tools/ab.py CAND REF --suites maps/generated/MIX`.
