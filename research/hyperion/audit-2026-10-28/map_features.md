# Audit: map_features (2026-10-28)

Files: `bots/astraeus/src/draft/map_features.cc`, `map_features.h`. Checked line by line against
`tools/mapgen/grid.mjs` (travel, bfs, clearance, groups, reachNear), `generate.mjs` (spawnFields,
sideGroups, metrics), `tools/draftlab/features.mjs` (extras, mapKey) and `model.mjs` (raw, zOf,
champValues, rankTeams, deployedTeam).

## Changed

**Commit 1, cleanup (byte-identical: bench 8/8 identical replays, total fuel +0.00%; native parity
582 maps (`maps`, `maps/gen`, `maps/gen-s1`): 0 key / feature / team mismatches before and after).**
The bench does not show the draft turn's fuel. The changes do no extra work, so the draft's fuel
should be the same or a few instructions lower.

- `map_features.h`: the header named `rankTeams + pickOrder`; the bot mirrors `deployedTeam`, which
  has no pickOrder. `model_team` says its result is ascending ids (which is also the pick order).
  `compute`'s doc lists every throw.
- `choke`: an `int`, scanned over `[Si/4, (3Si+3)/4]` (equal to `floor(S/4)` and `ceil(3S/4)` for
  integer S >= 0). Dropped the `isfinite(choke) ? ... : nan` branch: the range is never empty, so
  choke is never null (in the JS either).
- `model_team`: `s > best_s || best_s == -inf` became `s > best_s`. Scores are finite, so the first
  combination always beats -inf and ties still keep the first team in lexicographic order, as the
  stable JS sort does.
- Removed the `const auto& s = in;` alias. Added a comment on detour's quirky `cheby` (see
  Suggestions 3).
- Renamed compute's `near` lambda to `group_dist` (`near` is also travel's crystal mask). Commented
  `Group::lo/mlo` (sideGroups' tie-break).
- Reworded travel's doc comment: it starts from `base` instead of searching from the spawn, and the
  padding's purpose is fuel.

**Commit 2, fix (bot replays byte-identical; changes only the native/JS-parity path).**

- `travel` at level 2 (crystals), map_features.cc:175-182: the head lists that seed leaps from
  walking distances held only tiles *beside* (within 1 of) something unwalkable. JS `travel` tries
  crystals from every tile within 2 (`near`, R = 2). A tile two from a wall, with all 8 neighbours
  walkable, can still be the best crystal origin: wall column at x=6, a spawn on its left,
  `d(7,10)` was 12 in C++ and 11 in JS. Now the lists use `near` when crystals are on. Dashes from
  such tiles are still never tried (their `over` mask is empty), which is still exact. Fuzzed with
  400 random maps x 2 sides x levels 1 and 2 against JS `Grid.travel` (fields and dash_short): 34
  mismatches at HEAD (all level 2), 0 after. The bot calls `compute(..., crystals = false)`, so it
  never runs level 2. Only `native.mjs` (crystals on) could see it, and no map in `maps`, `maps/gen`
  or `maps/gen-s1` reaches that fallback with a difference.

## Considered, not changed

- The `Dashes` table, padding, `beside` masks and Dial's buckets: I checked them against the JS
  dash rule (the middle tile is king-adjacent to both ends and is not a wall or the other spawn,
  and the landing tile must be passable). Level 1 is exact. A dash over a walkable middle tile
  never beats walking, and an in-bounds end never has all its middle tiles out of bounds, so
  counting out-of-bounds as blocked in `blocked` changes nothing. Each bucket's capacity `n` holds
  because relaxations reach at most v+8 and each tile enters a bucket once per distance.
- `clearance_sum` caps at 6 instead of running the full BFS: it gives the same `min(clear, 6)`. A
  skipped expansion from a tile at 6 would only write values >= 7, and anything written later is
  >= 6.
- The compute pass's sum order (altar_centre, typeGems, frac) matches the JS's, so the doubles
  match bit for bit. I left them alone.
- `compute` copies `fA = openA, fB = openB` in the rare fallback. Swapping in pointers saves a copy
  of two vectors on a few maps, which is not worth the extra indirection.
- `map_key` builds only in `draft_parity` builds. It matches mapKey (64-bit wrap, order-independent).
- Draft fuel: the zero-fills (`d_v` 4N bytes, `beside_v`, clearance's `d_v`) cost about 60k at
  100x100 against a 10M first turn. Not worth touching.

## Suggestions

1. **The `crystals = false` fuel gate** (map_features.h:33-36, draft.cc `choose`). On maps whose
   spawns only a dash or crystal joins, the bot throws (~3.9k) and falls back to the table draft.
   The README puts two level-2 travels at ~8.6M on a 72x72 archipelago. The fix above makes level 2
   slightly dearer (more seeds). It could be made cheap and exact. The fallback needs only `fA`/`fB`
   up to `S` (front, altars) plus S itself, so the Dial loop could stop once `S` is settled, with
   the remaining tiles counted only for altars. Or skip crystal targets with `d[j] <= v + 9` via a
   precomputed 7x7 "any far tile" bit. No ladder map needs it, and it only matters if
   competition-style maps ever disconnect spawns on foot. Severity low, effort medium.
2. **Parity coverage**: the level-2 bug passed native parity because no corpus map exercises a
   crystal origin with all-walkable neighbours. `replays/audit-mf/fz.mjs` + `fz.cc` (scratch,
   gitignored) is a 30-line fuzz of `travel` against `Grid.travel`. A similar fuzz in
   `tools/draftlab/` (random grids through `native_main.cc` plus a travel-only mode) would cover the
   paths real maps don't. Severity low, effort small.
3. **Detour's `cheby` is a JS quirk the model was fitted on** (map_features.cc:430-431, generate.mjs
   metrics). It measures from A's spawn corner `(sx, sy)` to its mirror (B's *opposite* corner) and
   subtracts `sw` on both axes, even when the gap runs along y (where `sh` is the relevant size). So
   it overstates the true spawn-to-spawn Chebyshev gap by `sw - 1` (or by a mix of `sw`/`sh`). It is
   consistent across maps, so it is harmless to the model as fit, but if metrics ever changes,
   compute `max(|gapx|, |gapy|)` between the two spawn rectangles and refit. Severity low.
4. **Perspective and opponent picks** (no change, judgement): all features are from absolute team 0's
   side. That is fine: the symmetry makes A's and B's values equal except for sideGroups' tile-index
   tie-break on equidistant groups, which assigns those groups to one side by tile index rather
   than by who reaches them. The draft could also use what the rules give it: earlier rounds' enemy
   picks are visible (`draft.visibility`). The deployed model drops counter terms (fit at ~1e-4), so
   that is a lab question, not a code one.
5. **Input validation** (map_features.cc:330-334) rejects bad camp types and coordinates. It accepts
   `in.t` values outside 0..4 and spawns that run off the map (`sx + sw > W`). The engine never
   produces either, and native input comes from mapgen, so this is only defensive. If kept, checking
   `sx >= 0 && sx + sw <= W` (and the same for y) prevents an out-of-bounds write in `travel`'s
   `unwalkable` on malformed input. Severity very low.
