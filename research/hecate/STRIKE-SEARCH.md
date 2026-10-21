# hecate: strike search

Goal: on turns with an enemy in reach, choose our moves and hits by searching every action sequence the rules
allow (cambc-rules.yaml `turn`, `abilities`), scored against what the enemies can still do afterwards, at a
measured and capped fuel cost. Farming is out of scope: camps enter only as targets on fight turns.

## Today

`plan_strikes` (plan.cpp) picks from a fixed menu, and every move must end where it hits:
- stay: A, A R A, A + spell;
- walk: W A, melee A W R A, ranged W R A;
- dash: D A, melee A D, D W A, and Heart of Ruin's landing before or after A.

It keeps the three best candidates by bound and prices only those plus our own tile.

Missing:
- melee W A R A;
- moving away after hitting (Vesper A D; melee A W D, A D W);
- attack plus spell kills (the spell is priced on health from before the attack);
- Vendetta's refresh;
- the stun on Marcella's reset attack;
- Cassi's stun with a walk.

Heal and shield are cast before the plan sees them. `chase()` and `retreat()` run fixed orders of their own.

Fuel on turns over 90k (FUEL-GATES.md): `plan_strikes` 6k mean, 25k max.

From plan3 (EXPERIMENTS.md, planner rounds 2-3):
- Exact danger (Reach queries, 500-1200 uncached) on many tiles is what costs fuel. Its retreat planner played level
  but ran out of fuel 2.5x as often as main, even with camps-below and Strike-above bounds.
- Two ideas lost: a stun valued by the turn it denies instead of a flat 80 (48.5%), and the chase as a goal chosen
  before acting, with steps priced at the kill's worth (43.0-46.2%).

## Design

### Moves

| Action | Legal when | Effect |
|---|---|---|
| W n | walk left, not after an excludes-walking spell; ranged: attack unspent | walk spent; ranged: attack too |
| A t | attack left, t in range and seen from the current tile | attack spent (ranged: walk too); a kill by Vendetta zeroes both cooldowns |
| R | cast left, reset ready, attack spent | attack restored; Marcella's next attack stuns |
| D L | cast left, dash ready, L one of our landings from the current tile | moved; Heart of Ruin's landing hits within 1 of L |
| S t / S c | cast left, not walked (so only from the start tile) | unit target t or ground centre c; walk forbidden after |
| Cassi's stun | cast left | the walk stays |
| shield, heal | cast left | phase 2 |

- **One cast per turn holds after a refresh** (findings: a second cast is refused). Vendetta's refresh therefore
  gives exactly three things:
  - A (kill), then R, then A, when the reset was cooling down;
  - a waived `cast_cost` when R, then a killing A, refunds the slot;
  - a dash readied for moving after an attack, with no attack left.

  Confirm with a quick probe that no cast is allowed after a refresh in the same turn.
- **Our landings** come from our own static window (our open tiles, every visible champion, live camps, Pathing's
  bumped tiles and the step guard). Reach's windows are the enemy's.
- **Sight for our attacks** is exact. A target seen through our ward stays seen. From a new tile, test with
  `shadow_cast` from that tile (~125-173), only when walls or bushes lie between it and the target. `sight()`
  over-counts inside bushes, and a refused attack throws (~3.9k).
- **The held tributer (`hold`)** is respected in every leaf: by moves that leave its stun reach, and by Varg's splash.

### Camps as targets (fight turns only)

- **Who uses them.** A live, visible member is a target only for:
  - Vendetta's refresh, above;
  - Varg's splash, both ways: an enemy hit splashes adjacent camps, and a camp hit splashes enemies within 1 of it,
    reaching a foe 2 tiles away (`probe-varg-splash`);
  - Heart of Ruin's landing.
- **Value.** The camp damage itself counts for nothing; only what it enables scores.
- **Waking is priced, not banned**, for every effect that touches a camp (direct hits, splash, landings, ground
  spells, stuns). Waking costs a group nothing (no regeneration, respawn untouched); the cost is who it hits.
  1. **Woken set.** The touched groups' striking members not read awake this turn. Unread or unknown members
     count as asleep. A member the leaf stuns skips the first phase.
  2. **Target of each woken member.** The nearest within its reach among: our end tile, visible allies, and fixed
     enemies (acted this round, stunned, channelling or holding a capture). An enemy yet to act is assumed to
     leave. Ties go by turn order (`world.slot(·, round + 1)`).
     - If the target is us, the hit adds to the end-tile danger at weight 1.
     - If it is an ally, it adds at weight 1 if the ally has acted, 0.5 if it can still move.
     - If it is an enemy, it earns nothing for now: camp damage on enemies lost twice in fight simulations, so it
       is a separate later test.
  3. **Hard bans, only these:**
     - waking any sleeping Monolith member, the siege target included: it hits for 200 at range 5 and leaving its
       reach takes several phases;
     - a woken hit landing on an ally with a kept recall, a tribute or a capture hold;
     - a woken hit that would be lethal to an ally or to us.
  4. **Bookkeeping.** The search's camp hits never write `memory.claim` or `memory.crew`. An ally's claim costs
     nothing extra, as our damage helps it.
  5. **Pricing order.** The camp terms are exact and cheap, so they join the upper bound before any Reach query.

  Today's code is looser: Varg's splash and ground spells wake groups with no check on allies. The bans in the
  stashed `wake_camps` work (ally claims, allies in reach) were never tested.

### Leaf score

`hits + progress(end) - danger(end, removed)`:
- hits: `hit_worth` on health as it stands at that point, plus `stun_worth` (flat 80 plus channel parts, as now).
- progress: `gain_to(end)` along the goal field. Leaving the walk unused keeps today's "the goal walks after",
  worth `step_value`. The goal still chooses that walk.
- danger: camps plus 0.25 x each enemy's `Safety::blow`, as `expected()` does now, with three additions:
  - credible unseen threats through `Threat::at`, for end tiles beyond a step;
  - an enemy Heart of Ruin hurt but not killed by the leaf has its blow scaled by its new `damage_scale` over the
    old;
  - from phase 3b, `removed` drops killed and stunned enemies.

### Search and pruning

Group the sequences by whether their value depends on order:
- **Order-dependent families are listed exactly:**
  - the reset family: no dash, at most 9 end tiles, every ordered target pair, Varg's splash included;
  - attack plus spell, from the start tile only;
  - Heart of Ruin's landing before or after an attack;
  - Marcella's armed stun.
- **Single-attack dash paths (D, W D, D W, plain dashes) carry no order dependency.** For each end tile and target,
  keep the best attack point on any feasible path (start, mid tile or end). That is exact, and it avoids listing
  ~2000 paths.
- **Ground centres** are scored numerically, all of them within 4 of the start tile.
- **Leaves collapse** to the best value per (end tile, removed set). Reach is queried once per (end tile, foe) and
  summed per set.
- **Pricing order.** Tiles are priced exactly in falling order of their upper bound: hits + progress - camps, then
  each foe's Strike share by size. Pricing stops when no bound beats the best priced leaf, or at
  `max_exact_queries`. Unpriced tiles keep the pessimistic Strike price. No fuel reads.
- **Strike must stay an upper bound on Reach.** `Safety::blow` returns nothing outside Strike's reach, so every
  Reach rule change goes into `compute_strike` too.
- **Possible saving.** Where a foe's 9x9 window has no walls, bushes, holes, camps or allies, Reach may equal Strike,
  so no query is needed. Verify that equality in `debug_block` first.
- **Safety net for distance-3 end tiles.** `step_guard` covers only radius 1-2, so the winning leaf's end tile must
  also pass `Safety::lethal`. If it fails, take the next leaf.
- **Hidden blockers.** On a refused move, take the next-ranked leaf from the current state. Beliefs are fixed for
  the turn, so a full re-plan learns nothing and triples the worst case.
- **WASM costs.** No zero-filled tables (`Raw`/`Unwritten` storage); read `kept_recall` and buffs once per foe;
  never call `live()` on an unseen unit.

### Fuel

The search runs uncapped at 100M first, before any cap is set. Measure it on the bench maps plus shared-gem and
Monolith maps from `maps/gen`, where a third of out-of-fuel turns happen. Record the distribution of:
- tiles priced, Reach queries and fuel per call;
- how often each bound prunes.

Then set `max_exact_queries` so the cap binds in under 0.5% of calls (FUEL-GATES rule 2). If that cap would cost
more than today's 25k worst case, cut the per-query cost first (the Strike-equals-Reach shortcut, sharing memos with
`step_guard`) rather than raising the cap. Today's estimates (~9-12k on a typical fight turn) are targets, not
derivations.

## Phases

Each phase is one commit:
- A/B on ladder + `--gen` (582 games, both sides) against the previous phase's frozen commit, plus a cumulative
  run against the baseline frozen in `bots/baselines/hecate-vN` before phase 1, and a run against nemesis.
- Keep or drop at the real budget by TODO.md's rule (drop if clearly worse, below ~47%). The 100M run tells
  behaviour from fuel.
- Out-of-fuel turns (`oof.py` on the A/B) no higher than the previous phase's.
- Results go in EXPERIMENTS.md.

1. **Search core.** Every legal sequence above, camps as targets with the bans, today's scoring. Checks, all in
   `debug_block`:
   - a dominance check: the old planner's best value, scored the same way, must never beat the search's, since the
     search's candidates are a superset;
   - an exhaustive enumerator on a sample of turns, which must agree with the pruned best;
   - a counter of refused or thrown actions, which must be zero apart from hidden blockers.

   The fuel measurement above comes before the A/B.
2. **Heal and shield as options.**
   - Heal is valued like `shield_worth`: `min(amount, missing health, what could hit that ally)`.
   - `decide`'s early `heal_ally` and `shield_if_needed` (and `reset_may_kill`) go on strike turns. So do `act()`'s
     end-of-turn calls once the search has priced "no cast". Non-strike turns keep them.
3. **Enemy response.**
   - **3a, rules.** Varg's basic reach to p grows by 1 when a unit other than us stands within 1 of p, in both
     `Reach` and `compute_strike`. This also changes `want_home`, `step_guard`, `prey` and turn order, so it gets
     its own A/B.
   - **3b, removal.** Killed enemies drop out of the end tile's danger. With Cassi and Issac, both bodies drop,
     the unseen one included. A stunned enemy drops only if it has exactly one turn before ours (with two it keeps
     its full blow, so no extra Reach build) and is not Marcella or already stunned. `stun_worth` stays at 80. A
     channel-only `stun_worth` is a later, separate test.
4. **Retreat and chase turns through the search.**
   - **4a, retreat.** `want_home` still decides to retreat. The search plans the turn with plan3's retreat score:
     every enemy in reach at full damage, plus life + bag where that could kill us, and home progress around
     `Safety::avoid()`. `retreat()` keeps tributing first when that is safe, and keeps setting `claim` and
     `banking`. `dash_away`, `flee_camps` and `retreat_step` go on these turns.
   - **4b, chase.** `prey()` still picks the target and `decide` still reaches `chase()` at the same point. The
     search plans the turn with `prey`'s attack tiles as the goal field and the normal step value, not steps priced
     at the kill's worth. That is neither half of the lost test. `decision = 'C'` and the rally post stay.
     `dash_to_attack` and the fixed step, attack, reset, cast order go.
   - `step_guard`, `pursuit` and `threat_strike` stay (TODO.md "Don't remove").
5. **One danger model: separate design, after 1-4 are measured.**
   - Folding `want_home`, `step_guard` and `prey` into the search must carry everything they decide:
     - the low-health retreat and its `finishing_camp`/`holding_capture` exceptions;
     - the pack zone (the top retreat trigger before deaths; also a no-go zone for chase, farm and bank);
     - `camp_trapped` with siege limits;
     - pursuit beyond reach;
     - Cassi and Issac's linked death;
     - `paying_soon` and `own_ground`;
     - `killable_now`;
     - turns with enemies seen beyond strike reach.
   - Two fight-simulation limits to fix first: fights at leaves need health in the memo key (fighters use
     turn-start health), and `fight(p, exclude)` excludes only one enemy.
   - Reconcile with FUEL-GATES phase 3, which sets limits on those same functions.

## Not in this plan

- farming tactics through the search;
- one currency for our health and enemy health;
- a cast's cooldown priced by next turn's strike;
- allies finishing a foe before its next turn;
- stunning awake camps that hit us;
- a ward placed first to reveal bush targets;
- valuing camps woken onto enemies (`wake_camps`) inside the search.
