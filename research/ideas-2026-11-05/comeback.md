# Cooked comebacks (id `comeback`, seeds 544000-544999)

The user's idea: when the game is cooked (far behind, normal play rarely wins), gamble. "have we tried invading
aggressively ... prioritising their side of the map instead of ours. or even doing the equal scoring thing with like
treating dists as min(d(src to des), d(sym(src) to des)). possibly also combine with increased grouping behavior to
pick off champs". Added by the user since: (e) itemisation when cooked, (f) ambush on predicted enemy paths, (g) a
crystal-hop wipe at a predicted enemy camp, carry tracking, tiers by how cooked we are and a learned selector.

Dev copy `bots/variants/oc-comeback-dev` (= `bots/ocean` = `variants/oc-retest-clean`, plus oc-mp-dev's mirror pull
ported, plus `model/race.{h,cc}` from `variants/oc-race`, plus `economy/comeback.cc`). Knobs in `params::comeback`;
`def = 0` is off. Variants `variants/oc-cb-<name>`, made by `comeback-tools/mkvar.py`.

## Why it is new

Invades and the mirror pull lost or read level ungated, map-gated, situation-gated and with a learned map gate
(EXPERIMENTS "Invade / opening steal", "Mirror pull" passes 1-3). None was gated on being cooked. When cooked,
P(win | normal) is ~5-10%, so a high-variance gambit pays if it lifts the comeback rate at all: the extra losses it
causes fall in games already lost.

## Evidence

**Ladder** (`replays/invade-ladder/analysis`, 968 top-team games of 2026-11-04/05; `comeback-tools/cooked_stats.py`).
Cooked by the altar guard's trigger (leader at 600+ tributed and 200+ ahead):

| Definition | Games cooked | Comeback | Cook round (median) | Rounds left (median) | Gap (median) |
|---|---|---|---|---|---|
| g600: leader 600+, 200+ ahead | 871 | 8.0% | 702 | 207 | 344 |
| g400: 400+, 150+ ahead | 936 | 14.5% | 577 | 330 | 225 |
| rs: 300+, gap ≥ 100 + 200 (1 - r/2000) | 861 | 10.6% | 610 | 313 | 269 |
| wb: with bags, 700+, 300+ ahead | 738 | 3.9% | 724 | 186 | 326 |

g600 comebacks by rounds left: 4.7% (under 100), 6.9% (100-200), 8.4% (200-400), 19.0% (400-800).

What separates the 70 comebacks from the 801 losses, from the cook point on (means a game):

| | comebacks | losses |
|---|---|---|
| kills on the leader's bodies | 5.11 | 1.22 |
| leader gems taken in those kills | 83.9 | 18.8 |
| trailer deaths | 1.86 | 3.35 |
| trailer gems lost in bags | 26.4 | 40.8 |
| leader tributes / mean size / median gap | 6.8 / 63.5 / 31 rounds | 10.3 / 84.7 / 23 rounds |
| leader body-rounds on its own half | 88% | 75% |
| leader bodies' mean pairwise distance | 14.3 | 12.8 |
| leader carriers (30+ gems) with no ally within 4 | 48% | 45% |

So comebacks are made by kills on the leader (with their bags) while not dying: the leader stays home (75-88% of
its body-rounds on its own half), spread out (13-14 tiles between bodies), and its carriers walk alone about half
the time. That is the case for hunting in packs on their side, and for banking our own bags before a hunt.

**Self-play** (oc-retest-clean mirror, real budget, the 2,560 maps of `cb-m` = fresh 544200-544209, one side each;
`replays/comeback/ana-self-m`): a side is cooked in 95% of games by g600, and the leader closes fast.

| Definition | Games cooked | Comeback | Cook round (median) | Rounds left (median) | Gap (median) |
|---|---|---|---|---|---|
| g600 | 2426 | 8.7% | 711 | 61 | 393 |
| g400 | 2481 | 15.5% | 602 | 187 | 221 |
| rs | 2420 | 10.3% | 643 | 128 | 279 |
| wb | 1845 | 6.1% | 616 | 193 | 153 |

g600 comebacks by rounds left: 5.9% (under 100), 11.0% (100-200), 13.6% (200-400), 16.4% (400-800).

| From the g600 cook point (a game) | comebacks (210) | losses (2,216) |
|---|---|---|
| kills on the leader / its gems taken | 6.12 / 198 | 0.84 / 21 |
| trailer deaths / its gems lost | 1.81 / 21 | 3.06 / 55 |
| leader tributes / mean size / median gap | 3.5 / 135 / 34 rounds | 6.3 / 184 / 19 rounds |
| leader body-rounds on its own half | 93% | 84% |
| leader carriers (30+) with no ally within 4 | 43% | 31% |

Where the leader dies after the cook (`leaddeaths.py`), a game:

| | comebacks | losses |
|---|---|---|
| leader deaths on its own half (gems) | 4.30 (144) | 0.56 (13) |
| on our half (gems) | 1.88 (55) | 0.33 (9) |
| within 3 of an altar (gems) | 2.85 (111) | 0.24 (12) |
| leader bags of 100+ taken | 0.43 | 0.03 |
| trailer deaths on its own half / theirs | 1.41 / 0.40 | 2.55 / 0.50 |

A comeback is kills on the leader with its bags, half of the gems at altars and mostly on its own half, while the
trailer stays alive. Our cooked side is the weaker one, though: those kills come where it happened to win fights.

## Design

**Cooked signal** (`def`): 1 the altar guard's trigger (enemy ≥ `enemy_min` 600, lead ≥ `gap` 200, off below
`gap_off` 100; levels by lead: mild, deep at `deep_gap` 300, hopeless at `hopeless_gap` 450). 2 the need ratio: our
gems still needed over theirs ≥ `ratio` (1.6; deep 2.2, hopeless 3.0; enemy ≥ `ratio_min` 400) — in a mirror both
earn alike, so it is how many times longer we take, and it scales with rounds left. 3 the race model
(`variants/oc-race`, READY): enemy ≥ `race_min` 500 and margin < -`race_k`. 4 (later) an EV gate fitted offline
from the random logger. The level is computed from the scores, which every body reads alike, so the team agrees
without comms.

**Gambits** (bits; `mild`, `deep`, `hopeless` masks pick them per level):
- (a) `pull`: the mirror pull while cooked, `steps - lam * max(0, steps - c * mirror_steps)` on every group (or
  enemy-side ones), c swept.
- (c) `deny`: enemy-side groups' worth x (1 + `deny_w`): contest and steal their camps.
- (b) `hunt`: the top `hunters` bodies by fighting weight hunt. Their turn (after the altar guard's, before the
  chase): the chase with a lower bar (`bar`: a lost fight is taken while our turns to kill them are at most bar x
  theirs to kill us; with `pack`, only with the other hunters, up to two, in sight within `pack_radius`), without
  the own-ground limit; else walk to the best quarry (seen in the last 20 rounds, off their spawn's edge, by
  `carry_w` x its estimated bag plus its life, per step), followers keeping with the lead hunter; else hold the
  hunting ground (`ground` 0: their side's best group by worth over walk; 1: their altar nearest their spawn),
  bush stands first, out of camp reach. `bold` drops the lost-stand retreat. `hide_bag`: bank first.
- (e) `items`: the shop's fight value x `items_fight` (1.5, 2, 3), economy passives (Prospector, Treasure, Tribute,
  Capture) x `items_econ`, the learned emblem table skipped; `items_dmg` prices fight power by output alone;
  `items_hunters_only`.
- (f) `ambush`: hunters hold the bush that sees most of the enemy's predicted route flow (their spawn to their worthy
  groups and altars, groups to altars for carriers, weighted by worth).
- (g) `hop`: the crystal-hop wipe at a predicted enemy camp (census first).

**Carry tracking**: World already keeps each enemy's bag as last read, zeroed at death, respawn and attributed
tribute landings; the race model (race.md) found staleness terms no better, so `est_carry` is that belief (pair
gems for Cassi and Issac). `carry_w` 0 is plain targeting.

**Combining**: tiers by level (masks), then a learned selector: `log_random` draws one gambit set per cook episode
from a hash of the map and the episode (recomputable offline), so outcomes per gambit are causal; per-gambit
outcome models are fitted offline and baked in.

**Fuel**: nothing runs until cooked. While cooked the pull turns off the farm's pre-prunes (as the mirror pull's
runs did, +2% mean fuel), the hunt adds one field per game and a chase a turn.

## Judging

Screens at 2x fuel (200k a turn), SPRT 0.50/0.51 on the dev suite `cb-e` (544000-544039), paired per map and side
with a one-side self-play baseline at the same fuel (`replays/comeback/self2x-*`) where a sharper read is needed;
the comeback rate (`cooked_ab.py`-style, cand cooked against ref cooked in the same A/B) as the mechanism. Winners
at 2x then get the real budget, the confirm `cb-c` (544100-544139), `cb-v` (544900-544909, `--mix varied`) and the
panel.

## Results

All screens: against `variants/oc-retest-clean`, own drafts, fast runner, **2x fuel** (200k a turn, 400k the first),
on `cb-e` (fresh 544000-544039, 20,480 games at most), SPRT 0.50/0.51 (stops at H0 or H1). Comeback rates are from
CAND's own `CBK` / `CBE` trace lines (`cbrate.py`): CAND cooked against REF cooked in the same A/B, by the variant's
own cooked test. "flips": games whose winner differs from the 2x one-side self-play baseline on the same map
(`pair.py`, `replays/comeback/self2x-e`). Triggers: g600 = enemy 600+ and 200+ ahead (the default), g4 = 400+ and
150+ ahead.

**Round 1** (`q1.txt`; hunters keep their bags, bar 0 = only won fights, `bar` 2 = a lost fight is taken while we
last 2+ turns, pack, bold = no lost-stand retreat):

| Variant | Gambit | Trigger | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|
| s-null | none (trace only) | g600 | 49.8 | 402 | 44.9-54.6 | H0 | 7.9 / 7.9 |
| s-pull1 | (a) pull c 1, all groups | g600 | 49.8 | 904 | 46.5-53.0 | H0 | 8.6 / 9.7 |
| s-deny | (c) deny 0.5 | g600 | 50.3 | 3960 | 48.7-51.8 | H0 | 11.2 / 11.0 |
| s-items2 | (e) fight x2, econ x0.5 | g600 | 50.1 | 856 | 46.8-53.5 | H0 | 9.0 / 8.7 |
| s-hunt3 | (b) 3 hunters, bar 0 | g600 | 50.0 | 1314 | 47.3-52.7 | H0 | 8.9 / 8.8 |
| s-hunt3b | (b) 3, bar 2, bold | g600 | 49.5 | 982 | 46.4-52.6 | H0 | 8.4 / 8.8 |
| s-hunt5b | (b) all 5, bar 2, bold | g600 | 49.2 | 916 | 46.0-52.5 | H0 | 7.9 / 8.9 |
| s-hi | (b)+(e) | g600 | 49.4 | 923 | 46.2-52.6 | H0 | 8.1 / 9.0 |
| s-hunt3b-g4 | (b) 3, bar 2, bold | g4 | 48.4 | 942 | 45.2-51.6 | H0 | 12.3 / 16.3 |

**Round 2** (`q2.txt`):

| Variant | Gambit | Trigger | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|
| t-amb-g4 | (f) ambush bush, 3 hunters | g4 | 48.8 | 1063 | 45.8-51.8 | H0 | 13.1 / 16.1 |
| t-alt3-g4 | (b) ground = their altar, 3 | g4 | 47.8 | 653 | 44.0-51.6 | H0 | 11.9 / 18.3 |
| t-alt5-g4 | (b) their altar, all 5 | g4 | 49.0 | 1221 | 46.2-51.8 | H0 | 13.3 / 15.2 |
| t-hunt5-r16 | (b) all 5, need ratio 1.6 | ratio | 48.2 | 606 | 44.2-52.2 | H0 | 8.2 / 12.7 |
| t-race | (b) 3, race margin < 0 | race | 49.5 | 2217 | 47.4-51.6 | H0 | 16.1 / 26.1 (REF's by a mirrored margin) |
| t-pull1-g4 | (a) pull c 1 | g4 | 50.2 | 4030 | 48.6-51.7 | H0 | 15.5 / 15.6 |
| t-items3-g4 | (e) fight x3, econ x0.25 | g4 | 50.1 | 3032 | 48.3-51.8 | H0 | 15.3 / 15.4 |

**Forensics, s-hunt3b** (982 games extracted, g600, means a lost game from the cook): kills on the leader 1.24
against REF-cooked 0.74, its gems taken 34 against 12; but our deaths 4.41 against 2.81 and our gems lost 73 against
46. The hunt trades +0.5 kills for +1.6 deaths, and the hunters die with their bags. Hence round 3: bank first
(`hide_bag` 10), lost fights only against a carrier of 40+ (`bar_bag`).

**Round 3-4** (`q3.txt`, `q4.txt`; `snipe`: no hunt walk, every body's chase takes the bar against carriers of 40+
and leaves the own-ground limit):

| Variant | Gambit | Trigger | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|
| u-h3c | (b) 3, bar 2 vs carriers 40+, bank first | g600 | 48.4 | 639 | 44.5-52.2 | H0 | 6.6 / 9.3 |
| u-h5c | (b) all 5, the same | g600 | 48.5 | 670 | 44.7-52.3 | H0 | 6.4 / 9.3 |
| u-h3c0 | (b) 3, bar 0, bank first | g600 | 49.4 | 693 | 45.6-53.1 | H0 | 7.7 / 9.3 |
| u-deny1 | (c) deny 1.0 | g600 | 50.3 | 2280 | 48.2-52.3 | H0 | 9.9 / 9.6 |
| u-deny-g4 | (c) deny 0.5 | g4 | 50.3 | 5683 | 49.0-51.6 | H0 | 16.3 / 15.9 |
| u-hop-g4 | (g) crystal hop, 3 bodies | g4 | 47.6 | 603 | 43.6-51.6 | H0 | 11.6 / 17.1 |
| v-snipe | snipe, bar 2, carriers 40+ | g600 | 50.2 | 922 | 47.0-53.4 | H0 | 10.1 / 9.0 |
| v-snipe-g4 | snipe | g4 | 50.3 | 3136 | 48.6-52.1 | H0 | 15.9 / 15.9 |
| v-snipe0 | snipe, bar 1, any target | g600 | 49.7 | 906 | 46.4-52.9 | H0 | 9.1 / 9.2 |
| v-h3c-hl | (b) as u-h3c, hopeless level only (lead 450+) | g600 | 49.2 | 427 | 44.5-53.9 | H0 | 7.8 / 8.1 |

Flips against the self-play baseline are 2-5% of games (s-null 0.5%, s-deny 2.1%, s-hunt3b 3.0%, t-pull1-g4 4.6%,
u-h3c 3.6%): a cooked gambit changes few winners, so its ceiling is small.

**Round 5** (`q6.txt`, combinations of the level non-disrupting gambits; `u-hopd` = hop at deep/hopeless only, g4
with cuts 250/350):

| Variant | Gambit | Trigger | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|
| u-hopd | (g) hop, deep and hopeless levels | g4 | 48.0 | 523 | 43.7-52.3 | H0 | 13.2 / 17.2 |
| w-free | deny 0.5 + snipe + items x2 | g600 | 50.2 | 2759 | 48.3-52.1 | H0 | 10.0 / 9.9 |
| w-items15 | (e) fight x1.5 | g600 | 49.9 | 856 | 46.5-53.3 | H0 | 9.0 / 8.7 |
| **w-free-g4** | deny 0.5 + snipe + items x2 | g4 | **51.3** | 1688 | 48.9-53.7 | **H1** | **18.2 / 15.2** |
| **w-dp-g4** | deny 0.5 + pull c 1 + snipe | g4 | **51.2** | 2066 | 49.0-53.4 | **H1** | **17.9 / 15.6** |

The two H1s are early stops (an early stop reads high) and the best of ~30 screens (the best of many reads high):
both go to held-out confirms on `cb-c` (544100-544139) at 2x with no SPRT, all 20,480 games.

**Round 6** (`q7.txt`, `q9.txt`: the hop with the ward tile chosen to see the most landing tiles, and a
decomposition of `w-free-g4`):

| Variant | Gambit | Trigger | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|
| w-itemsd | (e) damage only, fight x3 | g600 | 49.9 | 919 | 46.7-53.1 | H0 | 9.3 / 9.1 |
| w-itemsh | (b)+(e), items for hunters only | g600 | 48.8 | 525 | 44.5-53.1 | H0 | 5.9 / 8.0 |
| x-hop2-g4 | (g) hop, 3 bodies | g4 | 47.2 | 595 | 43.2-51.2 | H0 | 11.1 / 17.3 |
| x-hop2s-g4 | (g) hop, site share 30%+ of their worth | g4 | 47.0 | 624 | 43.1-50.9 | H0 | 11.4 / 17.4 |
| y-ds-g4 | deny + snipe | g4 | 50.9 | 2952 | 49.1-52.7 | H1 | 17.1 / 15.1 |
| y-di-g4 | deny + items | g4 | 51.6 | 1800 | 49.3-53.9 | H1 | 18.8 / 15.3 |
| y-si-g4 | snipe + items | g4 | 50.2 | 4957 | 48.8-51.6 | H0 | 16.1 / 16.1 |
| y-free-g3 | deny + snipe + items | 300+, 100+ ahead | 51.6 | 2535 | 49.7-53.5 | H1 | 26.0 / 22.1 |

Every H1 has deny in it and a g4 or earlier trigger; deny alone at g4 read 50.3% over 5,683 and snipe + items with no
deny 50.2% over 4,957. With CIs of ±2 points these are all consistent with one effect of about +0.5-1 point, so the
held-out confirms decide (and `q12.txt` sweeps deny's trigger down to always on: if deny wins always on, it is a farm
change, not a comeback gambit).

**Random gambit logger** (`oc-cb-log1`, `cb-L` 544300-544339, 20,480 games, 2x, g4; at its first cook each
CAND body hashes the map and episode into one of 9 arms, the same for the whole team): CAND 48.6% overall (four of
the arms are the disrupting ones), 10,017 CAND-cooked games, about 1,100 an arm.

| Arm | Comeback % | ± (95%) |
|---|---|---|
| items (x2) | 17.0 | 2.2 |
| snipe | 16.0 | 2.2 |
| normal | 15.9 | 2.1 |
| pull | 15.8 | 2.2 |
| deny | 15.7 | 2.1 |
| hunt (3, bar 2 vs carriers, bank first, bold) | 11.0 | 1.9 |
| ambush | 10.3 | 1.8 |
| hunt + items | 10.1 | 1.7 |
| hop | 9.9 | 1.7 |

By state bin (cook round, need ratio, gap) no arm beats normal by more than its noise in a bin with any weight; the
disrupting arms lose 3-12 points in every bin except the few games cooked past a need ratio of 2 (221 games, normal
0 of 21).

**Learned selector (ii)** (`fitsel.py`): logistic outcome model on the cook state (round, gap, need ratio, scores,
side) and 14 map metrics with arm interactions, 5-fold by map, value by inverse propensity on the held-out maps. Over
all 9 arms it reads 16.5-16.8 ± 2.2 (C 0.01-0.1; picks items 23%, deny 19%, normal 18%, pull 13%, snipe 13%, hop 6%,
hunt 5%); over the 5 level arms 16.2-16.5. Normal is 15.9 and the best single arm (items) 17.0: the selector has no
margin over the best single arm, so it is not baked in. The logger cannot resolve per-state differences of a point
or two (about 120-280 games an arm a bin).

**Round 7** (`q10-q13`: held-out confirms of the H1s on `cb-c`, all 20,480 games, no SPRT; tiers (i); deny's trigger
swept down to always on):

| Variant | Gambit | Trigger | Suite | Win % | Games | 95% CI | SPRT | comeback cand / ref |
|---|---|---|---|---|---|---|---|---|
| **w-free-g4** | deny + snipe + items | g4 | cb-c | 50.4 | 20480 | 49.7-51.1 | - | 17.3 / 16.6 |
| **w-dp-g4** | deny + pull + snipe | g4 | cb-c | 50.6 | 20480 | 49.9-51.2 | - | 17.5 / 16.4 |
| **y-di-g4** | deny + items | g4 | cb-c | 50.3 | 20480 | 49.6-51.0 | - | 17.3 / 16.6 |
| z-tier1 | mild deny+items; deep (300+) +snipe; hopeless (450+) +pull | g4 | cb-e | 51.4 | 1875 | 49.1-53.7 | H1 | 18.4 / 15.2 |
| z-tier2 | the same, cuts 250 / 350 | g4 | cb-e | 51.4 | 1763 | 49.1-53.7 | H1 | 18.6 / 15.1 |
| z-tier3 | mild deny; deep +items; hopeless +snipe+pull | g4 | cb-e | 50.2 | 6070 | 49.0-51.5 | H0 | 16.1 / 15.9 |
| z-deny-all | deny all game | always | cb-e | 49.6 | 8346 | 48.5-50.7 | H0 | - |
| z-deny-g3 | deny | 300+, 100+ ahead | cb-e | 50.1 | 5536 | 48.8-51.4 | H0 | 23.0 / 22.6 |
| z-di-g3 | deny + items | 300+, 100+ ahead | cb-e | 51.4 | 2543 | 49.5-53.3 | H1 | 25.9 / 22.9 |
| z-di-g2 | deny + items | 200+, 75+ ahead | cb-e | 50.6 | 20480 | 49.9-51.3 | undecided | 29.5 / 28.2 |

The early H1s on `cb-e` are not independent: ab.py shuffles with a fixed seed, so every SPRT screen plays the same
first ~2,000 games, and the H1s (all with deny and items or snipe) stopped there. Held out, the three confirms read
50.3-50.6%, comeback +0.7 to +1.1 points: the same small effect each time, none significant alone. Deny all game
loses (49.6%), so deny is a comeback gambit, not a farm fix. Next: `w-dp-g4` on a fresh suite `cb-d`
(544400-544439) and on `cb-v` (`--mix varied`) to settle whether +0.5 is real.

**Round 8** (`q14.txt`: `w-dp-g4` on a second fresh suite and on stress maps, 2x):

| Suite | Win % | Games | 95% CI | comeback cand / ref | OOF cand / ref |
|---|---|---|---|---|---|
| cb-c (544100-544139) | 50.6 | 20480 | 49.9-51.2 | 17.5 / 16.4 | 1,191 / 1,280 |
| cb-d (544400-544439) | 50.4 | 20480 | 49.8-51.1 | 17.2 / 16.2 | 1,121 / 1,136 |
| cb-v (544900-544909, `--mix varied`) | 50.2 | 5120 | 48.8-51.6 | 15.5 / 14.4 | - |
| **held out, pooled** | **50.46** | 46080 | **50.0-50.9** | +1.0 to +1.1 each | |

The same +1 point of comeback on every held-out suite, and a pooled win rate whose CI just clears 50. Frozen as
`bots/variants/oc-comeback-dp` (= `oc-cb-w-dp-g4`). It costs no fuel at 2x (out-of-fuel turns level); the real
budget A/B (`q15.txt`, cb-c and cb-d) measures it at 100k.

**Round 9** (`q15.txt`: `oc-comeback-dp` at the real budget, 100k a turn):

| Suite | Win % | Games | 95% CI | comeback cand / ref | OOF turns cand / ref |
|---|---|---|---|---|---|
| cb-c | 50.3 | 20480 | 49.6-51.0 | 16.2 / 15.7 | 162,751 / 160,192 |
| cb-d | 50.3 | 20480 | 49.6-51.0 | 16.5 / 15.6 | 160,819 / 157,499 |
| **pooled** | **50.3** | 40960 | **49.8-50.8** | +0.5 / +0.9 | +1.6% / +2.1% |

## Verdict

No gambit wins significantly at the real budget. The best, `oc-comeback-dp` (deny 0.5 + mirror pull c 1 + snipe at
g4: once the enemy has 400+ and leads by 150+, value their side's camps 1.5x, rank camps by the nearer of the two
sides' paths, and take lost fights while we last 2+ turns against carriers of 40+ gems), reads 50.46% at 2x over
46,080 held-out games (CI 50.0-50.9) and 50.3% at the real budget over 40,960 (49.8-50.8), with +1 point of comeback
from cooked states at 2x and +0.5-0.9 at the real budget, and 2% more out-of-fuel turns. It is frozen as
`bots/variants/oc-comeback-dp`; it is not a merge candidate on this evidence (the panel was not run, as it did not win).

What the programme found:
- Cooked is common and late: at g4 one side is cooked in ~49% of games, normal play comes back 15-17% of the time.
  Comebacks are kills on the leader carrying its bags, mostly on its own half and at altars.
- Every gambit that takes bodies off the farm loses, alone or combined: pack hunting (all bars, sizes, triggers and
  grounds), the ambush bush, the crystal hop (four forms), and hunts with itemisation. They buy +0.5 kills on the
  leader for +1.6 deaths and the bags of the dead; comeback falls 3-6 points. The crystal hop is rare (sites on 21%
  of maps on a worthwhile group, 12 teleports in 603 games of u-hop-g4) and loses its bodies' farm time while it waits.
- The gambits that keep the farm (deny, mirror pull, snipe, items) are each level alone and worth about +0.5 points
  of win rate combined, too small to separate from noise in 40k games at the real budget.
- Tiers (i) read like the combos (the mild tier already holds deny + items); the learned selector (ii) has no margin
  over the best single arm (16.5-16.8 against 17.0, ±2.2), so neither is baked in.
- Deny all game loses (49.6%): its value is as a cooked response, not a farm change.
- Early SPRT stops on one suite are not independent across variants (ab.py's fixed shuffle seed plays the same first
  ~2,000 games every time); five H1s there shrank to +0.3-0.6 held out.
- Not built: tiebreak awareness (2.6% of games reach round 2000, so the ceiling is a fraction of a point) and race
  `if_kill` targeting (the race-margin trigger itself lost: t-race 49.5%).
