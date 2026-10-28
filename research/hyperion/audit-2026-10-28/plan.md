# Audit: combat/plan.cc, combat/plan.h (2026-10-28)

## Changed

One commit, `astraeus audit (plan): cleanup`. The bench (00ambush, 00lanes, 01hooks, 00interlock,
`--test-draft`, 100M) gives 8/8 identical replays. Total fuel fell 2,211,802,776 -> 2,211,718,294
(-84k over the 8 games; 12,984 turns cheaper, 259 dearer, and the dearer ones are codegen noise).

- `Board` (strike_enemy) had three dead fields, `attack`, `reset` and `shield`. Filling them cost
  `my_can_cast`, `my_can_attack` and two `my_cooldown` host calls on every `strike_enemy`; they are
  removed. `ready_slot()` then had no other use and went too.
- `Search::read()` asked for each slot's cooldown up to three times (the `ready` array, `ready_slot`
  for the shield and heal, and `read_spells`). `ready` is now a member that `ready_of(kind)` and
  `read_spells` reuse.
- `add_unseen()` repeated `read_spells`' `my_damage(s)` host call (and its try/catch). It now takes
  `raw` as a parameter.
- In `read()`'s foe loop, a local `float shield` shadowed the member `int shield` (the shield
  slot). It is renamed `absorbs`.
- `read_geometry()`: the `read_into` lambda and the temporaries are replaced by direct
  `read_grid` calls, and the two comments about the guard are merged into one.
- `use_slot()` was used once, for the shield. It is inlined into the execution switch like the
  other ops.
- The strikers loop calls `safety.strike_of(e)` once instead of twice (same calls, same order).
- Comments: removed a statistic from a past experiment on `max_nodes` and a reference to "the old
  menu's landing_wakes" on `land_bad`. That comment now gives the actual reason. plan.h's header
  comment is reflowed, without the rules-file pointer.

## Considered, not changed

- **No stun value on a killed target.** `hit_unit` (armed, :1241), `spell_unit` (:1286),
  `centre_value` (:1311) and `land_at` (:1346) all add the stun's worth even when the same blow
  kills. A dead champion loses nothing to a stun, so this is overvalued. abilities.cc's
  `cast_at_enemies` does the same, though, and `stun_worth` also carries a tributing enemy's
  tribute value, which a kill cancels too but `kill_distance` does not count. Fixing this in plan.cc
  alone would make the two files disagree, so it goes under Suggestions.
- **Enemy Hearts of Ruin: at most one.** Repeat picks within a team are illegal, so
  `hors`/`hor_unit`/`Leaf::hor` never need 2 entries. Shrinking them to one is safe but touches
  the leaf layout and the factor code for no gain. Left as is.
- **Reach bounds.** For a ranged champion, `read()` (:1121) and `strike_possible` overestimate:
  without a reset a ranged champion cannot walk and then attack. This only lets in extra foes the
  search then finds no legal hit on, so it is harmless.
- `debug_search = true` costs nothing in release, because every use sits inside `debug_block`.

## Suggestions

1. **A basic attack or HoR landing on a recalling enemy does not price the cancelled recall**
   (medium severity, small effort). By the rules, any damage cancels a recall, but `x.recall` is
   read only when a non-landing cast is ready (`recall = casts && ...`, :1139), and only
   `spell_unit`/`centre_value` add `params::recall_value`. `hit_unit`, `land_at` (whose `land_stun`
   uses `stun_worth(..., damaging=true)`, which leaves the recall out) and `best_hit` (strike_enemy)
   never add it. abilities.cc's `hit_worth` does add it for any non-kill damage, so the two files
   disagree. To fix: always read `recall`, add `recall_value` on a non-kill hit in `hit_unit` and
   `land_at` (and in `Board`), and narrow `hoisted()`'s recall exception (:718) from spells to any
   strike on a recalling foe.
2. **Stun counted on kills** (low-medium, small, cross-file). See above. A stunning cast that kills
   scores `stun_worth` on top of the kill. So the search may spend Ryth's, Prism's or Tavi's cast
   (or Marcella's reset arm) on a kill a basic attack already makes, instead of keeping the cast
   for a shield, a heal or the next turn. The fix is to add the stun only when the blow does not
   kill, here and in abilities.cc, and to decide whether a kill on a tributing enemy should then
   get the tribute part separately.
3. **Walk-alone leaf only for Prism and Stellar** (medium, needs an A/B). `plan_strikes` (:1729)
   offers "walk, nothing else" as a priced leaf only for ranged champions without a reset, a dash
   or a non-exclusive hit spell. For Cassi, Vesper, Tavi and Willow the walk node is grown but is
   `owed`, so it is never settled. Their "attack here" option is then weighed against "do nothing
   here plus `step`", both priced at the start tile's danger, never against a walk to a safer tile.
   Offering the terminal walk leaf for every ranged champion that can walk (`!melee && can_walk &&
   moves && !walked_first`) would make this consistent.
4. **Landings use a hard ban where attacks and spells price the wake** (medium, medium effort).
   `land_bad` (:432, :1212) refuses any HoR landing that touches a sleeping striker, even when it
   also hits a foe. Basic attacks and ground casts instead go through `wake()`, which prices who the
   woken camp hits. The landing also stuns the camp members within 1, which then skip their next
   attack, and neither path models that. Routing landings through `wake_at` would make HoR's
   choices consistent with the other champions'. The cost/on_us for stunned members should drop
   their first hit.
5. **`strike_enemy` ignores Varg's splash on camps** (low, small). `best_hit` sums splash only on
   enemy champions, so a Varg attack next to a sleeping camp member wakes its group without that
   being priced. The search does price this through `touch1`. farm.cc calls `strike_enemy`, and so
   does plan_strikes' fallback after a refused move.
6. **`wake()` bans any group with a sleeping Monolith outright** (:1403), even when the Monolith's
   reach covers no champion. This is a judgement call (a woken Monolith is dangerous for 2+ phases),
   but it could be priced like the other strikers, with a ban only when we or an ally would be in
   its reach.
7. **Ground spells are only searched when exclusive** (`sp.ground && sp.excl`). Every current
   ground spell is exclusive, so this is fine today. A future non-exclusive ground spell would be
   skipped silently. A `static_assert` over the champion table, or a comment, would document the
   assumption.
8. **Fuel.** There are no fuel gates in these files. `max_nodes`, `max_exact_queries` and
   `max_sets` are fixed bounds. `read_spells` still makes one `my_damage_to` host call per foe per
   ready slot. If `raw * x.taken` with the shield arithmetic (already the catch fallback) matches
   the engine exactly, which I have not checked, those calls could go. That is worth looking at
   only if read time shows up in `SRCH` traces.
