# Fight-model calibration against Fish and Mite (2026-11-11)

Question: [cal-notes.md](cal-notes.md) found ocean's stand and chase verdicts calibrated, but only in the mirror, where
the opponent leaves lost stands by the same model. Is the model calibrated against Intercontinental Fish and Mite, the
opponents we lose to? **Answer: yes, where it decides. At both boundaries the first-death curve crosses 50% at margin 0
against both, and the games-won discontinuity is flat. The parts are biased differently against Fish (its members
deliver less of their simulated damage relative to ours than in the mirror), which shows as a short-lived bodies gain
from standing at the boundary against Fish that does not reach 20-round bodies or game results. `hit_given_reach`
transfers: reaching enemies deliver 0.77x the mirror's share for Fish, 1.09x for Mite, 0.94x pooled. Nothing to
correct; no bot changed, no A/B or live quota spent.**

## Method

- **Live games.** Our scrims against pinned Fish (ref r2) and Mite (r4, r5) from `research/ladder-scrims-2026-11-06`,
  for v105, v106, v108, v109 and v111. Their `model/safety.cc` and `combat/fight.cc` are identical, so the five versions
  share one fight model (they differ in farming, banking and greed arms). 2,690 games; 2,384 distinct with verdict
  rows after deduplication by replay hash (1,097 Fish, of which we won 728; 1,287 Mite, won 785).
- **Exact sources.** Each version's source is the scheduler's frozen build workspace
  (`~/tmp-offload/handoff/sched/gates.jsonl` maps version to workspace: the masked source as uploaded). Release builds
  re-run against puppets of the opponent's recorded inputs (`tools/replay/harness`, cambc 5.0.1) reproduce **2,690 of
  2,690** ladder games, inputs, round hashes and per-turn fuel identical, so every game's version and source are proven
  (the scrim log's queue-time version is right for all of them).
- **Instrumentation** (`tools/replay/harness/live_trace_bot.py`): cal-dbg's CS (stand) and CC (chase) lines with the margin, ported
  onto each version (chase_trade has no boost argument here), plus an HG line at each turn's end: every visible enemy
  whose strike reaches our tile, with the bot's `strike.at(d)` and `blow(e, p)`, the terms the strike search prices at
  `hit_given_reach`, and whether the search priced that tile (`search_priced_end()`).
- **Re-run build** (`tools/replay/harness/direct_batch.py`): the bot built as release code (the harness's `RELEASE_CODE` cmake patch)
  with only the trace lines inside `fc_block`, a fuel-paused window that flushes stdout inside it and refunds 2. It
  plays against the puppet; each game is trusted through the round before its first input or round-hash difference
  from the ladder replay, and its rows stop there (outcome windows read the ladder replay). **1,968 games reproduce
  exactly and 81% of all rounds are trusted.** Rows from fully reproduced games alone give the same tables
  (`fishcal/results-full-games.txt`).
  - The harness's tracer (fuel replayed from a recorder run) reproduces only 75 of v105's 600 games (25% of rounds),
    the plain v105 source included; plain debug builds, 150 (43%).
  - Fuel facts found on the way, on cambc 5.0.1: a debug-style window (`fuel_pause`, `fuel_adjust(2)`, `fuel_resume`)
    costs nothing net (`fuel_adjust(x)` refunds x). But printf output is buffered and written at the turn's end,
    outside any window, at about 110 fuel a turn that prints. Flushing inside the window makes 85% of turns
    fuel-identical to the release build's; the rest differ by a few units of codegen at the two call sites.
- **Mirror baseline.** The same instrumentation on v105's unmasked source (`bots/variants/fishcal-v105`) against
  itself, debug builds, the standard 1,280-game suite (`replays/batch-20261110-224607-ab-fishcal-self-v105-*`, pinned).
  Both seats run the same code, so a map's two side assignments are the same game: 640 distinct, 610 with verdicts,
  both teams logging.
- **Outcomes and statistics** as in cal-notes (`fishcal/collect.py`, `fishcal/ana.py`): deaths within 10 and 20 rounds
  by pick, who loses a champion first, damage exchanged, games won; 95% CIs from a Poisson bootstrap over games.

## Results

### Stand verdicts (self 583k, Fish 342k, Mite 407k)

P(our side loses a champion first | a death within 10 rounds), by margin:

| margin m | self | Fish | Mite |
|---|---|---|---|
| ≤ −3 | 13.6% | 9.1% | 11.4% |
| −1.5..−1 | 24.1% | 20.3% | 24.3% |
| −0.5..−0.25 | 39.5% | 41.7% | 39.9% |
| −0.25..−0.1 | 47.3% | 46.1% | 44.6% |
| **−0.1..0 (won, stay)** | **49.0%** (46.5-51.4) | **45.9%** (42.2-49.3) | **50.1%** (46.5-54.1) |
| **0..+0.1 (lost, leave)** | **50.8%** (48.0-53.2) | **57.1%** (53.5-61.3) | **53.6%** (49.8-57.0) |
| +0.1..+0.25 | 54.7% | 55.1% | 53.3% |
| +0.5..+1 | 67.2% | 69.6% | 62.6% |
| +1.5..+3 | 83.4% | 85.9% | 82.4% |

All three cross 50% at m ≈ 0. Fish's curve is steeper near the boundary and a little more extreme in the tails.

Jump won − lost at m = 0 (local linear):

| | bandwidth | bodies/10r | bodies/20r | our death /10r | an enemy's death /10r | games won |
|---|---|---|---|---|---|---|
| self | 0.25 | −0.009 (−0.023..+0.005) | −0.017 (−0.030..+0.005) | +1.8 pts | +1.2 pts | −0.055 (−0.126..−0.012) |
| Fish | 0.25 | **+0.045** (+0.025..+0.069) | +0.026 (−0.008..+0.054) | +1.9 pts | +4.1 pts | −0.018 (−0.044..+0.011) |
| Mite | 0.25 | −0.001 (−0.024..+0.021) | −0.004 (−0.030..+0.028) | +2.6 pts | +1.6 pts | −0.002 (−0.022..+0.018) |
| self | 0.5 | −0.015 (−0.022..−0.004) | −0.015 (−0.026..+0.003) | +1.8 pts | +0.9 pts | −0.037 (−0.078..−0.005) |
| Fish | 0.5 | **+0.025** (+0.008..+0.045) | +0.014 (−0.008..+0.037) | +2.0 pts | +3.0 pts | +0.010 (−0.009..+0.030) |
| Mite | 0.5 | +0.004 (−0.013..+0.020) | +0.004 (−0.014..+0.025) | +2.4 pts | +2.5 pts | +0.000 (−0.014..+0.020) |

- **Mite: flat**, as in the mirror.
- **Fish: staying at the boundary gains bodies over 10 rounds** (it kills a Fish 4 points more often for 2 points more
  of our deaths). The gain halves by 20 rounds and games won do not move. Fully reproduced games alone give the same
  (+0.043, +0.027; games −0.006, +0.009).
- Fish subgroups (`fishcal/results-all.txt`): the bodies gain is everywhere (healthy +0.044, alone +0.029, 2+ allies
  +0.067, 3+ enemies +0.110). Games won are level in every subgroup except champions under half health, where staying
  loses games against both (Fish −0.13, −0.25..−0.05; Mite −0.08, −0.15..−0.01; self +0.02 ± 0.05): a subgroup among
  ~50 tests, but the same sign for both opponents.

### Chase candidates (self 178k, Fish 102k, Mite 112k)

The curves stay below 50% on the lost side, as in the mirror (a declined chase has no fight of its own). Jumps:

| | bandwidth | bodies/10r | bodies/20r | games won |
|---|---|---|---|---|
| self | 0.25 | +0.021 (−0.001..+0.046) | +0.030 (−0.006..+0.073) | +0.042 (−0.002..+0.094) |
| Fish | 0.25 | +0.018 (−0.020..+0.056) | +0.060 (+0.005..+0.112) | −0.000 (−0.043..+0.048) |
| Mite | 0.25 | −0.017 (−0.064..+0.021) | −0.016 (−0.080..+0.035) | +0.004 (−0.038..+0.044) |
| self | 0.5 | +0.000 (−0.015..+0.023) | −0.002 (−0.028..+0.026) | +0.008 (−0.023..+0.038) |
| Fish | 0.5 | +0.028 (+0.005..+0.057) | +0.025 (−0.008..+0.065) | +0.013 (−0.019..+0.048) |
| Mite | 0.5 | −0.000 (−0.035..+0.032) | +0.007 (−0.037..+0.045) | +0.005 (−0.026..+0.040) |

Level against both; the same small Fish bodies lean as for stands, no games.

### Mechanisms

Stand roster members that hit within their arrival + 1 rounds, our champion staying:

| member | arrival | self | Fish | Mite |
|---|---|---|---|---|
| enemy, seen | 0 / 1 / 2 | 47.8 / 30.9 / 23.1% | 43.8 / 25.9 / 16.7% | 42.5 / 26.1 / 20.1% |
| enemy, unseen | 0 / 1 / 2 | 18.6 / 12.9 / 12.6% | 17.5 / 8.4 / 8.3% | 15.0 / 8.9 / 9.4% |
| ally | 0 / 1 / 2 | 30.3 / 18.4 / 10.4% | 27.2 / 18.9 / 9.8% | 26.7 / 19.4 / 10.7% |

Realized over simulated damage in 5 rounds, engaged stays (both sides strike in the sim's first turn):

| | theirs | ours | balance (theirs / ours) | balance, \|m\| ≤ 0.5 |
|---|---|---|---|---|
| self | 0.400 | 0.331 | 1.21 | 1.08 |
| Fish | 0.341 | 0.381 | **0.89** | **0.87** |
| Mite | 0.391 | 0.371 | 1.05 | 1.04 |

- Fish and Mite members hit less often than the mirror's, seen and unseen: neither commits members to a stand the
  way ocean does.
- Against Fish our side delivers more of its simulated damage and Fish less. Near the boundary the balance is 0.87
  against the mirror's 1.08, so the sim overstates Fish's damage relative to ours by about a fifth (a margin of about
  log2(1.08 / 0.87) = 0.3). That is the direction of the bodies jump. It does not move the first-death crossing or
  games won.
- Of FISH_MODEL.md's two readings, the measured one in aggregate is the second: Fish's members deliver less of their
  simulated damage than ours do, and its unseen and arriving members join less often (8% against the mirror's 13% at
  arrival 1-2), which fits its lack of pursuit beyond sight. The first-death curve is nonetheless level with the
  mirror's, so per death Fish needs less of the damage the sim gives it.

### `hit_given_reach`

Per reaching enemy (strike.at(d) > 0 at our turn-end tile): the damage it deals us before our next turn over the
blow the strike search prices (`blow(e, p)`), summed.

| end tile | self | Fish | Mite |
|---|---|---|---|
| priced by the strike search | 0.129 (0.123-0.134) | 0.099 (0.091-0.105) | 0.141 (0.134-0.146) |
| all turns | 0.087 | 0.076 | 0.101 |
| P(it damages us at all), priced | 17.5% | 15.6% | 16.4% |

- Against the mirror, Fish delivers 0.77x and Mite 1.09x; the two pooled by rows 0.94x. The constant was fitted in
  self-play, and the top two opponents together take it as the mirror does.
- By type, Fish's Heart of Ruin delivers about half the mirror's share (0.09 against 0.17) and Mite's Cassi, Tavi and
  Prism more (0.19-0.22 against 0.11-0.14). By distance the share falls from 0.15-0.18 at 1 tile to under 0.1 at 3+.
- The search charges 0.234 x blow (x Heart of Ruin's missing-health factor, 1 for every other type), 1.8x the realized
  0.129 in the mirror. It is an SPSA-tuned price, not a probability (it also prices the variance, stuns and turns
  lost), so the absolute gap is not a miscalibration. Only the live / mirror ratio is evidence, and it is near 1.

## Verdict

The fight model is as calibrated against Fish and Mite as against itself where it decides: the first-death curve
crosses 50% at m = 0 for both, and moving either boundary would not change games won (CIs about ±0.02-0.04 a
decision). Against Fish the model is somewhat pessimistic in damage terms. Standing there gains about 0.03-0.05 bodies a
boundary decision over 10 rounds, and nothing over 20 rounds or in games. A correction would have to rest on Fish's
lower damage delivery, which Mite shares only weakly (balance 1.04 against the mirror's 1.08) and which a bot cannot
condition on without knowing its opponent. Applied to every opponent, it would unbalance the mirror's cancelling
biases (cal-notes) for a gain the game results do not show. `hit_given_reach` needs no change. The open thread is the under-half-health subgroup, where staying at the
boundary loses games against both opponents (not the mirror). Test it only with a mechanism, not a threshold.

## Reproducing

The harness runs the whole re-run chain for a live version in one command (`tools/replay/harness/README.md`,
v105-v111): scrim manifest, workspace, decode, puppets and release re-runs, trace bot, traced re-runs, ladder
extracts. Data goes under gitignored `replays/v1xx/`; the analysis scripts are in `research/combat-lab/fishcal/`.

```
py tools/replay/harness/pipeline.py --version v105 --jobs 32       # any version the scheduler's gates.jsonl lists
python3 research/combat-lab/fishcal/collect.py live v105 replays/fishcal/live-v105.jsonl.gz
python3 research/combat-lab/fishcal/collect.py self replays/batch-...-ladder replays/fishcal/self-ladder.jsonl.gz
python3 research/combat-lab/fishcal/ana.py replays/fishcal/self-*.jsonl.gz replays/fishcal/live-v1*.jsonl.gz --sections calib,jump,members,damage,hg,sub
python3 research/combat-lab/fishcal/fueldiff.py v105 direct                # a re-run's per-turn fuel against the ladder's
```

The self-play rows come from a debug batch of `bots/variants/fishcal-v105` (v105's source with the same lines in debug
blocks) against itself.
