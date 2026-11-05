# Opponent panel for idea winners (ocean, 2026-11-05)

The final "not exploitable" check for every idea winner. Picked by `bots/variants/oc-base1` (ocean, the draft5 draft,
farm R1+F1) against every candidate. The goal was diversity of lineage and style, and win rates of roughly 35-75%, so
that a change can move them. Fast runner, cambc 5.0.0, real fuel, `--no-test-draft`.

## The panel

| Member (use this dir) | What it is | Why |
|---|---|---|
| `variants/panel-astraeus` | astraeus, the parent; a frozen copy of `bots/astraeus` (working tree at 09:30, 2026-11-05) | Required. Ocean's own lineage without the draft5 draft and the farm changes. |
| `variants/panel-proteus` | astraeus d04b171 plus enemy turn windows and team slot assignment through comms | Required. A different turn-order and combat model, and the closest member (53.7%). |
| `variants/panel-demeter` | astraeus 38aa25ce plus pair-yield | The farm style: it shares camps and splits yield differently. |
| `variants/panel-ocean-td` | ocean (before the R1+F1 merge) on `test_draft`: the top 10 teams' ladder compositions | Ladder drafts, including compositions we never draft ourselves. This is AGENTS.md's deliberate exception: ocean keeps its own draft. |
| `baselines/v67` | the 2026-11-03 release, before fuel campaign 5, the ostrich and the SPSA constants | The oldest unsaturated baseline: older tactics and fuel habits, and other constants. |

The `panel-*` directories are copies of the live directories as measured: their `src/` is identical to the copies
that ab.py froze for these runs (`replays/frozen/6960f0939f4d`, `7e6881b5c366`, `0f03b448744d`, `8628f405cb3a`). Don't
edit them; the live `bots/astraeus` etc. may move on.

## Measured rates (oc-base1's wins)

Screening was on `maps/suites/merged/panel-514500` (fresh-514500..514504, ladder mix): 1,280 maps, both sides, 2,560
games per opponent. Logs are in `replays/ab/panel-oc-base1-vs-*/`.

| Opponent | Win % | 95% CI | OOF base / opp | Verdict |
|---|---|---|---|---|
| proteus | 51.7 | 49.8-53.7 | 27.0k / 27.4k | **panel** |
| baselines/v68 | 51.6 | 49.7-53.6 | 27.0k / 14.8k | unsaturated, but an astraeus snapshot (11-03); v69 covers it |
| baselines/v69 | 52.3 | 50.4-54.2 | 26.9k / 16.7k | unsaturated, but near-astraeus (11-03/04): adds little diversity |
| astraeus | 54.7 | 52.8-56.6 | 28.3k / 28.2k | **panel** |
| diana | 55.2 | 53.2-57.1 | 26.5k / 26.0k | astraeus fc99b847 plus the ostrich: same lineage, skipped |
| demeter | 56.6 | 54.7-58.5 | 26.7k / 25.1k | **panel** |
| astraeus_wip | 57.6 | 55.7-59.5 | 29.8k / 133.9k | its out-of-fuel turns (4.5x ours) dominate the result: skipped |
| baselines/v67 | 69.8 | 68.0-71.6 | 19.6k / 15.6k | **panel** |
| variants/ocean-td | 71.5 | 69.7-73.2 | 24.3k / 25.0k | **panel** |
| baselines/v66 | 73.7 | 72.0-75.4 | 19.6k / 14.3k | borderline; v67 covers the same era with more room |
| river_ac | 91.7 | 90.6-92.7 | 15.9k / 12.2k | saturated |
| hyperion | 93.0 | 91.9-93.9 | 14.8k / 6.3k | saturated |
| river | 98.5 | 97.9-98.9 | 11.7k / 447.1k | saturated: it runs out of fuel badly (447k turns) |

Not measured, because history puts them well above 80%: baselines/v61 (84-85% for astraeus on 2026-11-01) and v65
(76-78% then; astraeus has gained since). hermes is astraeus 90e2e0d (2026-10-24) plus a prototype, older than
river_ac.

No .htb or river-lineage bot is unsaturated. river_ac is an htb port of astraeus 5a0dbb98, and both rivers date from
2026-10-27.

**Base rates on the panel-check suite.** The panel's own suite is `maps/suites/merged/panel-check-514510`
(fresh-514510..514519, ladder mix, 2,560 maps, 5,120 games). Don't develop or tune on it. Logs are in
`replays/ab/pchk-oc-base1-vs-*/`.

| Member | oc-base1 win % | 95% CI | OOF base / opp | Fail if a winner reads below |
|---|---|---|---|---|
| panel-astraeus | 55.6 | 54.2-56.9 | 55.7k / 56.2k | 53.7 |
| panel-proteus | 53.7 | 52.3-55.1 | 55.1k / 54.9k | 51.8 |
| panel-demeter | 56.3 | 55.0-57.7 | 50.9k / 48.8k | 54.4 |
| panel-ocean-td | 74.4 | 73.2-75.6 | 48.6k / 49.3k | 72.7 |
| baselines/v67 | 69.9 | 68.7-71.2 | 37.5k / 30.6k | 68.1 |

Mean over the five: 62.0%.

## The rule

A winner W passes the panel when both of these hold:
1. **It doesn't lose significantly to any member.** For each member X, W's rate w_X on the panel-check suite (5,120
   games) must not fall below the base's rate b_X by more than 1.96 * sqrt(w(1-w)/5120 + b(1-b)/5120). That is about
   1.7-1.9 points (the right-hand column above). Put the other way, the 95% CI of w_X - b_X must reach 0.
   - The two-sample CI is used because b_X has noise of its own. Testing W's CI upper bound against b_X alone would
     fail a neutral change on some member about a third of the time.
   - Even so, a neutral change fails one of the five members ~12% of the time. If exactly one member fails, rerun W
     and the base against that member on a second fresh set from your own seed range (10 ladder-mix suites, 5,120
     games), pool both sets, and decide on the pooled numbers.
2. **It gains on average:** the mean of w_X - b_X over the five members is > 0.

If the base changes (e.g. `bots/variants/oc-base2`), re-measure b_X with the base in the CAND slot (about a minute per
member) before judging.

## Invocations

Run from the repo root, one at a time (COMMON.md). Wins are the candidate's (the first bot). Replace
`variants/oc-<id>` with the winner's directory.

```sh
source /home/ubuntu/venv/bin/activate
export CAMBC_BIN=$PWD/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
S=maps/suites/merged/panel-check-514510
py tools/ab.py variants/oc-<id> variants/panel-astraeus --no-test-draft --suites $S --name pchk-<id>-vs-astraeus
py tools/ab.py variants/oc-<id> variants/panel-proteus  --no-test-draft --suites $S --name pchk-<id>-vs-proteus
py tools/ab.py variants/oc-<id> variants/panel-demeter  --no-test-draft --suites $S --name pchk-<id>-vs-demeter
py tools/ab.py variants/oc-<id> variants/panel-ocean-td --no-test-draft --suites $S --name pchk-<id>-vs-ocean-td
py tools/ab.py variants/oc-<id> baselines/v67           --no-test-draft --suites $S --name pchk-<id>-vs-v67
```

`--no-test-draft` leaves every directory's `params.h` alone. The winner plays its own draft, and `panel-ocean-td`
keeps its `test_draft = true`, which is the intended exception. The total is in the `**total**` row of
`replays/ab/pchk-<id>-vs-*/summary.md`. COMMON.md asks for ≥10k games against astraeus and proteus: add a second
5,120-game set from your own seeds for those two and pool.
