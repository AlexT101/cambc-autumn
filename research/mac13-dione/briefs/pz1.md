# pz1: a dominant Prism takes the enemy's gems (charybdis macro, DIONE programme)

You are an implementation subagent for DIONE, an orchestrator improving the macro of the Cambridge Battlecode bot
charybdis. Work ONLY in the git worktree `/home/ubuntu/wt/mac13-dione` (branch `mac13-dione-20261113`). Never touch
`/home/ubuntu/cambc-autumn` (read only), other worktrees under `/home/ubuntu/wt/`, `bots/charybdis`,
`bots/variants/chy-ref` (frozen reference: never edit), or any variant you did not create. Do not commit or push. Read
`AGENTS.md` and `cambc-rules.yaml` first (engine-verified rules; C++ only; comment only counterintuitive behaviour;
`unity.cpp` includes every `.cc`). Off limits: the draft (`draft/`) and emblem choices.

## Setup and running
`./copybot variants/chy-ref variants/pz1` (never copy `.cambc/`); edit only `bots/variants/pz1/src`. Python:
`source ~/venv/bin/activate`. Prefix every ab.py run with
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`.
Every A/B is `py tools/ab.py variants/X variants/chy-ref --no-test-draft --fuel 200000 --suites <suite> --name
mac13-dione-pz1-<tag>`, long ones in a tmux session of the same name, waited on with background until-loops on
`replays/ab/<name>/summary.json` (foreground sleep is blocked; commands over ~3 min get backgrounded). Only ever kill
or delete things carrying exactly the prefix `mac13-dione-pz1-`. No `--threads`, fgate.py, gates, live tests or other
opponents. Iterate only on `maps/suites/mac13/screen` (10,240 games) or `maps/suites/mac13/study` (2,048; `--debug`
for traces); never `dev`, `hold` or `conf`. The machine is heavily loaded: a 10k screen takes ~10-15 min.

## Why (chy-ref mirror, 2x fuel)
- The race is relative: a gem the enemy does not get is worth as much as one we get. chy-ref's farm prices gems
  absolutely (plus a tuned middle-band premium, `params::mid_exposure`, for every champion; raising it for everyone
  lost: 2.4 read 48.6%).
- Winners take the middle and the enemy half: capture gems a game, winner vs loser: own half 762 vs 719, middle
  137 vs 76, enemy half 128 vs 89. Groups on a team's own half are taken 87% by that team, 13% by the other.
- Turns near enemies are worth little to the body taking them (idling 1 farm turn in 20 near enemies cost nothing;
  in safe space it cost 6.7 points). An enemy body near a threat it gives way to loses its farm turns: being zoned costs
  (an earlier programme's "every champion avoids a dominant enemy Prism" lost 4.7 points).
- The first Prism death decides 89% of games; the killer's bag is ~2x the victim's, so a dominant Prism (Focus
  well above every enemy's, unable to be burst) is safe where others are not.
So a dominant Prism should farm where its gems also come out of the enemy's share, and where its presence costs enemy
bodies their farm turns.

## Design
1. **Dominance (one-sided safety).** Our Prism is dominant when no enemy body or plausible pair of them could burst it
   before its next turn and the enemy Prism (if alive and believed) is weaker than it by the existing definitions
   (read `prism_dominant` and the lethal/burst code in `model/safety.*`, `combat/fight.cc`; reuse them; no new
   thresholds). Hysteresis only on facts (seen Focus, health), not counters.
2. **Denial value for the dominant Prism only.** In `economy/farm.cc` farm_turn's valuation for our Prism while
   dominant, a group's gems are worth gems x (1 + q), q = the share the enemy would otherwise take. Derive q from the
   map geometry the farm already has (the middle-band walk share d_enemy / (d_ally + d_enemy) from the two spawns; q =
   1 - that share, so enemy-half groups approach 1 and own-half groups approach 0), or from a measured split; state
   which and why. Keep the prune bounds valid: the most this can multiply a value is 2, so the exact bounds and every
   pre-facts prune must include it for the Prism while dominant (read how `exposure_most` and `carried_bonus` /
   `keep_most` are folded into the bounds and do the same).
3. **Nothing else changes**: allies, carry/funnel rules, retreat, strike search, banking. (Allies already stop
   funneling to a dominant Prism.)
4. Measure on a debug batch: dominant-Prism rounds per game; our Prism's capture gems by side (own/middle/enemy half)
   and the enemy's capture gems; Prism deaths; first Prism death share. Script ideas: `/tmp/dione/side.py
   <analysis_dir>` (captures by side for winners/losers; adapt to cand/ref), `/tmp/dione/pdeath.py <analysis_dir>
   <cand_team_name>` (first Prism death split); extract with `node tools/replay/extract.mjs <batch> --out <dir> --threads 24`.
5. When it first builds and a 256-game smoke (`py tools/ab.py variants/pz1 variants/chy-ref --no-test-draft --fuel
   200000 --name mac13-dione-pz1-smoke`) is clean, freeze `./copybot variants/pz1 variants/pz1-s1` and continue.
6. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check prune-bound validity,
   the dominance test (team sides, stale beliefs), and fuel. Fix findings.
7. Final: builds; smoke clean; `diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/pz1/src >
   research/mac13-dione/patches/pz1.diff`. Kill your tmux sessions; delete your batches except summaries.

## Stop condition, deadline, report
Stop when the final checks pass, and in any case report by **08:55 UTC** with your best variant. Report: what changed,
the measurements before/after, every variant read (name, change, suite, games, win %), auditor findings and fixes.
