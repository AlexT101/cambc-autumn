# The opening schedule (DRAFT-COMPUTE #5)

2026-10-26. A coordinated opening computed in the draft's 10M-fuel first turn, sent in the plan's schedule section
and used by the farm as a bonus.

- **Round 1:** level (49.7% of 1164 against main 80db5f7); followed strictly it lost (45.4%). The model's plans beat
  the greedy only inside the model.
- **Round 2 (calibration, below):** the model now matches the bot's gems before the first fight (its greedy 102%,
  real job sequences 84%, median capture error 9 rounds), and plans only to its predicted first contact.
  - Followed strictly, its plans still lose: 46.9%, with 3.4% fewer gems by round 300.
  - As a bonus it is level: 51.1% against 80db5f7 and 53.2% against 12c2e69f. A fresh suite (seed 7171) gave 49.0%,
    so the 53.2% did not confirm; pooled, 51.9% of 1,676.
  - The search's predicted gains (median +26%) are its own noise: the same plans score 1.5% worse in a
    near-identical model, and 3.4% worse in games.

## The greedy opening today

The baseline mirrored on the 70 ladder maps (`replays/sched-base-mirror`, one side), rounds 1-300:

- **Champion-rounds:** walking 55.6%, damaging camps 20.4%, on a camp tile (holding, waiting) 10.7%, standing still
  7.8%, dead 4.4%, tributing 1.1%.
- **Transit:** 107,637 rounds in legs between anchors (camp work, holds, tributes, spawn). 31,904 of them (30%) are
  over the shortest walk, mostly tactical: camp to camp 46% over (kiting, retreats, attack-tile changes), hold to hold
  55%, spawn to camp only 16%. A schedule fixes choice, not these.
- **Start:** first camp hit at median round 12, first capture at median round 25.
- **Convergence:** of the groups first worked, 179 had one ally, 84 two, 34 three, 35 four or five; of all clears in
  the opening, 1402 by one ally, 521 by two, 404 by three or more. Mostly deliberate crews on big groups.
- **Map side:** of gems captured (both teams), 18,743 on their own side, 5,490 mid, 2,842 the enemy's.

Nothing here is an obvious coordination failure; the question is whether a searched assignment beats it.

## The model

Python prototype (scratchpad, not committed) then C++ in [schedule.cpp](../../../bots/astraeus/src/schedule.cpp).

- **Groups:** the farmed groups nearest our spawn, each with its mirror (at most 64). Per group: total health, gems,
  gold, respawn, and the camp damage per round of clearing (deadliest first, as `min_camp_damage`).
- **Travel:** one walking field per group centre (mirror rows by symmetry), spawn steps from the steps section's
  fields, one field per altar's tribute tiles (at most 8).
- **Bodies:** our predicted picks (`draft_order()`'s first distinct picks; Cassi and Issac separate), output
  `raw_output` at base stats, base health, attack range.
- **Event simulation, both teams, 300 rounds:** walk to attack range, clear with whoever is there (outputs add), the
  first holder captures (6 rounds), the crew moves on. Camp hits are shared by the workers; one at the recall line
  (35%) recalls (5 rounds), heals and walks back. Bank at the nearest altar at the chain limit (45 gems). Respawns per
  the rules. Value: tributed gems and gold (0.2 gems a gold, `prices()` in round 1) discounted linearly to half at the
  horizon, half of a bag still carried.
- **Enemy:** our farm's greedy rule (rate = worth / (cycle (1 + cycle / horizon)), home_ground weight, crews by share
  of work left, unaffordable groups last) on its side, reacting to us.
- **Search:** the greedy's own choices as the start, then simulated annealing over our plan (replace a job with one of
  the 8 groups nearest the job before, insert, delete, swap, move a job to another body), anytime.

### Enemy models compared (Python, 70 ladder maps, model value summed)

| Search | Ours | Theirs |
|---|---|---|
| Greedy against greedy | 18,305 | 16,599 |
| Against the reactive greedy, 25 / 50 / 100 evaluations, no bank flags | +6.6% / +9.5% / +13.3% | -7% / -9% / -12% |
| Same with a per-job bank flag | +8.1% / +12.4% / +15.4% | -6% / -9% / -10% |
| Against a fixed enemy timetable (from one greedy run), 150 evaluations, scored against the reactive greedy | -17.3% | +14.5% |
| Against our plan mirrored, 1500 evaluations, scored against the reactive greedy | -12.7% (first model) | |

- **Mirrored enemy:** both teams score the same by construction, so it cannot see denial (the coordinator's map
  control idea) and the search only exploits tie-breaks. Plans tuned against it lose to a reacting enemy.
- **Fixed timetable:** half the cost, but plans tuned against an enemy that does not react lose once it does.
- **Reactive greedy:** the only model whose plans hold up, at about 2x the cost per evaluation. In the model, about
  half the gain is denial: the enemy's value falls about as much as ours rises.
- **Early rounds as pure pathfinding** (the coordinator's second idea): the model has no fight model at all, so this
  is already the case. Its cost is the event loop and the enemy's decisions, not fights.

### Calibration (the model's weakness)

The bot's own job sequences (each champion's groups worked, in order, from the replays), replayed through the model
with both teams' real sequences:

- **Timing:** capture rounds are unbiased (median model minus actual +2 rounds) but scattered: median |error| 32
  rounds over 1045 matched captures.
- **Gems:** the model predicts 81% of the gems actually captured by round 300 (21,929 of 27,075); per-map
  correlation 0.60.
- **Two directions of error:** on the bot's real choices the model is pessimistic (81%), on its own greedy it is
  optimistic (17,743 captured by team 0 against 14,146 in the replays). The search maximises the model, so it
  finds where the model is most wrong (the optimiser's curse).

## Draft fuel (round 1; round 2 below)

- **Per evaluation:** 19k-344k (median 142k) in WASM. On 00corners: 245 events at ~570 fuel each, plus the enemy's 44
  decisions at ~2.3k each (16 nearest groups). An event selection over cached times, nearest-group lists and a
  precomputed home-weighted worth cut it from 630k to 240k there.
- **Evaluations:** the search spends what the analysis leaves (8.4-9.9M of the 10M), less twice the costliest
  evaluation above `draft_reserve` + 60k: 19-246 evaluations, median 55, over 4-64 model groups (median 14). The
  model predicts a median +13% from them.
- **Missed picks:** none on 130 maps (70 ladder, 60 `maps/gen`). Fuel left after the schedule: 146k-1.56M, median
  470k. Before the twice-the-costliest margin (1.5x the first evaluation), one map came down to 59k.
- **Order:** the write and the pick come after, as before; the search is anytime and resumable.

## Encoding

The section sits at `schedule_at`, after the ward tiles since 12c2e69f (after the attack tiles before):

- 8 bits: a hash of the body types it was made for. Champions compare their allies' types: a counter rule that
  changes our picks after round 0 makes the schedule ignored.
- 3 bits: bodies. 4 bits a body: its job count (at most 15).
- The jobs round-robin (every body's first, then every second), each a map group index of ceil(log2(groups)) bits.

Fixed-width indices decode for ~20 fuel each. Ranks by distance ("the k-th nearest group") would save about 40% but
cost a pass over the groups per entry (~8k on 50 groups).

- **Size:** 6-53 bytes, median 22 (130 maps).
- **Degrading:** with less space the writer drops the latest jobs first, by lowering the per-body cap. The least
  useful section is 15 + 4 x bodies + one index per body bits (6-8 bytes). With less than that it writes nothing and
  leaves `schedule_at` 0.
- **Champion decode:** at static map build, 0.7-3.3k fuel (median 2.0k) in round 1.

## The consumer

[bot.cpp](../../../bots/astraeus/src/bot.cpp) `follow_schedule`, then two uses in `farm`:

1. **Own entry:** our current entry weighs as last turn's choice does (`stickiness`, 1.2), and the loop reads it
   first when there is no last choice.
2. **Allies' entries:** an ally with no claim posted is taken to claim its entry (`claim_or_entry`, also in
   `crew_work`). At the start, early movers would otherwise take the groups later ones were sent to.

- **Progress:** an entry is passed once its group is held by someone else or captured and back too late to wait for,
  or once the body's claim moves to one of the next two entries.
- **Fallback:** a body's schedule ends at its death, its last entry, round 300, or a claim off it (v2). While an
  enemy is in sight, our own entry gets no bonus.

## A/B results

All `--no-test-draft`, 1164 games (ladder 140, `maps/gen` 512, `maps/gen-s1` 512).

| Variant | Against | Overall | Ladder | gen | gen-s1 |
|---|---|---|---|---|---|
| v1: bonus, schedule followed to its end | 801ed7d | 49.4% (46.5-52.3) | 52.1% | 48.2% | 49.8% |
| v2: v1, ending at a body's first claim off its schedule | 801ed7d | 50.1% (47.2-53.0) | 55.0% | 48.4% | 50.4% |
| v3: v2, the entry as the farm's target while on schedule | 80db5f7 | **45.4% (42.6-48.3)** | 44.3% | 45.9% | 45.3% |
| v2 rebased (the branch) | 80db5f7 | **49.7% (46.9-52.6)** | 52.9% | 47.7% | 51.0% |

Out-of-fuel turns level in every run (v2b 4657 against 4618).

Openings against the baseline in the same games, by round 300, from the replays:

| Variant | Captured | Tributed | Deaths | By 150: captured, tributed |
|---|---|---|---|---|
| v1 | -2.2% | -4.1% | +14% | -0.4%, -2.7% |
| v2 | +0.4% | +0.7% | +1% | +0.8%, +1.4% |
| v3 | -4.9% | -4.2% | -2% | -7.1%, -8.1% |

v3's losses are on every side (own -3.7%, mid -17%, enemy -6%), and its first capture is 4.6% later.

### Diagnosis

1. **v1, stale entries.** A claim matched its scheduled entry on 22% of turns; the first claim matched the first
   entry for 66% of champions.
   - With ±32 rounds of timing error, entries after a deviation assume jobs that never happened. They still pulled
     our champion (stickiness) and, through allies with no claim (banking, recalling, retreating: 17% of turns),
     blocked groups for the rest.
   - Tributes fell 4% and deaths rose 14%. v2 ends a body's schedule at its first deviation, and the harm went away.
2. **v2, a weak bonus.** 74% of first claims follow the first entry; after that the farm overrides the schedule.
   - On 00corners the plan split the team two, two and one. The farm put four of five on the big group 18 by round
     9 (its crew tier), the plan went off at once, and the schedule did nothing measurable.
3. **v3, the plan's quality.** Making the entry the target tests whether the plans are better than the farm's
   choices. They are not: 4.9-7.1% fewer gems captured, 45.4%.
   - Together with the calibration, the model's predicted +7-15% is its own error, which the search seeks out.

## What didn't work, and what would be needed

- **Mirrored enemy and fixed timetable:** both lose against a reacting enemy (above).
- **Following the plan:** a bonus too weak to follow it (v1, v2) or strict following (v3).
- **What would be needed:** a model faithful enough that its plans survive.
  - It would cover spell clears from out of reach (the farm kites wolves with no damage; the model charges every
    ranged body), sleeping camps, the farm's crew rules and real clear times (the 32-round scatter).
  - The search would also have to stay cheap enough for ~50 evaluations of a reactive enemy in WASM (incremental
    re-simulation from snapshots would roughly double that).
  - Until the model predicts the bot's own sequences well (well above 0.60 per map, far below ±32 rounds), a
    searched schedule is unlikely to beat the greedy.
- **The branch (round 1):** kept v2 (level, 49.7%). It cost ~8M draft fuel and 2k a champion in round 1, and changed
  openings by under 1%.

## Round 2: calibration

Data: 80db5f7 against itself, 130 games (70 ladder, 60 `maps/gen`, one side; `replays/sched-cal-*`), rounds 1-300.
Scripts in the session scratchpad: `calib2.py` (one step), `calibjobs.py` and `calib6.py` (rollouts),
`optim.py` (the model's own greedy), `ownplan.py` (the draft's plans), `longclear.py`, `contact.py`.

### One step at a time

Each step predicted from the replay's real state at its start, so that errors do not compound (old mirror data):

| Step | Model / actual, summed | Median error |
|---|---|---|
| Walk spawn to a group | 91% | -2 rounds |
| Walk group to group | 71% | -1 |
| Clears | 69% | +0.8 |
| Clears of 40 rounds or less (91% of clears) | **102%** | +1.0 |
| Camp damage taken | 124% (ranged 158%) | |
| Clear to payout | measured median 7, model range + 6 | |

The physics is right; the error is in the tails.

- **Long clears:** the 9% of clears over 40 rounds hold 47% of clear time.
- **What interrupts them:** of the 459 in the new data, 241 have a recall and no fight, 130 a fight and a recall,
  26 a fight alone. They are heal and bank trips and fights. (A first count, which took self-casts for fights, had
  them all as fights.)

### Rollouts of the bot's real jobs

Each champion's real jobs (in order, with both teams' real jobs), then gems and capture rounds against the replay.

| Model and harness | Gems, all | Median \|error\|, all | Gems before the first fight | Median \|error\| before |
|---|---|---|---|---|
| Round 1 (passing hits as jobs) | 75% | 36 | 75% | 18 |
| Jobs only when the visit ends in a clear or a share | 74% | 35 | 81% | 18 |
| + the replay's holder takes the capture | 74% | 22 | 82% | **9** |
| + hold 1 + 6 rounds after a clear (measured, capfix) | 75% | 22 | 84% | 9 |
| + the replay's own tributes (bankreal) | 77% | 23 | **88%** | 10 |
| + melee workers tank, ranged with spells kite (rules) | 76% | 23 | 86% | 10 |

- **Signed errors:** median +2 to +4 rounds throughout (the model slightly late). By job index the median |error| is
  2 on jobs 0-1, 9 on job 2, 18 on job 3, 35-45 by jobs 4-8: per-job drift compounds.
- **Chain limit instead of the replay's tributes:** 10, 15, 20 or 30 gems instead of 45 give 81-83% before the
  fight, all worse.
  - The bot banks small bags (median 15 gems, quartiles 8-28; 1.5 captures a tribute), but where the altar is
    cheap. A threshold cannot say that.
- **Kiting and tanking:** right by the rules, but they measure slightly worse, so they are left out.
- **What's left before the first fight:** a third of real captures are missed. The model arrives to find the group
  respawning (median 31 rounds left) or held, because a rigid job list cannot re-time itself.

### The model's own plans (where the search exploits it)

| What | Model / actual |
|---|---|
| The model's greedy against the bot, all 300 rounds | 112% (115% with capfix) |
| The same, before the first fight | **101%** (102% with capfix); per-map correlation 0.62 |
| The draft's strict-variant plans, replayed in the Python model, both sides | 92% |

- **Contact:** the first fight comes at a median round 56 (quartiles 29-143).
  - The model has no fights, so its optimism is all after it.
  - Its own contact estimate (a body arriving within 8 tiles of a group an enemy works or holds) gives a median of
    46, a median |error| of 22 and a correlation of 0.44; it comes earlier in 83 of 130 games.
- **Against the targets:**
  - Before the first fight, the targets are met for timing (9-10 rounds) and for the model's own greedy (102% of
    gems), not for rigid real sequences (84-88%).
  - Over the whole horizon they are far off (75-77%, 22 rounds), because of fights.

### The model changes kept (schedule.cpp)

1. **Hold:** 1 + 6 rounds after a clear (was range + 6).
2. **Planned only to first contact:**
   - The greedy-vs-greedy run gives the model's contact; our plan covers jobs begun before it (at least 30
     rounds), then the greedy rule takes over, as the farm does in play.
   - Every plan is scored to round 300.
   - Only jobs begun before the horizon are sent: a median 1-2 a body, 66 bits.
3. **Scoring to 300, not to the horizon:** stopping at the horizon (tried first) let the search game truncation.
   Work in progress counted nothing, and plans favoured small groups that finish in time (+83% on 00corners).

### Round 2 A/B (1164 games, `--no-test-draft`)

| Variant | Against | Overall | Ladder | gen | gen-s1 |
|---|---|---|---|---|---|
| c3: strict (entry as target), calibrated, to contact | 80db5f7 | **46.9% (44.1-49.8)** | 44.3% | 47.9% | 46.7% |
| c2: bonus (v2), calibrated, to contact | 80db5f7 | 51.1% (48.2-54.0) | 48.6% | 52.5% | 50.4% |
| c2 rebased, section after the wards | 12c2e69f (m160) | 53.2% (50.3-56.0) | 49.3% | 54.7% | 52.7% |
| the same, on a fresh suite (`mapgen suite --seed 7171`, 512 games) | 12c2e69f (m160) | **49.0% (44.7-53.3)** | | | |

- **c3's opening against REF:** captured -6.2% by round 150 and -3.4% by 300, tributed -8.7% and -3.7%, mid
  groups -8.8%; deaths level.
- **c2:** out-of-fuel turns 4702 against 4503; rebased 4011 against 4309, and 1788 against 1780 on the fresh
  suite.
- **The rebased c2's 53.2% did not hold on the fresh suite (49.0%):** level, pooled 51.9%.

The strict test still loses, less than round 1's -4.6 points. The plans' check is direct:

- **Draft's prediction:** the C++ search predicts a median +26% (quartiles +8% and +55%) over its greedy.
- **A second model:** the same plans in the Python model (the reference the port matches: greedy 206.0 against
  206.1 on 00corners) score 1.5% worse for us and 1.8% better for the enemy.
- **Real games:** 3.4% fewer gems than REF.

The search finds plans that win on the C++ model's small differences, and the more it searches, the more it fits
that noise.

### Draft fuel and size (12c2e69f, the section after the wards)

- **Missed picks:** none on 139 maps (70 ladder, 60 `maps/gen`, and the 9 dense-camps and tiny-groups maps).
- **Fuel left after the schedule:** 109k-1.59M, median 312k.
- **Evaluations:** 1-203 (median 34) at 22k-499k each (median 197k); the heaviest maps get 1-18.
- **Horizon:** 30-300 rounds, median 46.5.
- **Section:** 35-339 bits, median 67 (8 bytes), at bits 205-5567.
- **Heavy maps:** gen-dense-camps-120205502 gets no schedule, because the analysis and the ward search leave too
  little in round 0 for its greedy stage. It is skipped safely.

### Residuals: what the model cannot capture

1. **Fights:** from the first contact (median round 56) the bot's openings are fights, retreats and heal trips.
   The model has none, and its contact estimate is weak (correlation 0.44). A fight model in the draft would need the
   enemy's real picks (unknown until the last round) and the bot's fight rules.
2. **Re-timing:** a fixed job list cannot follow a game that drifts. A third of real captures before the fight are
   lost to groups the model believes respawning or held. The greedy re-plans and matches 102%; a plan does not.
3. **Banking:** the bot banks by risk and distance terms (bags at stake, recall-to-bank); a chain limit misses them
   by 4-7 points.
4. **Search noise:** with model and reality within ~10% in aggregate, plans chosen for a few points of model value
   are chosen for model noise. A planner would need errors per plan, not per total, smaller than the gains it seeks.
   The checks here show the plans' advantage does not survive a second model.

The schedule's remaining value is the bonus's coordination at the start (level, c2: 51.1%, 53.2%, then 49.0% fresh). The plans themselves are not
better than the farm's own choices.
