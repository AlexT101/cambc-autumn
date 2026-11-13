# Brief C: one price for a life and a bag in every fight decision (stakes by what the team loses)

You are an implementation agent for PHOEBE, who owns a macro refactor of our Cambridge Battlecode bot `charybdis`
(C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-phoebe` (branch `mx-phoebe-20261113`); never
touch `/home/ubuntu/cambc-autumn` (read-only reference) or any other worktree, never push, never commit (PHOEBE commits).
Another implementer works in `bots/variants/phb-lethal` at the same time: do not touch it.

## Read first
- `/home/ubuntu/wt/mx-phoebe/AGENTS.md`, `cambc-rules.yaml` (kills hand the killer 100 gold and every carried gem; a
  champion respawns 60-61 rounds after death with no gems; Cassi & Issac share a life: either death kills both, one
  kill reward, both bags; Prism +1.5 Focus per carried gem), `docs/api/cpp.md` as needed.
- The bot: `bots/variants/chy-ref/src` (= charybdis 529). The fight-side valuations use two flat constants,
  `params::life_value` (276.6, in enemy health points) and `params::gem_value` (17.5 a gem): `model/safety.cc`
  (`stake`, the trade evaluation near lines 977-1050, bag focus), `combat/fight.cc` (`prey` cost near 969,
  `stand_lost_at` near 565), `combat/guard.cc` (~532), `combat/abilities.h` / `abilities.cc` (`hit_worth`, kill
  worth), `combat/plan.cc` (strike search bag terms), `combat/self_abilities.cc`.
- The economy side prices the same things differently: `economy/capture.cc` `prism_premium(a, gems)` (expm1(k rho H):
  a gem the Prism keeps is worth 1 + premium gems, median ~3 early, ~1 by r300, 0 once it will not be kept),
  `economy/farm.cc` (a body's rate of worth per round, `output`), `economy/bank.cc` (EOQ bank floor with an online
  carrier hazard). History: CHANGES.md 525 (bag focus in the fight model, +1.1), 527 (consistent Prism-gem pricing
  across every *economy* choice: the C7 consistency gain, +2.8, came from every subsystem valuing the Prism's gems the
  same way). The fight model was not part of 527.

## Why
Measured in 1,360 mirror games (PHOEBE): a team whose Prism dies first loses ~92% (it carries ~75% of the gems a losing
team loses at death); the first champion death of a game leaves the victim's team winning only 34%; Cassi & Issac die
most (first victim in 43% of games, 2.9 deaths a game in losses) and are killed mostly by the enemy Prism, whose kill
adds their bags to its Focus. The fight model prices every life the same (276.6) and every gem the same (17.5),
whoever carries it and whoever would take it. The economy prices the Prism's gems at 1 + premium and a body's time at
its own rate. So a fight decision and a farm decision disagree about what is at stake, the same kind of inconsistency
527 removed inside the economy.

## The design: stakes in one currency, calibrated to today's level
1. **A life's stake by what the team loses**: the rounds the body is out (respawn, then its walk back to work: derive
   the walk from the map, e.g. its spawn-to-work steps, not a constant) times that body's output rate as the farm
   already measures/prices it, plus what the killer gains (100 kill gold at the bot's own gold price, the bag at the
   killer's gem price below). Cassi & Issac are one life of two bodies (both outputs, both bags). For enemies (prey,
   kill worth), use the same formula from the enemy's side with what we know (its type's output prior or our own
   same-type estimate, its seen bag).
2. **A bag's stake by its holder and its taker**: our keeping Prism's bag at 1 + `prism_premium` a gem; a bag an enemy
   Prism would take (it is the likely killer: in reach, the bot's threat model already knows who strikes) adds the
   Focus it gains (use our own premium as the symmetric estimate of theirs, there is no other measurement); an enemy
   bag our Prism would take, the same from our side.
3. **Calibration, not re-tuning**: `life_value` and `gem_value` were fitted by a tune lab and set the overall level of
   aggression. Keep that level: express the new stakes as multipliers whose team-average (over the bodies and bags the
   fight model meets, e.g. the mean of the life stake over our living bodies this turn) is 1, so the constants keep
   their meaning and only the *relative* stakes change (the Prism's life and premium bag up early, a low-output body's
   life down, the C&I pair counted as two). State the calibration in a comment.
4. Apply it at every fight-side site above, consistently (our own stakes and the enemy's). Leave `model/turn_order.cc`
   (its rank codes need fixed multiples of 15), the draft (`draft/`), emblem choices and `bots/variants/chy-ref` alone.

Keep it general and derived: no new hand-picked constants, no per-champion special cases beyond what the rules make
different (C&I's shared life, the Prism's Focus per gem). Fuel: the stake of each body is computed once a turn and
cached; no per-node recomputation in the strike search.

Measure the mechanism (debug study on `study`): deaths a game by champion type (our side), our Prism's first-death round
and rate, Cassi & Issac deaths, kills made, gems captured (the farm cost), for CAND vs REF.

## How to work
1. `./copybot variants/chy-ref variants/phb-stakes` (from the worktree root; never copy `.cambc/`), edit only
   `bots/variants/phb-stakes/src`. Build: `source ~/venv/bin/activate && cambc build bots/variants/phb-stakes`.
2. Debug studies: `bash research/mx-phoebe/ab.sh stkdbgN phb-stakes maps/suites/mx-phoebe/study --debug` (2,720
   games, ~3 min; extract with `node tools/replay/extract.mjs BATCH --out DIR`; scripts in
   `research/mx-phoebe/scripts/`: flow.py --by-bot phb-stakes, deaths.py, firstdeath.py). Win-rate reads only on the
   `train` suite:
   `tmux new -d -s mx-phoebe-stkN 'bash research/mx-phoebe/ab.sh stkN phb-stakes maps/suites/mx-phoebe/train'`
   (10,200 games, ~5-15 min); wait on `replays/ab/mx-phoebe-stkN/summary.json` with a background until-loop (never a
   foreground sleep). At most 3 such reads; noise is about +-1 point. If a read loses, find out why before changing
   anything (which bodies die more or less, which fights are now refused or taken).
3. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit any file) to check your diff
   against this brief and the rules (respawn timing, linked deaths, who gets the bag, calibration really averaging to 1,
   fuel); fix what it finds; make sure the bot builds; play the smoke
   `source ~/venv/bin/activate && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/phb-stakes variants/chy-ref --no-test-draft --fuel 200000 --name mx-phoebe-stk-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
4. Kill every tmux session you started (`tmux ls | grep mx-phoebe-stk`). Delete your replay batches
   (`replays/batch-*mx-phoebe-stk*`) once read, except the last train one.

## Stop condition and report
Stop when the design is implemented, audited, smoke-clean, and you have at most 3 train reads (or earlier if a read
shows a clear bug you cannot fix). Report: what you changed (files, functions, as a design, with the calibration), each
train read (win %, CI, OOF CAND/REF), the mechanism numbers CAND vs REF, the auditor's findings, open doubts. Leave the
final version in `bots/variants/phb-stakes` and write its diff to `research/mx-phoebe/patches/phb-stakes.diff`
(`diff -ruN bots/variants/chy-ref/src bots/variants/phb-stakes/src`).
