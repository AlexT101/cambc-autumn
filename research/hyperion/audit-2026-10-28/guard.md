# Audit: `bots/astraeus/src/combat/guard.cc` (guard)

Branch `worktree-agent-a7189be3662e73ec6`. Line numbers are after both commits.

## Changed

### Cleanup (1473bca8): byte-identical, 8/8 bench replays; fuel +0.01% total (mean 50161 -> 50165)
- **`GuardFoes` owns the exact exposure.** `exposure` (with its per-foe Reach cache), `expose_here`, `no_worse` and `visible_of` moved from lambdas in `step_guard` into the struct. `step_guard_cover` had its own copy of the here-exposure loop and the no-worse test; it now calls the same members, so the cover can't drift from the guard's first test. The `bound` alias lambda and the `foes`/`strikes`/`at`/`reaching` locals are gone.
- **`pack_boxes` is flatter.** It returns early once built this round, and the loop-invariant `(hurt || home)` test is hoisted out of the enemy loop into one early return. `std::tuple_size_v<std::remove_reference_t<decltype(members)>>` became `constexpr int pack_members = 8`, which also sizes `box`.
- **Smaller tidies.** `in_square(here, e.pos, Strike::max_reach + 2)` now reads `+ dash_range`, which is what the 2 means. `n < foes.size()` is named `all_listed`. The local lambda `fight` became `simulate`, so it no longer shadows `Safety::fight`. The comma-expression return in `outcome` is now a plain block, and `step_guard_cover`'s `g.n == 0 ||` check is gone (it is implied by `reaching == 0`).
- **Comments.**
  - Rewrote the pack-zone block: it read "hurt or carrying, at less" and said "pack zone of our own half", but the zone is also built when hurt away from home.
  - Dropped a float-rounding rationale that only argued equivalence with an earlier implementation.
  - Added notes: `draw_box`'s side is the largest odd side that fits, and its squares overlap at the far edges; `settled` holds one entry a tile plus the two unions.

### Fixes (3a2ffc7a): bench replays identical (no teleports there); fuel +0.03% total (mean 50161 -> 50176)
- **The step guard now places a visible teleporting enemy at its destination** (`GuardFoes` constructor and `exposure`, around guard.cc:247-279). `Safety::blow`, `approach` and `credible_enemy_may_hit_within` already have a `teleport_pending()` enemy with a known `tp_dest` act from `tp_dest`. `threat_strike` returns no strike if it can't act before our turn, so one with `reach >= 0` lands first. GuardFoes, however, measured distance from `e.pos` and used `reach_of(e)`, which `Reach::build` builds at `origin_ = e.pos`. Three things went wrong as a result:
  - A tile near the landing but far from `e.pos` got `near == 0`, so it was judged no worse than ours and never guarded.
  - Tiles near `e.pos` were falsely counted as exposed.
  - `visible_of(near)` disagreed with `fight_key`, whose visible threats come from `blow()`.

  The foe now sits at `tp_dest`, and its exact blow is `strike.blow(dist)`, exactly as `Safety::blow` computes it.

## Considered, not changed
- **`costliest` asymmetry.** It decays when `reaching == 0` but not when `n == 0` (guard.cc:322-328). The difference is arbitrary but harmless; making it uniform would change fuel-gate history, so it doesn't belong in a cleanup.
- **`lethal(q)` can be asked twice** on the `k == 2` path (guard.cc:458, 461). Caching it eagerly would call it on paths that never need it. It is cheap once the threats are built.
- **Folding the two union-fight blocks into one helper.** They return slightly differently: the first skips `note_placing` on a fuel shortfall. Not worth obscuring the flow.
- **`open_bits` layout probe.** The SDK doc comment says "one byte per tile" while `linear_buffer_size()` is packed bits; the probe in `open_bits` already guards against either. Kept.
- **`step_safely`, `own_ground`, `draw_box`, `pack_covers`, `in_pack_zone`.** All correct as read. `pack_covers`'s greedy row sweep and `draw_box`'s clamped tiling both terminate and cover exactly.
- **The subset enumeration reads `subsets[mask ^ top]`, which is never stale.** If `mask ^ top` were covered by a minimal set, `mask` would be covered too and skipped. So the static array's leftovers from earlier rounds are never read.

## Suggestions
1. **Fuel gates in `step_guard` drop the whole guard** (guard.cc:331 `step-guard-entry`, 434 `step-guard-look`; 395 `step-guard-sim` keeps a partial guard). When fuel is short we step with no guard at all, into tiles that hand the enemy the first strike.
   - Make it bounded instead: the bound-pass tiles (`exposed[0..bounded)`, or `step_guard_cover`'s board) are a cheap superset with no Reach and no fight. Two ways:
     - Return them as the guard when a later stage can't be afforded, which is conservative rather than permissive.
     - Better, cap the work: at most one union fight plus one fight a tile, sorted as now, under a fixed budget, which would let the entry gate go.
   - Severity medium (it bites in exactly the crowded fights where the guard matters). Effort small to medium.
2. **The pack zone ignores teleports** (guard.cc:86). A teleporting enemy's box is drawn around `e.pos`, not `tp_dest`. It is the same class of bug as the fix, but changing it would alter retreat behaviour, so it is left for a deliberate change. Low severity, small effort.
3. **`pack_radius` is uniform (max_reach + 1 = 7) for every member** (guard.cc:30-35, 107-114). A walking melee enemy with no dash strikes at 2, yet its box is 15 wide. The box could use each member's `threat_strike(world, e).reach + 1` (or `fight_reach`) and be exact per champion. That would shrink zones against Ryth, Marcella and Varg and keep them for Vesper and dashers. Medium severity (it over-retreats against melee packs); small effort. Behaviour-changing, so it needs an A/B.
4. **`no_worse` compares enemy exposure only** (guard.cc:281). A step that keeps the same enemies and damage but leaves an ally's `fight_ally_radius` is treated as safe as our tile, yet its fight has fewer allies. One fix is to also require `fighting_allies(q) ⊇ fighting_allies(here)`, or to drop the shortcut whenever `here_mask != 0`. Low severity (one or two steps rarely change the ally set); small effort, but `fighting_allies` is in Safety.
5. **A walk then a dash can end 3 from `here`** (guard.cc:483-486). The deferred guard is centred on the tile it was worked out from, with radius `dash_range`; a dash after a walk can land up to 3 from that tile, outside the guarded square. `bot.cc:309` re-guards after the plan search moves us. I couldn't verify that every other walk-then-dash flow (farm, bank, chase) re-guards. Worth checking in pathing/plan. Low severity.
6. **Heart of Ruin's dash landing is not modelled.** It deals 1.5 Focus damage and stuns enemies within 1 of the landing tile. A guarded tile next to an enemy may be the best landing because that enemy loses its next turn. The guard prices that tile as if the enemy still acts. Plan/abilities may already value the landing, but the guard can veto it. Medium severity for HoR only; medium effort.
7. **Pack-zone self health mixes times.** It is frozen at the first query (`pz.health`) but adds the live `a.shield` (guard.cc:91), and `hurt` ignores the shield (line 79). Varg/HoR shields cast this turn count toward `ours` but not toward `hurt`. Probably intended; noting it. Low.
8. **Willow's guard ignores dash** (guard.cc:470-480, radius 1). That is correct for Willow, but `heals()` is the selector: a future healer with a dash would be guarded at radius 1 only. Trivial; maybe assert or take the same radius loop.
