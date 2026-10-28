# Audit: champions.h (2026-10-28)

File: `bots/astraeus/src/champions.h`, the per-champion facts table and its helpers.

I checked every row of the table against `cambc-rules.yaml`: ranged/melee, the three stats, the passive, both ability slots in order, their multipliers, stuns, targeting, excludes-walking, shield durations and Heart of Ruin's landing radius. I also checked the row order against the SDK's `cambc::champion_type`. Every value matches.

## Changed

Commit `a61fb990`, "astraeus audit (champions): cleanup". The 8 bench replays are byte-identical, with a fuel delta of +0.00% (2211802776 -> 2211802776; no turn got cheaper or dearer).

- **Table readability.**
  - Each row is now labelled with its champion name, replacing the separate list of the index order.
  - `ranged` is now a named constant (`melee` / `ranged`) instead of a bare `true` / `false`.
  - The special abilities use designated initializers (`AbilityFacts{.kind = K::dash, .multiplier = 1.5f, .stuns = true, .radius = 1}`) instead of seven positional fields.
  - There is a new `shield(mult)` builder, with the shared `shield_turns = 5`.
  - The designated initializers must name `AbilityFacts` explicitly. Bare `{.kind = ...}` braces inside the `std::array` are taken by brace elision as the inner C array.
- **Order check.** I added `static_assert(champion_table.size() == champion_type::heart_of_ruin + 1)`, so a change to the SDK enum's length fails at compile time.
- **Wrong comment fixed.** `AbilityKind::dash` said dashes cross "champions". The rules allow crossing allies and *unseen* enemy champions only; visible enemy champions and visible camps block the path.
- **`Targeting::self` now notes that dashes use it too.** Their landing tile is not a target, which is why `range()` special-cases dashes.
- **Removed the unused `Stat::at`.** Nothing calls it; the shop adds growth directly.
- **Reordered the `ChampionFacts` methods** into groups: attack geometry, then slot queries, then reaches, then the tribute passive. Semantics are unchanged.
- **Trimmed `reach()`'s comment.** Its body already shows the ground 3x3.

## Considered, not changed

- **Writing `has()` as `slot_of(kind) >= 0`.** It reads more cleanly, but `has` is on hot paths, and two comparisons are cheaper in WASM than the loop.
- **Inlining `melee_range` / `ranged_range` into `attack_range()`.** Only this file uses them, but as named rule constants they are fine.
- **Removing `AbilityFacts::duration`.** Nothing reads it at runtime, but `economy/camps.cc:329` static-asserts that Heart's and Varg's shield durations are equal, so it stays.
- **Using the SDK constants for the stats.** The SDK exposes passive constants but not per-champion stats, so the table remains a transcription.

## Suggestions

1. **`stun_reach` ignores a walk before a stun that does not exclude walking.**
   - **Where:** `champions.h` `stun_reach`; used by `World::ready_stun_reach` (`model/world.h:452`), `ally_stops` (`combat/fight.cc:442`) and `stoppable_winning_tribute` (`combat/fight.cc:420`).
   - **Rules:** no ability spends the walk, and only excludes-walking spells forbid a walk before them.
   - **Effect:** three champions can stun one tile farther in a single turn than `stun_reach` says:
     - Cassi: walk, then stun, reach 5 (not 4).
     - Heart of Ruin: walk, then dash 2, then the radius-1 landing, reach 4 (not 3).
     - Marcella: as a melee champion she can walk, attack, reset, then make the stunning attack, reach 2 (not 1).
   - **Consequences:**
     - `ally_stops` under-counts allies that can stop a winning enemy tribute, so the self champion may divert for a stop an ally would have made.
     - `stoppable_winning_tribute` misses an enemy one tile beyond the no-walk reach.
   - **Fix:** add `stun_reach_with_walk(slot) = stun_reach(slot) + (abilities[slot].excludes_walking ? 0 : 1)` for this-turn questions about a champion that can still move. This is general: Ryth, Prism, Tavi and Ren are all excludes-walking and get +0. Callers must also check `can_move` or stun state. The callers are outside this file, so I did not change them.
   - **Severity / effort:** low-medium, small effort; it changes behaviour, so it needs an A/B.
2. **Marcella's stun needs a prior attack.**
   - **Where:** `ready_stun_reach` (`model/world.h:452`) counts her reset slot whenever the cooldown is ready.
   - **Rules:** the reset fails while the attack is unspent, so she must first attack something in range, which can be the stun target itself, and must still have the reset this turn.
   - **Effect:** the model is right when the first attack hits the same target. When planning an ally Marcella's stop in `ally_stops`, though, it ignores whether her attack is already spent with the reset on cooldown. `World::read_stuns` handles this for self (`!my_can_attack()`), but the ally and enemy paths do not.
   - **Severity / effort:** low, small effort.
3. **`raw_output` (`model/world.h:737`) belongs here as a `ChampionFacts` method, and it misses two passives.**
   - **Where:** it is a pure function of the facts, Strength and Focus, and is used by the draft and by fight sizing.
   - **Missing:**
     - Varg's splash: up to Strength again per extra enemy adjacent to the target.
     - Ren's retaliation: 0.2 x Focus per hit he *takes*, which is a function of incoming hits rather than output, so it may belong in a separate "punish" term.
   - **Also:** `draft.cc:143`'s `spells` counts only `AbilityKind::damage` and so drops Heart of Ruin's landing damage, which `raw_output` includes via `lands()`. That is harmless today because `spells` is gated on `ranged`, and Heart is melee.
   - **Severity / effort:** low, medium effort, needs an A/B.
4. **Ryth's passive is computed outside the table.**
   - **Where:** `economy/shop.cc:143-144` adds `ryth_health_strength_ratio * health growth` to Strength per health shard.
   - **Suggestion:** a `ChampionFacts::strength_per_health(float bonus_health)` helper next to the table would keep passive arithmetic in one place, beside `tribute_gold_per_gem`.
   - **Also:** `draft.cc` uses base stats only, so this does not affect the draft.
   - **Severity / effort:** cosmetic.
5. **Fuel gate on dashes in `economy/farm.cc:711`.**
   - **Where:** `static const int dash_kind = 150 * n_groups < full_field_cost_estimate() ? facts().dash_kind() : 0;`
   - **Effect:** on maps with many groups it drops dash-aware fields (`dash_walls` / `landing_dash_walls`) for every dashing champion (Vesper, Vendetta, Issac, Ren, Heart of Ruin). This is a fuel gate on a modelling choice. Making the dash field cheap, for example by caching per-group fields or building them incrementally across turns, would let it go.
   - **Severity / effort:** medium, medium effort; this is outside my file, so it belongs to the farm auditor.
6. **One cast per turn across both slots.**
   - **Where:** this rule is not encoded in the facts.
   - **Effect:** summing both slots' per-cooldown damage, as `raw_output` does, is fine at cooldown 8. Any code that plans *both* slots in one turn would be wrong, though, for example Stellar or Prism damage plus damage, or Heart shield plus dash.
   - **Suggestion:** a facts-level constant or comment would make this visible. I found no current misuse in the callers I read.
   - **Severity / effort:** informational.
