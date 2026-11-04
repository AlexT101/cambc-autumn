# Round 2, W1: leaves_at judges q for the round we arrive (fix notes)

Branch `osc/r2-1-arrival-round` (worktree `/home/ubuntu/wt/osc-r2-1-arrival-round`), base 8c0f3d49. Baseline
`variants/astraeus-8c0f3d4`.

## Plan

### Mechanism, confirmed in the source (8c0f3d49)

- `leaves_at(q)` (fight.cc) is `drawn_home || stand_lost_at`, the same two helpers want_home runs, so the code
  is already shared. What differs is the world they read:
  - `stand_reach` reads each enemy with `fight_reach(e)` = `threat_strike(e)` (this round's window,
    `turns_before_ours`) and `approach(e, q)` (its Reach built with that window, from where it stands now).
  - `in_pack_zone(q)` counts members within `pack_radius` of where they stand now, and its `home` test reads
    `own_ground` at our tile, not q.
- Asked in round t, the veto is answering for round t+1, when want_home at q reads the window
  `turns_before_ours` gives then and the enemies after their turns in between.

### The model: one stand, judged for a given round

`stand_lost_at` and `drawn_home` take which round they judge: our turn now (want_home) or our next turn
(`leaves_at`: the veto and keep_out). For the next turn, each enemy e:

- **Advance** `k = turns_before_ours(e)`: its turns before our next turn. It is taken to spend them walking
  at us, as the stand already takes its pursuers to: a walk of `w` turns now is `w - k` then; `w <= k` makes it a
  hitter.
- **Window** after our next turn: `turns_after_next(e)` (its turns between our next turn and the one after) and
  `arriving_strike(e)`: threat_strike's strike over that window, from its first turn after our next one.
- Hit/walk at q:
  - `k = 0` (it cannot move before then): exactly what want_home will build: its Reach for the next window
    (a second Reach per enemy, built only when that window is two turns, as the current one is then one).
  - `k >= 1`: by terrain distance `enemy_reach::distance` from where it stands: `w = D - R' - k`. Its Reach
    from a tile it has not reached yet cannot be built; the terrain bound is the same one approach() uses
    past the reach.
- Unseen enemies seen last round: walk_in the same way (advance and window).
- Pack zone: each member counts within `pack_radius + k` of q, and `home` is read at q.
- Teleporting or stunned enemies keep this turn's read (rare; their turns are not their own).
- `lethal(q)`, the recall line and the hold tests are left as they are: they price the turns before our next one,
  which is what they are for.

want_home keeps the read for now (k = 0 for every enemy, this round's window), so want_home at t+1 and the veto at t
are one function judging the same round from the same inputs, up to where enemies actually walk.

### Callers

- `leaves_at` (only caller: `work_veto`, for the asked tile and for our own tile's `leaves_here`).
- `keep_out` / `work_around` (guard.cc): the work guard's cheap neighbour version of drawn_home's pack test,
  switched to the arriving pack zone so the board and the veto agree.
- Not changed: `pack_zone()` boxes (farm, bank, chase keep-outs), `step_guard`, every other Safety consumer
  (FIX-BRIEF-R2: a next-round window for every consumer lost 0.3-0.8 points).

### Fuel

Per veto ask: one terrain distance per near enemy (host search, kept per enemy tile), a second Reach build
(~2k) per enemy per turn at most, only when its next window is two turns and it cannot move first. The stand
simulation is still one per ask; rosters may hold more walkers.

## Outcome (short)

The approach can't win at 10k games. The full model removes the stream's pathology: on the detector, episodes
-17%, retreat churn -36%, and the example cycles are gone. But it loses 1.6-2.1 points against astraeus-8c0f3d4.
The loss persists at 4x fuel, with no out-of-fuel turns at all, so it is behavioural, not fuel. Every way of making the veto
judge the next round's stand lost:
- the window alone;
- the advance alone;
- the advance kept to the pursuit horizon;
- now ∪ next;
- the model on farm steps only.

The committed version, **1dc5cbfa**, keeps only the parts that do not lose: the next-turn pack zone and believed
enemies as hitters. It reads 50.2% (49.2-51.1), and the detector is flat. It is neutral; don't merge it for its own sake.

## What was built (c62e2604, then 08a70039 with ablation flags)

- `Safety::arriving_reach(p)`: stand_reach as our next turn will read it.
  - Each enemy is advanced by `turns_before_ours(e)`: its walk `w` becomes `w - k`, and `w <= k` makes it a hitter.
  - It strikes over the window it gets after our next turn: `turns_after_next`, and `arriving_strike` via
    `strike_over`, the old threat_strike widening factored out.
  - `k = 0`: an exact second Reach for that window (`next_reach_of`, second pool).
  - `k >= 1`: by terrain distance (`enemy_reach::distance - R' - k`), and a current hitter stays a hitter.
  - Believed (age-1) enemies are advanced the same way; one whose last tile reaches p hits.
- `stand_lost_at`/`drawn_home` take `next`: `leaves_at` (the veto, and its `leaves_here`) passes true, want_home false.
  This is one function judging two rounds.
- Pack zone (guard.cc):
  - Members carry `ahead` (turns_before_ours). `in_pack_zone(p, next)` counts a member within
    `pack_radius + ahead` of p, and reads `home` (own_ground) at p.
  - `work_around`/`keep_out` (the work guard's neighbour board) use the next-turn read.
  - `pack_zone()`/`pack_covers` boxes are unchanged (`active()`, `ours(home)`).

## Episodes (exact reruns; the "before" builds reproduce the originals' D lines byte for byte)

Step-then-leave counts every champion of ours: a non-R step, then an R turn back to the start with `home:`. A cycle
is p→q→p→q. The after games diverge, so these are counts per game, not like-for-like turns.

| game (vs) | build | turns | step-then-leave | cycles |
|---|---|---|---|---|
| mega-groups-410408202-12 (v66), h0 | before / c62e | 9975 / 2739 | 775 / 2 | 769 / 0 |
| same, debug builds | before / c62e | 9974 / 4642 | 775 / 6 | 769 / 0 |
| 00the-line-21 (v68), debug | before / c62e | 8557 / 3324 | 97 / 12 | 38 / 0 |
| leaky-diagonals-600207807-12 (v68), plain | before / c62e | 9244 / 2170 | 697 / 2 | 672 / 0 |
| same, debug | before / c62e | 3690 / 3521 | 71 / 2 | 55 / 1 |
| gen-classic-410400004-21 (v66), debug | before / c62e | 6478 / 6939 | 30 / 11 | 9 / 2 |

- The named examples came from the investigator's debug reruns.
  - mega h0 r405-445: before, X(55,5)↔R(54,5) every round with the veto passing. After: no cycle; h0 holds
    captures elsewhere.
  - the-line h5/h6 and leaky h4 r594-600: no undo moves in those windows after.
  - classic h8 r223-225: same.
- What remains in the after games:
  - strike-search and chase steps (W2);
  - enemies not believed at all before the step (vision: an enemy appears from q);
  - believed-unseen enemies counted as walkers (fixed by the believed-hitter rule, classic h9 r982-984).

## A/B (osc-r2-10k, 10,240 games, vs variants/astraeus-8c0f3d4, own drafts)

| variant | stand next-turn | window | advance | pack next | win % | 95% CI | OOF CAND | OOF REF |
|---|---|---|---|---|---|---|---|---|
| c62e2604 (first cut) | yes | yes | yes | yes | 48.4 | 47.4-49.4 | 364,984 | 157,505 |
| full2 (+believed hitters) | yes | yes | yes | yes | 47.9 | 47.0-48.9 | 371,340 | 157,146 |
| advonly | yes | no | yes | yes | 47.8 | 46.8-48.7 | 360,401 | 159,827 |
| hz (advance only within the pursuit horizon now) | yes | yes | horizon | yes | 48.6 | 47.7-49.6 | 290,319 | 159,979 |
| hznowin | yes | no | horizon | yes | 48.8 | 47.8-49.7 | 279,711 | 158,486 |
| hzor (hz ∪ this turn's stand) | yes | yes | horizon | yes | 48.2 | 47.2-49.1 | 320,238 | 159,617 |
| winonly | yes | yes | no | yes | 49.4 | 48.4-50.3 | 195,202 | 157,038 |
| winor (next window ∪ this turn's stand) | yes | yes | no | yes | 49.7 | 48.7-50.6 | 244,869 | 163,083 |
| farmonly (full, F/G steps only) | F only | yes | yes | yes | 49.0 | 48.0-49.9 | 336,170 | 156,490 |
| nocontest (full, bar contest) | not X | yes | yes | yes | 48.3 | 47.3-49.2 | 370,805 | 158,397 |
| none (refactor, believed hitters) | — | no | no | no | 50.2 | 49.3-51.2 | 163,282 | 156,255 |
| packonly (pack next; stand as before) | no | — | — | yes | 50.4 | 49.4-51.3 | 164,357 | 156,877 |
| packunseen (pack next, believed hitters) | — | no | no | yes | 50.3 | 49.3-51.2 | 164,113 | 155,887 |
| **1dc5cbfa (final, = packunseen cleaned)** | — | no | no | yes | **50.2** | **49.2-51.1** | **169,493** | **156,363** |

Same, at `--fuel 400000` (no out-of-fuel turns on either side):

| variant | win % | 95% CI |
|---|---|---|
| full2 | 48.0 | 47.0-48.9 |
| winor | 49.4 | 48.4-50.4 |
| hz | 48.8 | 47.8-49.8 |
| none | 50.0 | 49.0-50.9 |

**Why it loses.**
- Fuel: the advance doubles out-of-fuel turns. Bigger rosters and more refusals mean more re-searched routes and
  more veto asks.
- But the 4x-fuel runs lose the same, so the cause is the decision itself.
  - In a round where the enemy gets no turn before our next, stepping in is safe for that interval. Leaving
    before its double turn costs little.
  - The step does something meanwhile: a camp hit, contest (a camp tile held every other round keeps resetting
    the enemy's capture), a capture's progress, farm and bank tempo.
- Under the brief's test, "if moving forward was worth it, being there must not look worse once we arrive",
  this pattern is turn-order kiting, not a pair of models that disagree. Pricing the arrival round refuses those
  steps: stuck_fail +52% and stuck_idle +6.5% on the detector, and the win rate falls.
- Keeping the change to farm steps still loses 1 point.

## Detector (vs baselines/v69, ladder+gen+gen-s1+fresh-4104, --bridge-oof, osc_compare against round2-v69, 1196 common games)

| kind | round2-v69 | full (trace of full2) | 1dc5cbfa (final) |
|---|---|---|---|
| retreatchurn | 502,708 | 321,672 (-36.0%) | 476,128 (-5.3%) |
| claimflip | 516,541 | 521,591 (+1.0%) | 528,393 (+2.3%) |
| goalflip | 295,402 | 234,085 (-20.8%) | 292,172 (-1.1%) |
| branchflip | 192,248 | 136,896 (-28.8%) | 186,070 (-3.2%) |
| wander | 69,566 | 67,907 (-2.4%) | 68,968 (-0.9%) |
| stuck_idle | 41,443 | 44,133 (+6.5%) | 45,809 (+10.5%) |
| stuck_fail | 28,993 | 44,126 (+52.2%) | 37,854 (+30.6%) |
| pingpong | 28,118 | 21,972 (-21.9%) | 34,743 (+23.6%) |
| jitter | 25,281 | 19,505 (-22.8%) | 30,905 (+22.2%) |
| preyflip | 5,004 | 4,627 (-7.5%) | 4,708 (-5.9%) |
| **all** | 1,705,304 | **1,416,514 (-16.9%, CI -19.8 to -14.0)** | 1,705,750 (+0.0%, CI -4.0 to +4.3) |
| oof turns | 19,376 | 45,750 (+136%) | 22,287 (+15%) |
| win vs v69 (1708 games) | — | 46.4% (44.1-48.8) | 51.1% (48.7-53.5) |

- The final's small-kind rises (pingpong, jitter, stuck_fail) sit inside the diverged-game noise; its overall CI is
  ±4%.
- The packunseen trace read nearly the same: all -0.2%, retreatchurn -4.0%, pingpong +18%.

## Auditor (read-only, on c62e2604) and responses

1. **High: a stunned enemy whose lost turn falls before our next got this turn's read** (never a hitter). This
   is valid for the full model; it would make it more pessimistic. Not built, since the full model is dropped.
2. **Medium-high: a teleporter with 0 turns before ours is skipped**, though it lands and acts next turn. This is
   valid for the full model too; dropped with it.
3. **Medium: damage taken before our next turn is lost** (the arriving stand starts at full health). Tested as
   now ∪ next (winor, hzor): it loses too.
4. **Medium: paying_soon, hold_outlasts and recall_line still read the current turn.** Left as is: each is more
   pessimistic again in the direction that lost.
5. **Low-medium: the spawn-band exclusion uses the current tile.** Dropped with the full model.
6. **Low: strike-memo `widened` thrash between threat_strike and arriving_strike.** No live caller holds the
   reference; the code is gone in the final.
7. **Low: `in_pack_zone(p, false)` now reads own_ground(p) when p is not the cached tile.** Kept, as more
   correct; comment fixed.
8. **Low: some next-turn reads are more pessimistic than next turn will be** (age-2 drop, Reach vs terrain bound).
   Noted.

Also from the auditor:
- Willow has no veto counterpart. Not done: it needs support.cc's stations guard, outside this scope.
- The farm, bank and chase keep-outs use the old `pack_zone()` boxes. Left as they are.
- No new fuel gate.

## Fuel

- Final: OOF turns 169,493 against 156,363 (+8.4%).
  - The cost is the pack members gathered off our own ground and the next-turn pack test for each neighbour in
    work_around.
  - Plus the believed-hitter stands, whose rosters go to the fight simulation.
- The full model: +130% at 100k fuel per turn.
- bench.py was not run, as this is not a fuel-only change.

## Open

- **The parity step-then-leave (A1's turn-order share) is worth keeping as measured.** A fix that wants it gone
  must price what the step earns during the safe interval, not refuse it. For example: value the work done at q
  over the interval before the enemy's double turn, against the two steps.
- **W2 interaction.** The full model's stuck_fail +52% is the "refusal becomes an idle turn" pattern that W2 fixes.
  If W2 lands, a re-test of full2 (08a70039 flags: all true) on top of it is cheap. Even so, the 4x-fuel result says
  the refusals themselves cost.
- **Willow** (A4) and the strike-search and chase steps (W2) are untouched.
