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
| 2 | Grouping: early, big maps, and as a comeback | LOSSES.md #6 and #7; the user (comeback grouping) | **lost**: the real pack forms (cooked spacing 5.9 to 5.0-5.25) and loses 0.8-0.9 points |
| 3 | Altar bush ambush, and altar warding | the user (2026-11-06); altar.md, comeback.md "ambush", fix-lock.md | **lost or level** on the 1-2 altar subset (-0.1 to -0.5 points; comeback 16.1-16.8% vs 17.4%) |
| 4 | Capture-reset loop fix | LOSSES.md #8 and #10; fix-macro.md section 4 | **level** (the loop is rare locally; four arms H0) |
| 5 | Draft heal price with spawn stands | spawncamp.md "Other gaps" and section 4 | queued |
| 6 | Carry tracking (`carry_w`) measured alone | comeback.md "Carry tracking" | queued |
| 7 | Kill targeting by race `if_kill` | race.md "Not done"; fix-kill.md; comeback.md | built as `es_kill` (item 13's race); +3.8 points on triggered games, in confirmation |
| 8 | Invade minimax, and the draft-time rollouts | invade.md (the user's 2b; "coordinator's draft-time rollout ideas") | queued |
| 9 | Mirror-pull gating on 04sunburst | EXPERIMENTS "Mirror pull" ("the user's call", +0.07) | **dropped: single-map overfit; property gates already tested (lost)** |
| 10 | 10k-parameter NN for gem and gold value | value.md (the user's idea 6) | design written; data and training running |
| 11 | Live test of the perma-lock finalists | EXPERIMENTS "Perma-lock when ahead"; fix-lock.md | **parked**: no perma-lock variant is significant locally |
| 12 | Safer Prism when ahead | the user (2026-11-06, via the coordinator) | **level, slightly positive** against ladder comps (+0.2 points); M 150 in held-out confirmation; banking when ahead loses 9 points |
| 13 | Endgame solver | the user (2026-11-06, via the coordinator); race.md | built (`oc-bl-es*`); deny +5.0 and kill +3.8 points on triggered games (2%), not yet significant; held-out confirmation running |
| 14 | Enemy ward inference | the user (2026-11-06, via the coordinator); bush.md (idea C), CHANGES 421 | **level** (memory -0.2, inference -2.8 points on its 1-3% triggered games) |
| 15 | Deny the bag, not the altar: carrier interception | the user (2026-11-07); EXPERIMENTS "Perma-lock when ahead" round 2; altar.md | queued after 13; design first |

Run order: 1, 2, 4, 12, 14, 13, 15, 3, 5, 6, 7, 8, 10. Item 9 is dropped and 11 is parked. The ids stay fixed as items are
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

**Design (2026-11-07).**
- **Data:** checkpoints every 20 rounds from 61k games at 2x (`bin/valfeat.mjs`), both sides of each: the base
  mirror, against ladder comps, and pk5. Each row is round, tributed, carried, held gold, lifetime gold, living bodies
  and summed health share, for us and for them.
- **Label:** the side's final win. Held out by game (1 game in 10).
- **Model:** an MLP 13-64-64-1 (5k parameters), numpy Adam (`bin/nn_train.py`), against a logistic baseline.
- **Gain test before any bot code:** the implied rate (dP/d(held + earned gold)) / (dP/d(carried gem)) by round and
  lead bins.
  - Roughly flat in state: a constant `per_gold` is already the right shape, so stop.
  - Varying by 2x or more where farm makes choices: build a variant that sets a `per_gold` multiplier from the model
    at a fixed cadence (every 20 rounds, about 10k fuel, clamped to 0.5-2x), then a full paired A/B.
- **Caveat** (value.md): gold correlates with strength, so its derivative is confounded. The A/B decides.

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
8. The lock game (the user, 2026-11-07): lock, re-lock and break-lock timing belong in the scorer (6), not in a
   separate perma-lock gate. Holding a lock is worth it only when the solver says the hold flips the winner.
   Perma-lock gates alone lost or were level (EXPERIMENTS "Perma-lock when ahead").
   Arms (the user, 2026-11-07):
   - **Gated:** the lock moves only on one-altar maps (then 1-2 altars, 2-tile sites); only while their known bags
     exceed our lead; only within K rounds of the race's projected finish.
   - **Learned:** give the solver the features (altar count and site size, lead, their carried bags, our and
     their walk times to the site, lock-break cost, round) and fit when a lock move wins. Use the perma-lock
     round 2 paired games and new census logs as data, and learn per-move value instead of hand gates. Check by
     held-out log loss before any A/B.
   - Compare both against the solver with the lock moves off, on triggered games paired against a base mirror.

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

### 15. Deny the bag, not the altar: carrier interception

Source: the user (2026-11-07), after perma-lock lost. Forensics from perma-lock round 2: while we led, 80% of enemy
landings came from bags already carried that exceeded our lead, and lost leads were lost by round ~480 to the race,
not by round 2000. Holding the altar failed: holders die there, idle or dead 42% of body-turns before a landing.
- **Danger signal:** an enemy's known carried bag, or their bags together, exceed our lead (not "lead >= 1").
- **Action:** intercept the carrier on its route to the altar (from `to_altar` fields and its last-seen tile), not
  stand on the altar. Gate the intercept on the fight sim so the interceptor survives or trades up; the old altar
  guard took 96 against 68 leader gems a game but died 4.4 against 3.5 times.
- **Scope:** one-altar maps first, then 1-2 altars. Coordinate with item 13 (the solver may subsume it as its
  `deny` move) and item 3 (the bush ambush is a static form of interception).
- **Tests:** a trigger-rate census first; then full arms paired against a base mirror on triggered games, at 2x
  fuel; then real budget held out, `--mix varied`, and the panel including bots/fish (mirror bias: Fish locks
  and tributes unlike our mirror).

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

### Method from here: paired full runs

Most of these gates fire in only a few percent of games. On those, SPRT accepts H0 after a few hundred games
whatever the effect, so it is no evidence. Instead:
- every arm plays all 20,480 bl-dev games at 2x (1-2 altar subset: 3,000);
- it is paired game by game against a mirror on the same maps;
- the effect is reported on the games that differ (`bin/pairt.py`), with a 95% CI.

Scripts are in /home/ubuntu/tmp-offload/backlog/bin.

### 2. Grouping, round 2 (the real pack, `oc-bl-pk3` / `oc-bl-pk5`): lost

**Design:** while cooked, the leader is the largest carrier (20 gems or more), else the strongest by health x
(Strength + Focus). Followers more than R from it walk to it before farming; within R, they take its claimed group at
3x. A leader on spawn or recalling leaves the pack off.

**Verification** (2,048 games): cooked nearest-ally distance 5.89 to 5.0 (pk3), 5.85 to 5.25 (pk5), against round
1's 0.1. 41% of follower turns are still more than 3 away (catch-up walks, plus bank, retreat and chase turns,
which come first).

| Arm | Win % (2x, 20,480) | Triggered | On triggered | Overall |
|---|---|---|---|---|
| pk5 | 49.2 | 35.1% | -2.2 (-3.1..-1.3) | -0.77 |
| pk3 | 49.1 | 36.0% | -2.5 (-3.5..-1.6) | -0.91 |

**Verdict:** a real null, worse. A pack that forms costs farm, as the earlier squads, deathballs and packs lost
31-46% (EXPERIMENTS "Shared lesson") and the cohesion leans lost. Don't retry movement packs.

### 14. Enemy ward inference: level

**Measured first (512 games):**
- 12,263 hits on our bodies standing in bushes; 4,069 of them had an enemy ward in the cluster;
- entries into a warded cluster: hit within 3 rounds 25.0% when the ward was unseen, 20.8% when it was known,
  against 3.7% for unwarded clusters.

**Arms** (fixc's bush rank):
- `wm_mem`: a seen ward is remembered until its tile is seen empty;
- `wm_infer` 20: a hit in a bush that no visible enemy and no camp explains marks the cluster for 20 rounds.

| Arm | Triggered | On triggered | Overall |
|---|---|---|---|
| wmm | 2.7% | -0.2 (-4.4..+4.0) | -0.00 |
| wmi | 0.9% | -2.8 (-10.0..+4.4) | -0.02 |
| wmmi | 3.0% | -1.6 (-5.5..+2.3) | -0.05 |

**Verdict:** a hidden bush changes few decisions, and avoiding warded bushes doesn't help. Knobs: `bl::wm_mem`,
`wm_infer`.

### 12. Safer Prism when ahead: level to slightly positive against ladder comps

**Trigger:** in self-play both sides draft the same comp, so the gate (our Prism, no enemy Prism) never fired in
20,480 games, and the early SPRT screens were void. Against oc-base10 on test drafts it holds in 78% / 75% / 65% of
games (M 0 / 50 / 150).

**Arms:** recall line 0.45 and pack-zone ratio 1.5; psm50b also banks instead of keeping the gems. All are paired
against oc-base10 vs oc-base10-td (74.1%).

| Arm | Win % vs td | Triggered | On triggered | Overall |
|---|---|---|---|---|
| psm0 | 74.3 | 61.3% | +0.4 (-0.5..+1.2) | +0.21 |
| psm50 | 74.3 | 52.2% | +0.4 (-0.4..+1.2) | +0.21 |
| psm150 | 74.3 | 33.3% | +0.6 (-0.2..+1.4) | +0.19 |
| psm50b (+ bank) | **65.0** | 73.6% | **-12.4** | **-9.13** |

**Verdict:** banking a winning Prism bag loses badly; Prism's Focus from carried gems is worth more than the early
points. psm150 goes to a 40k held-out confirmation.

### 13 and 7. Endgame race (`oc-bl-es*`): positive on triggered games, not yet significant

**Build:** `model/race` from oc-race, gated to round 1000+ or a side at 500+, with |margin| <= 150 rounds. Knobs off
are identical; with them on, 0 of 16 bench games change, at +1% fuel.

**Arms:**
- `es_deny`: deny any visible tribute whose cancel flips the projected winner;
- `es_bank`: bank now when only that wins;
- `es_kill` 0.5 (item 7): a kill that flips the winner is worth half a win's gems.

| Arm | Triggered | On triggered | Overall | Gate games |
|---|---|---|---|---|
| esd | 1.8% | +5.0 (-0.9..+10.9) | +0.09 | ESD 3 |
| esb | 2.1% | +2.8 (-2.8..+8.4) | +0.06 | ESB 307 |
| esdb | 2.2% | +1.3 (-4.0..+6.6) | +0.03 | |
| esk | 2.8% | +3.8 (-0.6..+8.2) | +0.11 | ESK 2,789 |

esd's gate fires in only 3 games, so most of its triggered games are race::update's fuel diverging (+1% fuel). Its
+5 is probably noise.

**Next:** a held-out confirmation running on bl-conf1, 20,224 fresh maps (s660100-s660178), 40k games at 2x paired:
esd, esk, esdk (deny + kill) and psm150, then esdk at the real budget.

### 3. Altar ambush and warding (on `oc-draftfin-snap`): lost or level

**Build:**
- The ambush bush is a new draft fact (2 x 14 bits, `ab_on` only): a bush tile 2-3 from the altar, most bush
  neighbours first.
- The ambusher is the lowest-index ally carrying under 20; it waits there while cooked.
- `ab_strong` holds fire except at a tributing or isolated enemy.
- `aw_w` weights the altars' tiles in `ward_bushes`.
- The knobs-off copy is identical to oc-draftfin-snap.

**Results** on bl-alt12 (1,500 maps of 1-2 altars, 3,000 games at 2x, paired against the knobs-off copy; mirror
comeback 17.4%):

| Arm | Win % | On triggered | Overall | Comeback |
|---|---|---|---|---|
| ab (wait, strike on sight) | 49.7 | -2.4 (-6.1..+1.4) | -0.33 | 16.6% |
| abs (+ strength gate) | 49.9 | -0.9 (-4.6..+2.7) | -0.13 | 16.8% |
| aw2 (warding) | 49.6 | -2.4 (-7.5..+2.7) | -0.47 | 16.2% |
| aw5 | 49.6 | -2.1 (-6.9..+2.8) | -0.43 | 16.2% |
| abw (ab + abs + aw2) | 49.7 | -1.5 (-5.6..+2.6) | -0.40 | 16.1% |

**Verdict:** taking a body off farm to wait at the altar costs more than its hits gain, as the cooked guards and
the route-flow ambush lost before. Altar warding takes wards from the work. Not a candidate.

### 3, follow-up A: is the gate too weak? No cell holds (offline, no new games)

**Method** (`bin/item3_mine.py`): the paired diff on triggered games of each arm against the knobs-off mirror
(bl-alt12), split by gate-time features read from the mirror's scores:
- altar count;
- the cook round (the first checkpoint cooked);
- the deficit then;
- the enemy's carried gems then.

Cells were found on even-hash maps and checked on odd-hash maps.

**ab / abs** (the cooked gate is the gate itself, so these features are pre-divergence):
- The best found cells fall to 0 on the check half: cook 600-1000 with the enemy carrying under 100, +5.4/+8.1 to
  0.0; deficit 300+, +4.5/+6.0 to 0.0.
- The only cell positive on both halves is 2 altars and cook 600-1000: +1.7/+3.4 then +4.3, about 50 games a half,
  CI about ±14. Noise.

**aw / abw** (warding acts without a gate): the split reads ±20-40. That is selection on the mirror's later cooked
state, not gate time. Mirror-cooked games can only flip up, never-cooked games only down. So it cannot test the gate.

**Not mined:** the fight-sim strength near the altar and the bush-to-route distance need traces, and the brief said
no new games.

**Verdict:** no stricter-gate arm is built.

### Held-out confirmation (bl-conf1: 20,224 fresh maps, s660100-s660178, 40,448 games a run)

At 2x, paired against a base mirror on the same maps.

| Arm | Triggered | On triggered | Overall |
|---|---|---|---|
| esd | 1.7% | **+6.5 (+2.1..+10.9)** | +0.11 |
| esk | 2.6% | **+4.4 (+1.2..+7.7)** | +0.12 |
| esdk | 2.7% | **+4.4 (+1.2..+7.6)** | +0.12 |
| psm150 (vs td) | 33.8% | **+0.8 (+0.3..+1.4)** | +0.28 |

**Real budget, esdk:** 50.0% of 40,448 (CI ±0.5, too coarse for +0.1). Out-of-fuel turns rise 9%: race::update and
current() run every turn.

**Next:** both are ported onto oc-base14 (`oc14-bl-esdk`, `oc14-bl-psm150`) for 40k-game real-budget confirmations
there (chain10). The B1 grid is running (chain8).

### 6. Carry tracking: level

| Arm | On triggered | Overall |
|---|---|---|
| carry_w 0.5 | +0.1 (-1.1..+1.3) | +0.05 |
| carry_w 1 | -0.1 | -0.05 |
| carry_w 2 | -0.8 (-1.8..+0.3) | -0.48 |

The bag weight is already about right. Drop.

### 10. Value MLP: result

- **Fit:** 5.3M rows from 61k games. Held-out log loss 0.434, against the logistic baseline's 0.464.
- **Implied gems per gold** (held + earned gold, per carried gem): 0.10-0.19 in every round and lead bin, so flat.
  The exception is from round 1000 while 150+ ahead, where it falls to -0.10 / -0.19.
- **Verdict:** a constant-shaped price is right, so there is no NN in the bot.
- **The one non-flat cell** gets a table arm, gold at 0 or at half price late while 150+ ahead (`oc-bl-ng0`/`ng05`),
  queued as chain11.

### Real-budget confirmation on oc-base14 (fresh s661100-s661178, 40,448 games, paired against base14 mirrors)

| Arm | Win % | Out-of-fuel turns, cand / ref | Triggered | On triggered | Overall |
|---|---|---|---|---|---|
| esdk | **49.5 (49.0-49.9)** | 327k / 298k | 72.6% | -0.7 (-1.4..-0.0) | **-0.54** |
| psm150 (vs base14-td, mirror 74.4%) | 74.6 | 265k / 287k | 44.3% | +0.5 (-0.1..+1.0) | +0.21 |

- **esdk at the real budget:** the +0.12 at 2x is outweighed by the race model's fuel, +10% out-of-fuel turns. The
  lazy version is next (chain10b: es_gap 400 and a per-round if_kill memo).
- **psm150:** positive but not significant at the real budget. Its oc-base15 knobs-off identity runs in chain13.
- **B1 grid:** the full disk killed 8 of its 11 arms. The three that ran (k75 x w0.25 / 0.5 / 1.0) read -0.6 / -1.9
  / ... with CIs of ±10 on 100-150 triggered games, so the grid is underpowered on bl-esk. The 8 lost arms are
  requeued as chain14.

### 13 and 7 at the real budget on oc-base14: the race's upkeep alone loses ~0.5

These are 40,448-game runs, each paired with a base14 mirror.

| Arm | Win % | Out-of-fuel turns, cand / ref | On triggered | Overall |
|---|---|---|---|---|
| esdkl (lazy: es_gap 400, if_kill memo) | 49.4 (49.0-49.9) | 326k / 299k | -0.8 (-1.5..-0.1) | -0.56 |
| esdkn (lazy, no debug trace) | 49.4 (48.9-49.9) | 331k / 300k | -0.9 (-1.6..-0.1) | -0.61 |
| esdkf (lazy, skipped under 50k fuel) | 49.5 (49.0-50.0) | 320k / 300k | -0.7 (-1.4..+0.0) | -0.49 |
| esu (race::update only, every action off) | 49.5 (49.0-50.0) | 307k / 297k | -0.7 (-1.5..+0.0) | -0.47 |

- **The update alone accounts for the loss.** On bench (default 16 at 100M), esu has 15 of 16 replays identical
  and +0.57% total fuel, about +300 a turn from round 0. It makes 77.7k turns dearer and 2.6k cheaper.
- **So ocean is fuel-tight:** a +0.6% fuel tax costs about half a point, which also argues for exact fuel savings
  in general.
- **Next, `oc16-bl-esw` on oc-base16.** The race has no per-turn upkeep:
  - World's by-round score vector carries the enemy score in its high half;
  - the stale-bag tracking is dropped (its tune terms were 0);
  - there is no per-turn call: Pathing's constructor attaches itself once, and `race::current(world)` recomputes on
    the first read of a round, inside the read window (round 1000 or a score of 500);
  - the actions are esdk's (es_deny, es_kill 0.5, es_gap 400, if_kill memo).
- **Its bench at 100M against base16:**
  - eswoff (knobs off) is identical, 16/16 and 52/52, with equal fuel;
  - esw0 (actions off) has identical replays, 16/16 and 52/52, and +6 fuel a turn (+0.01%), all of it the packed
    score.
  - A first build gated a `race::update` call in main and cost +28 a turn: 22 for the call (play_turn is flattened),
    6 for the packing.
- **Its run:** an identity check (eswoff knobs off; esw0 actions off), then a paired sequential test at the real
  budget against oc-base16-td on the bl-ps16 chunks (H1 +0.25, chain19).

### 10. The late-gold table arm: level

On bl-dev at 2x (20,480 games, paired):
- ng0 (gold at 0 from round 1000 while 150+ ahead) -0.07 points, -1.1 on its 6.9% triggered (CI -2.7..+0.6);
- ng05 (half price) -0.05, -1.0 on 5.3% (-2.8..+0.8).

Overall that is CI about -0.19..+0.04 / -0.15..+0.04 points (the triggered share times the triggered CI), so both
upper bounds are below +0.25. The MLP's cell doesn't transfer. Drop.
- **`oc16-bl-esw` result (paired with the base16 mirror; futility, the CI upper bound below +0.25, applies only from
  20k games):** chunk by chunk -0.57, -0.50, -0.16, then -0.18 at 20,480 games (CI -0.57..+0.22), so it stopped for
  futility. Out-of-fuel turns are still +2% in the window, so the reads cost there too.
- **Next arms (chain21):** `oc16-bl-eswd` (es_deny only, which reads the race only when a small visible enemy
  tribute is in reach) and `oc16-bl-eswf` (esdk, but no race read with under 60k fuel left, `es_fuel`). Both are
  sequential tests on the same chunks.
- **chain21 results (futility only from 20k games):**
  - eswd (deny only) stopped at 25,600 games, +0.01 (CI -0.20..+0.23). It changes 3% of games.
  - eswf (esdk with a 60k fuel floor) stopped at 40,960 games, -0.05 (CI -0.32..+0.21).
- **Verdict on items 13 and 7: level at the real budget on oc-base16 in every form tried.** The +0.12 at 2x doesn't
  survive the real budget, even with the upkeep gone. `oc16-bl-esw` stays as the zero-upkeep base for any later
  race work.

### Decisions on the rest of the queue (2026-11-07)

| Item | Test | Decision |
|---|---|---|
| 12, psm150 on oc-base16 (real budget, vs base16-td, paired) | sequential, H1 +0.25 | futility at 56,320 games: +0.016 (CI -0.18..+0.22) |
| 3, committed cell ab-c2 (2 altars, cooked 600-1000), fired games | sequential, H1 +2 | **H0** at 26,368 games (932 fired): -0.54 (CI -2.41..+1.33) |
| 3, ab on fresh 1-2 altar maps | SPRT 0.50/0.5025 | **H0** at 5,920 games (49.7%) |
| 3, abs | SPRT 0.50/0.5025 | **H0** at 5,296 games (49.6%) |
| 6, cw05 | SPRT 0.50/0.5025 | **H0** at 58,797 games (49.9%) |
| 6, cw1 | SPRT, capped at 80k | undecided at 80,896 games: 50.1% (49.7-50.4), LLR -1.26; level |
| B1 grid on bl-esk (k 75/150/300 x w 0.25/0.5/1, 4,396 games each) | paired | every arm -0.05..+0.05 overall (CIs ±10 on ~190 triggered); the bank arms dkb150/dkb300 -0.23/-0.16 |

### 15. Carrier interception: census, then arms on oc-base16

**Census** (`oc16-bl-icc`: oc-base16 plus ICC prints; 10,240 games at the real budget against oc-base16-td on
bl-ps16-0..1; per game in /home/ubuntu/tmp-offload/backlog/icc-all.tsv):
- **The literal signal is common and harmless.** "We lead and their known carried bags exceed the lead" holds in
  52.6% of games, from a median round 178, for about 61 rounds a game. Those games are won 77.3%, against 74.2% for
  the rest.
- **Landings that cut the lead** (by half a bag or more) come in 10.4% of games, which are won 79.0%.
- **By altar count**, for triggered games:

  | Altars | Win % | Interceptable |
  |---|---|---|
  | 1 | 80-83 | 88-89% |
  | 2 | 77-79 | 84-86% |
  | 3+ | 72-73 | 81-84% |

  Interceptable means a carrier seen within 5 rounds, with an ally's walk to an altar no longer than its own.
- **The dangerous slice is a big bag.** Games with a bag of 100+ come to 7.1%, won 65%; 200+ to 2.8%, won 61%. 93%
  of these are interceptable by that measure.

**Ground truth, ladder against local** (`bin/bigbag.py`, from the extractor's rounds.json: a round where we lead and
an opposing champion carries 100+ gems that exceed the lead):

| Games | n | Win % | 100+ slice | Won in slice | Won outside | 200+ slice | Won in 200+ |
|---|---|---|---|---|---|---|---|
| Local, against base16-td (bl-ps16-0) | 2,400 | 76.6 | 12.2% | 64.7 | 78.2 | 4.5% | 55.1 |
| Ladder, ours (capture and archive, no scrims) | 1,781 | 74.2 | 26.3% | 63.5 | 78.1 | 11.9% | 59.9 |
| Ladder against Fish | 107 | 35.5 | 43.0% | 50.0 | 24.6 | 15.9% | 58.8 |
| Ladder against the top teams | 587 | 75.6 | 29.3% | 65.1 | 80.0 | 16.0% | 54.3 |
| Ladder against the rest | 1,087 | 77.3 | 23.0% | 64.8 | 81.0 | 9.3% | 65.3 |

- **Ladder opponents carry big bags past our lead about twice as often as local opponents** (26% of games against
  12%; Fish 43%). The loss gap inside the slice is the same, about 14 points.
- **So local A/Bs underweight item 15 about 2x.** An arm is judged on its triggered-game diff and scaled by the
  ladder's slice rate, and checked on the Fish panel before any ship.

**Arms** (`oc16-bl-ic`, knob `params::bl::ic_bag`, 0 = off):
- **The trigger:** a known enemy bag of ic_bag+ gems, seen within 5 rounds, that exceeds our lead.
- **Who goes:** the nearest living ally that is not itself carrying a big bag.
- **The move:** it walks to the carrier's route, met halfway down the altar field from its last sighting, gated on
  `safety.fight` there not being lost. Chase and the strike take over once the carrier is in reach.
- **The arms:** ic100, ic200, and ic100x (ic100 also while behind).
- **The test:** knobs-off identity on base16, then sequential tests as above (chain23).

**Item 15 results** (sequential tests at the real budget, paired with the base16 mirror on bl-ps16; futility from
20k games):

| Arm | Fires in | Decision |
|---|---|---|
| ic100 | 3.9% of games | futility at 20k: -0.20 (CI -0.53..+0.13) |
| ic200 | 1.5% | **H0** at 20k: -0.23 (CI -0.55..+0.09) |
| ic100x (also while behind) | 11.1% | futility at 82k: +0.02 (CI -0.19..+0.23) |

- ic100x led early (+0.52 at 15k, CI +0.05..+0.99) and regressed to level. It is still the only arm that reads
  positive on triggered games, and the ladder slice is 2x local, so it is worth a Fish-panel look only if a stronger
  form appears.
- Verdict: level, not merge-ready.

### 13 point 8. The lock game, gated (`oc16-bl-lk1` / `lk2`: race on, deny and kill off, lock moves on 1 / 1-2 altar maps)

- **The gate:** es_race's window, the race lost, their known bags past our lead, and `race::if_altar_locked(a)`
  flipping the winner.
- **It almost never fires:** the walk (LKW) shows in 0.0% / 0.1% of games.
- **The sequential tests stopped for futility:** lk1 at 51k games, -0.00 (CI -0.23..+0.23); lk2 at 20k, -0.17 (CI
  -0.58..+0.24). The changed games (7-9%) come from the race reads, not from locks.
- **Untested as built.** Next: `lk1w` / `lk2w` with `lk_window` off, reading the race from round 1 once their known
  bags pass our lead (the census's danger slice starts at a median round 178).

### 5. Draft heal price: no effect

`oc16-bl-dh05` / `dh0` changed 0 of 5,120 games each; the knobs-off copy is identical on bench. No group on these
maps has every member within our attack range of a spawn tile, so the leads never change. Item 5 is a no-op as
specified, and its value was small anyway (4.6% of maps, leads only). Dropped.

### 8. Invade minimax: the predictor fails exactly where a steal could reach (offline, no arm)

`bin/firstgroup.py` reads 1,777 of our ladder games (willow/analysis). It compares the enemy's first captured group
with the mirror of our own first capture, which is the rollout predictor's guess:

| Their first group: steps from our spawn minus from theirs | Games | Predictor right | Their capture, median round |
|---|---|---|---|
| all | 1,777 | 47.2% | |
| < 0 (nearer us) | 15 (1%) | 0% | 46 |
| 0-4 | 196 (11%) | 11% | 50 |
| 5-9 | 148 (8%) | 40% | 37 |
| 10+ | 1,418 (80%) | 53% | 24 |

A steal can only reach their group before payout where that group is near our side (about 12% of games). There the
mirror predictor is right 0-11% of the time. The flag the design needs, "their likely group is reachable," selects
the maps where the guess is nearly always wrong.

**Verdict:** item 8 is closed without an arm, given every earlier steal form also lost. Reopen only with a better
predictor of their opening (for example, a learned one from the archive's first captures by opponent).

### 13 point 8. The lock game: the held lock, by the rare-gate method

**Why the first arms told us nothing.** Reading from round 1 (`lk1w` / `lk2w`) wasn't enough: the target appeared in
0.1-0.4% of games. A single lock's tune::lock_delay (15 rounds) almost never flips the race.

**The held arm.**
- `lk1h` / `lk2h` price a held lock, `lk_hold` 60 rounds past the lock delay (`race::if_altar_locked(a, extra)`).
- While the solver says the hold flips the race, altar_guard's guard holds the site and keeps it relocked.
- The target then appears in 0.4% / 1.4% of all games.

**The mirror and the test.**
- `oc16-bl-lk2m` is lk2h with `lk_act` off. It makes the same reads and what-ifs and prints LKT, but never locks.
- Games where the mirror fires none are level between arm and mirror, -0.14 (CI -0.51..+0.23). 13% of them still
  differ, from codegen and fuel at the real budget, which is noise with zero mean.
- lk2h was paired against lk2m on the fired games (LKT in the mirror), on the 1-2 altar maps of fresh suites
  s663000-s663129, against oc-base16-td at the real budget, with H1 +5 points on fired games.

**Result: H0** at 42,524 games.
- 841 fired (1.98%): +1.43 on fired (CI -0.90..+3.76), +0.03 overall; flips +56 / -44.
- By altar count: 1 altar, 249 fired, +2.8, median start round 919; 2 altars, 592 fired, +0.8, median start 848.
- The fired games are in /home/ubuntu/tmp-offload/backlog/lkh-fired.tsv (map, side, first LKT line: round, altar,
  margin, altar count; arm and mirror wins).

**The learned arm isn't feasible on this data.** The 841 fired games hold only 100 flips, too few to fit "when a lock
move wins" with any confidence. Item 13 point 8 is closed: a held lock is worth at most about +0.03 overall locally.
On the ladder the big-bag slice is 2x, so that is about +0.06.
