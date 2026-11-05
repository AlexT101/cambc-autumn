# F: value, the gem/gold exchange rate (ocean, 2026-11-05)

User's idea (6): "consider enemy gems/gold, our gems/gold, map features. perhaps we can make a 'gem/gold' value
function that computes the gem/gold exchange rate. idk how to model this. this can be simple or even like a 10k
param NN, that we inference every few turns when we have leftover fuel."

"Inference when there is leftover fuel" would be a fuel gate (FUEL-GATES.md), so any model must be a table or a
fixed, bounded computation.

## What the bot does

- Farm prices a group at `gems + per_gold * gold` (+ Marcella's tribute gold).
- `prices().per_gold = gold_price_scale (1.408) * gems_share * next_emblem.saved / next_emblem.cost`: the gems' worth
  of farm time the next emblem's gold saves, over our share of the gems still to farm (which reads the enemy's
  score: `1000 - enemy`). It is already state-dependent and falls to 0 at the end.
- The draft's fixed 0.2 only feeds round 1's lead guesses (draft.cc type_facts), not the picks.
- Combat values (life 300, gem 15 and so on) are in enemy health points, not gold.
- History: `gold_price_scale` 1.0 / 2.5 / 3 were all level (EXPERIMENTS ~2563, 2647). The 1.5x scale and the c2
  gold lean earned gold at a level win rate (~2799). Uniform gold 3x in farm lost (46.9%).

## Offline fits (`scratchpad/df/f*.py`)

Logistic P(team A wins | state at a checkpoint), Newton/IRLS in numpy, by checkpoint or by state bin. Exchange
rate = coef(gold per gold) / coef(tributed gem per gem).

1. **Ladder archive** (2026-11-02/04/05, 546k games, both ratings > 2150: 60k): tributed gems, lifetime gold,
   rating difference. Implied 0.86 gems/gold at r100, 0.55 at r300, 0.26 at r600, 0.13 at r1000. This is
   confounded: without carried gems, lifetime gold stands in for untributed captures. The archive has no carried
   gems.
2. **Our A/B replays** (`replays/.analysis`, 33,980 batch games, engine v2_0_0, rows at 16 checkpoints): tributed
   and carried gems, capture gold (earned - 100 x kills), kills, deaths; 20% of games held out.
   - Gold improves held-out log-loss at every checkpoint (e.g. r300 -0.5331 vs -0.5492 without gold).
   - Rate by round: 0.41 (r50), 0.30 (r200), 0.21 (r300), 0.15 (r500-1200), 0.10 (r1400-1600), 0.05 (r1800).
   - Spent and unspent gold have the same coefficient.
3. **The bot's own `per_gold`**: oc-value-trace (oc-base1 + a debug print every 25 rounds) on fresh-514000, 512
   games. Median 0.39 (r50), 0.23 (r200), 0.16 (r300), 0.056 (r600), 0.029 (r1000), 0.018 (r1400). The mean is
   ~1.5-2x the median.
4. **Same state, both sides**: close games (|lead| < 75), binned by the higher tributed score (the bot's progress
   variable):

   | max tributed | data | bot median | bot mean |
   |---|---|---|---|
   | 0-100 | 0.293 | 0.313 | 0.49 |
   | 100-250 | 0.193 | 0.163 | 0.23 |
   | 250-400 | 0.106 | 0.097 | 0.15 |
   | 400-600 | 0.063 | 0.051 | 0.08 |
   | 600-800 | 0.036 | 0.024 | 0.04 |
   | 800-1000 | 0.017 | 0.006 | 0.013 |

   In lopsided games (|lead| ≥ 75) the data reads 2-20x higher, the dominance confound. Pooled, with a lead
   indicator, the leader's and trailer's gold are worth the same: 0.21 at 100-400 tributed and 0.12-0.15 at
   400-800, against the bot's mean of 0.23 / 0.15 and 0.08 / 0.04.

**Reading:** where confounding is smallest, the bot's per_gold matches the data within its own spread. Only past
~400 tributed may the data put gold 1.5-2.5x higher. Enemy gold cannot be read in play (rules hidden_scores), and
the enemy's score is already in `gems_share`.

## Design (knobs `params::value::`)

- `late_mult` M (1 = off): `per_gold *= 1 + (M - 1) * clamp((max(ally, enemy) - 250) / 250, 0, 1)`, applied after
  `prices()`'s cache. The table is the fitted shape (flat to 250, full at 500+), so no fuel gate and ~10 fuel a call.
- Grid: M = 2, 3. Before cutting, also sweep `gold_price_scale` 1.0 / 2.0 on oc-base1: the base changed since the
  last sweep.
- **Expected:** small. Uniform scale changes were level, and late gold choices are few. Applies to games past
  ~250 tributed with gold-bearing groups left.

## Results (EXPERIMENTS "value (ocean, 2026-11-05)")

On df-c1 + df-c2 (fresh-514210..514229), SPRT 0.50/0.51:

| Variant | Win % |
|---|---|
| M 3 | 47.4 (H0) |
| M 2 | 48.9 (H0) |
| M 0.5 | 50.1 (10,240, level) |
| `gold_price_scale` 1.0 | 48.8 (H0) |
| `gold_price_scale` 2.0 | 50.0 (10,240, level) |

**Cut:** `per_gold` is at its optimum. The late lean loses with a dose-response, so the data's higher late rate was
confounded (dominance, not gold's value). Nothing kept.

# Round 2: structural gaps in gold pricing (ocean = oc-combo2, 2026-11-05 evening)

Round 1 tried only scalar multipliers on `per_gold`. An audit of `bots/variants/oc-combo2` (= `bots/ocean`) found
structural gaps; round 2 tests each as a knob in `bots/variants/oc-value2-dev` (`params::value2::`, all off by
default; off, bench.py replays at 100M are identical to oc-combo2: default 16/16, wide 52/52, 64 maps of
fresh-519039 128/128). Against `variants/oc-combo2`, own drafts, fast runner, real fuel, `--sprt 0.50,0.51` on
`maps/suites/merged/v2-dev` (fresh-519000..519038, ladder mix). Variants are `bots/variants/oc-v2-<tag>`
(`replays/value2/mkvar.py`), logs in `replays/value2/`.

| Knob | Gap | Change |
|---|---|---|
| `price_bought` (1) | `prices()` and `affordable_prefix` call `best_emblem` with `shopping` false, so they price `current_emblem`'s pick while `buy_shards` starts the learned arm (`learned_arm`) | set `shopping` around those calls: price what will be bought |
| `ally_gold_weight` w (2) | farm prices a split hold's whole gold (`holders(G) > 1`: big groups, Monoliths), though we get `gold / n` | our share plus the allies' at weight w (1 = off). Gems are the team's score, so whole gems are right; only gold is personal |
| `holder_price_mode` (3a) | the holder choice prices gold at a flat 0.3 | 1: a curve of the higher tributed score (round 1's fitted close-game rates, 0.29 -> 0.017), common to all allies so they still agree |
| `draft_per_gold` (3b) | the draft's lead guesses price gold at a flat 0.2 | 0.4 (round 1's traced early per_gold) |
| `remember_ally_paid` (3c) | an out-of-sight ally's gold rate ignores its Treasure | the rate read when it was last in sight |
| `lump_power` k (4) | gold is priced linearly over the next emblem's cost | gold g at C (f((h + g) / C) - f(h / C)) of per_gold, f(x) = x^k to 1 and linear past it (h our gold, C the next emblem's cost): the gold that completes an emblem is worth more, far from it less. The prunes price gold at k x per_gold, a bound |
| `fight_weight` w (5) | Strength, Focus and Health count only toward camps and heal trips; Skirmish is worth 0 | each emblem's saving gains w x (share of damage taken from champions, prior 500 camp damage) x (1 - P_now / P_b), P = output x max health / damage taken; Skirmish's passive w x share x (1 - 1/1.1), and it becomes a candidate |
| `passive_scaled` (6) | `passive_saved` prices gold at `saved / 150` without `gold_price_scale` | multiply by the scale |

`prices()`'s cache key omits gold held and items; only `lump_power` reads gold held, and it reads it in farm, outside
the cache (its memo context includes it), so the key needs nothing new.

## Round 2 results (SPRT 0.50/0.51 on v2-dev unless "full": all 19,968 games)

SPRT stops read high when they stop on H1 and low on H0; the full runs are the fair comparison. "Changed" is how many
of 128 bench games (64 maps of fresh-519039, 100M fuel) differ from oc-combo2's.

| Variant | Changed | Win % | Games | Verdict |
|---|---|---|---|---|
| 1 `price_bought` | 116/128 | 49.6 | 8,675 | H0 |
| 1 + `gold_price_scale` 1.2 / 2.2 / 3.0 | | 49.5 / 49.8 / 49.7 | 8,118 / 11,314 / 9,397 | H0 each |
| 2 `ally_gold_weight` 0 / 0.5 | 27/128 (w 0) | 50.2 / 50.1 | 14,123 / 15,268 | H0 (level) |
| 3a holder price curve | 0/128 | 49.6 | 1,050 | H0 (identical games stop the SPRT early) |
| 3b `draft_per_gold` 0.4 | 6/128 | 50.0 | 8,838 | H0 |
| 3c `remember_ally_paid` | 0/128 | 48.9 | 663 | H0 (no-op) |
| 4 `lump_power` 1.5 / 2 / 3 | 120/128 (k 2) | 48.5 / 49.4 / 47.1 | 3,706 / 8,585 / 2,309 | H0, dose-response: lumpiness loses |
| 5 `fight_weight` 0.25 / 0.5 / 1 / 2 | 123/128 (w 0.5) | 51.7 / 53.8 / 52.6 / 52.2 | 6,140 / 2,671 / 4,117 / 5,142 | **H1 each** |
| 5 w 0.5, full | | **52.6** (51.9-53.3) | 19,968 | OOF 193.8k / 182.1k |
| 5 w 1, full | | **52.7** (52.0-53.4) | 19,968 | OOF 196.9k / 180.8k |
| 5 w 0.5, prior 2000, full | | 52.4 (51.8-53.1) | 19,968 | |
| 5 w 0.5, no Skirmish candidate, full | | 52.1 (51.4-52.8) | 19,968 | |
| 5 w 0.5, scope 1 (choice only, not in prices), full | | 51.5 (50.8-52.2) | 19,968 | |
| 5 w 0.5, scope 2 (prices only, not the choice), full | | 50.7 (50.0-51.4) | 19,968 | SPRT undecided |
| 6 `passive_scaled` | 120/128 | 49.9 | 10,047 | H0 |

**Reading.** Only the fight term wins, and mostly through what it buys (scope 1 keeps 1.5 of its 2.6 points; scope
2, gold's price alone, 0.7): Health and stat emblems now count for fights too. Its champions finish more emblems
(5.16 begun per champion against 4.70 in 320 games): more Bruiser, Durability and Home Health, some Skirmish late.
The weight is flat from 0.5 to 1 (and 2 in the SPRT), the prior and the Skirmish candidacy matter little. Fix 1's
mismatch is real (116/128 games change) but pricing the learned emblem, which saves less than current_emblem's
argmax by construction, lowers per_gold and loses at every scale. Fixes 3a and 3c never change a game: the holder
comparison only runs with a gold bonus or Marcella in a pair, where the flat price cancels.

Fuel: at 100M the fight term costs nothing per turn (wide set mean 52,358 -> 51,912, >100k turns 6,173 -> 6,200);
at the real budget, wide set mean 51,599 -> 50,600, OOF 888 -> 703. In the A/Bs its out-of-fuel turns rise 6% (w
0.5), mostly on mut-the-pack and shared-gem maps: longer fights, not dearer turns.

## Spreading gold over the team (the user's "fushia style spreading", 2026-11-05 evening)

The user: "fushia style spreading. bc if we always argmax 'value' based on the combination of bonuses and champ
scaling (e.g. higher scaling champs get prioed more for funneling) then everything gets funneled into one champ so see
fushia for how they try to spread".

**fushia.** Not a ladder team: big-arm's capture has no team of that name (teams table: only Rauschen, Kuchh_bhii
match), and no archive day lists one. It is a bot in big-arm's checkout, `~/cambc-autumn/bots/fuchsia/` (excluded
in big-arm's `.git/info/exclude`, so untracked; files dated 2026-10-24, big-arm at 05e475fb), the "fuchsia" of
EXPERIMENTS (2026-10-28, demeter's camp targeting). Copied here unchanged, without build output, as `bots/fushia`;
it builds on cambc 5.0.0. Against oc-combo2 it wins 0.3% (v2-pan, 5,058 games, 62 matches failed): saturated, no use
as a panel member. Its spreading is one rule, in `capture/capture.h`:
- every ally scores each reward group in view for each capturer as `value / (steps + capture_time) x S / (S +
  wealth)`, `S = 2294` ("wealth at which an ally's claim counts half: the poorer ally gets the gold"), wealth = gold
  + 30 x shards owned (an emblem 5 shards), value = gold x its bonus + gems x a gem price in gold (0.62 early to 4.18
  at round 2000); the best pairs are handed out greedily, one ally per group. Its farm choice ignores value (the group
  hittable soonest) and its shopping is a fixed build per type.

**Measured spreads** (Gini of a side's lifetime earned gold over its bodies; capture gold = earned less 100 a kill):

| Side | Games | Gini earned | Gini capture gold | max / mean | Note |
|---|---|---|---|---|---|
| oc-combo2 (v2-dev games, both sides) | 600 | 0.381 | 0.383 | 2.31 | kill gold 15% of earned |
| fushia (vs oc-combo2) | 500 | 0.257 | 0.259 | 1.72 | loses every game; kill gold 5% |
| Intercontinental Fish (ladder 11-04 / 11-02) | 554 / 10,514 | 0.515 / 0.443 | 0.532 / 0.459 | 2.91 / 2.48 | rank 1 |
| Mite | 361 / 7,999 | 0.419 / 0.341 | | 2.44 / 2.12 | rank 2 |
| Pantheon | 337 / 6,302 | 0.384 / 0.301 | | 2.33 / 1.95 | rank 3 |
| Univardisty | 563 / 5,201 | 0.234 / 0.221 | | 1.70 / 1.66 | rank 4-5, the most even |
| Ad Astra, test4 | | ~0.49 | | ~2.7 | |
| BattleCats | 493 | 0.248 | | 1.77 | |

(Ladder: games of 600+ rounds, sides of 3+ bodies and 300+ gold, `replays/ladder-archive/<day>/data`.)
- ocean does funnel: per body, earned gold over the side's mean is Vesper Vale ~2.0-2.2, Marcella 1.6-2.1, Prism 1.4,
  Vendetta 1.35, and Cassi 0.35-0.4, Issac 0.45-0.55, Willow 0.2-0.5. The paths: farm prices gold at our own
  per_gold times our bonus (Vesper's +33%, Cassi's and Tavi's gold_farmer_weight), so gold groups go to those whose
  emblems save most and who are paid most; the holder choice (capture.cc value_holder, outvalues_holders, farm's
  pick_up) hands holds to gold-bonus owners and Marcella; and kills pay the killer. fushia's types spread further
  (Marcella 1.8, Vesper 1.4, the rest 0.55-1.4).
- The ladder does not favour spreading: the top team funnels the most (Gini 0.44-0.52), the next two sit near ocean,
  and the most even (Univardisty, BattleCats) are ranks 4-12. In our own games the side with the higher Gini wins
  more (54-56% above the median), though that is confounded by kill gold going to winners.

**Knobs** (`params::value2::`): `spread_hold` S weighs every hold in holder_value by S / (S + wealth), with wealth as
fushia counts it (ally gold read raw, items as last seen); with `spread_hold_any` (default) holds are compared for
every group, not only where a gold bonus or Marcella is in it. `spread_farm` S scales farm's per_gold by ((S + team
mean wealth) / (S + ours))^`spread_farm_power`: a negative power funnels instead.

**Results** (v2-dev; SPRT unless "full"):

| Variant | Win % | Games | |
|---|---|---|---|
| spread_hold 2294 / 1000 / 500 | 48.8 / 48.0 / 48.6 | 3,428 / 2,543 / 3,178 | H0, lost |
| spread_hold 2294 with the holder price curve (3a) | 49.1 | 4,238 | H0 |
| spread_hold 1e9: every hold compared, no wealth weight (control) | 50.0 | 10,877 | level: the weight is what loses |
| spread_hold 2294 / 500, compared only where before | 48.9 / 46.5 | 2,510 / 1,467 | H0, lost |
| spread_farm 1000 / 300, power 1 | 48.4 / 49.8 | 3,932 / 10,712 | H0 |
| spread_farm 1000, power 2 | 49.2 | 5,948 | H0 |
| spread_hold 2294 + spread_farm 1000 power 2 | 48.0 | 2,827 | H0 |
| **funnel**: spread_farm 300, power -1, full | **51.4** (50.7-52.1) | 19,968 | (SPRT 51.2, H1) |
| funnel: S 300 power -2 / S 100 power -1 / S 1000 power -1 / S 1000 power -2, full | 51.2 / 50.9 / 50.4 / 51.6 | 19,968 each | |
| fight term (w 0.5) + funnel S 300 power -1, full | **53.6** (52.9-54.3) | 19,968 | f5 alone 52.6, funnel alone 51.4: about additive |

**Reading.** Spreading gold loses wherever it is applied, and funnelling it, the opposite, gains ~1.3 points at
every setting tried: with the richer body pricing gold higher (power -1 at S 300: a body with twice the team's mean
wealth of ~1000 prices gold (300 + 2000) / (300 + 1000) = 1.8x), it takes the gold groups and completes its emblems sooner. That agrees with the
ladder's top team (Fish, Gini ~0.5). The user's worry, everything funnelled into one body, does not show as a cost:
ocean's Gini (0.38) sits mid-ladder, and pushing it either way, the gold went better concentrated. The funnel's factor
is read once a turn (allies' wealth only changes in their own turns, ours by buying).

**Confirmed** (`bots/variants/oc-v2-f5sf300mc`: `fight_weight` 0.5, `spread_farm` 300, `spread_farm_power` -1),
on suites no A/B had used:

| A/B | Suite | Win % | 95% CI | Games |
|---|---|---|---|---|
| f5 + funnel vs oc-combo2 | v2-conf2 (fresh-519140..519179) | **53.8** | 53.1-54.5 | 20,480 |
| f5 + funnel vs oc-combo2, `--mix varied` | v2-var2 (fresh-519210..519219) | 53.0 | 51.6-54.4 | 5,120 |
| f5 + funnel vs f5 | v2-conf2 | 50.9 | 50.2-51.6 | 20,480 |

Panel (panel-check-514510; oc-combo2's rate in brackets): astraeus 60.4 (57.9), proteus 58.9 (56.1), demeter 62.6
(59.2), ocean-td 78.8 (76.6), v67 75.1 (71.7); second set on v2-pan2 (fresh-519310..519319): astraeus 61.2 (57.2),
proteus 59.4 (56.6). Every member up, mean +2.9: passes. Fuel: out-of-fuel turns in the A/Bs +11% over oc-combo2
(+5% over f5); the wide bench at 100M reads mean 53,536 (f5 51,912, oc-combo2 52,358), and at the real budget 908
out-of-fuel turns (oc-combo2 888, f5 703). Caching the factor per turn changed nothing, so the cost is the games it
plays, not its arithmetic.

**Shipped** as CHANGES 413-414 (`bots/ocean` = `bots/variants/oc-value2`, frozen as `bots/variants/oc-base3`).

# Round 3: a scaling-aware funnel (ocean = oc-base3, 2026-11-05 night)

The user: "perhaps we funnel harder in some way by considering champ scaling (certain champs make better use of gold,
their shards provide more stats, or their abilities have higher multipliers...) maybe test / learn / tune this".
Dev copy `bots/variants/oc-value3-dev` (knobs `params::value3::`, all off: bench.py at 100M identical to oc-base3,
16/16 default, 52/52 wide, 128/128 pool); variants `bots/variants/oc-v3-<tag>` (`replays/value3/mkvar.py`).

## Does ocean already route gold by scaling?

A body's farm gold price is already its own: `prices()`' per_gold is gems share x its next emblem's saving (from
its own growth, abilities and Focus multipliers, and since CHANGES 413 the fight value) / cost, times its gold rate,
times the wealth funnel. What it lacks is any comparison with the team's other bodies' use of gold. Where ocean's gold
goes (4,096 games of oc-base3 against oc-combo2 on fresh-519100..519107; end-of-game earned gold over the side's
mean, and "base" capture gold: Marcella's 2 tribute gold a gem out, Vesper's +33% divided out):

| Body | earned | base | Body | earned | base |
|---|---|---|---|---|---|
| Vesper Vale | 2.17 | 1.86 | Stellar | 0.84 | 0.97 |
| Marcella | 1.73 | 1.26 | Heart of Ruin | 0.79 | 0.87 |
| Prism | 1.44 | 1.59 | Tavi | 0.68 | 0.78 |
| Vendetta | 1.38 | 1.44 | Willow | 0.53 | 0.61 |
| Varg | 1.01 | 1.08 | Issac | 0.51 | 0.57 |
| Ryth | 0.89 | 1.01 | Cassi | 0.36 | 0.40 |
| Ren | 0.88 | 0.95 | | | |

So the bonuses explain only part of it: a third of Marcella's gold is tribute gold, but Vesper still captures 1.9x the
mean with its bonus divided out, and Prism (no gold bonus) 1.6x, from their own emblem savings and the funnel.

## Which bodies' gold wins (offline fits)

Logistic P(side wins) on the rating difference (ladder), the side's total minus the opponent's, and per type the
body's emblems (ladder) or earned gold (ours, per 150) above its side's mean, both sides folded into one coefficient,
Ryth the reference, centred (`scratchpad/v3/ladder_fit.py`, `fit_ours.py`). Ladder: 2026-11-02 (engine 2.0.0), games
with a top-50 team, round 600, 34,202 sides; an emblem in the side's total is worth +0.226. Ours: the 4,096 games
above at round 600, 6,510 sides; 150 gold in the total +0.282.

| Body | ladder beta (se) | ours beta (se) | Body | ladder beta (se) | ours beta (se) |
|---|---|---|---|---|---|
| Prism | +0.106 (0.016) | +0.168 (0.029) | Ren | -0.028 (0.024) | +0.045 (0.053) |
| Marcella | +0.075 (0.009) | +0.038 (0.031) | Varg | -0.017 (0.018) | +0.027 (0.043) |
| Vesper Vale | +0.063 (0.009) | +0.042 (0.029) | Heart of Ruin | -0.036 (0.011) | -0.037 (0.036) |
| Vendetta | +0.056 (0.010) | +0.037 (0.035) | Willow | -0.048 (0.010) | -0.095 (0.047) |
| Ryth | +0.027 | +0.006 | Issac | -0.015 (0.019) | -0.146 (0.035) |
| Tavi | +0.020 (0.014) | -0.300 (0.149) | Stellar | -0.196 (0.104) | +0.189 (0.135) |
| Cassi | -0.006 (0.017) | +0.027 (0.037) | | | |

Both agree that gold on Prism, Marcella, Vesper and Vendetta wins more, and on Willow, Issac and Heart of Ruin less:
the direction ocean already routes in. These are correlations (a body that farms well both earns and wins), so the
tables are tested in play, not trusted. Tables (1 + shrunk beta / the total's beta, shrinkage tau 0.05), in type
order Ryth, Vesper, Vendetta, Cassi, Issac, Stellar, Prism, Marcella, Willow, Ren, Varg, Tavi, Heart of Ruin:
t1 (ladder) 1.11 1.27 1.24 0.98 0.94 0.84 1.42 1.32 0.80 0.90 0.93 1.08 0.85; t2 (ours) 1.02 1.11 1.09 1.06 0.65 1.08
1.45 1.10 0.82 1.08 1.05 0.89 0.91; t3 (their mean) 1.06 1.19 1.16 1.02 0.80 0.96 1.44 1.21 0.81 0.99 0.99 0.99 0.88.

## Variants (farm's per_gold x (ours / the team's mean)^p, after the wealth funnel unless "no wealth")

- e1: efficiency = the fight power (output x max health) an emblem's 5 shards in the body's best stat add, times its
  gold rate (absolute, so it grows with the body's other stats: a funnel by scaling). e2: without the rate.
- t1-t3: the type tables above. h1: the same efficiency on the gold part of holder values (h1any: holds with gold
  compared whatever the bonuses).
- tune: SPSA (`tools/tune`) on the 13 type weights from t3, p 1.
