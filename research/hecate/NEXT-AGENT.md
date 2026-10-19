# Prompt for the next agent

Paste the block below into a new session.

```
You're continuing work on the hecate bot (bots/hecate, C++), on the main branch of this repo.

Read first:
- AGENTS.md: repo rules, tools, testing.
- cambc-rules.yaml: the game rules; it overrides docs/.
- research/hecate/CHANGES.md item 15: what the 2026-10-19 overnight session changed.
- The newest entries at the end of research/EXPERIMENTS.md: every experiment of that session, kept or dropped, with results.

Owner's direction:
- A robust, intuitive, logical bot. Prefer behaviour derived from the rules (reach, sight, cooldowns, health, walking distance, measured rates) over tuned constants, fixed decision orders or special cases.
- Logical changes stay even when level or slightly below 50% (other parts may need to catch up); drop only what is clearly worse (< ~47% over 1102 games) or wrong.
- Remove fuel checks over time so behaviour is predictable: make the guarded work cheap first, then remove the gate. Never accept more out-of-fuel turns than main.
- Keep the teleport, Tavi and Willow code.
- Past experiment results are hints, not rules: many were run on older bots.

Where things stand:
- main has: logical bug fixes, fuel rounds 1-2, the strike planner (plan.cpp), carrier chasing and a game-ender stop, the wall- and sight-aware danger model (Reach in safety.cpp) with its fuel round, siege heal-trip and siege-membership fixes, emblems chosen by measured value, measured-rate banking, cheaper exact fight simulation.
- Baselines: bots/baselines/hecate-v2 (start of that session), hecate-v3 (af51a77, after the planner).
- Out-of-fuel turns are still above hecate-v3's (about 50 vs 28 per 16 bench games vs rival). The remaining cost is Reach queries and fight sims on fight turns (step_guard, want_home, prey), plus the planner.

Open threads, roughly by value:
1. Retreat timing. The loss analysis (EXPERIMENTS.md) found the team with the first death loses 70%, 88% of deaths come within 4 turns of a retreat starting, and 53% of retreats last one turn. Price "fight back here" against "leave" under one danger model.
2. The retreat planner (branch plan3, unmerged): level with main at 100M fuel and at the real budget (49.8%), but out-of-fuel turns about 2.5x main's. Its next steps are listed in its EXPERIMENTS.md entry (exact danger only for the top paths, fewer dash-walk paths).
3. Fuel gates still needed: farm evaluation, step_guard, want_home/pursuit, prey, travel-dash, ward bush clusters, approach. Removing the sim gates outright triples out-of-fuel turns. Cheaper Reach queries and fewer of them per turn are the lever.
4. Choose the turn's goal before acting (decide() acts first, then picks chase/bank/farm). A chase-first attempt lost (branch plan2-wip-chase-stun); retry after the fuel work.
5. Allies don't answer a teammate's fight (the comms rally is read as a plain sighting).

How to test:
- Batches are fast: 746 games take ~2.5 min on 22 threads. Judge on ladder + maps/gen + maps/gen-central plus fresh suites (suite seeds 6501/6502 and 6601/6602 were the holdout and confirm pools: `node tools/mapgen/mapgen.mjs suite gen --out DIR --seed S`, and `suite central`). 1102 games give a standard error of ~1.5 points.
- Check other opponents too (baselines/nemesis-v2, rival): several changes were level in self-play but gained 2-5 points against them.
- For fuel: `py tools/fuel/bench.py run <bot> --opp <opp> --fuel 0`, against rival and nemesis-v2 (16 games each; counts swing by about ±20, so compare against main measured in the same session).
- Never run concurrent builds of the same bot directory: copy bots per test.
```
