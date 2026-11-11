# Giving way to a closing pack (2026-11-11)

Brief: the [overruns](../overruns/README.md) read found that live Fish wins the early fights it starts with the
numbers (-0.40 kills each for us, 136 of them in 260 games) and that our target had walked towards the pack 61% of
the time. Build the candidate that stops that, for a live pair against v115 (= `oc-dfuel-506` = ocean), where it is
judged on the mechanism's own metrics.

**Answer: a family of three strengths of one rule, the pack zone's margin (`pg-z6`, `pg-z7`, `pg-z8`).** Each step
of margin removes more of the fights the enemy starts with the numbers and costs more against the bodies:

| | fresh maps, 200k fuel | enemy-started outnumbering fights a game |
|---|---|---|
| `pg-z6` (margin 1) | -0.13 ±0.52 | -10% and -19% (two samples) |
| `pg-z7` (margin 2) | -0.59 ±0.53 | -18% and -20% |
| `pg-z8` (margin 3) | -1.79 ±0.55 | -29% and -27% |

No strength is a local win; `pg-z6` is level and the other two lose. For the live pair I would send **`pg-z8`**: it
is the only one whose effect a 512-game pair can see (below). It is a measurement arm, not a shipping candidate.

## What the fights show

Live v115 against Fish r2, the 136 engagements Fish started with more bodies ([tools/approach.py](tools/approach.py)
on the overruns pickles; strength is health times Strength summed a side, the zone's own measure):

- **The pack arrives in pieces.** Three rounds before the first hit the target itself sees an outmatching pack
  (at `home_retreat_ratio`, on our half) within 5 tiles in 15% of the cases, within 6 in 35%, within 7 in 40% and
  within 8 in 45%. Against Mite 8, 25, 34 and 39%; against the Flp4 body 6, 22, 30 and 33%. The zone's radius is 5,
  the farthest one-turn strike, so it reads one member where the pack is three.
- **The step towards the pack is a farm step.** In the round before the hit the target stepped towards the pack in
  52%, stood in 22% and stepped away in 14%. In a debug sample against the Flp4 body (148 such engagements) its
  decision that round was farm in 79, retreat in 31, hold in 14; of 76 steps towards the pack 59 were farm steps and
  2 chases. Against the Mt3q body 57 of 71.
- 72% are on our half (Chebyshev distance to the two spawns), where a healthy champion gives way only to the zone.
- 37% of the pack's members within 8 of the target are out of its own sight. Nothing here addresses that.
- Stampede, side a, rounds 139 to 148: our Ryth stands alone 4 to 7 tiles from six Fish bodies for ten rounds on
  our half, steps back towards them at 147 and is stunned by Cassi at 148. The zone held it at the edge of their
  reach, one enemy step from a stun.

## The change

`params::pack_margin` (combat/guard.cc): the pack zone counts a member from `Strike::max_reach - 1 + pack_margin`
tiles instead of from its one-turn reach. Everything that reads the zone follows: the retreat it starts, the work
guard that keeps farm, bank and chase steps out of it, and the prey test. The ratios are unchanged.

- `pg-z6`: margin 1, the two-turn reach (`Strike::max_reach`).
- `pg-z7`: margin 2.
- `pg-z8`: margin 3, the edge of a champion's sight (`vision_radius`): every member we can see.

With the margin at 0 the build plays ocean's games: 52 of 52 bench replays byte-identical at 100M fuel.

Other arms, all built in the same source and all worse:

- `pg-p` (`home_pursuit`): `stand_lost_at` counts pursuers on our own ground when healthy and bagless too.
- `pg-z6p`: margin 1 with `home_pursuit`.
- `pg-z8a` (`pack_abroad`): margin 3, and the zone off our own half for the healthy at `hurt_retreat_ratio`
  (the second half of the arm the overruns README suggested).
- `pg-c8`, `pg-c6` (`pack_closing`): the margin only for a member seen to step nearer since our previous turn.

## Results against oc-dfuel-506

`py tools/fgate.py CAND variants/oc-dfuel-506 --fuel 200000 --first-batch 35 --max-batches 3 --ci 0`: fresh
ladder-v2 maps against the Flp4 and Mt3q bodies, both sides. The pool holds 38 batches of 2,560 maps, so "batch 40
upward" does not exist; batches 35 to 37 are its last three and no gate had played past 16.

| gate | win% (95% CI) of n | Fish, Mite | outcome |
|---|---|---|---|
| `pg-z6` fresh, 200k | 49.87% (49.35-50.39) of 7,680 maps | -0.43, +0.16 | level |
| `pg-z7` fresh, 200k | 49.41% (48.88-49.95) of 7,680 maps | -0.34, -0.83 | lost |
| `pg-z8` fresh, 200k | 48.21% (47.66-48.76) of 7,680 maps | -1.65, -1.93 | lost: REJECT after two batches (-1.65 ±0.67), the third -2.08 ±0.94 |
| `pg-p` fresh, 200k | 49.38% (48.84-49.91) of 7,680 maps | -0.86, -0.39 | lost |
| `pg-z6p` fresh, 200k | 49.17% (48.62-49.71) of 7,680 maps | -0.83, -0.84 | lost |
| `pg-z8a` fresh, 200k | 48.15% (47.48-48.82) of 5,120 maps | -1.21, -2.49 | lost: REJECT |
| `pg-c8`, `pg-c6` | not gated | | no effect on the mechanism (below) |

`pg-z8`'s loss is modest and is not a collapse: in the samples below our gold by round 300 moves by -1% and 0%, our
captures by -0.4% and -0.5%, our tributed gems by -1% and 0. What it gives up is ground: the enemy's captures by 300 rise
by 0.7 and 0.3 a game and its gold by 4% and 1%.

## The mechanism, candidate against base on the same games

Two samples against the static bodies `spar-dvn1-Flp4` and `-Mt3q`, both sides, read with
[tools/packmetrics.py](tools/packmetrics.py) (the overruns README's definitions; intervals resample games):

- A: the 128 ladder maps, debug builds (for the traces), 508 paired games a bot.
- B: `maps/gen` and `maps/gen-s1`, release builds, 2,048 games a bot.

| | base | pg-z6 | pg-z7 | pg-z8 |
|---|---|---|---|---|
| enemy-started outnumbering fights a game, A | 0.537 | 0.437 (-0.100, -0.197 to -0.006) | 0.431 (-0.106, -0.203 to -0.014) | 0.394 (-0.144, -0.236 to -0.049) |
| the same, B | 0.364 | 0.328 (-0.036, -0.077 to +0.004) | 0.299 (-0.065, -0.103 to -0.026) | 0.260 (-0.104, -0.141 to -0.065) |
| any fight entered outnumbered a game, B | 1.264 | 1.209 | 1.188 | 1.087 (-0.177, -0.268 to -0.081) |
| rounds a champion of ours is outnumbered within 8, a game, A | 53.2 | 52.3 | 49.8 | 41.4 (-11.8, -17.8 to -5.8) |
| the same, B | 34.3 | 33.3 | 32.3 | 27.8 (-6.5, -9.4 to -3.6) |
| share of those rounds it stepped towards them, B | 22.3% | 21.1% | 20.3% | 20.1% (-2.2, -2.9 to -1.5) |
| first target died, B | 22.1% | 19.8% | 21.2% | 20.5% |
| first target had moved towards the pack, B | 55.3% | 55.7% | 60.0% | 60.2% |
| our deaths by round 250 a game, B | 0.69 | 0.66 | 0.64 | 0.65 |

- **The rule fires.** In A, retreats the zone starts only through the margin (`PGZ ... 0` trace lines) by round
  250, against the Flp4 body: 7.6 a game for `pg-z6` and 20.3 for `pg-z8` (16.3 against Mt3q), beside 11.3 and
  9.4 inside the old radius.
- **It removes fights; it does not change the ones that remain.** In a fight the enemy still starts with the
  numbers, the first target dies as often and had walked towards the pack as often as before. So the live read is
  the count of those fights and the time spent outnumbered, not the per-fight rows.
- **Distance does the work, not the approach.** `pg-c8` counts the margin only for members seen stepping nearer:
  3.6 margin retreats a game and no change (0.512 fights a game against 0.537; outnumbered rounds 54.6 against
  53.2). `pg-c6` the same (0.486). A pack with dashes closes three tiles in a turn; what avoids it is not standing
  within its sight.
- `pg-p` removes as many as `pg-z6` (0.427 a game in A) for a larger loss; with the margin it adds nothing
  (`pg-z6p` 0.441).

## Fuel at 100k

No cost. `tools/fuel/bench.py --set wide --fuel 0` against each body (52 games), and the out-of-fuel turns of
sample B (release, 2,048 games):

| | mean fuel a turn, Flp4 / Mt3q | bench out-of-fuel turns | sample B out-of-fuel turns a game |
|---|---|---|---|
| base | 46,370 / 46,252 | 664 / 474 | 5.19 |
| `pg-z6` | 45,958 / 45,994 | 629 / 444 | 5.39 |
| `pg-z7` | 45,866 / 46,225 | 597 / 461 | 5.29 |
| `pg-z8` | 46,234 / 45,916 | 568 / 446 | 5.26 |

## Reading the live pair

```
py research/ideas-2026-11-11/packgive/tools/packmetrics.py live 115 NEW --pair
```

It takes the two versions' finished scrims against Fish and Mite from the scrim log
(`research/ladder-scrims-2026-11-06/data/games.jsonl`), unzips and decodes the replays it has not seen into
`~/tmp-offload/packgive/live`, and prints a column a version and the difference with a 95% interval, for Fish, Mite
and both; `--pair` keeps the (map, side, opponent) cells both versions played. `--since` and `--refset` narrow the
games. It needs numpy (the venv).

v115 by this script, 256 cells an opponent (it reproduces the overruns table: -0.42 of 135 and -0.06 of 118):

| | Fish | Mite |
|---|---|---|
| enemy-started outnumbering fights a game | 0.527 | 0.461 |
| net kills in them, each / a game | -0.42 / -0.223 | -0.06 / -0.027 |
| first target died | 37.0% | 19.5% |
| outnumbered rounds a game, on our half | 51.9 | 33.2 |

What a pair of 256 cells an opponent can resolve, from v114 against v115 (two versions with no pack change):
the fights a game differ by -0.02 with an interval of ±0.14 against one opponent and ±0.10 against both; the
outnumbered rounds on our half by ±10 and ±6.5; the first target's death rate swung 10.7 points against Fish on
its own. If the local rates carry over, `pg-z8` moves the fights by about -0.14 a game and the outnumbered rounds
on our half by about -9 against both: each at the edge of what the pair shows. `pg-z7` (-0.09) and `pg-z6` (-0.05 to
-0.09) are inside it.

- Read first: "they did, they had: a game" and "outnumbered rounds on our half a game". They should fall.
- Then "net kills a game" under it (Fish -0.223 now) and "first death by 150 ours". They show whether the fights
  avoided were the losing ones; expect them inside the noise.
- Guard rows: "our gold by 300", "our captures by 300", "their captures by 300".

## Verdict

- The mechanism is real and adjustable: the zone's margin removes a tenth to three tenths of the fights the enemy
  starts with the numbers, in step with the margin, with no fuel cost.
- Nothing here ships on local evidence. `pg-z6` is level; `pg-z7` and `pg-z8` lose 0.6 and 1.8 points to the
  bodies, and that loss is ceded camps, which real Fish and Mite will take as well, not fights the bodies happen
  to lose.
- The gain it can buy is small: the fights in question cost 0.22 kills a game against Fish and 0.03 against Mite.
  Removing three in ten of them is a few hundredths of a kill a game.
- `pg-z8` goes to live to measure whether fewer of these fights means fewer early deaths against the real teams.
  If it does and the win rate holds, `pg-z7` is the strength to weigh for shipping; if the fights do not fall
  live, the idea is closed.

## Files

- Candidates (gitignored): `bots/variants/pg-z6`, `pg-z7`, `pg-z8`; the other arms `pg-p`, `pg-z6p`, `pg-z8a`,
  `pg-c8`, `pg-c6`; `pg-dev` is the source with every option off.
- Patches against `oc-dfuel-506`: [pg-z6.patch](pg-z6.patch), [pg-z7.patch](pg-z7.patch),
  [pg-z8.patch](pg-z8.patch); they differ only in `pack_margin`. `patch -p1 --dry-run` in `bots/ocean` applies
  each cleanly (its working tree has someone's uncommitted comms edits; `params.h` applies at an offset of 7 lines).
  They carry the unused `home_pursuit` and `pack_abroad` options and the `PGZ` / `PGP` debug traces, as tested.
- [tools/](tools/): `packmetrics.py`; `approach.py` (the geometry above) and `branch.py` (decisions before a
  fight, from the `D` and `PGZ` lines); `dbg.sh` / `dlines.py` (sample A), `rel.sh` (sample B), `fg.sh`, `bench.sh`.
- Working data: `~/tmp-offload/packgive` (`ext-*` and `ext2-*` decoded samples, `mech-*.txt` tables, `logs/`).
