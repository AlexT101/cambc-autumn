# hc1: fewer home trips from the farm (charybdis macro, DIONE programme)

You are an implementation subagent for DIONE, an orchestrator improving the macro of the Cambridge Battlecode bot
charybdis. Work ONLY in the git worktree `/home/ubuntu/wt/mac13-dione` (branch `mac13-dione-20261113`). Never touch
`/home/ubuntu/cambc-autumn` (read only), other worktrees under `/home/ubuntu/wt/`, `bots/charybdis`,
`bots/variants/chy-ref` (frozen reference: never edit), or any variant you did not create. Do not commit or push. Read
`AGENTS.md` and `cambc-rules.yaml` first (engine-verified rules; C++ only; comment only counterintuitive behaviour;
`unity.cpp` includes every `.cc`). Off limits: the draft (`draft/`, picks) and emblem choices (which emblem a champion
builds toward; when to shop is in scope, what to buy is not).

## Setup and running
`./copybot variants/chy-ref variants/hc1` (never copy `.cambc/`); edit only `bots/variants/hc1/src`. Python:
`source ~/venv/bin/activate`. Prefix every ab.py run with
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`.
Every A/B is `py tools/ab.py variants/X variants/chy-ref --no-test-draft --fuel 200000 --suites <suite> --name
mac13-dione-hc1-<tag>`, long ones in a tmux session of the same name, waited on with background until-loops on
`replays/ab/<name>/summary.json` (foreground sleep is blocked; commands over ~3 min get backgrounded). Only ever kill
or delete things carrying exactly the prefix `mac13-dione-hc1-` (others' runs share the `mac13-dione-` prefix). No
`--threads`, no fgate.py, gates, live tests or other opponents. Iterate only on `maps/suites/mac13/study` (1,024
maps = 2,048 games; `--debug` for traces) or `maps/suites/mac13/screen` (5,120 maps, 10,240 games); never use `dev`,
`hold` or `conf` (the orchestrator's decision suites). ab.py has no game cap: for a small batch make a suite dir of
symlinks to a subset of study maps. Delete your replay batches when done (~0.3 GB per 1k games).

## Why (measured in the chy-ref mirror at 2x fuel)
- **Turns in safe space are what wins.** Idling the farm branch 1 turn in 20 only when no enemy is visible within 10
  lost 6.7 points (43.3% of 10,240); the same idle only with an enemy within 10 cost nothing measurable (49.8%). Turns
  near enemies are worth little; turns in safe space are worth a lot.
- **The home cycle is the largest safe-space time sink.** Per team-game (200 debug mirror games, D lines
  `D <round> <handle> <branch> <farm_group> <claim>` at bot.cc:764): ~42 completed recalls. By health at the recall
  start and the branch in the turns before it: full health from the farm branch 13.3, 50-90% health from farm 8.5,
  under 50% from farm 4.6, from a hold (P) 5.5, from retreat 4.0, respawns 5.2. Each arrival is followed by a median
  15-19 rounds until the champion first hits a camp or takes a capture share, ~1,000 such rounds a team-game (~20%
  of team turns), plus the 5-turn recall channels. Camps deal ~15-16k damage a team-game, enemies 12-17k; Willow (when
  drafted) heals ~15 HP a round against ~52 of capacity. Gem and gold clusters never attack (strength 0), so a hurt
  champion can work them without healing; groups sit alive and untouched for 28% (gem clusters) to 41% (gem + wolf) of
  the game, so such work is usually available.
- The farm's recall is a priced option (`economy/farm.cc`, FarmRecall / recall_farm; `bot.cc` start_recall /
  continue_recall; `want_home` in `combat/fight.cc` holds the recall line `params::recall_health_fraction`). Scaling
  the recall line alone (x0.79) read level (50.4%), so the fix is not a constant: it is what the champion does instead
  of going home, and whether the trip home is priced against the real alternatives.

## Task
1. **Diagnose** with a debug batch (add `debug_block` traces): for each completed recall that started from the farm
   branch (and from holds), record why it was chosen (travel: farm priced the recall + walk from spawn as sooner;
   heal: the recall line or a camp the champion could not finish at its health; shop: gold to spend; other), the
   champion's health and gold, the best farm target it had instead and that target's price, whether a harmless group
   (no attacking member alive) was within reach, and whether Willow was alive and near. Tabulate turns by cause.
2. **Fix the largest avoidable causes, with logic tied to the rules**, e.g.: a hurt champion that would recall to heal
   first prices the harmless work it can do at its health (it takes no camp damage there) against the trip home, and
   the work's value against the heal's (rounds of future work the heal enables); recalls that heal also shop, and a
   shop alone is only worth the trip if the stats bought pay for the cycle's rounds; Willow heals a hurt ally near her
   when that saves the ally's trip home (only if it does not take her from the Prism when the Prism needs her). Each
   rule must be stated as a mechanism; constants derived from rules or measured, not tuned by hand.
3. When it first builds and a 256-game smoke (`py tools/ab.py variants/hc1 variants/chy-ref --no-test-draft --fuel
   200000 --name mac13-dione-hc1-smoke`) has no failed games, freeze a snapshot `./copybot variants/hc1 variants/hc1-s1`
   and continue.
4. Verify on a debug batch: completed recalls from farm and home->productive rounds per team-game down; camp + capture
   time up; still not up; deaths not up. OOF turns near chy-ref's (~600 per 10k at 2x fuel).
5. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check the diff against this
   brief and the rules (prune bounds in farm_turn stay valid, stale caches, Memory reset on death, fuel). Fix findings
   unless a study read shows the fix loses; say which.
6. Final: builds; the 256-game smoke clean (no failed games, no DRAFT-UNFINISHED / PLAN-CHECK); save
   `diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/hc1/src > research/mac13-dione/patches/hc1.diff`.
   Kill your tmux sessions; delete your batches except summaries.

## Stop condition, deadline, report
Stop when the final checks pass, and in any case report by **08:15 UTC** with your best variant so far. Report: what
changed (files, functions), the diagnosis table, before/after numbers, every variant you read (name, change, suite,
games, win %), the auditor's findings and what you did, and suspected leaks.
