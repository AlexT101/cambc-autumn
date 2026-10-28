# Audit: economy/siege.cc (siege)

File: `bots/astraeus/src/economy/siege.cc`: `siege` (Monolith and sealing-group sieges), `kite` and
`kite_productive_action` (big groups on shared-gem maps), `kites_with_spells`.

## Changed

### Commit 1, cleanup (6c44bb83): byte-identical

- `siege_candidate` now returns a `SiegeTarget {g, sealing, joining, bursting}` instead of three
  bool out-params. `siege_ready` takes that target, which replaces the old `int joined` (a group
  index standing in for a bool).
- Added `stop_siege(memory)` for the three copies of "drop the siege, reset staging, return false".
- `low`: removed `role = f.ranged ? range : 1`. `attack_range()` is already 1 for melee, so `role` was
  always `range`.
- `tiles` lambda: one prepare branch (`many ? prepare_attack_tiles : prepare_member_tiles`) and one
  fallback, where it had two copies of the shortcut path and a comma expression.
- Fuel-only host-call swaps with the same results: `clear_board`, `draw_square` and `board_empty`
  in place of the SDK's checked `clear()`, `draw_chebyshev()` and `is_empty()`. In `kite`,
  `and_into(near, standable, goals)` replaces clear, `|=` and `&=`, and `copy_into(standable, out)`
  replaces clear and `|=`.
- `kite_productive_action`: the visibility bit is computed once per endpoint (`seen`), not three
  times inline.
- `kite`: uses `f.ranged`, not `world.me().facts().ranged`.
- Comments:
  - Rewrote `kite_productive_action`'s header ("Enter over two activations; an interior firing
    turn revalidates…" did not say what the function decides).
  - Replaced the "local ablation" and "cold-build" comments, which were experiment jargon.
  - Fixed `siege_candidate`'s join comment, which left out the burst case.
  - Moved "champions without spells stand guard", which sat next to the unrelated `!attackers`
    return, to the line it describes.
  - Explained the `forbidden` ground centres, the staging test (`at_stage`) and the gather rule.
  - Said why the candidate cost counts steps from our spawn: every ally agrees on the target.
  - Clarified the cleared-health comment and the Ryth note in `kites_with_spells`.

Bench, 100M fuel with `--test-draft`:
- Standard 4 maps (00ambush, 00lanes, 01hooks, 00interlock): 8/8 replays identical; total fuel
  -0.02% (2211.80M to 2211.35M).
- 00stampede, 00monolith, 01boss-battle and 00elkring, against a frozen HEAD copy: 8/8 replays
  identical; total fuel -0.09% (2187.70M to 2185.64M). These maps exercise `kite` and the Monolith
  siege.

### Commit 2, fixes (f6ca998f): changes behaviour

On the 4 siege and kite maps the 8 replays are still identical (the case did not come up there);
total fuel -0.01% against base.

- `SiegeLoad::strongest` now counts only the live members (`siege.cc` `siege_load`). It sets
  `low`'s floor on the hit a step takes while we are out of every member's reach
  (`hit = max(hit, strongest)`). It used to take the strongest member *dead or alive*. In a
  sealing group whose golem or elk is dead, the wolves left were then priced at the dead monster's
  120/60 Strength, so siegers walked out "low" at health they could afford. While respawning,
  every member counts as alive, so that case is unchanged. With no live member it is 0, which is
  harmless.

## Considered, not changed

- **Ordering of attack and cast.** After stepping, `siege` attacks, casts, then resets; on its
  goal it casts, attacks, then resets. After a walk the order cannot matter, because every damage
  spell excludes walking. When the step fails it could matter on a kill. Unifying the two orders
  would not be byte-identical, so I left it.
- **`!fresh &&` on our own `engaged` test.** It is redundant: the world sets `awake = asleep` for
  any group that is not alive (world.cc's observe and its respawn note). I kept it as a guard.
- **The `static` monoliths list.** Swapping it for a `static const` lambda init would only trade
  one guard for another.
- **Where `kite` writes `memory.claim`.** It sets the claim before
  `if (board_empty(goals)) return false;`. Moving it after the check may change what farm reads,
  so I left it.

## Suggestions

1. **Siege casters never cast from out of reach of elk, golems or Monoliths** (`siege.cc` ~222,
   `tiles(ability_range)` minus threat). Modelling gap, medium severity, small-to-medium effort.
   - The "cast from out of its reach" branch builds tiles within 4 (ability range) of a live member
     and drops the threat. Every member with reach >= 4 (elk, golem, Monolith) threatens all of
     those tiles, so the set is empty except for wolves. The caster then falls back to `range`
     (3), inside reach.
   - A **ground** spell reaches 5 (range 4 plus radius 1). Stellar and Prism could hit an elk or
     golem (reach 4) from distance 5 without being hit, as `kite`'s ground stations already do.
     A Monolith (reach 5) has no such tile.
   - Fix: give ground casters the stations `kite` builds (centres within 1 of a member, cast
     tiles within 4 of a centre, minus threat), and check that `cast_at_camp` aims ground casts
     at a centre next to the member.
2. **Siege `low` ignores nearest-champion targeting** (`siege.cc` ~190-198). Modelling gap,
   medium severity, small effort.
   - `hit` sums every live member whose reach covers us. A monster attacks only the *nearest*
     champion, so a ranged sieger behind a melee tank takes nothing from members nearer the tank.
   - `kite_productive_action`'s `exposure(p, supported)` already models this, with
     `tanked = ally nearer the member`; reuse it here.
   - `siege_ready`'s pool check makes the same assumption (all live Strength hits the team every
     round for the whole clear). It overstates the cost, because members die during the clear.
     That one is a tuning question.
3. **`exposure` counts groups that cannot attack within the horizon** (`siege.cc` ~391-399).
   Modelling gap, low-medium severity, small effort.
   - Respawning groups are counted. Only `alive && health <= 0` members are skipped.
   - The rules say a group returns *asleep* and attacks only once damage or a stun wakes it.
     Neighbouring asleep groups (h != g) are counted as attacking too.
   - Our action here only damages g. The only way they wake within 2 phases is if someone else
     hits them.
   - Skipping respawning groups and `member_asleep(i)` members of h != g would stop the step
     search refusing productive tiles next to sleeping camps. This is a judgement call (another
     champion could wake them), so I didn't make the change.
4. **`kite_productive_action` gives up near any harmless member** (`siege.cc` ~312). Modelling gap,
   medium severity on stampede-like maps, medium effort.
   - A live gem or gold cluster within 5 of us returns false, because its range-5 viewer tiles
     were not prepared. Big groups usually contain clusters, so the interior and step decision is
     often skipped exactly where it would act.
   - Fix: prepare the clusters' viewers in `kite`'s `prepare_member` loop (they are static and
     cached), or use the cluster's `attack_range` tiles, which are cheaper. Then target clusters
     with basic attacks in `damage`.
5. **Unit-spell melee kite from unit stations whatever `kites_with_spells` says** (`siege.cc` 489).
   Inconsistency, low severity, trivial effort.
   - `unit_stations = !ground_stations && unit_range > 0` skips `kites_with_spells`. Marcella
     (2x60/8 = 15 a turn against 45x1.125 = 50.6 for her basic attacks) and Ren therefore stand
     at unit-spell stations, out of reach of wolves only, while shop.cc buys them Strength
     because `kites_with_spells` is false.
   - Either gate `unit_stations` on `kites_with_spells` too (they then stand guard like other
     non-casters), or document why unit casts are worth it for them.
6. **`kite` target choice** (`siege.cc` ~442-466). Simplification or gap, low-medium severity,
   small effort.
   - The cost is Chebyshev distance to the centre, not walking steps, so a group across a lake
     looks near.
   - A cleared group that then fails `capture_taken` or is beyond `2 * vision_radius` ends the
     whole kite (`return false`), when the next-best live big group could have been kited.
   - Fix: apply those cleared-group conditions inside the selection loop.
7. **The reset model misses an attack spent earlier in the turn** (`siege.cc` 374). Exactness,
   very low severity, trivial effort.
   - The reset is modelled only if the simulated basic attack hit, or a ranged walk spent the
     attack. If the attack was already spent at turn 0 (`!can_attack`), the reset is legal too.
     The exact condition is `attacked || !attack`.
   - Only Ryth, with enough Focus to pass `kites_with_spells`, has a reset slot and ground
     stations, so this almost never fires.
8. **Siege staging counts only visible allies** (`siege.cc` ~168-180). Modelling gap, low
   severity, medium effort.
   - Allies at the far side of a Monolith's stage ring (radius 7) can be out of sight, so the team
     waits out `siege_max_wait` though it has gathered.
   - Fix: use comms claims or the last-seen positions of allies whose claim is g.
9. **`siege_ready` and `low` use our own `camp_hit_factor()` for the whole team** (`siege.cc` 109,
   196). Approximation, low severity. Allies' Jungle and Durability are known from their items
   (beliefs track `camp_dealt`); a per-ally taken factor would make the pool check exact.
10. **Fuel gates.** These are existing gates, not new ones.
    - `siege`'s `tiles` (prepare with `end_reserve`): on short fuel it notes `siege-no-tiles` and
      falls back to a square around the strongest member.
    - `kite`'s `prepare_member` loop: one failed prepare drops *all* stations, and the bot reverts
      to guard squares.
    - Both build static, per-group, per-range boards. Warming them for the current claim during
      spare turns (pathing's `warm_up`) would make the fallback almost never fire. A partial
      fallback in `kite`, which keeps the stations already prepared, would also degrade less.
