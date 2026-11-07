# Backlog queue (ocean, 2026-11-06)

A low-priority serial queue beside the SPSA soup tune. Each item is a variant `bots/variants/oc-bl-<name>`, copied
from `variants/oc-base10`, with knobs in `params::bl::`.

## Protocol

- **Knobs off.** Replays must be byte-identical to oc-base10 at 100M: `tools/fuel/bench.py`, both the default 16
  and the wide 52.
- **Screen.** Against oc-base10, at 2x fuel:
  - fast runner, `--no-test-draft`, `--fuel 200000`, `--sprt 0.50,0.51`;
  - each arm has its own `--sprt-seed` (660001 and up);
  - `--threads 32`, one A/B at a time.
- **A winner** needs all of these:
  - a held-out real-budget A/B of at least 20k games on a fresh suite (`maps/suites/fresh/s660xxx`);
  - then `--mix varied`;
  - then the panel (research/ideas-2026-11-05/PANEL.md).
- **A level item** gets a forensics note (does the gate fire, and is the decision right?) and a record of its
  knobs, for the soup.
- **Live tests.** Only after local significance, and never run from here.

Results also go to EXPERIMENTS.md, "Backlog (ocean, 2026-11-06)".

## Queue

| # | Item | Source | Status |
|---|---|---|---|
| 1 | Tiebreak awareness | comeback.md "Not built"; rules `round_limit` | **level** (too small to measure; right sign) |
| 2 | Grouping: early, big maps, and as a comeback | LOSSES.md #6 and #7; the user (comeback grouping) | farm-lean arms lost or level, but **no pack formed** (0.25 tiles), so grouping is untested; a real-pack arm (movement coupling, cooked only, R 3/5) runs after item 4 |
| 3 | Altar bush ambush, and altar warding | the user (2026-11-06); altar.md, comeback.md "ambush", fix-lock.md | queued after 13; built on `variants/oc-draftfin-snap` |
| 4 | Capture-reset loop fix | LOSSES.md #8 and #10; fix-macro.md section 4 | **level** (the loop is rare locally; four arms H0) |
| 5 | Draft heal price with spawn stands | spawncamp.md "Other gaps" and section 4 | queued |
| 6 | Carry tracking (`carry_w`) measured alone | comeback.md "Carry tracking" | queued |
| 7 | Kill targeting by race `if_kill` | race.md "Not done"; fix-kill.md; comeback.md | queued |
| 8 | Invade minimax, and the draft-time rollouts | invade.md (the user's 2b; "coordinator's draft-time rollout ideas") | queued |
| 9 | Mirror-pull gating on 04sunburst | EXPERIMENTS "Mirror pull" ("the user's call", +0.07) | **dropped: single-map overfit; property gates already tested (lost)** |
| 10 | 10k-parameter NN for gem and gold value | value.md (the user's idea 6) | design first |
| 11 | Live test of the perma-lock finalists | EXPERIMENTS "Perma-lock when ahead"; fix-lock.md | **parked**: no perma-lock variant is significant locally |
| 12 | Safer Prism when ahead | the user (2026-11-06, via the coordinator) | built (`oc-bl-ps`, knobs off identical); screens queued |
| 13 | Endgame solver | the user (2026-11-06, via the coordinator); race.md | design first; queued after 14 |
| 14 | Enemy ward inference | the user (2026-11-06, via the coordinator); bush.md (idea C), CHANGES 421 | queued after 12; measure first |

Run order: 1, 2, 4, 12, 14, 13, 3, 5, 6, 7, 8, 10. Item 9 is dropped and 11 is parked. The ids stay fixed as items are
added.

### 1. Tiebreak awareness

**Evidence.**
- After round 2000, more tributed gems wins, then more lifetime gold, then more kills. A full tie goes to team B.
- 2.4% of oc-base10's local games reach round 2000 (p2-1-held, 20,480 games). 3.0% end after round 1900.
- comeback.md left this unbuilt, because the ceiling is a fraction of a point. That is the reason it is cheap to
  screen and quick to cut.

**Design.** The variant gets the round-2000 projection: `at_limit` for each side, meaning tributed gems plus the
bags whose walk and channel land by round 2000. Knobs:
- `bl::tb_bank`: in the last `tb_rounds`, a bag that can still land by round 2000 banks at the nearest altar. The
  bank skips `tribute_safe`'s kill-window wait when an unbanked bag counts for nothing.
- `bl::tb_deny`: when the enemy's `at_limit` beats ours and the gap is within one visible enemy bag, the
  channel-deny threshold (`deny_gems`) falls to 1 in the last `tb_rounds`.
- `bl::tb_gold`: in the last `tb_rounds`, with tributed gems level (|gap| within `tb_tie`), groups that pay too late
  to tribute keep their gold value. Gold breaks the tie: `per_gold` otherwise falls to 0 at the end.

**Ceiling.** Below 2.4% of games. The screen decides.

### 2. Grouping: early, big maps, and as a comeback

**Evidence.**
- LOSSES.md #7: before r200, Fish's nearest ally is within 4 on 77-80% of turns, against 63% for ours. On big maps
  after r200, the median distance is 4 for Fish and 8 for us.
- LOSSES.md #3 and #6: we initiate without the bodies near.
- comeback.md: comebacks are kills on the leader while not dying.
- Earlier cohesion attempts (EXPERIMENTS "Cohesion, four parallel attempts"): only exact tie-breaks paid (CHANGES
  292). Leans that moved non-tied choices lost. None of them was gated on round, map size or being cooked.

**Design.** One mechanism with three gates. It is pure grouping, not the old hunt: no seeking fights.
- **Mechanism:** a pack anchor, either the strongest awake ally or the claim centre of the crew lead.
  - Farm's group choice is penalised by `grp_w` × max(0, steps from the anchor − `grp_r`) for non-anchor bodies.
  - Retreats tie-break toward the anchor.
  - Path steps prefer tiles within `grp_r` of a visible ally.
  - Fights come only from the existing fight sims.
- **Gates:**
  - (a) `grp_gate=1`: round < `grp_early` (200), or map area ≥ 70×70;
  - (b) `grp_gate=2`: cooked (comeback's cbdp gate, enemy 400+ and 150+ ahead);
  - (c) `grp_gate=3`: both.
- **Check:** under (b), cbdp's mirror pull and deny must still lead the pack to their side's camps together.

### 3. Altar bush ambush, and altar warding

**The user's idea.** On one- and two-altar maps with bushes near an altar, while cooked, hide in the altar's
bushes. Enemies must come to the altar to tribute, so we hit them there.

**Rules that matter** (cambc-rules.yaml):
- Damage does not interrupt a tribute. A stun cancels it, and so does a lock placed within 2.
- A kill takes the victim's whole bag.
- Attacking from a bush does not reveal the attacker. A bush tile cannot be seen from outside.

**Not repeats of these, which lost:**
- the cooked guard (altar.md g1-g5, h1-h6): a visible guard that the leader waits out;
- the e3 cooked guard, kept as the escort (CHANGES 408);
- comeback's route-flow "ambush" bush (t-amb-g4, 48.8%), which was computed in play a slice per turn and held by
  hunters who then took lost fights.

**Pieces:**
1. **Altar choice.** The altar their carriers use, from their past tributes as seen, else the one nearest their
   spawn and camps by walk. On two-altar maps the team may split.
2. **Bush choice**, precomputed in the draft and passed through DraftPlan (draft-features.md, oc-draftcond):
   - candidate bush tiles within strike reach of each altar's tribute tiles (within 1 of the altar);
   - for each tile, its cover against the predicted approach paths.
3. **Strength-gated hit and run.**
   - Wait in the bush until the existing fight sims say our local strength wins. A channelling carrier is the prime
     target, best hit with a stun or a lock to cancel the channel.
   - After the strike, return to the bush or recall to heal, and repeat.
   - Stop once the race margin or the gem lead clears.
4. **Altar warding.** On 1-2 altar maps, with no cook gate, give the altar and its bushes priority for wards.
   Vision is per champion, so choose the body that wards: the one that will fight there.

**Arms:**
- (a) the warding factor only, always on 1-2 altar maps;
- (b) the cooked bush wait, then a strike on sight;
- (c) (b) with the strength gate and the repeat cycle;
- (d) (a) and (c).

**Judging.**
- Develop on a one- and two-altar subset, reporting the comeback rate against oc-base10.
- Then judge on full ladder-mix suites under the usual protocol.

### 4. Capture-reset loop fix

**Evidence.**
- 03colosseum-a (LOSSES.md #10, fix-macro.md section 4) had 1,328 capture resets. Issac stepped onto a lone gem
  cluster (`F`) and stepped off the next turn (`R`), 565 times; Cassi did the same on group 25.
- `fixm::finish_wait` ended that game, but left the loop itself alone.

**Design.**
1. Find the oscillation locally with `tools/replay/osc_detect.py` / `stalls.py` on base10 A/B replays.
2. Add hysteresis. A body that retreated off a hold tile last round does not re-claim the same group for
   `cr_ban` rounds unless the threat it fled is gone. Or the reverse: on a hold tile, the retreat needs the threat
   to exceed the hold's value plus a margin.

**Expected size.** Small, but it is a correctness fix that may also save fuel.

### 5. Draft heal price with spawn stands

**Evidence.** spawncamp.md says the draft's trip-home heal price (`draft.cc type_facts`: `heal` per kite clear) ignores spawn
stands. A group whose strikers reach a stand on our spawn heals for free each turn. This acts only on the ~4.6% of
maps with a group near a spawn, and only through the draft (its leads and the model's features).

**Design.**
- `bl::dh_stand`: in `type_facts`, a group whose strikers all fire on spawn stands gets a heal cost of 0, and its
  damage is charged at `dh_share`.
- If the picks come from the F92 model and not from `type_facts`, the change reaches only round 1's lead guesses.
  Then it is a play change, judged by the same 2x A/B with own drafts; it needs no draft lab.

### 6. Carry tracking (`carry_w`) measured alone

**Evidence.**
- `carry_w` exists only in oc-comeback-dev. There it weighs a hunt quarry's estimated bag (`est_carry`, World's
  last-read bag) against its life.
- The hunts lost, so `carry_w` was never isolated. oc-base10 keeps only snipe's `bar_bag` threshold on the same
  estimate.

**Design.** A carry-weighted target choice in the normal fight path (`fight.cc`'s chase and target worth) instead of
the hunt:
- `bl::carry_w` scales the estimated bag in the target's worth, where gems now count `gem_value` each;
- `bl::carry_stale` optionally decays an unseen bag by its age.

Arms: carry_w 0.5, 1 and 2, each with its own seed.

### 7. Kill targeting by race `if_kill`

**Evidence.**
- race.md gives `if_kill(v)`, whose delta has the expected sign (fix-kill.md).
- Kill refusal on it was level (kr0h 50.0%, at +39-54% out-of-fuel turns). Targeting was never tried.

**Design.**
- Port `model/race.{h,cc}` (oc-race) to the variant.
- Among kill-reachable targets, rank by `if_kill(v).margin() − margin()` when two or more are in reach, and only
  then, since each call costs ~1.7k fuel.
- Gate it to endgame states (a side at 500+), where the margin carries information.

### 8. Invade minimax, and the draft-time rollouts

**Evidence.** invade.md tested the opening steal in every form and it lost or was level:
- whole team, raider, bush raider, sprint, split, hop;
- gates L0-L2;
- mirror pull passes 1-3.

The user's minimax nuance: "they might do the same, but we'll still go their side to scout it". The coordinator's
rollouts were (a) predicting their group by playing our own opening for them, and (b) drafting for interception.
Neither was built.

**Design.**
- A draft-time rollout of both openings: ours as farm would play it, theirs as the mirror policy would. It flags the
  maps where their likely first group is reachable before payout while ours stays covered: the home group is still
  cleared on time by the bodies that stay.
- Then the steal fires only on flagged maps, with the home-return the invade verdict asked for.
- All static analysis is precomputed in the draft and passed through DraftPlan, within the draft's first-turn 10M
  fuel (headroom from `tools/draftlab/firstturn.py`).

**Prior.** Low. Every steal form lost, and the rollout predictor is the mirror predictor (47% on the ladder).

### 9. Mirror-pull gating on 04sunburst: dropped

Dropped: a single-map gate is an overfit. The user meant a map property (sunburst-like: many camps, few
high-value ones), and property gates were already tested in mirror pull passes 1-3 (map, observation, situation and
learned GBM gates). They lost.

### 10. A 10k-parameter NN for gem and gold value

**Evidence.**
- value.md found `per_gold` at its optimum: the late leans lost with a dose-response, and the data's higher late
  rates were confounded.
- The user's idea is inference "when there is leftover fuel". That would be a fuel gate that reads measured fuel,
  which this queue rules out. So any model runs at a fixed cost on a fixed schedule.

**Design first.** Before building, write out:
- the training data: the archive or logged A/B states;
- the label: the final win, by checkpoint;
- the features: tributed, bags, round, map features;
- a fixed evaluation cadence, with its cost: a 10k-parameter MLP is ~10k multiply-adds, ~20-40k fuel at ~1-2
  instructions each;
- the expected gain, against a table of the same shape.

Build it only if that gain is plausibly above the noise.

### 11. Live test of the perma-lock finalists: parked

No perma-lock variant is significant locally: gwin 49.9, g2b500 49.9 and n8l50 49.7 on 20,480 held out, and the
round-2 grid had no winner. By the user's rule, nothing goes live. Reopen only if one becomes significant; even
then, the coordinator runs it, not this queue.


### 12. Safer Prism when ahead

**The user's idea.** Take the case where we have Prism and the enemy doesn't, and our Prism's bag plus our
tributed gems beat the enemy's tributed gems by a margin M. Then Prism plays safer:
- it retreats earlier;
- it refuses marginal fights and chases;
- it keeps within ally support;
- it avoids unseen-enemy zones and bushes;
- it banks at the safest altar.

The case may generalise to any champion carrying a winning bag.

**First**, audit what oc-base10 already does for Prism:
- its itemisation (health?);
- the big-bag break-off and the safest-altar bank (pool b5 and b1);
- `brake_bag`, `hurt_retreat_ratio`, fixc's `bag_big` / `bag_ratio`.

Then build only the missing parts.

**Arms:** M in {0, 50, 150}, plus one or two safety-level knobs. All are tunable `params::bl::` constants, so the
soup can take them later.

### 14. Enemy ward inference (measure first)

**The user's idea.** An enemy hits one of us in a bush when no enemy is placed to see into it. Then an enemy ward
must cover that bush. Treat the bush as visible to all of them, since they may share sightings, and devalue it as
cover. That touches bt3's bush preference, retreat ties, and any ambush or wait logic.

**Rules that matter** (cambc-rules.yaml):
- A bush tile cannot be seen from outside. From inside a bush, your own cluster is transparent.
- A ward sees a 13x13 square (radius 6), shadowcast, and sees its own cluster when placed on a bush.
- Wards never expire. A champion's new ward replaces its old one, at most every 10 rounds.
- Attacking from a bush does not reveal the attacker.

**Inference.** The consistent ward centres are the tiles whose radius-6 shadowcast reaches our bush tile. Intersect
them over observations. Devalue either every bush tile any consistent ward covers, or only the tiles all of them
cover (a knob). Clear the inference when that enemy places a new ward elsewhere, if we see it.

**Existing pieces to extend:** `ward_memory` (bush.md, idea C, level-cut) and the reveal ward (CHANGES 421).

**Measure first.** Count the hits on our bush champions with no visible enemy able to see in, on a ladder-mix
suite. If they are rare, record that and skip.

### 13. Endgame solver (design first)

**The user's idea.** When the race is close, plan the fastest way to the win and compare it with the enemy's.
The plan covers:
- who tributes where and when (channel `ceil(gems/10)` turns of a whole bag; a Tribute emblem cuts
  `floor(0.33 b)` for b > 3);
- altar choice and the walk there;
- the alternatives: a kill (`race::if_kill`), a lock or stun to cancel their channel, a deny.

Then act on the plan that maximises our win probability.

**First, audit what exists:**
- the race model (`model/race`, in oc-comeback-dev and oc-race, not in oc-base10);
- `game_ender` / `stop_game_ender`, `channel_to_deny` and the timed lock (`lock_plan`);
- bank.cc's `closing`, `race_left` and `any_risk`;
- b1's altar choice.

Write the missing parts here before building.

**Constraints:**
- a fixed per-turn fuel bound, evaluated only while the race margin is within K;
- static parts (altar walk fields) precomputed in the draft;
- tested on the close-endgame subset, then on full suites.

**Audit (2026-11-07): what oc-base10 has.** There is no solver, only separate yes/no checks on what we can see.
- **`game_ender` / `stop_game_ender`** (fight.cc:880, 1005; bot.cc:406)
  - What it does: picks the nearest visible enemy whose own bag (or Cassi+Issac's pair bag) reaches 1000 minus
    their score. With our bag winning, it keeps only enemies who land before our `win_lands`.
  - The enemy's walk is crow-flies to the nearest altar (`carrier_tribute`, fight.cc:491).
  - The response is a fixed order: stun, then the timed lock, then attacks.
  - Missing: several enemy bags that win together, unseen bags, teammates' bags on our side, round 2000, and any
    ranking of the options.
- **`channel_to_deny`** (fight.cc:1071)
  - What it does: denies any visible channel of 112+ gems that we can lock or stun in time.
  - Missing: a check that the deny changes the winner.
- **The timed lock** (`LockPlan`, fight.cc:924-1001)
  - What it does: holds one plan, set by `stop_game_ender`, and waits 8-11 steps out of reach.
  - Missing: it never re-plans when a channel restarts.
  - Results: it fires 0.0-0.3 rounds a game (fix-lock.md).
- **bank.cc**
  - `gems_short`, `winning_bag`, `race_left` and `closing` look at our side only. `ally_rate` is our score gain
    since round/2.
  - `any_risk` and `tribute_ok` handle round 2000 for our own channel.
  - `bank_gems` / `safer_altar` scores bags of 150+ gems by threat ETA, walk and ally cover.
  - Missing: enemy bags and timing in the choice to bank or carry.
- **The race model** (`model/race.{h,cc}` in oc-race / oc-comeback-dev, ~500 lines; not in oc-base10)
  - `Race{us, them}`: per side, tributed gems, rate, up to 6 bags (`land`, `walk`, `channel`, `opp`, `altar`,
    `risk`, `locked`), and `we_win()` with the round-2000 tiebreak.
  - What-ifs: `if_kill`, `if_bank_delay`, `if_enemy_banks`, `if_enemy_cancelled`.
  - Cost: ~3.5k a turn (p90 4.9k).
  - Accuracy: endgame winner 0.887 local and 0.852 live (race.md); the bags carry the signal.
  - Its walk is crow-flies to the nearest altar, and its what-ifs are unvalidated. Its one live use, the race gate
    for holds, lost (20.4% / 48.0%).
  - Its dependencies all exist in oc-base10.
- **Draft precompute**
  - What exists: oc-base10 stores per-group steps to the altars (`drafted_altar_steps`). `Pathing::to_altar(a)`
    fields are built by `warm_up` early in play, so per-tile altar fields need no draft slot. They wouldn't fit
    anyway: 8,192 bits, with a p10 headroom of 5.4k.
  - What would fit in oc-draftfin's PlanFacts: small per-altar facts, for example spawn-to-altar steps for both
    sides, the lock-tile distance, and the enemy's exit step.

**What is missing:**
1. Enemy walk times on real fields.
2. Several bags that win together, and unseen bags.
3. Teammates' bags in `win_lands`.
4. An altar choice against the enemy's lock and stun reach.
5. Round 2000 in the stop choices.
6. One scorer over kill / stun / lock / deny / bank.
7. A per-turn fuel cap.

**Minimal build (`oc-bl-es`).**
1. Port `model/race` and gate it on |margin| <= K (`es_k`) so that it costs nothing elsewhere. Replace its
   crow-flies altar with min over altars of `to_altar(a)` steps plus `lock_turns`.
2. `game_ender`: a candidate is an enemy whose cancel (`if_enemy_cancelled`) or kill (`if_kill`) flips
   `we_win()`. Keep the existing executors (`stop_game_ender`, `LockPlan`). Knob `es_ender`.
3. `channel_to_deny`: deny only when the cancel flips the winner, whatever the bag size. Knob `es_deny`.
4. `closing`: bank now when the earliest enemy `land` is before our bag's `land` plus a margin. Knob `es_bank`.
5. Fuel: race plus at most 4 what-ifs, about 8k, only while the gate holds.

Trigger rate first, as for every rare gate: a census copy prints the gate and each would-be change. The arm then
runs in full on the triggered maps, paired against a base mirror.

## Results

(One section per item as it finishes.)

### 1. Tiebreak awareness: level

Variants: `oc-bl-tbg` (`tb_gold` 0.1), `oc-bl-tbd` (`tb_deny`), `oc-bl-tb1` (both), and `oc-bl-tb` (knobs off). The
deny knob was built as designed. The bank knob was not, because bank.cc's `any_risk` already takes any risk on a
last-chance tribute.

**Reach.** Of 20,480 oc-base10-like games, 2.4% reach round 2000.
- 44 of those are tied on tributed gems, 36 at 0-0 (gold decides them; 14 are gift-wrapping mutations with no gold
  at all).
- The rest are decided on tributed gems. The loser's unbanked bag exceeded the gap in 63, almost all of them obese
  bags that no channel could land in time.

**Results.** Paired flips are against the knobs-off copy on the same maps.

| Run | Games | Result |
|---|---|---|
| Round-2000 subset at 2x: `tb_gold` | 682 | +5 net (7 / 2) |
| Round-2000 subset at 2x: `tb_deny` | 682 | 0 (1 / 1) |
| Round-2000 subset at 2x: both | 682 | +5 (8 / 3) |
| The same subset at the real budget: both | 682 | -10 (9 / 19), fuel divergence |
| Held-out round-2000 subset at 2x: `tb_gold` | 550 | +2 (5 / 3) |
| Full screen at 2x: `tb_gold` (seed 660001) | 651 | 50.4%, H0 |

**Forensics.** The gate fires only on tied scores from round 1200. Its flips are 0-0 games that gold decides:
homonoliths, shared-gems and one-gem mutations. The decision is right, at about +0.02 points overall.

**Knobs to record:** `bl::tb_gold` 0.1, `bl::tb_round` 1200. It is a binary gate, of no use to the soup's SPSA.

### 2. Grouping, round 1 (farm leans): no pack formed, so grouping is not yet tested

Variants `oc-bl-grp1/2/3` use the walk penalty (w 0.5, r 5); `oc-bl-grpj1/j2/j2x` use the anchor-claim join (2, 2,
10). `oc-bl-grp` has the knobs off and is identical.

| Arm | Gate | Win % (2x) | Games | Comeback cand / ref |
|---|---|---|---|---|
| grp1 | early or big | 46.1 | 1,764 | |
| grp3 | early, big or cooked | 46.4 | 1,742 | |
| grpj1 | early or big, join 2 | 48.7 | 4,473 | 16.0 / 18.3 |
| grp2 | cooked | 50.1 | 4,495 | 16.2 / 16.5 |
| grpj2 | cooked, join 2 | 50.1 | 3,491 | 17.3 / 17.3 |
| grpj2x | cooked, join 10 | 49.4 | 1,212 | 17.2 / 17.6 |

**Forensics.**
- The gate fires on 98% of follower farm turns with a known anchor claim (trace copy `oc-bl-grpj1-trace`).
- The mean nearest-ally distance moves by 0.25 tiles at most early, and by 0.04-0.1 while cooked.
- Followers keep their own groups (claims, crews and holds outweigh the lean). What changes is which camps they farm,
  and that farm is worse.
- With cbdp's pull on, the cooked pack is no tighter, and its comeback rate is unchanged.

This round did not test grouping, because no pack formed. Next comes a real-pack arm, cooked only:
- the leader (the strongest, or the carrier) picks the camp by farm value;
- followers walk to the leader first when they are more than R from it (R 3 or 5), then take the same camp;
- the pack retreats together, and a recall breaks it until the champion is back.

The behaviour gets verified before the A/B: on cooked self-play, nearest-ally distance must fall to about R+1 or
less. The write-up will also compare it with the cohesion attempts that lost.

**Knobs to record:** `bl::grp_gate`, `grp_w`, `grp_r`, `grp_join`, `grp_early`, `grp_area`.


### 4. Capture-reset loop fix: level, and the loop is rare locally

Variants: `oc-bl-crh` (`cr_hold`), `oc-bl-crb` (`cr_ban` 10), `oc-bl-crhb` (both), `oc-bl-crz` (`cr_zone`), and
`oc-bl-cr` (knobs off, identical).

**Reach.** 512 oc-base10-like games (p2-1-held, 1,024 team-games) were checked with `hold_metrics`:
- 2,216 walked capture resets in all; 48 team-games have 10 or more, 2 have 30 or more, none has 100;
- the worst is 55 (03colosseum-a's 1,328 is a ladder outlier that `fixm::finish_wait` already ends);
- 7 games hold tight F/R loops on one group; the rest of the resets are real fights (a body leaves the hold because
  an enemy arrives).

**One real inconsistency.** `holding_capture_now` (capture.cc) keeps a hold by `winning_bag`, which counts a long
ally channel over the full horizon. Farm prices the same group by `gems_short(tribute_window)`. So one turn says
the group is not needed and the next says it is.
- `cr_hold` makes the hold use farm's test.
- `cr_ban` stops a body that retreated off a group from re-claiming it for N rounds.
- `cr_zone` turns farm's zoning on whether or not a bag is at stake.

| Arm | Seed | Win % (2x) | Games | SPRT | Out-of-fuel turns, cand / ref |
|---|---|---|---|---|---|
| crh | 660007 | 49.9 | 387 | H0 | 27 / 27 |
| crb | 660008 | 50.3 | 3,095 | H0 | 318 / 327 |
| crhb | 660009 | 49.7 | 600 | H0 | 45 / 53 |
| crz | 660011 | 49.8 | 8,770 | H0 | **1,176 / 718** |

**Forensics.**
- `cr_hold` changes very few games (the SPRT stops at 387 because nearly every pair is the same game).
- The ban does not reduce F/R alternation, which stays at about 1.3 loops a game. Most alternations are retreats
  from a real threat followed by a return once it has gone, which is the right decision.
- `cr_zone` costs fuel (+64% out-of-fuel turns) for no win-rate change.

**Knobs to record:** `bl::cr_hold` (a consistency fix, safe to fold in if anything touches capture.cc), `bl::cr_ban`.
Drop `cr_zone`.
