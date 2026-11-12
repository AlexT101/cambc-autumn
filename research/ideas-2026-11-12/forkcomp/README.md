# Forking live Mite games, and per-composition constants (2026-11-12)

The user (2026-11-12): sample frames from live Mite games, put ourselves there and play on (fresh occurrences on fresh
maps too); and should constants differ by draft or composition, split first on the number of picks?

## A. Forking live Mite games: built, works, about as informative per game as a fresh-map gate

**How.** `fastrunner livefork` ([livefork.rs](livefork.rs), a new subcommand in a runner copy, wasm engine, [build.sh](build.sh)
builds it under `replays/forkcomp/runner`; the shared runner is untouched). The main line is the live game itself:
our live release build against the opponent puppet of the replay harness (tools/replay/harness), so the engine state
(cooldowns, buffs, gold, channels, locks, captures, wards, respawns) and our bot's memory are exactly the live game's.
At each fork round the state is snapshotted and each arm plays to the game's end with some team's champions replaced
by fresh instances of another bot. Hidden state:
- **The opponent's memory** (Mite's beliefs, its 8 shared bytes) cannot be had: the body starts cold, shared bytes
  zero. Its draft memory is its own plan for Mite's real picks: a draft with the picks forced (wengine::DRAFT_PICKS)
  computes it, and it is written into the puppet team's draft memory during the main line's draft (never read by the
  puppet, not in replays). No PLAN-CHECK or DRAFT- line in any of the 25,106 arms with a body.
- **Our variants** (any bot, e.g. charybdis) start cold too: their draft memory replaces ours in the engine's memory
  (the API refuses writes in play; the 1024 bytes are found by scan, once each time), shared bytes zeroed at the
  team's first turn.
- Main line = live game: **1,650 / 1,650** live Mite games (v105-v112, Mite r3 era) reproduce the live score exactly.

**Runs** (`livefork_run.py`, forks at rounds 100/300/600 when 30+ rounds remain, 16 pooled slots; data in `data/`):
live1 = v111+v112 (530 games, 1,438 forks, 8 arms, 221 s wall), live2 = v105-v109 (1,120 games, 3,008 forks, 6 arms,
327 s), local1 = the same maps and sides with our build against the body from round 1 (body warm; 64 s). An arm costs
~150 ms CPU (median 130), the main line and drafts ~170 ms a game.

Our win rate from the fork (points; SE clustered by game). "Live" is the puppet arm = what happened:

| fork | live | body continuation | body - live | body cold-start bias (local1) | our side cold-started (live1) |
|---|---|---|---|---|---|
| r100 | 61.3 | 68.8 | **+7.4 ± 1.4** | +4.5 ± 2.3 | +2.3 ± 2.3 |
| r300 | 61.0 | 66.6 | **+4.9 ± 1.2** | +3.1 ± 2.1 | -3.4 ± 2.3 |
| r600 | 54.0 | 55.9 | +1.3 ± 1.3 | -0.3 ± 2.4 | +0.3 ± 2.1 |
| all | 59.3 | 64.6 | +4.9 ± 1.0 | +2.8 ± 1.8 | -0.4 ± 1.2 |

- The body plays on **weaker than real Mite from the same positions**: +7.4 points to us at r100. About 4 of those are
  its cold start (local1: a fresh body, same or another noise seed alike, does +4.5 worse than the warm one at r100,
  nothing by r600); the rest is the body itself. At full games on these maps and sides, our live build beats the
  body 71.3% (± 2.0) against 62.1% live against Mite.
- Outcome agreement, body continuation vs live: 62/72/79% at r100/300/600, against 70/74/85% between two body noise
  seeds (the ceiling): the body's continuation is a bit further from Mite's than from itself.
- Our side cold-started shows no bias (-0.4 ± 1.2), as it agrees with the warm run about as often as two seeds do.

**Value: the calibration A/B.** chy-life (520) against chy-519 is +1.23 ± 0.18 points on the fresh-map gate (122,880
games, 61,440 of them the candidate's). Both swapped in for our side at the same forks, same body seed:

| forks | life - 519 (points) | candidate arm plays | share of forks whose outcome differs |
|---|---|---|---|
| r100 | +0.67 ± 0.74 | 3,300 | 29% |
| r300 | **+1.82 ± 0.56** | 3,266 | 16% |
| r600 | -0.39 ± 0.36 | 2,326 | 5% |
| all | **+0.81 ± 0.36** | 8,892 | |

- It finds the known gain, smaller (the variant plays only after the fork, and from Mite positions).
- Information per candidate play, z²/N: 5.7e-4 for all forks against 7.7e-4 for the fresh gate (0.75x); an arm is
  about 0.6x a game's CPU, so per CPU it is level. r300 forks alone read 3.2e-3 (4x), but that round was picked after
  the fact and suits this change (a mid-game Prism fix); a change that acts in the opening reads nothing there.
- Limits: positions only on the 128 ladder maps, from our old versions against Mite r3; the continuation is the body
  (5-7 points easier); a finite pool (~1,650 games set up; v113/v115/v116 hold ~10k more Mite games, not yet in the
  harness). "Fresh occurrences on fresh maps" do not exist for real Mite: on fresh maps the positions would come from
  games against the body, which is what fgate already plays.

**Recommendation.** Keep fgate as the gate. Use livefork for two things:
1. **The Mite body's fidelity**, a measurement fgate cannot make. From live positions, the body's continuation
   should match the live outcome rate by fork round (body - live, 0 is perfect), and agree with it as often as two
   body seeds do. Hand it to the Mite-body work as a check or a fitting target. The cold-start share (local runs)
   comes out of it.
2. **A second read for mid-game behaviour changes against Mite positions** (r300 forks, held-out games), never as
   the only gate.

**Follow-up costs.**
- Register v113/v115/v116 in the harness: `pipeline.py --version vN --opps mite`, about 30 min wall each. That adds
  Mite r6/r7 positions, and v116 is charybdis-p3, our current family.
- A run is about 5 min wall per 1,000 games at 16 slots.
- Porting livefork.rs into tools/fastengine/runner takes two lines in lib.rs ([lib.rs.patch](lib.rs.patch)) plus a
  review.

## B. Per-composition constants: no measurable interaction; leave as is

**What pick count is.** The map sets 3-5 picks a team. On the ladder it is mostly size: 3 picks on 21 of 128 maps
(median 31x31), 4 on 26, 5 on 81 (median 57x57); correlation with log area 0.57.

**What already depends on it in c520-ps:**
- the draft model (per pick count);
- the learned emblem table (`learned_arm[picks][type][ordinal]`);
- the 3-pick economy roles (Tavi on gold maps, Stellar, Marcella captures, Monster for all);
- crew caps by team size;
- the fight model, which simulates the enemy's actual champion types;
- `recall_health_fraction` and `gold_price_scale`, linear in map features (area, spawn distance, gems, altars,
  big-group share, symmetry; mapcond shrink 0.25).

The ~100 other params.h constants are flat.

**Measured** ([picksplit.py](picksplit.py), on the per-game logs of five SPSA runs, 2.7M paired games). Per constant,
the score gradient's change in 3- and 5-pick games against 4-pick games, with map-clustered SEs and a permutation null
over maps:

| run (bot, opponents) | paired games | omnibus p | prize of a split (debiased bound, points) / null 95% |
|---|---|---|---|
| lq-tune1 (ocean, Flp4/Mt3q bodies + ocean, fresh) | 405k | 0.105 | +0.20 / +0.26 |
| s88 (bsk, Fish/Mite bodies, ladder) | 617k | 0.52 | -0.24 / +0.87 |
| s87b (ocean, Fish/Mite bodies, ladder) | 617k | 0.085 | +0.72 / +1.22 |
| oc6 (ocean, panel, ladder only) | 102k | 0.84 | -0.38 / +4.31 |
| oc5 (ocean, panel, ladder + fresh) | 962k | 0.215 | +0.25 / +0.33 |

- No run beats its null.
- No constant flips sign between splits.
- The few single constants at p ≤ 0.01 (fight_weight in s87b; recall_health_fraction in oc5, already the mapcond
  finding) do not replicate across runs.
- These bounds overstate realised gains about 4x: oc-mapcond2 realised a quarter of its bound and read level.
- Splitting by opponent (Fish vs Mite bodies) is also null: s88 p 0.97, s87b p 0.75, prizes ≤ +0.07.

**Recommendation: leave as is.** Pick count is already used where mechanics differ (draft, emblems, 3-pick roles).
Its effect on the rest is mostly map size, which the closed mapcond line already tested. A split would halve the data
behind each constant for a gain that is at most a few tenths of a point. If the labs filler runs an SPSA round on
c520-ps (tune.py logs games.jsonl), `picksplit.py RUN` and `--split opp` re-check this for free on the current bot.
