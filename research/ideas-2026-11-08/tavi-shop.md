# Tavi's shop: reserve, respec, Greed by selling, Willow pair (ocean = oc-base25, 2026-11-08)

The user's idea: smarter shop logic for Tavi, who buys shards anywhere and sells items on spawn at full price.
Switches: `params::tavi::` in `bots/variants/tv-*/src/params.h` (dev copy `bots/variants/tv-dev`); all off is
oc-base25 (bench.py `--set wide --test-draft` at 100M: 52/52 replays identical, fuel identical).

## Rules (probe-tavi-sell, cambc 5.0.0)

- A sale off spawn is an error. On spawn a turn may hold any number of sales, of any items and counts, before or
  after buys (the SDK's `invalid_action_sell_already_sold` never fired). Shard 30, emblem 150; the stats go with the
  item (Health sold lowers health and max alike). So a respec on spawn is free and instant.
- Health bought off spawn raises max only (900 -> 975 max, health stays 900), as the YAML says.

## What ocean's Tavi does now (oc-base25)

- Buys every turn, anywhere, with all its gold (`bot.cc` shop(): shards anywhere for `Passive::remote_shop`); never
  sells. Its build follows the learned emblem arms (`emblem_table.h`: Prospector, Hunter, Capture, Bruiser...).
- Drafts: Tavi in 10.7% of ocean's own drafts (survey of 48,640 maps, seeds 1040000-1040189; both sides draft the
  same), 90% of them 5-pick; usually with Willow and Prism (Willow protects Prism). Tavi + Willow without Prism: 1.1%.

### 800 Tavis in 400 self-play games on Tavi maps (`replays/tv-sample400`, decoded)

| | |
|---|---|
| lifetime gold | median 600, p75 1165, p90 1937; 43% earn 750+ |
| gold carried (mean while alive) | median 8.8, p90 13.9 |
| gold at a fight's start (8,738 fights) | 30+ in 0.0%, median 7 |
| spawn visits a game | median 6, p90 16 |
| gold + refund reaching 750 on spawn | 36% of Tavis (first at median round 528); 13% keeping passive emblems |
| champion damage | 50% casts (16.7 casts a game hit a champion), 50% basic attacks |
| camp damage | 25% casts, 75% attacks |
| final build (shard-equivalents) | Strength 52%, Health 40%, Focus 8%; Bruiser 29%, Prospector 15%, Hunter 13%, Durability 11%, Capture 9%, Skirmish 6%, Treasure 6%, Jungle 5%, Power 2% |

Per shard over a game: a Focus shard adds ~16.7 x 16 = 270 champion damage (casts), a Strength shard ~240 champion
damage (~48 attacks) plus ~750 camp damage.

### Ladder (big-arm archive 2026-11-04..07, engine 3.0.0 = cambc 5.0.0, 420,685 Tavi games; 275 top-10 replays decoded)

Full report: `~/tmp-offload/tavi/data-report.md`.
- Tavi picks: overall 27.6%, top-10 teams 9.7% (Mite 42%, Vvvvv 14%, us 7-14%; Fish, BattleCats, Ad Astra,
  NEETCoders, Trzy never). All three top teams that pick her win less with her (Mite 56% vs 73%, us 62% vs 71%,
  Vvvvv 48% vs 56%; not controlled for map or opponent).
- Nobody at the top holds gold: Tavi has the least unspent gold of any champion (end of game median 10, top-10 7);
  fights starting with 30+ gold: Mite 0.7%, Vvvvv 0.1%, us 0.3%, ocean locally 0.1%.
- Selling: 1.15% of Tavi games, almost all 8 teams around rank 500 (who sell to fund Greed). Top-10: only
  caterpillow, 13 times in 2 games, selling and rebuying the same Durability Health emblem on spawn (net nothing).
- Greed: 0.7% of Tavi games (median round 960), 2 of 6,578 top-10 games, none above rating 2150. A logistic on rating
  gap and game length gives Greed +0.39 (+-0.09) above rating 1900, only among weaker teams.
- Builds: Vvvvv 100% Focus, Mite moved Focus -> Strength on 11-07, ours Strength then Health from ~round 400.
  Correlational win terms (Strength-main baseline): above 2150 Focus-main -0.14 (+-0.05); top-10 Focus-main
  -0.39 (+-0.07), Health-main +0.45 (+-0.18).

So no top team does what T1-T3 do; the data argue against Focus at fights (T1, T2) and leave Greed (T3) open.

## Arms and predictions (written before the screens)

- **T1 reserve** (`reserve` X, Power Focus at engage = an enemy in sight within 6; `reserve_trigger` 1 also needs
  damage taken). No failure case in the data for the premise: champion damage per Focus shard is ~1.1x a Strength
  shard's and Strength also farms, so "Focus at the fight" buys ~10% more champion damage for X gold, while X sits
  unspent between fights (fights start every ~80 rounds). Prediction: -0.5 to -2 points on Tavi games, worse at X 300.
- **T2 phase respec** (on spawn, sell the other stat's Power/Bruiser/Greed; Focus in a fight phase, Strength in a
  farm phase; 1: an enemy within 8 in the last 40 rounds, 2: higher score 500+). Only Bruiser/Power stat items move
  (31% of the build); same reasoning as T1: Focus ~= Strength on champions, Strength >> Focus on camps. Prediction:
  0 to -1.
- **T3 Greed by selling** (on spawn, gold + refund >= 750: sell and buy 25 Greed shards = 40 shards' stats). Triggers
  for ~36% of Tavis around round 528, then +60% stats on Tavi for the last third of the game; sell-all loses the
  passives (half the build), keep-passives triggers only 13%. Modes: 1 sell all; 2 keep passives; 3 keep passives
  until the higher score reaches 500 (late gold is worth little), then all; `greed_stat` main / best-priced / Health.
  Prediction: +0.5 to +1.5 on Tavi games for 1 and 3, about a third of that for 2.
- **T4 Willow pair** (Willow protects Tavi at every pick count when no Prism; 3 picks already did). 1.1% of maps.
  Prediction: within +-2 on those maps (Willow then leaves the team's farm to guard Tavi).

Tests: SPRT `0.50,0.5025` against oc-base25 on the Tavi maps only (non-Tavi games are byte-identical, so they
add zero-variance pairs): rates below are Tavi-game rates; overall = x 0.107.

## Results (screens on the Tavi maps of seeds 1040000-1040399, own drafts, SPRT 0.50,0.5025)

Rates are on Tavi games; overall = (rate - 50) x 0.107. Non-Tavi games are identical pairs.

| Arm | Win % (95% CI) of games | LLR, decision | Prediction |
|---|---|---|---|
| T1 reserve 150 | 50.0 (49.4-50.7) of 21,654 | -0.25, undecided at suite end | -0.5 to -2 |
| T1 reserve 300 | 49.8 (49.2-50.5) of 21,654 | -0.79, undecided | worse than 150 |
| T1 reserve 150, hurt trigger | 48.2 (47.3-49.1) of 12,673 | -2.95, H0 (rerun after the disk-full crash) | -0.5 to -2 |
| T2 phase respec, enemy near | 49.8 (49.2-50.5) of 21,654 | -1.38, undecided | 0 to -1 |
| T2 phase respec, late | 50.0 (49.3-50.6) of 21,654 | -0.73, undecided | 0 to -1 |
| T3 Greed, sell all (main stat) | 48.5 (47.1-49.9) of 4,943 | -2.95, H0 | +0.5 to +1.5 |
| T3 Greed, keep passives | 49.9 (49.2-50.6) of 19,996 | -3.00, H0 | a third of that |
| T3 Greed, late (mode 3) | 49.5 (48.4-50.5) of 8,904 | -2.95, H0 | +0.5 to +1.5 |
| T3 Greed, best-priced stat | 49.5 (48.7-50.4) of 14,200 | -3.02, H0 | |
| T3 Greed, Health | 49.3 (48.3-50.3) of 10,221 | -2.95, H0 | |
| T4 Willow guards Tavi (no Prism) | 48.6 (46.5-50.7) of 2,152 (Tavi+Willow maps) | -0.34, undecided | within +-2 |

- **Undecided T1/T2:** each ran the whole suite. Their upper bounds are +0.05 to +0.07 points overall, far below
  the +0.25 bar, so they are rejected by bound: a decision at +0.25 on Tavi games would need ~10x the maps.
- **T4** is not testable at this volume: Tavi+Willow without Prism is 1.1% of drafts, so even +5 points there is
  +0.06 overall. It is not worth forcing compositions.
- **T3 missed its prediction** (forensics: `~/tmp-offload/tavi/scripts/fx.py`, 400 Tavi maps both sides, 36% of
  cand Tavis reach Greed at median round 525). Greed puts 40 shards' stats into one stat, which wipes out the Strength
  and Health balance. `main_stat` picks Focus for Tavi (cast-weighted), so sell-all Greed goes 1425 maxHp, 145 Str,
  110 Focus to 900 / 60 / 510, and the Tavi dies 1.42 times in the last 41% of the game. Greed in Health goes to
  3900 / 60 / 110 and dies 0.58 times, but does little damage. Both lose. The +60% stat total is worth less than a
  balanced build, which is consistent with no top ladder team going Greed.
- No arm reached H1, so there was no held out, panel, merge or live-queue line.
