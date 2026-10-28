# Audit: map_economy (`bots/astraeus/src/draft/map_economy.h`)

## Changed

Commit `astraeus audit (map_economy): cleanup`. Bench replays (00ambush, 00lanes, 01hooks, 00interlock, both sides) are byte-identical, 8/8. Total fuel 1900995506 -> 1900995108 (-398, about 0.00%), all of it in the one-off measurement.

- Removed `MapEconomy::gem_groups`. Nothing read it, inside this file or out.
- Grouped the fields and commented them: the weighted per-round supply, `damaging_gems`/`mixed_gems`, the pure-gold trio, and the unweighted `reachable_gems`/`total_gems`.
- Added the reasoning behind `tavi_map` (Tavi shops anywhere, so far-off gold suits it) and `prospector_map` (clusters give at least half the supply, gold counting half).
- Reworded the weight comment so it says what the code does: groups at least as near us count in full; enemy-side ones are scaled by the ratio of distances; everything is per round of respawn plus the 6-round hold.
- Simplified the pure-gold test. `strength == 0 && gems == 0` already means "only gold clusters" (every monster has Strength > 0 and gem clusters pay gems), so `cluster_gold == gold` was redundant. `ours` now comes first.
- `std::min<int>` became `std::min`, since both sides are int.
- Dropped the "v61" history tags from comments.

## Considered, not changed

- **Folding `reachable_gems` into `gems > 0`.** They are equivalent, but shop.cc reads the field (see S3).
- **Moving the play-side helpers to another file** (`economy_pick_count`, `economy_three`, `support_protected(world, c)`). They live in `draft/` but only play code uses them. Moving them is a cross-file change (see S7).
- **Hoisting `from_ally_spawn()` out of `enemy_spawn_steps`.** The measurement runs once per instance, so the saving is negligible.

## Suggestions

S1. **Monoliths inflate the supply denominators** (map_economy.h:48-51). Severity medium, effort small, needs an A/B. A reachable monolith adds 200 gems / (150+6) ≈ 1.28 to `gems` per round. That is more than three 3-gem-cluster groups (21/56 ≈ 0.375 each). Yet with 20000 HP and 200 Strength, that supply is rarely realised. `damaging_gems` already leaves monoliths out. As written, one monolith can flip `cluster_gem_map`/`stellar_map`/`prospector_map` to false. Try skipping `has_monolith` groups in `gems`/`gold` as well.

S2. **The weight ignores clear time** (map_economy.h:47). Severity medium, effort medium. A capture cycle is clear time + 6 + respawn. A cluster (120 HP) dies in a turn or two, while a golem group (5000 HP) or an elk group takes tens of turns. The weight `1/(respawn+6)` therefore overrates monster supply against cluster supply, which biases `prospector_map`/`stellar_map` towards false. Possible fix: add `group.health / k` for a nominal team damage k (draft.cc already estimates clear times for picks).

S3. **`reachable_gems > 0` is the same as `gems > 0`** (shop.cc:386). Severity none, effort trivial. Every reachable group's weight is strictly positive (home > 0, respawn+6 ≥ 1), so the float sum is positive exactly when some reachable group has gems. shop.cc could test `profile.gems > 0` and the field could go.

S4. **`total_gems` counts unreachable groups and monoliths** (map_economy.h:34, used at draft.cc:1029). Severity low-medium, effort trivial, judgement call. The draft picks the gold-only roster (`gold_three`) only when `total_gems == 0`. A single monolith, or gems we cannot reach, switches it to `mixed_three`. Reachable non-monolith gems may be the intended test.

S5. **`mixed_gems` is neither weighted nor gated by `ours`** (map_economy.h:54). Severity low. One enemy-favoured mixed group sets it, while every other stellar_map input is a weighted ratio. That is probably fine on symmetric maps, since the mirror group exists too. Note it if `stellar_map` misfires.

S6. **Groups exactly between the spawns count fully for both teams** (`own <= enemy`, map_economy.h:45). Severity low. For `tavi_map`'s pure-gold groups this counts contested central gold as ours. Weighting ties at 0.5 is an option.

S7. **The helpers are in the wrong file** (map_economy.h:66-90). Severity none, effort small, cross-file. `economy_pick_count`/`economy_three`/`support_protected(world, c)` are play-only (shop.cc, capture.cc, farm.cc, support.cc, comms.cc, bot.cc) but sit in `draft/`. `economy/` or `bot_parts.h` would read better.

S8. **The caches ignore their argument** (map_economy.h:62, 68, 83). Severity none. `map_economy(map)` and the two `static` lambdas cache the first call's input. That is correct for one map per instance, but the signatures suggest otherwise. A comment or a parameterless accessor on `StaticMap` would make it explicit.

The thresholds (`12` steps, `120` gold, the `2x` and `4x` ratios) are tuned constants. Revisit them only through an A/B.
