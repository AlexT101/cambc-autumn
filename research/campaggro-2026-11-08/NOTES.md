# Camp aggro: wake a Monolith onto an enemy (v87 = oc-base25, 2026-11-08/09): stopped after the conservative smoke

User idea: camps attack the nearest champion within range (ties to the earlier turn), so wake a high-Strength camp
that an enemy is strictly nearer than any of us. Conservative arm first; lean in only if it works.

## How often (live, v86-v89 against Fish and Mite, 2,555 games; `occur.py`, `detail.py`)
- A sleeping Monolith with an enemy within its range, strictly nearer than all of us, one of ours within 4 of a group
  member, holding over two round ends: in 392 games (15%), 2,668 episodes. Golem 324 games, Elk 780.
- Typical shape: the enemy 2-3 tiles from the Monolith, us 3-4; 83% on the enemy's half; the enemy mostly at full health.
  With us outside its range altogether: 16 rounds, one map. So the waker is nearly always inside the range, shielded
  only by the nearer enemy.
- Fish and Mite don't do it on purpose: ~7 distinct Monolith wakes in 2,555 games hit only us, mostly Heart of Ruin dash
  landings (whose stun also skips the camp's next attack).

## Arms (`ca-flee.patch` = oc-base25 -> v87-ca-flee; `bots/variants/v87-*` are gitignored)
- `v87-ca-k1`: combat/camp_aggro.cc, before the strike search. Basic-attack a sleeping group's member in reach when a
  Monolith member would fire on an enemy: worst cases are every enemy fleeing (a walk, plus a ready dash, unless it
  has acted), allies yet to act stepping in, and us staying (a melee waker steps). No member may fire on us. Value =
  200 x the victim's camp factor x min(3, phases until it walks out); fire if it beats our blow on an enemy now (a
  kill there comes first). The 3-phase cap is the walk-out time from 2-3 tiles. The blow gate rarely binds (200 a
  phase against our 50-100), so its k was not varied.
- `v87-ca-flee`: + model/safety.cc find_members, Monolith members only: an enemy yet to act shields a tile at its
  distance after its walk and ready dash, not where it stands (the smoke showed our bodies hit once it walked away).
- `v87-flee`: the Safety change alone (control).

## Smoke (debug, 4,096 games on ca-smoke = ladder-v2 1334000-1334007; `scan.sh`, `outcome.py`, `victim.py`, `paired.py`)
- k1 fired 113 times (~2.8 per 100 games, in 1.6% of games); no crashes.
- Woken group's damage over 8 rounds: enemy 77k, us 81k. Phase 1 hits the enemy (225 a fire); from phase 2 we take
  more. Hits on us land while farming (30k), chasing (17k) or retreating (14k) next to it, not sieging it. We were
  there for our own work, and once the enemy leaves or dies we are the nearest. The victim dies within 8 rounds 28%
  of the time (58% under 35% health), with 0.23 of our deaths per fire.
- ca-flee did not change this (enemy 74.8k, us 74.0k): the damage is our choice to stay, not the shield model.
- Triggered games paired against a base mirror (same maps and seats): k1 42.2% vs 50.0% of 64 (delta -7.8 ±14.7,
  flips +9 -14); ca-flee 38.7% vs 48.4% of 62 (-9.7 ±16.1).

## Screens (ca-scr, ladder-v2 1330000-1330079, 40,960 games; SPRT 0.50/0.5025, seeds 1335001-1335006) and spar
| Arm | Real budget | 2x fuel | Spar (6,656 paired) |
|---|---|---|---|
| ca-k1 | 50.0% (49.5-50.5) of 40,960; LLR -0.53, undecided at cap | 50.0% of 14,333; H0 | +0.24 ±2.84 |
| ca-flee | 50.0% (49.5-50.5) of 40,960; LLR -0.73, undecided at cap | 49.8% of 5,906; H0 | -0.44 ±2.87 |
| flee | 50.0% of 17,339; H0 | 50.1% of 5,154; H0 | +0.69 ±2.41 |
The aggro arms' out-of-fuel turns at the real budget are +5% (432,908 vs 411,330; flee alone level). They are not the
cause, since 2x is H0 too.

## Verdict: stop, no lean-in
The woken Monolith fires on whoever stays near it, and the arm only fires when we are near it (3-4 tiles, inside its
range). So the exchange is even (77k vs 81k) and the triggered games lean negative. The general arms (tied
distances through the later turn slot, golems and elk) make the same even exchange more often. The one-sided cases
(the victim pinned by a tribute, or none of us in range) almost never occur: 1 of 162 fires, 3% of live opportunity
rounds, and 16 live rounds. Leaning in would first need a follow-up that leaves the range once the enemy can walk
out, which is a positioning change with its own costs.
