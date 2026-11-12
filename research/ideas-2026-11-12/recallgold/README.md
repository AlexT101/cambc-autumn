# Unspent gold in the recall value (charybdis-p3 = CHANGES 519, 2026-11-12)

User idea: "consider unspent gold in recall value formula. can be multiple variants say a % of (all gold earned +
constant) or differ depending on game state / time."

## How a recall is valued today

Rules: a recall moves a champion to its own spawn in 5 turn ends (3 with Home); any damage or a stun cancels it. Gold
is spent only on one's own spawn or while dead (Tavi anywhere), 30 a shard. So gold carried on a recall becomes stats
when it lands, and cancelling one puts that purchase off. Death does not lose gold, because a dead champion can still shop.

charybdis has two recall values:

- **Enemy recall** (`params::recall_value` = 66.3 enemy health points, an SPSA constant). The strike search,
  `hit_worth_of`, `stun_worth` and the basic-attack picks add it for a blow that cancels a visible enemy's kept recall.
  `turn_order.cc` uses a fixed copy, `turn_recall_value` = 60, which needs its value mod 15. The enemy's gold is
  hidden.
- **Own recall stop** (`HomeTrip::value`, `FarmRecall::value` in `economy/shop.cc`). It prices trips by way of spawn:
  banking via spawn, the recall out to farm, and `capture_recall`. The stop is worth the heal, plus the next emblem's
  gain only once our gold completes that emblem. Gold that buys only shards is worth nothing in it.
  `wants_shop` already prices the whole purchase (`affordable_prefix`, CHANGES 123).

## Data (charybdis 517 against the rt bodies, 2,560 games at 200k; `recalls.py`, `predict.py`, `fit.py`)

- Bodies' kept recalls (channel left 3 or less) that our blow cancelled: 3.2 a game. They carried 101 gold on
  average (median 22, p90 290).
- What a bot can read about that gold:

  | predictor | R² |
  |---|---|
  | the round | 0.008 |
  | our own team's mean earned gold | 0.003 |
  | the higher tributed score | 0.024 |
  | gold the enemy's stats show it spent | 0.097 |
  | the victim's true earned gold (hidden; upper bound) | 0.19 |

  "Spent from stats" is shards = the sum over the three stats of (stat - base) / growth, with Ryth's Strength from
  Health and Prism's Focus from gems taken out. It correlates 0.998 with true spent gold. The fit is gold = 25.6 +
  3.3% of 30 x shards. That is the user's "% of gold earned plus a constant", from readable data.
- Our own side holds more gold. Gold on our kept recalls that were cancelled: 246. At game end: 156 a champion,
  against the bodies' 47.

## Variants (all against `variants/charybdis-p3`; patches here)

Enemy side: `recall_worth(world, e)` replaces `recall_value` for recall cancels. It keeps the mean at 66.3 (Ḡ = 101),
so only the spread changes. Teleport cancels and turn order are unchanged.

- `rg-s100`: recall_value × Ĝ/Ḡ, where Ĝ = 25.6 + 0.0328 × spent-from-stats.
- `rg-s50`: recall_value × (0.5 + 0.5 Ĝ/Ḡ).
- `rg-score`: the game-state/time form. Ĝ = 39.6 + 0.114 × the higher tributed score (fitted the same way).

Own side: the stop is also worth what all our gold buys there (`stop_gold` = scale × `affordable_prefix(world).gain`,
in rounds). It takes the larger of that and the completed-emblem value.

- `rg-own`: scale 1.
- `rg-own75`: scale `shop_gain_scale` (0.751), as `wants_shop` prices a trip.

None of the shares or scales is a swept free constant. The fits come from replays, and the two scales are 1 and the
bot's own shop scale.

## Results against charybdis-p3 (fgate, 200k, pool batches 0-11; `p1.sh`)

| arm | win% (95% CI) | fresh maps (CAND games) | Fish | Mite | games differing | verdict |
|---|---|---|---|---|---|---|
| rg-s100 | 49.99 (49.93-50.05) | 10,240 (40,960) | +0.00 | -0.03 | 41 a batch (0.2%) | no effect; stopped at 5 batches |
| rg-s50 | 49.98 (49.94-50.02) | 10,240 (40,960) | -0.03 | -0.01 | 17 a batch | no effect; stopped |
| rg-score | 49.98 (49.94-50.02) | 10,240 (40,960) | -0.01 | -0.02 | 23 a batch | no effect; stopped |
| rg-own | 49.61 (49.31-49.90) | 20,480 (163,840) | 49.63 | 49.58 | ~1,970 a batch | REJECT (8 batches) |
| rg-own75 | 49.65 (49.42-49.88) | 30,720 (245,760) | 49.51 | 49.78 | ~1,850 a batch | REJECT (12 batches) |

The enemy-side rows were stopped after 5 batches. Their LLRs had long passed "not +0.5" (high -164) and their reads
were 0.00 ±0.06. The Fish and Mite columns of those rows are fresh-map deltas in points. For the own-side rows they are win%.
On one-site maps the own-side arms were level (50.05, 50.00). The loss is on multi-site maps (49.43, 49.51).
No arm was run at 100k: none had a 200k gain, so no out-of-fuel read was taken.

## Mechanism (b000 parts p0,p1: 2,560 paired games a bot against both bodies at 200k; `mech.py`)

| per game, CAND - REF | rg-own | rg-own75 | rg-s100 |
|---|---|---|---|
| our recalls landed (REF 44.3) | +2.69 (+2.32..+3.08) | +2.04 | +0.01 |
| gold held while alive, a champion (REF 60.5) | -8.3 (-10.1..-6.2) | -5.6 | -0.1 |
| team gold at game end (REF 868) | -61 (-91..-24) | -47 | -2 |
| team gold carried at deaths (REF 180) | -27 (-44..-8) | -22 | -0.4 |
| gold on our kept recalls the enemy cancelled (REF 1082) | -178 (-271..-79) | -78 | -2 |
| lifetime gold earned (REF 5727) | -22 (-83..+49) | -38 | -1 |
| enemy kept recalls we cancelled (REF 3.24) | +0.02 | +0.12 | +0.02 |
| games won | -0.2 pts | -0.6 pts | +0.1 pts |

- **Own side.** The change does what it says. We go home about 3 more times a game and hold 14% less gold. We end
  games with 61 less unspent gold, and we lose less gold to cancelled recalls. Earning drops slightly from the
  extra trips, and win rate falls. The base's step function (gold counts only once it completes an emblem), plus
  wants_shop's whole-purchase price, already spends gold about as well as these forms. Lowering the scale (own75)
  moves the result toward zero, not past it.
- **Enemy side.** Re-weighting `recall_value` by the enemy's expected gold almost never changes a decision. A blow
  on a recalling enemy is taken for its own worth either way, and only 0.7-2.4% of games differ. The gold at
  cancels stays at about 101 in every arm.

## Recommendation

Merge none. The enemy-side recall value does not depend on gold in any way that matters, because the bot's choices
do not hinge on it. The own-side stop already prices gold well enough. Valuing partial purchases sends us home more
and loses about 0.35-0.4 points on multi-site maps. psafe-a, our Prism's recall/heal before a game-ending tribute,
does not interact with these arms: `home_trip` returns before pricing gold for a winning bag, and the enemy-side
change never touches our own recalls.

Files: `recalls.py`, `predict.py`, `fit.py` (data), `mech.py` (paired mechanism), `p1.sh` (gates), `rg-*.patch`.
Logs and extracts: `~/tmp-offload/recallgold/`.
