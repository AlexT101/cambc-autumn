# CALYPSO: macro refactor of charybdis (2026-11-11)

**Outcome: no candidate beat the reference; `bots/charybdis` is left unchanged.** Best 10k+ readings: pr-bonus3 49.3%
(dev) / 50.5% (holdout + standard), cal-f 49.2%, cal-a 49.2%. The tried designs are kept as diffs against charybdis in
`patches/` (variants are git-ignored), the analysis scripts in `scripts/` (run on `extract.mjs --out` directories),
and the implementer briefs beside this file.

Reference: `bots/variants/charybdis-ref` (charybdis at 81fc6f968). All A/Bs at `--fuel 200000`, own drafts
(`--no-test-draft`), fast runner. Suites: `maps/macro-dev` (5,120 ladder-v2 maps, 10,240 games), `maps/macro-holdout`
(1,280 maps), standard `ladder,gen,fresh`. Subsets of macro-dev for probes: `macro-dev1500` (first 1,500 maps).

## Baseline measurements (charybdis vs itself, 400 macro-dev maps, 800 team-games; `tools/replay/macro_stats.py`, `analyze.py`)

- Games end at 1000 gems in ~845 rounds on average; only 14/400 reach round 2000.
- Time: walking ~53% of alive time (with a bag 27%, without 25%), attacking camps 19%, holding captures 5%,
  recall channel 6%, dead 4% (winners) / 11% (losers). Walks back out from spawn or a recall are ~21% of alive time.
- Recalls: ~44 a team-game; 45% start at full health (recall as travel/banking), 57% carry gems.
- Winner vs loser: deaths 2.3 vs 6.5, kills 6.5 vs 2.3, carried gems lost 61 vs 288 a game, capture gems 1053 vs 904,
  gold earned 5706 vs 4623. The bags lost in deaths are the largest single winner/loser difference.
- Captures are 84% own-side by round 600; both teams together capture ~36% of the camps' production
  (camps are not supply-bound; walking binds).
- Fights (analyze.py, net-swing outcome by start state): more lifetime gold (items) present wins 83%, more carried
  gems 81%, more HP present 78%, initiative 66%, more champions 63%; the side fighting in its own half wins only 32%.
- Death risk per 1000 champion-rounds: ~0.13 with no enemy seen in the last 5 turns, ~3.2 after seeing one (25x).
- Lead in tributed gems at round 300 wins only 60%: games are decided late, mostly by fights and bags.

## Experiments

- Big bags decide games: 265 deaths with 100+ gems in 400 games, the victim's team wins only 15%. 80% of those
  victims are Prism (its Focus hoard: `keeps_gems` keeps every gem until the bag wins), 77% of killers too. None died
  channelling: they die retreating (R for the last 3+ turns in most debug traces), banking a winning bag (B) or stopping
  the enemy's game-ender (E). The bigger Prism bag at round 300/400/500 wins 61/68/71% of Prism mirrors (tributed lead at
  300: 60%).
- A/Bs are fast: 3,000 games in ~1.3 min wall when the box is quiet.

### Knob probes (macro-dev1500, 3,000 games each): is the macro landscape flat along tuned constants?
| probe | change | win % |
|---|---|---|
| p-home | home_power 1.89 -> 0.95 (enemy side less discounted) | 49.8 |
| p-haz | carrier_hazard x2 (smaller bags banked) | 50.9 |
| p-gold | gold_price_scale x1.5 | 50.5 |
Flat (within ±1.8 noise): the tuned constants sit near optima; gains need new structure, not retuning.
| p-purs3 | pursuit_steps 2 -> 3 (leave earlier before contact) | 48.9 |
| p-hrr | hurt_retreat_ratio 3.34 -> 2.0 (hurt or bag carriers give way sooner) | 50.1 |
| p-gemv | gem_value x2 (fights value carried gems more) | 51.0 |

### Prism hoard probes (macro-dev1500, 3,000 games each): the hoard is the game's dominant mechanic
`keeps_gems` keeps all of Prism's gems (+1.5 Focus each) until its bag wins. Capping it:
| probe | change | win % |
|---|---|---|
| pr-nohoard | Prism banks like everyone | 28.7 |
| pr-cap300 | Prism keeps gems only below 300 | 34.8 |
| pr-cap600 | below 600 | 48.4 |
The hoard is worth ~21 points against a hoarding opponent; even 600-gem caps lose. Prism already takes ~54% of its
team's capture gems by round 600 and ~77% of kill gems. The Prism with the bigger bag wins the Prism duel (narrative,
probe2-011: an 844-gem Prism kills four of ours in one round with its 3x3 ground spell while our 736-gem Prism keeps
starting and cancelling a 74-turn winning tribute at the mid altar). Direction: more hoard, better protected, and the
enemy hoard as the prize, not less.
| pr-nowin | Prism keeps a winning bag unless its channel is <= tribute_window (never a long winning channel) | 42.4 |
| pr-bonus3 | carried_bonus x3 (captures valued more for Prism's Focus) | 51.3 |
Cashing the winning bag matters: most games end with one big tribute (401 completed 200+ gem tributes in 400 games,
90% by the game's winner; channel median 41 rounds). But 2,652 such channels start and 2,184 are cancelled; one
completes ~45% of the time with no enemy within 10 tiles at its start and 5-15% with one or more. The endgame is
the race to open a ~40-round window at an altar.
| p-tw25 / p-tw6 | tribute_window 11 -> 25 / 6 | 49.4 / 49.2 |

### cal-a: threat-conditioned economy (10,240 games macro-dev): 49.2% (48.2-50.2), dropped
Bank floor hazard x3.7 while an enemy was seen in the last 5 rounds (with hysteresis until that bag banks), and
the static enemy-ground weight lifted by the share of enemy bodies provably unable to reach a group before our work
ends (dead or tracked far). The hazard rule changed ~8 bank decisions a game; the territory lift chose a group ~1 a
game (absence comes almost only from dead enemies). Level: non-Prism bags are not where games are lost, and
provable absence is too rare to move the farm.

### cal-b: two-step lookahead farm choice (10,240 games macro-dev): 48.7% (47.8-49.7), dropped
The top-6 solo candidates rescored by the best two-group sequence rate (follow-up from the candidate's centre
field, respawn timing, health budget); the choice changed ~40 times a game (smoke example: a near group beside a
respawning gem cluster over a far corner group). Level to slightly worse: farm routing is not what decides these
games; the Prism war is. (Possible second-order cost: allies lining up on the same unposted follow-ups.)

### cal-c v1: the Prism war posture (10,240 games macro-dev): 44.7% (43.7-45.6)
Outgunned (enemy Prism's known bag >= ours, ties included) -> our Prism keeps out of its next-turn stun zone (farm,
steps, early leave), bag-carrying allies too, winning tributes held while it could reach the altar, our Prism skips
stop_game_ender; dominant -> our Prism hunts it. Replays (999 kept games, `replays/scratch/prismcmp.py`): our Prism
died far less (516 vs 796 deaths, 252 vs 295 with 50+ gems) but carried 10% fewer gems at r300/r500 and completed
fewer 200+ tributes (453 vs 538); it was still first to lose a 50+ bag in 189 games against 167. Avoidance made the
Prism passive, and a smaller hoard loses the duel when it comes: survival bought with farm time does not pay.
Ties-as-outgunned (both bags 0 early) made it avoid from round 1. Ablations requested.

### cal-c final (ties fixed, audited), ablated (macro-dev1500, 3,000 games each)
| part on | win % |
|---|---|
| avoid (our outgunned Prism keeps out of the enemy Prism's next-turn zone, leaves it early) | 47.2 |
| ally (bag-carrying allies avoid that zone) | 50.2 |
| hold (no winning tribute an outgunning Prism can reach) | 50.0 |
| noender (our outgunned Prism skips stop_game_ender) | 49.5 |
| hunt (our dominant Prism prices the smaller enemy Prism first) | 50.1 |
| all | 44.2 |
The posture costs more farm time than the deaths it saves, and the parts interact badly together.

### cal-d: win window + escort on every map (macro-dev1500, 3,000 games): 49.7 (pre-audit snapshot)
The window rule never fires: winning bags are 600-1,600 gems (60-107-turn channels) and unseen enemies' bounds sit at
"now", so no altar ever has a provable window; only the multi-altar escort changes play (~2.4 a game). Cancelled
200+ channels rarely cost the carrier (16 of 879 stun-cancels died within 8 rounds), and 89% of stun-cancels are
by the eventual winner: retrying is cheap, so holding back does not pay.

### The one lever that leans positive: Prism's power is underpriced
pr-bonus3 (carried_bonus x3, 3,000 games: 51.3%), replays of 901 kept games: our Prism carried 3-4% more gems at
r300/r500, died 16% less (735 vs 874), was first to lose a 50+ bag in 223 games against 257; all deaths 4,687 vs
5,201. Also Prism sits on unspent gold far more than anyone (>=150 gold in 32% of its alive rounds 100-800, p90 535;
every other champion <=6%, Vesper 14%): `wants_shop` prices a trip by farm rounds saved, and Prism never banks, so it
rarely goes home. Both value Prism's power as farm speed while it decides the duel. -> cal-e: one constant,
`prism_power_weight`, applied to the kept-gem bonus and Prism's shopping trips.
| cal-d final (audited) | 49.7 (3,000) |
| pr-bonus10 (carried_bonus x10) | 48.1 (3,000): too strong a funnel; the hoard's value peaks below x10 |
| pr-bonus3 on full macro-dev | 49.3 (10,240): the dev1500 lean was noise |

### cal-e: Prism's power weighted x3 in the kept-gem bonus and in its shopping trips: 46.2% after 5,074 dev games, killed
Sending Prism home to spend its gold costs far more than the stats buy: the hoarding Prism's time on the map (farm,
fights, kills) is worth more than ~5 shards. Its unspent gold is not a missed opportunity, it is the price of
staying out.
cal-e's own read of why: tripling the shop value makes every group within that value of the recall channel cost
the same (FarmRecall's max(channel, arrive - value)), so Prism recalls toward far picks, and every trip exposes the
hoard on the walk back out; shop trips rose by ~2.4 a game and Prism's median gold fell from 25 to 15 while the
win rate fell. Prism already recalls ~7.7 times a game, 62% of them at full health (travel and capture recalls).

### cal-f: the dominant Prism hunts the smaller enemy Prism (10,240 games macro-dev, first-smoke snapshot): 49.2%
While our Prism's bag is strictly bigger than the enemy Prism's last-seen bag (both >= brake_bag, sighting fresh), it
walks for the enemy Prism ahead of farming within a pursuit horizon, allies without bags within 8 follow. Level: the
smaller Prism, seen or not, is rarely caught by a walk (both walk a tile a turn, and the hunted one keeps its own
safety), and the hunt's farm time offsets the kills it does make.

### cal-g: a bodyguard for a 50+ gem Prism (the strongest non-Prism, non-healer, non-pair ally farms only within 6 of the Prism, else follows it at 2-4): 46.1% after 3,857 dev games, killed
Active in 44/48 smoke games, ~112 turns a game following without a farm group (half idle beside the Prism, half
trailing it at 13+ tiles after its altar and home trips). Protection never repaid one champion's lost farm.
cal-f's final read (48-game debug smoke): 4.8 hunts a game, mean 2.8 turns, 0.4 ending in an enemy Prism kill (mean
42 gems taken, eight of 17 kills of empty bags), our Prism never died hunting; a fleeing Prism walks as fast as we do
and the strike search still declines supported prey.

## Conclusion so far (21:25)
Every change that takes any champion's time off the farm (avoidance, hunts, escorts, shop trips, bodyguards) lost
2-6 points; every valuation change that keeps the farm intact (territory, bank hazard, lookahead routing, kept-gem
bonus, win windows) landed at 48.7-49.7 over 10,240 games. charybdis is at a local optimum in its own mirror: the
decisive quantity (Prism hoard relative to the enemy Prism) grows from farm time, and both sides farm the same way.
| pr-bonus3 on macro-holdout + ladder,gen,fresh | 50.5 (3,840; holdout 50.3 of 2,560) | level |
| pr-norecall (Prism never recalls as travel: no recall-to-farm, no capture recall) | 45.3 after 6,093 dev games, killed |
| all-nocaprecall (no capture recalls for anyone) | 47.4 after 6,099, killed |
Recall-as-travel is a real gain, for Prism most of all: its full-health recalls are not waste.

## What these experiments say about charybdis's macro

1. **The game is the Prism war.** ~90% of compositions draft Prism, our A/Bs are always mirrors, and Prism's Focus hoard
   is the dominant resource: the bigger hoard wins the Prism duel 97% of the time, the first 50+ gem Prism death
   decides 55% of games (the victim's team then wins 10%), and taking the hoard away costs 21 points.
2. **The hoard grows from farm time, and charybdis's farm is at a local optimum.** Every removal of an existing
   time-on-map mechanism hurts (Prism travel recalls -4.7, capture recalls -2.6, hoard caps -1.6 to -21), and every
   behaviour that spends any champion's time on something other than farming loses (Prism avoidance -2.8, all of
   cal-c -5.8, extra Prism shop trips -3.8, a bodyguard -3.9, hunts -0.8), because the opponent's hoard keeps growing
   meanwhile. Valuation changes that keep the farm intact are level within noise (48.7-50.5 over 10k+ games).
3. **The endgame cannot be timed.** Winning bags are 600-1,600 gems (60-160-turn channels); with unseen enemies no
   provable window ever opens, and cancelled channels are cheap retries (89% of stun-cancels belong to the eventual
   winner), so holding back does not pay.

## Open leads
- The only way left to win the mirror is more hoard per champion-round without time off the farm, or less for the
  enemy at no farm cost. Unexplored: the opening plan (draft/open_plan.cc's early routes) aimed at the first Prism
  lead (the bigger Prism at r200 already wins 56%); turn order/priority for Prism duels (exclusive spells mean whoever
  starts its turn within 4 of the other strikes first); cal-g's bodyguard had real bugs (its old farm claim kept
  pulling it away, see the agent's audit) and could be retested with them fixed, though lesson 2 predicts a loss.
- Farm speed proxies (cal-b's lookahead) and map control (cal-a) do not move a mirror whose outcome is the Prism duel;
  they might matter against a different opponent (e.g. the teacher) where the duel is not symmetric.
| pr-noshoptrip (Prism never goes home only to shop) | 49.3 after 7,093 dev games, stopped: level |
pr-norecall's replays (1,026 kept games): without travel recalls our Prism died far more (1,153 vs 891 deaths, 532 vs 358
with 50+ gems), was first to lose a 50+ bag in 262 games against 198, and carried 5-7% fewer gems. Recall is the
hoard's safe transport as much as a shortcut: walking a bag across the map is where it gets caught.

### cal-g retest with its audit's leaks fixed (joins only within 8 of the Prism, farms normally when no group near it, station 3-4 tiles): 49.3% (10,240 dev)
The bugs explained the first -3.9; the fixed bodyguard is level, not a gain.

### cal-h: bag exposure priced into walk-or-recall (FarmRecall::sooner adds hazard x swing x bag / income per exposed round off our ground): 50.2% (10,240 dev), 50.1% (3,840 holdout + standard)
Fires rarely: Prism's heal value already makes the recall the sooner trip on most of its big-bag choices
(~1 flip in 16 debug games). Level.

### cal-m: pr-bonus3 + cal-h + fixed cal-g merged: 49.0% (10,240 dev)
Three level changes do not stack. Final: `bots/charybdis` unchanged.

### cal-o: Prism-first opening plan (draft/open_plan: a gem held by Prism worth 1 + per_gold x 1.5/8 x 30 = 2.69 gems in the plan's capture value and holder choice; picks and emblems unchanged): 50.1% (10,240 dev), 50.0% (3,840 holdout + standard)
Level: the opening's holder/route shift does not change the Prism race measurably (the farm's run-time holder choice
already prices carried_bonus, so plan and farm mostly agreed anyway).

### cal-p: Prism duel initiative (our Prism publishes the team's lowest priority while an enemy Prism seen within 3 rounds is within 10 tiles): 48.4% (10,240 dev), dropped
Overriding the published priority breaks the turn-order logic's own plans (kill bids, follow intents, heal slots
assume the computed rank) and out-of-fuel turns rose 529 -> 696; acting last is not a free initiative.
Final: `bots/charybdis` unchanged.
