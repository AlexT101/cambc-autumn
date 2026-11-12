# Prism safety on the game-ending tribute (prismsafe, 2026-11-12)

The user's request: "also test prism safety on final tribute - ie recall/prioritise having high health in prism's
batch game-ending tributes if the game score is not close and the enemy doesn't also have prism (most conservative
first, can generalise by pruning the two and branches asw)".

Base and REF: `variants/charybdis-cb9f86d` (= bots/charybdis, CHANGES 517). Results: EXPERIMENTS.md "Prism safety on
the game-ending tribute".

## What a winning bag's rounds are spent on (REF, 2,560 games against the rt bodies at 200k)

`mech.py`, `timeline.py` and `cancels.py` on fgate pool batch 0, parts p0-p1 (640 maps, both sides, both bodies).
A winning bag means the Prism's gems plus our score reach 1,000.

- 52% of games have one. Those games are won 96.2% of the time. The bag is lost (the Prism dies carrying it) in
  58 of 1,339 (4.3%), and 23 of those 58 games are lost.
- The bag is huge (median 542 gems at the first winning round), and the Prism is already at an altar (median distance
  0). So the time goes into the channel, not the walk. A winning-bag Prism spends 69 rounds a game channelling a
  tribute, 11 recalling and 2 walking.
- That channel is about 57 turn ends long (a turn per 10 gems). It is started 2.3 times a game and cancelled 2.0 times:
  926 stuns, 501 enemy locks, 1,171 by our own choice. 72% of the starts are made below full health.
- The deaths: 43 of 60 are basic attacks, mostly Vesper Vale (25) and Marcella (14). The common shape is a Prism
  standing in or restarting the channel while its health runs down (0.43, 0.32, 0.22, 0.11 and dead), or starting it
  already hurt.
- Enemy Prism games: 90 of 1,339 (7%), with 11% of bags lost there against 3.8%.

So the risk is the long channel, and the user's "high health" applies to starting it.

## The change (`finish_heal`, combat/fight.cc; patches `psafe-*.patch` against charybdis-cb9f86d)

A Prism carrying the winning bag, not in a channel and off its spawn, below the health line goes home instead of
starting the channel or walking on. `want_home` returns true, so the retreat runs and the turn-end recall is kept while
it is the sooner way home. `can_tribute_safely` refuses the tribute, which covers retreat's tribute path and the
recall keep. Mite's turn-end habit is already blocked by `want_home`. On spawn the turn end heals to full and buys
health shards, and the bag then goes out as before.
- **High health** = min(full, every living enemy's one-round strike, `Safety::strike_of`, summed). This is the health
  a burst from the whole enemy team before our next turn would take, so the Prism survives one round to react.
- **Not close** (`finish_lead`): the enemy's clock is its gems short, beyond the bags we saw, divided by its tribute
  rate over the later half of the game (`World::enemy_rate`, new). That clock must run past our trip: recall + heal
  turn + walk from the landing + the channel. The round limit also needs time for that trip plus `endgame_margin`.
- **No enemy Prism** (`finish_no_prism`): the enemy drafted none.
- The first build used `closing()` for the round-limit guard and never fired (10 of 20,480 games differed): `closing()`
  reads true for every winning bag, because its race is already run. Those runs are kept as `replays/ab/v1-*` and are
  not in the tables.

## Arms (bots/variants/)

| arm | not close (a) | no enemy Prism (b) | line |
|---|---|---|---|
| psafe-ab | yes | yes | burst |
| psafe-a | yes | no | burst |
| psafe-b | no | yes | burst |
| psafe-0 | no | no | burst |
| psafe-abF | yes | yes | full health |

## Results

The tables are in EXPERIMENTS.md. In short:
- The arms that keep the clock guard gain: psafe-a +0.22 and psafe-ab +0.18 on batch 0, and +0.17 and +0.14 on held-out
  batches 16-19 at 200k.
- The arms without the guard, b and 0, are level on batch 0.
- Healing to full (abF) saves the most bags (58 to 34) but delays each win by 27 rounds and loses -0.13.
- psafe-a at 100k: +0.19 (49.88-50.50) on batches 0-3 and +0.29 (50.04-50.54) on batches 4-9. Out-of-fuel turns are
  up 1.7%.
- Verdict: zone. psafe-a is a small, consistent gain, a candidate for combo stacking.

Mechanism, psafe-a against REF on the 2,560 mechanism games: bags lost 58 to 42, deaths carrying a winning bag 60 to
44, wins 0.8 rounds sooner (both won), 5.7% of games changed, net +4 wins (9 gained, 5 lost).

## Scripts

- `mech.sh BOT TAG` (copies of `~/tmp-offload/prismsafe/`) runs the mechanism games (with replays) and extracts them.
- `gates.sh` and `gates2.sh` run the fgate screens and the fixed reads.
- `mech.py EXT ref TAG...` gives the winning-bag metrics and the paired changes (`FLIPS=1` lists the flipped games).
- `timeline.py EXT/TAG` and `cancels.py EXT/TAG` give where the rounds go, the channel starts and cancels, and the deaths.
- `oof.py BOTS LO-HI [-fuel200000]` gives our out-of-fuel turns from the fgate runs.
Arms live in the gitignored `bots/variants/`: rebuild one with `./copybot variants/charybdis-cb9f86d variants/psafe-a` and `patch -p1 -d bots/variants/psafe-a < psafe-a.patch` (paths in the patch start at `charybdis-cb9f86d/src`).
