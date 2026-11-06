# The endgame race model (2026-11-06)

This is one shared estimate of when each team reaches the 1000-gem win. The rules that will use it are being
developed by other agents:
- kill refusal;
- the Tribute emblem price;
- the perma-lock gate;
- banking while the channel can finish;
- channel-interrupt priority.

Here it is purely informational: no decision reads it.

- **Code:** `bots/variants/oc-race` (frozen, `READY`; `oc-race-dev` is the working copy) is `variants/oc-retest-clean`
  (= `bots/ocean` = live v78) plus `src/model/race.{h,cc}`, `model/race.cc` in `unity.cpp`, and one call in `main.cc`
  (`race::update` after `comms::receive`).
- **Behaviour:** `tools/fuel/bench.py` at 100M fuel gives 16/16 replays identical to oc-retest-clean.
- **Scripts:** in the session scratchpad `race/`:
  - `racemodel.py`: the model in Python, with the parameters exposed;
  - `load_local.py`: reads the bot's `RC` trace lines;
  - `load_live.py`: a fog replica for any extracted replay;
  - `evaluate.py`: tuning and the report;
  - `ablate.py`;
  - `crossings.py`;
  - `fidelity.py`.

## Model

The model works from what one body knows at the start of its turn. For each team T it uses the following inputs.

**Tributed gems now.** `S_T` is exact for both teams (rule `hidden_scores`).

**Forward rate.** `rate_T = (S_T(r) - S_T(r - 600)) / 600`, from this instance's own score history (all of the
game so far before round 600). Tributes are exact for both teams. Gold and kills are hidden, so a collection rate
cannot be read for them. The tribute rate already nets out bags lost to deaths.

**Bags: one per living body.**
- Ours:
  - our own and visible allies' bags are exact;
  - an unseen ally's bag is its comms post (`comms::bag_of`, rounded up to 4, capped at 508).
- Theirs:
  - World's belief: the gems last read in sight;
  - zeroed at death and respawn, and when World attributes a tribute landing to that enemy;
  - `age` is the rounds since the bag was exact, and `score_since` their tributed gain since then.
- The tuned staleness terms are both 0: an unseen bag counts at its last-read value.
  - `stale_score` would take off that share of `score_since`.
  - `stale_growth` would add that share of their per-body rate per round of age.
  - Both lost accuracy on the training fold.

**Landing, for each bag of `est > 0`** (and always for our own, which the kill what-if fills):
- `walk`: steps from the bag's position (ours as known, theirs as last seen, else their spawn centre) to a tribute
  tile.
  - It uses `Pathing::to_any_altar()`, the static-wall field that is cached for the game.
  - Our field does not enter the enemy spawn. From there the walk is the best field value beside the spawn, plus 1.
  - From a pocket no walk leaves, the walk is a recall plus the walk from home.
  - It is 0 while channelling.
- `channel`: the turns left if channelling (visible), else `max(1, ceil(est/10))`, less `floor(0.33 b)` with a
  Tribute emblem as last seen.
- `opp`: rounds until the nearest opposing body could stand within 2 of the bag's altar, by Chebyshev distance. The
  altar is the nearest one as the crow flies.
  - For our bags, the opposing bodies are enemies seen in the last 8 rounds.
  - For theirs, they are all of ours.
  - The bag is at **risk** if `opp < walk + channel`.
- `land = walk + channel + 15 if the altar carries the other side's lock + 1.0 × channel if at risk` (rounds from now).

**Projection.** For each team:

    S_T(t) = S_T + sum of est_i over the bags with land_i <= t - r + rate_T × max(0, t - r - 80)

- `P_T` is the first `t` with `S_T(t) >= 1000`. It is extrapolated past round 2000, and is `race::never` (1e5) if a
  zero rate never gets there.
- The 80-round lag is how long gems collected from now on take to be tributed. Without it, the current bags would
  be counted twice (they are part of what the rate measures).
- `at_limit_T = S_T(2000)` counts only the bags that land by then.

**Outputs.**
- `P_us`, `P_them`, and `margin = P_them - P_us` (positive: we finish first, by that many rounds).
- `we_win()`: the earlier `P` if either is at most 2000, else the larger `at_limit` (a tie goes to team B).
- `danger(k)` is `margin < k`.

**What-ifs** re-project a copy of the turn's race. Only `if_kill`'s cost was measured (00quarry, both sides copied);
the others copy one side (~250 bytes, a fuel a byte) and re-project it.

| call | what changes | fuel |
|---|---|---|
| `if_kill(world, v)` | Our bag gains v's bag (both bags for Cassi and Issac) and channels longer from where we stand. Their side loses those bags, and its rate runs at `(alive - dead)/alive` for 60 rounds. | ~1.7k |
| `if_bank_delay(x)` | Our bag lands x rounds later. With `x < 0` it banks now, here: no walk, no lock delay. | one side copied |
| `if_enemy_banks(i, walk)` | Enemy i's bag lands after `walk` steps (-1: as modelled) plus its channel, with no risk or lock delay. | one side copied |
| `if_all_enemies_bank()` | Every enemy bag lands at walk plus channel: the "they would overtake us if they banked" test. | one side copied |
| `if_enemy_cancelled(i)` | Enemy i's visible channel restarts from a whole channel. | one side copied |

## API (`model/race.h`, namespace `aph::race`)

```cpp
void update(const World&, Pathing&);   // main.cc, every turn after comms::receive (done)
const Race& current();                 // computed on the first call of the turn, from the beliefs then
struct Race {
  int round; bool team_a; int self;    // self: our bag's slot in us.bags
  Side us, them;                       // tributed, rate, alive, n, bags[6], projected (P), at_limit
  Outcome base() const; float margin() const; bool we_win() const; bool danger(float k) const;
};
struct Bag { int gems; float est, land; vec2 pos; int16 age, score_since, walk, channel, opp;
             int8 index, altar; bool channelling, fast, risk, locked, routed; };  // index into world.allies/enemies
struct Outcome { float us, them, at_limit_us, at_limit_them; float margin() const; bool we_win(bool team_a) const; };
Outcome if_kill(const World&, const ChampionBelief& victim);
Outcome if_bank_delay(int extra);            // -1: bank now, here
Outcome if_enemy_banks(int index, int walk = -1);
Outcome if_all_enemies_bank();
Outcome if_enemy_cancelled(int index);
Projection project(round, tributed, rate, land[], gems[], n, dip = 1, dip_rounds = 0);  // the raw projection
```

Usage notes:
- **Fuel.**
  - `update` is ~310 fuel a turn (bench: +311 a turn, +0.59%).
  - The first `current()` of a turn costs ~3.5k (mean; p90 ~4.9k). The eager variant measured +6.7% on the bench.
  - A turn that never asks pays only the update.
  - Each what-if copies the sides (a fuel per byte) and re-projects.
- **Bags that are not routed.** A bag with `routed == false` (est 0, not ours) has no walk, altar or opp.
- **Freshness.** The race is computed from the beliefs at the first call. Our own bag after a kill during the turn
  is not in it: use `if_kill` for that.
- **Comparing margins.** Margins far past round 2000 are extrapolations. Compare `we_win()` or `at_limit`, not raw
  margins, when both `P` are past 2000.
- **Constants.** They are in `race::tune` (race.h). Change them only after rerunning `evaluate.py`.

Debug builds print an `RC` line every 10 rounds from every body. It holds round, handle, S_us, S_them, both rates,
P_us and P_them, then one `a<idx>:` or `e<idx>:` token per bag with the fields
`gems,age,score_since,walk,channel_or_-1,opp,flags` (flags: 1 Tribute emblem, 2 locked).
- Unrouted bags are routed inside the free `debug_block`, so the tuner sees every body.
- `racemodel.py` reproduces the bot's `P` within a round on 99.7% of lines (126k lines, 256 games), with the same
  sign on 99.996%. The rest is the instances' score histories differing by a mid-round tribute.

## Validation

### Data

**Local.**
- 768 traced games of `oc-race-dev` against `variants/astraeus-now-1106`, on the ladder and `maps/gen` suites,
  both sides, own drafts, fast runner (A/B `race-dev-v2`: 55.3%). That gives 360k body-views, every 10 rounds.
- The train and test folds split by map (crc32 of the name, so both sides of a map share a fold): 400 / 368 games.

**Live.**
- 560 distinct v78 scrim games (`replays/ladder-scrims/`, read only), against:
  - Intercontinental Fish: 245;
  - Mite: 245;
  - Vvvvv: 40;
  - Ad Astra: 40.
- The live replays carry no stdout (release builds), so `load_live.py` rebuilds the model's inputs from the
  extracted replay. For each of our bodies it uses:
  - its own `sees` for enemy bags;
  - zeroing at death, respawn and a matching tribute landing;
  - positions as last seen by any of ours;
  - our bags as comms posts them.
- Fidelity: on the 256 local ladder games, the replica and the bot's own trace agree on the projected winner in
  99.3% of rounds (median |margin difference| 0, p90 9 rounds).

### Tuning

- Tuning was coordinate descent on the local train fold. The objective was winner accuracy on endgame views (a side
  at 500 or more tributed); the all-rounds objective gave the same window and lag.
- **Chosen:**
  - `rate_window` 600;
  - `lag` 80;
  - `stale_score` 0;
  - `stale_growth` 0;
  - `risk_delay` 1.0;
  - `lock_delay` 15.
- **Train fold:**
  - The best train fold set was window 2000, lag 120 and a 0.1 growth, but it was worse on the test fold for timing
    and gave nothing on accuracy.
  - The live data, tuned on their own, picked exactly window 600 and lag 80, with risk 1.0.
- The landscape is flat beyond the window, the lag and the bags.

### (a) Accuracy

The table gives the predicted winner's accuracy (each body-view counts once).

| | local test | | live | |
|---|---|---|---|---|
| | all rounds | endgame (≥500) | all rounds | endgame (≥500) |
| lead (sign of S_us - S_them) | 0.678 | 0.860 | 0.699 | 0.794 |
| naive (tributed + rate, no bags) | 0.677 | 0.859 | 0.700 | 0.793 |
| bags at face value, banked at once | 0.710 | 0.885 | 0.742 | 0.849 |
| **model** | **0.711** | **0.887** | **0.743** | **0.852** |
| model without the risk delay | 0.711 | 0.885 | 0.743 | 0.852 |
| model without the lag | 0.711 | 0.887 | 0.741 | 0.845 |
| model with a 150-round window | 0.698 | 0.864 | 0.730 | 0.839 |
| first guess (150 / 40 / 0.5 / 0 / 0.5 / 5) | 0.696 | 0.863 | 0.729 | 0.839 |

By leading side's tributed gems:

| leader's S | 0-250 | 250-500 | 500-750 | 750-900 | 900+ |
|---|---|---|---|---|---|
| local test: lead | 0.562 | 0.728 | 0.819 | 0.887 | 0.936 |
| local test: model | 0.596 | 0.763 | 0.855 | 0.901 | 0.938 |
| live: lead | 0.638 | 0.706 | 0.766 | 0.799 | 0.874 |
| live: model | 0.665 | 0.759 | 0.839 | 0.848 | 0.905 |

By rounds to the actual end:

| rounds to end | 0-50 | 51-100 | 101-200 | 201-400 | 401-800 | 801+ |
|---|---|---|---|---|---|---|
| local test: lead | 0.868 | 0.830 | 0.809 | 0.734 | 0.641 | 0.529 |
| local test: model | 0.906 | 0.874 | 0.848 | 0.774 | 0.664 | 0.561 |
| live: lead | 0.853 | 0.807 | 0.784 | 0.743 | 0.648 | 0.614 |
| live: model | 0.949 | 0.903 | 0.871 | 0.799 | 0.675 | 0.615 |

**What adds information:**
- **The bags** (with the long window) add 3-6 points over tributed-only, most in the live games, where bags are
  bigger. Against Fish and Mite, being ahead on tributed gems with 750-900 is right only 80% of the time; the model
  is right 85%.
- **The walk and channel terms** add little to the winner: +0.1-0.3 points over banking every bag at once.
- **The risk and lock terms** add about nothing.
- The timing terms matter for the timing (b), not the sign.

Calibration (local test, then live): the win rate by margin bucket.

| margin | < -400 | -400..-200 | -200..-100 | -100..-50 | -50..0 | 0..50 | 50..100 | 100..200 | 200..400 | > 400 |
|---|---|---|---|---|---|---|---|---|---|---|
| local | 0.26 | 0.35 | 0.35 | 0.37 | 0.46 | 0.59 | 0.65 | 0.68 | 0.75 | 0.79 |
| live | 0.20 | 0.30 | 0.38 | 0.46 | 0.48 | 0.55 | 0.64 | 0.69 | 0.76 | 0.78 |

The margin is monotone and similar locally and live. A rule wanting "we are probably ahead" at 2:1 needs a margin
of about +100. The 0..50 bucket is large because it includes the early game, where both sides project far away.

### (b) Projected round against the actual end

The error is `min(P_us, P_them) - actual end round`, in gem-ended games, by rounds to the end. Each cell is bias /
MAE.

| rounds to end | 0-50 | 51-100 | 101-200 | 201-400 |
|---|---|---|---|---|
| local test: naive | +166/171 | +261/269 | +342/349 | +549/553 |
| local test: instant bags | +57/74 | +107/127 | +190/215 | +445/465 |
| local test: model | +76/77 | +119/123 | +198/210 | +448/463 |
| live: naive | +139/144 | +187/197 | +257/270 | +457/474 |
| live: model | +53/55 | +83/90 | +148/165 | +366/392 |
| live: first guess (lag 40) | +34/36 | +50/63 | +93/125 | +211/262 |

**The projection runs late.**
- Part of this is selection. Conditioning on "the game ends within 50 rounds" picks the views where the winner's
  big bag was about to land.
- The rest is the lag. The 80-round lag that maximises winner accuracy costs about 20-40 rounds of timing bias
  against lag 40.

Rules that need timing should read it accordingly:
- **Comparing the two P values** (as the margin does): that bias is shared by both sides.
- **"Can our channel finish before theirs":** use the bags' `land` directly, not P.

The bags cut the naive error by about 60% close to the end.

### (c) Crossings

`crossings.py` counts crossing events: the projected winner flips to them (or the margin drops below k) while a side
has at least 500 tributed. Each figure uses the first body's view each 10 rounds. The local test fold has 368 games
(166 lost); the live set has 560 (239 lost).

| | local: lost after the event | local: losses with an event | live: lost after the event | live: losses with an event | live: last event to end (median) |
|---|---|---|---|---|---|
| lead flips | 0.55 | 0.20 | 0.44 | 0.19 | 118 |
| naive flips | 0.50 | 0.22 | 0.47 | 0.19 | 101 |
| **model flips (k=0)** | **0.64** | **0.34** | **0.58** | **0.30** | 68 |
| model, margin < 50 | 0.43 | 0.27 | 0.44 | 0.28 | 95 |
| model, margin < 100 | 0.36 | 0.24 | 0.41 | 0.25 | 103 |

- An endgame flip of the model is followed by a loss 58-64% of the time, against a base loss rate of 43-45%.
- It catches about a third of the losses, about 70 rounds before the end.
- Flips of the tributed lead are no better than the base rate.
- Thresholds above 0 fire more often and on safer positions: the sign is the signal.

Two of the outputs gave nothing:
- The first-alarm measure (any flip after round 100) fires in most games and says little: a loss rate of 0.50-0.52
  with one, against 0.24-0.26 without.
- The danger margin `k` carries no extra warning.

## Fuel

`tools/fuel/bench.py` (16 games against hyperion, 100M fuel):

| variant | identical replays | mean fuel a turn | change |
|---|---|---|---|
| oc-retest-clean | | 52,827 | |
| oc-race-dev (lazy: update only) | 16/16 | 53,138 | +311 (+0.6%) |
| eager copy (`current()` every turn) | 16/16 | 56,361 | +3.5k (+6.7%) |

The first build computed the whole race in `update` at about 10k a turn (+24%). In the debug A/B it tripled
out-of-fuel turns (16.4k against 5.4k). What brought it down:
- making it lazy;
- dropping empty bags;
- caching each altar's opposition and the nearest-altar table;
- avoiding host calls (`in_bounds`, `my_record`).

At the real budget:
- The lazy copy changes games only through its +311 a turn. The traced ladder A/B against astraeus-now-1106 read
  59.0% (256 games), against 56.2% for oc-retest-clean.
- Out-of-fuel turns were 2,433 against 2,311 for the reference, the same ratio as the base's 2,357 against 2,242.

## Not done / next

- **Kill refusal.** Use `if_kill(v).margin() - margin()`. The model's kill gain is the victim's bag moved to our
  side plus their rate dip. Validate the sign of that delta on kills in the scrims before gating on it.
- **Smoke test.** A probe game on 03homonoliths printed every what-if every 50 rounds. At r850 (our bag 200, an
  enemy bag 200):
  - base: P_us 919, P_them 893;
  - `if_kill`: 947 / 1080 (our channel is longer, their bag is gone);
  - `if_bank_delay(50)`: P_us 957;
  - `if_all_enemies_bank`: P_them 864.
- **Perma-lock and channel interrupt.** Use `if_all_enemies_bank().we_win()` and `if_enemy_cancelled(i)`. These
  what-ifs are not validated beyond the projection itself.
- **Timing.** A separate, smaller lag for timing-only uses would remove most of the bias in (b). It is not split out,
  to keep one model.
