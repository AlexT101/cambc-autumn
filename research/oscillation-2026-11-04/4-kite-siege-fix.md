# Stream 4: shared-gems kite and siege progress (fix notes)

Branch `osc/4-kite-siege` (worktree `/home/ubuntu/wt/osc-4-kite-siege`), from 088bf3f4. Sub-issues from B-findings:
1 (shared-gems kite stations), 4's siege half and 7 (engaged siege never hands back, the siege wander), and the
Monolith-only staging waits.

## Plan

### What kite is for

On shared-gems maps (every gem source is a big group or a Monolith) `kite()` replaced siege (CHANGES 2): casters
stand out of every striker's reach and cast on cooldown, champions without spells stand guard "for the fights and the
capture", harmless members fall once the strikers are dead (then farm clears and captures). CHANGES 243 handed live
big groups to farm when no ally casts. EXPERIMENTS records two failed tries at the 600101605 standoff: "Non-kiters
standing guard" (ba53bab, 49.5%, the guards idled) and "Dropped, B" (kite() returning false when every station is held:
the yielders farmed, died to camps 10 times, the enemy then scored): "the standoff needs a fix where farm and kite
choose the group, not a yield".

### Mechanism confirmed (600101605, rerun of the phase 1 game, D lines identical)

- Team Vesper / Cassi / Issac / Marcella / HoR. The 112-gem group: 2 wolves (reach 3) beside 6 elks (reach 4). Unit
  spells reach 4, so only the wolves can be kited, and only from (17,17) on our side ((26,17) on theirs). Non-casters'
  guard square (radius 4 minus reach) is the same two tiles. Issac (no spells) took (17,17) at r~20 and held it all
  game; Cassi and Marcella (the only champions whose spells hit from there) and the rest walked at an occupied tile
  until round 2000 (B4's 224k turns). Farm never ran, so nobody took the gold clusters either: 0 gems, 0 gold, side B
  wins the tie.
- Experiment 1 (Dropped B again, plus guards off the caster tiles): yield whenever kite's walk fails. Freed champions
  went to farm, which priced the kited group solo (`fmode S`) or by joining (`J`), woke it on the walkers, and the
  team died 48 times (0-0 and 0-225). The yield also depended on the tile (walk fails from (18,23), not from (17,24)),
  so Marcella alternated G/F every turn: a new two-decider oscillation.

So the fault is two models of the same group: kite says "the stations clear it", farm says "I can solo or join it",
and neither checks that the stations exist for the champion it holds.

### Model change: one kite plan that both read (final, 9886f824)

- `kite_plan(world, g)` (siege.cc), the team's model of a live big group's kite:
  - **Geometry** (cached per group on its live members): per live striker, the least spell reach r (> its own reach)
    at which a standable tile within r of it lies out of every live striker's reach. Wolves among elks whose every
    tile at 4 is in an elk's reach need a reach-5 (ground) spell, or are not kitable at all.
  - **Output** (once a round): each ally's station spells (unit damage spells at their range; ground damage spells at
    range + 1 when the champion `kites_with_spells`) summed per reach. Every ally counts, dead ones too: the team's
    composition, so ownership does not flip when a caster dies and respawns.
  - `owned`: some live striker has output at or past its least reach. `reach`: the least such spell reach (an ally is a
    caster for g iff its station reach is at least this). `rounds`: the sum of strikers' health over the output that
    reaches each, unreachable while one has none.
- **One ownership rule for every decider.** kite() takes a live big group only if the plan owns it (replaces CHANGES
  243's "any caster on the team"); farm skips a live big group the plan owns (`kite_owns`, one line in farm.cc's group
  skip); siege_candidate skips it on shared-gems maps (a sealing big group was otherwise sieged by melee, waking it on
  the casters). When the plan stops owning it (the kitable strikers dead), kite drops it and farm prices it as before.
- **Roles by type, not by board:** a champion whose station reach is below `plan.reach` is a guard (station boards off),
  on a ring one step beyond `ability_range + ground_radius` of every live striker, so no guard stands on a caster's
  tile. A guard is wanted for the clear's end (the fights and the capture): it guards once
  `plan.rounds <= dist(our spawn centre, group) + kite_early`, and farms until then (skipping the owned group). The
  threshold is the same from every tile; `rounds` only falls while the group lives, so once wanted a guard stays wanted.
- **Station capacity by comms, not by sight:** a caster takes a station only if fewer than its board's tile count of
  casters with a lower index claim g (comms `claim_of`): the same from every tile, unlike seeing who stands where
  (vision is personal, so "the station is held" read differently inside and outside sight: the first version's
  vision-edge flip, found by the auditor). With no station left, kite declines and the champion farms elsewhere.
  `free_tiles` now only picks which station to walk at.
- **A failed station preparation** (bounded by `end_reserve`) holds the turn for kite (claim kept, prepared tiles kept,
  the rest built next turn) instead of turning the caster into a guard for a turn (a fuel-dependent role).
- Dispatch (bot.cc): on shared-gems maps siege() runs when kite() declines (Monoliths or sealing groups there were
  never sieged), then farm.

### Siege

- **Engaged siege never handed back** (topo-backdoor-600206713: Vendetta with 71 gems behind ally Prism in a 1-wide
  corridor): the `!engaged` exit generalised. Off its stand, when the funded step moves nothing while we could walk
  and (engaged) no live member is within our attack or spell range here, whatever the cooldowns, the turn is farm's.
  The usefulness test reads range, not whether an action landed this turn, so a cooldown does not make it alternate.
- **Siege wander** (gen-arena-600202624 Vesper): every other turn the strike search (`srch:nohit`) stepped off the
  stand, spending the walk, and siege walked back next turn. The stand was in the Monolith's fire (`hit 126`): the
  search's end-tile price subtracts awake camps' hits (`camp_at`), while siege accepts that fire and prices it itself
  (`low`, heal trips). Aligned: `Intent::own_fire` names the group whose fire the work already takes (the siege's
  claim or farm's Monolith crew claim, only while not heading home (`camp_fled`) or to an altar), and the search's
  camp price leaves out that group's members that reach us now. Fire from members not yet reaching us stays priced,
  so the search never steps into new fire for free (the auditor's point against excluding the group outright).
  Turning the search's walk off instead does not work: `walks` only gates the goal gain, and without it the search's
  ties go to the lowest grid cell, so it still steps.
- **Monolith-only staging waits** (16.5k turns in phase 1): checked, sensible. They are gather waits bounded by
  `siege_max_wait` (stuck_idle median 19 rounds, max 46 including the walk in), and they end in an engage. Unchanged.

## Auditor (read-only) findings and responses

1. *Guard timing `rounds > dist(here) + kite_early` is not monotonic*: dist falls a step a turn, rounds only when hits
   land, so a guard qualifies at D and fails at D-1. **Fixed:** distance from our spawn centre (fixed per group).
2. *Free-station test depends on vision* (personal sight; an ally out of sight reads absent; bush stations read
   free). **Fixed:** comms-ranked capacity (above).
3. *own_fire drops the group's fire unconditionally* (low/heading home, staging, stale `mono_group` while carrying).
   **Fixed:** only members already reaching us, only while the claim is the siege or Monolith-crew target, not heading
   home, not walking to an altar.
4. *Siege can take a kite-owned sealing group on shared-gems maps.* **Fixed:** siege_candidate skips owned groups.
5. *Ownership ignores geometry* (all station tiles inside another striker's reach: every caster yields, farm skips the
   group forever). **Fixed:** the plan's per-striker least station reach. Related: ownership flipped with caster
   deaths. **Fixed** (the whole team counts). Left: the geometry ignores unit spells' sight and ground stations that
   would also hit another group, so a caster's own board can still be empty where the plan owns the group; that
   caster farms.
6. *Siege yield loses `memory.siege` (join, stickiness) and is tile-dependent.* Partly addressed: usefulness is now
   "a member in range", not "an action landed". Kept `memory.siege = false` (as the old `!engaged` exit did); a
   blocked step is inherently tile-dependent; the corridor case recovered in the rerun (below).
7. *The wander fix may not stop the step* (ties go to the lowest cell). Verified on the debug rerun: siege turns
   that began with an earlier move fell from 45/456 (before) to 20/360 (final rules); the remaining back-and-forth
   is siege's own per-tile `low` (open issue below).
8. *A failed `prepare_member` turned a caster into a guard for a turn* (fuel-dependent). **Fixed** (holds the turn).
9. Smaller: kite only tries the nearest owned group; farm's `walk_on` and passing attack can still hit an owned group
   that was already `farm_group`; guard ring tiles are not checked against other groups' reach. Left open.
- Fuel: no concern (kite_plan is O(members) after the cached geometry; group_at is a table lookup).

## Episodes, before and after

- **600101605** (vs v69, side A; same bot as phase 1's whole-team idle): phase 1 0-0 gems, 0 gold, lost the tie; now
  455-0 gems, 10.5k-1.5k gold, win. Side B 227-0, win. The casters soften the wolves from (17,17), the rest farm gold,
  then farm takes the elks once no live striker is kitable.
- **topo-backdoor-600206713** (vs v68, side A): phase 1 328-358 lost at r2000, 2,949 stationary siege turns of
  3,545; now 1029-358 win at r1081, 454 stationary of 909 (ad23: 1034-482 at r860, 280 of 1,184).
- **gen-arena-600202624** Vesper (vs v65, side A): A→B→A siege turns 128/507 (phase 1) → 74/363; turns where an
  earlier mover had moved us before siege 45/456 → 20/360. This game now loses 630-1074 (it won in phase 1 and in
  ad23); single games diverge and decide nothing.

## Detector (1,024 games vs v69, gen + fresh/gen-s1, traced)

| | phase 1 (before-v69) | final (osc4-9886) |
|---|---|---|
| win % | 49.2 | 49.4 (OOF 5,517 vs 5,478) |
| all episode turns | 1,558,088 | 1,495,451 |
| **B4 siege/kite** episodes / turns / longest | 557 / 54,333 / 1,991 | **472 / 7,881 / 74** |
| B4 on monolith-only maps (turns) | 2,038 | 1,552 |
| B1 farm walk fails | 43,647 | 41,572 |
| B3 farm idle | 53,652 | 53,181 |
| A1 standlost flip | 29,453 | 23,551 |
| C3 claimflip | 410,005 | 409,392 |
| pingpong / jitter / stuck_idle turns | 38,584 / 34,225 / 79,162 | 26,167 / 21,671 / 65,040 |

Summary: `replays/osc/osc4-9886/summary.md`.

## Shared-gems maps (224: maps/osc4-sg-dev, all 214 other shared-gems maps of maps/gen, maps/gen-s1 and the ladder; maps/osc4-sg-known, the 10 known)

| | vs v69 | vs astraeus-088bf3f |
|---|---|---|
| astraeus-088bf3f | 48.0% of 448 (known 10/20) | — |
| 15b9 (first version) | — | 56.5% (OOF 8,006 vs 4,752) |
| ad23 | 58.9% (known 14/20) | — |
| **final 9886** | **58.3% (known 12/20)** | **60.0% of 448, CI 55.4-64.5** (OOF 8,803 vs 5,497) |

Phase 1's traced bot vs v69 on the known maps: 11/20. Known maps now (vs v69): both 600101605 games 455-0 / 227-0;
600101600 1080-0 / 1070-0; 600201608 1000-0 / 783-0. Still lost: 00stampede both sides 0-1060 (the opponent takes
the 160-gem group), 01elk-arena both.

## A/B (the verdict)

`variants/osc4-9886f82` vs `variants/astraeus-088bf3f`, maps/osc-fix-10k, both on their own drafts:
**50.2% of 10,240 (5,141-5,099), 95% CI 49.2-51.2.** OOF turns CAND 58,497 in 6,273 games, REF 56,522 in 6,229
(+3.5%). Shared-gems maps in the suite (59 maps, 118 games) 53.4% ±9.0; the rest 50.2% ±1.0. By family nothing
outside noise (monolith 53.4% of 148, monolith-only 52.8% of 108, topo-backdoor 53.0% of 100).

Fuel: more OOF on shared-gems maps (8.8k vs 5.5k in 448 games): champions that idled on kite now farm, which costs
more per turn. Elsewhere level.

## Files touched

- `economy/siege.cc` (kite, kite_plan, station_reach, kite_owns, siege_candidate skip, siege yield), `bot.cc`
  (dispatch, `intent.own_fire`), `bot_parts.h` (`kite_owns`).
- `economy/farm.cc` (stream 3's file): one condition in farm_turn's group skip, `kited(g) && kite_owns(world, g)`
  for a live group. Unavoidable: farm pricing a kite-owned group solo or by joining was what killed the team in
  Experiment 1. Stream 3 should keep it when merging.
- `combat/plan.{h,cc}`: `Intent::own_fire` and one condition in the search's camp list.

## Open issues

- **Siege's per-tile `low`** (arena-600202624): in reach `low` holds (fire 200), one step out it does not (fire 0),
  so a hurt caster steps in and out every turn. `low` should be judged at the stand siege walks to, not here (an
  A-family two-model flip inside siege).
- 00stampede and 01elk-arena still lost both sides: the opponent takes the big group's clear and capture.
- kite tries only the nearest owned group; a caster with no station there farms rather than kiting a second one.
- Farm's own pricing of big groups (solo `S` / join `J`) when not owned stays risky (stream 3).
- The plan's geometry ignores unit spells' sight and ground casts that would also hit another group.
- Pathing: `step_towards_funded` has no make_way, so an ally on a 1-wide corridor still blocks an engaged siege's
  step (now it yields to farm instead of standing). Stream 3 owns that change.
- Siege for big shared groups (13a6c1b, held) untouched.

## Follow-up: siege judges `low` at the stand (final 5012bf1)

Commits on top of 9886f824: 27840164 (first version), 8706f7e (after the audit), 87878e8, 5012bf1 (final).

### The oscillation

On gen-arena-600202624 a hurt caster flipped every turn between an in-reach stand and the tile beside it (D/SG trace:
`low1 hit200` at (16,14), `low0 hit0` at (16,13), and back). Siege's `low` is "health < hit · min(steps_out,
home_steps) + biggest", from the fire at the tile we stand on. Out of reach the fire is 0, so we are never low
there: siege walks to the stand, reads low on arrival, steps out, and repeats.

### The fix (siege.cc)

- The fire model is a function of the tile (`fire_at(p)`: uncovered members reaching p, their sum, the biggest,
  steps out). Engaged and off our stand, siege judges every stand with the in-reach formula, as it will read there:
  "health < hit_p · steps_out_p + biggest_p", where steps_out_p becomes the walk home from p (`home_exit_steps`) near
  our spawn, as the in-reach `low` takes it.
- **Siege walks only to stands it can hold** at its health. A stand that then reads low (fire taken walking to a deep
  stand) is judged next turn with the lower health. Health only falls until a heal, so a rejected stand is never taken
  up again before one: monotone without memory.
- **No holdable stand:**
  - A heal helps if some stand would hold at full health. Siege then walks home (`camp_fled`), or stays out of reach
    when below `heal_trip_fraction` and the recall is quicker, so siege_heal_trip keeps the recall.
  - Otherwise no heal helps, and the turn is farm's. Siege clears `siege_group()` (the old yield leaked it to farm's
    Monolith attacks too). Farm skips that group this round (`siege_declines`: one more condition in farm.cc's group
    skip). Without the skip, farm took the same Monolith with the same fragile champion and did the in/out itself
    (F0 → R every few turns).
- Gated on `!walk_home` (not `!heading_home`) and run on our spawn too, per the audit. Our spawn's own home stands
  (`home_stands`) are judged on arrival by the on-spawn formula, so they are left out.

### Auditor (read-only) and responses

1. *The stand formula was stricter than the in-reach `low` near home* (no `home_steps` min), and stands were
   unchecked from our spawn: a walk-out/walk-home loop. **Fixed:** the walk home from p near spawn; spawn included.
2. *Deep stands ignore the fire on the way in.* Tried in 8706f7e (the walk-in phases plus the arrival phase priced):
   **lost on Monolith maps** (45.9% of 2,682 games vs 9886f82, see below). Most Monolith sieges stopped. Left out:
   monotonicity holds without it (health only falls; a stand rejected after the walk-in is not retried).
3. *`!heading_home` skipped the check when siege_heal_trip does not keep the recall.* **Fixed** (`!walk_home`).
4. *The yield leaked `siege_group()`, and farm's Monolith crew could take the refused Monolith.* **Fixed** (cleared;
   farm skips the declined group this round). Left: clearing `memory.siege` drops join and stickiness, as every
   siege yield does.
5. *The walk home was decided on health < max, not on whether a heal helps.* **Fixed** (only if a stand would hold at
   full health; else yield, one consistent behaviour for a champion that can never hold a stand).
- Fuel: the auditor flagged members × allies per stand. **Fixed exactly:** cover per member computed once; tiles
  outside the group's threat skip the member loop; `home_exit_steps` only where it decides.
- Not re-audited after the fixes.

### Results

- **Arena episode** (vs v65, side A, traced):
  - Siege A→B→A turns: 128/507 (phase 1), 74/363 (9886), 15/273 (5012). Only 2 of the 15 have `low` set.
  - The game: 1023-233, won at r877. (Single games diverge.)
- **Detector** (1,024 games vs v69, gen + fresh):
  - Win rate 48.7%.
  - B4 siege/kite turns 7,881 → 6,959, longest 74 → 54.
  - A→B→A siege turns across all games 4.1% → 3.1% (phase 1: 14.7%).
  - Other groups level.
  - Output: `replays/osc/osc4-5012`.
- **10k A/B (maps/osc-fix-10k, own drafts):**
  - vs `variants/osc4-9886f82`: **50.0% of 10,240** (5,117-5,123), CI 49.0-50.9. OOF 60,518 vs 57,522.
  - vs `variants/astraeus-088bf3f`: **50.4%** (5,157-5,083), CI 49.4-51.3. OOF 60,373 vs 55,814.
- **Monolith maps** (fresh, unused by osc-fix-10k: maps/osc4-mono 538 maps and maps/osc4-mono2 803 maps, from the
  fresh-* and osc-fix-20k suites), vs 9886f82:

| version | osc4-mono (1,076) | osc4-mono2 (1,606) | pooled |
|---|---|---|---|
| 27840164 (first) | 49.1% | 48.9% | 49.0% |
| 8706f7e (walk-in priced) | 44.6% | 46.7% | **45.9%** |
| 87878e8 | 48.4% | 49.4% | 49.0% |
| **5012bf1 (final)** | 48.7% | 49.0% | **48.9%** (±1.9) |

  OOF on these maps is up ~16% (12.1k vs 10.5k on mono2). The 10k OOF is up 5% vs 9886. The traced detector's OOF
  is level (5,550 vs 5,409); there G-branch OOF turns are 52 vs 38.

### Still open

- Champions that can never hold a Monolith stand (fragile ones) now leave it to others. Pooled 48.9% on Monolith
  maps is within noise of level, but leans negative. A champion that can attack once per heal trip might be worth
  more than none; that is a value question, not an oscillation.
- Farm's own Monolith crew (crew.cc / farm.cc) prices the same Monolith with its own model on rounds siege has not
  declined (stream 3).
