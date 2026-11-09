# Per-map hardcoding audit (2026-11-09)

The user asked for no per-map hardcoding. The bar: does a rule carry over to fresh maps drawn from the ladder's
distribution? Lookups by identity (map name, hash, per-map table) fail it. Rules on map features, and models fitted
on ladder maps that take features as inputs, pass it. Out-of-distribution robustness is out of scope.

Audited: `bots/variants/oc32s-bsk` (v103), `bots/variants/oc-base25` (v87), `bots/ocean` (read only), and the dgate
opponent bodies (`spar-*-F/M/Fl/Mt3`, built by `research/ideas-2026-11-08/{spar,diverse}-tools` and
`research/ideas-2026-11-09/oppfidelity-tools`).

## Verdict

**None of the three bots looks anything up by map identity.** They have no map names, no ladder-map tables, no
per-map plans and no compiled-in map data (`src/` holds only `.cc`/`.h`, with no data files). Every map-dependent
choice is computed from the map at draft or play time, or comes from a model fitted on ladder maps with map features
as its inputs. The bots play an unseen map exactly as they play a ladder map.

**The opponent bodies do look up picks by ladder map.** On fresh maps they fall back to their own draft (below).

## Items checked (all three bots; line numbers are oc32s-bsk's, then oc-base25 / ocean)

| What | Where | Keys on | Unseen map | Verdict |
|---|---|---|---|---|
| `test_compositions::map_hash()` + `choose()` | draft/draft.cc:1274, 1288 (1198 / 1221) | A hash of the terrain, spawns, camps and our team | Only with `params::test_draft` on, which is off in every bot dir (params.h:47). There it seeds a weighted draw from 16 ladder-frequency compositions per pick count | Pass. The hash is a seed, not a lookup: any map gets a draw from the same distribution. No effect on own-draft play |
| `plan_check()` | draft/draft.cc:1151 (1075 / 1098); checked in model/world.cc:1649, draft.cc:1826 | Hash of width, height, group count, first spawn tile | Integrity check that the draft memory belongs to this map; on a mismatch facts are re-measured (local builds resign) | Pass (not a lookup) |
| F92 draft model (draft7) | draft/draft_model.h (generated), used by map_features.cc model_team | 92 map features (area, reach, altars, gems, ...; no symmetry or identity feature) plus pick count; the ladder prior `q` is per champion, unused (`counters = false`) | Evaluates the features of whatever map it is given | Pass (fitted on ladder maps, features as inputs) |
| Fallback draft tables `draft_three/four/five`, Tavi rule | params.h:27-38; draft.cc:1309 `choose_table_draft` | Pick count; `map_economy().tavi_map()` (pure-gold groups, gold, steps from spawn) | Computed from the map | Pass |
| `condition_on_map` / `model::condition` | draft.cc:1820, 1520 (1725 / 1748) | Linear in z-scores of area, spawn distance, altars, gems, big-group share, and a vertical-symmetry indicator (oc5's SPSA slopes, 0.25 shrink) | Features measured from the map | Pass (symmetry is read from the map, not from a table) |
| Opening plan (draftfarm, `params::open_plan`; oc32s-bsk only) | draft/open_plan.cc, draft.cc:748 `make_open_plan` | The map's groups, walks and our expected team, solved in the draft's first turn | Solved fresh on any map | Pass |
| `MapEconomy` (Prospector/Tavi/Stellar maps) | draft/map_economy.h | Group supply weighted by distance | Computed | Pass |
| Learned emblems `learned_arm` | economy/emblem_table.h | Pick count x champion x emblem ordinal | Not map-dependent | Pass |
| Map names in source | fight.cc:1156/1176 (`03homonoliths-a`), world.h:179 (`02the-pack`), world.cc:628 (`01islands`), ocean altar_guard.cc:13 | Comments only (examples of a situation) | None | Pass |
| Exact size or count branches (`width == N` etc.) | none found; the bsk-vs-v87 diff adds none | | | Pass |

The bsk diff itself (bsk's gain was concentrated on 00expanse/00quadrants in commit e49e7b604) is an analysis
finding. The code keys on situations, not maps.

Size on the ladder: zero. Nothing in the bots fires on a recognised map, so their ladder results carry over to
fresh maps from the same distribution as far as hardcoding is concerned.

## Opponent bodies (dgate): ladder-map pick tables

- `research/ideas-2026-11-08/spar-tools/patch_spar.py` patches `draft.cc` with `spar_forced()`. It looks up
  `test_compositions::map_hash()` (map and side) in `src/draft/spar_draft.h`, and on a hit plays live Fish's or
  Mite's exact picks for that ladder map and side, with the team lock off and Vesper allowed.
- `gen_table.py` writes `spar_draft.h` from `spar-tools/hashes.json`: 256 keys, the 128 ladder maps by 2 sides, from
  live drafts (`live.py`). Every `-F`, `-M`, `-Fl` and `-Mt3` body carries the full table: 256 entries in spar-o25,
  spar-oc29, spar-dvnK and spar-s88nK; `-Fl`/`-Mt3` are copies of `-F`/`-M` (oppfidelity-tools/newbodies.sh).
- **On an unseen map the hash misses**, so `spar_forced()` returns null. The body then drafts with its own draft
  (the ocean-family F92 model with its team lock), as v87, v91 or the noise bodies do. The game does not crash. But
  on fresh maps the opponent is no longer Fish's or Mite's composition: a fresh-map dgate would be playing our own
  draft against our own draft.
- The behaviour patches carry over unchanged. Fl's lock policy uses `lock_map()`, which is computed from walks to
  the altars, and Mt3's tribute habit is not map-keyed. Noise bodies seed their redraws from a hash of the walls and
  team, which is only a seed and works on any map.
- The gate tool itself is tied to ladder maps. `dgate.py` plays `--suites ladder` (line 104), counts
  `LADDER_GAMES` from `maps/*.map26a`, and loads a map-name classification
  (`~/tmp-offload/handoff/gate/mapclass.json`). That is fine for tooling, but a fresh-map gate needs its own.
- Options for fresh-map Fish/Mite picks:
  - A pick model fitted to Fish's and Mite's live drafts on map features. This would generalise in distribution.
  - Bodies on `test_draft`: hash-seeded draws from the top-15-team composition frequencies (ladder 2026-11-04/05,
    engine 3.0.0, so somewhat stale).
  - Accept own-draft bodies, stating that the opponent picks differ.

`bots/fish/src/draft/draft.cc:1101` has the same `map_hash`, also used only for its `test_draft` draw.
