# Brief C6: the Prism's time budget (implementer, with licence to research and iterate)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/c7-pgem variants/c6-prism` (never copy `.cambc/`). Edit only
  `bots/variants/c6-prism/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`; other implementers work in
  other `bots/variants/c*` directories: don't touch them.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem/shard family and stat a champion builds toward:
  `best_emblem`, the learned arms). *When* and *how much* to shop is yours; *what* to buy is not.

## Why
The Prism is the team's farm engine (a third of all camp damage; +1.5 Focus per carried gem, so its rate compounds)
and the duel decides games, so a Prism round is the team's most valuable round. Measured over 1,024 solo games of
chy-ref against `bots/idle` on `maps/suites/mac13/study` (no enemy at all; r1-600; the Prism's rounds):
- walking 48%, hitting a camp 18.7%, recalling 17%, standing still (hold or wait) 10%, tributing 5%.
- 5.6 completed recalls a Prism by r600; 90% shop on arrival (mean gold 117, about 4 shards); 67% start at >=90% HP.
  In 33% of them the next camp it hits is 5+ tiles nearer the recall's origin than the spawn: it went home to shop
  and walked back, ~30 rounds to the next hit. The trip rule (`economy/shop.cc` `wants_shop`, Prism branch) goes as
  soon as `shop_gain_scale x affordable_prefix().gain + heal` beats the trip's rounds: a now-or-never test. The right
  question is when to go, given that gold keeps arriving: a trip of K rounds bought with gold G at income D a round
  costs K D / G rounds per round, and holding gold unspent costs h a gold-round (the saving forgone): the economic
  order quantity sqrt(2 K D / h), as `below_bank_floor` (economy/bank.cc) already does for tribute trips. Trips that
  are transport anyway (the next target is nearer the spawn) cost little; trips that come back cost the full K.
- Walk segments that end in a camp hit average 14.5 rounds; in 22% of them (42% of the walking rounds) the target
  was 5+ tiles farther (Chebyshev) than the nearest group with monsters up at departure. That may be right (bigger
  groups), or the farm's pricing may be missing something; find out from traces.
- The mirror (`maps/suites/mac13/study` debug A/B traces) says the same: the Prism hits camps 13% of its rounds.
Scripts that produced these numbers: `/tmp/castor-tools/prism_walk.py` and `/tmp/castor-tools/prism_recall.py`
(args: an extract.mjs output dir, then a champion type name). The solo extract is
`replays/.analysis-castor-solo` (from `replays/batch-20261113-041626-solo-mac13-castor-solodbg-study-cand`, debug
build with `D <round> <id> <branch> <farm_group> <claim>` trace lines; `tools/replay/turn_budget.py` reads them).

## The task
Cut the Prism's non-productive rounds by fixing what the valuation misprices, starting with the shopping trips:
1. **Shop timing for the Prism** (and, if the same logic applies, for the others): replace the now-or-never trip test
   by a timing rule derived from the trip cost, the gold income rate (the bot measures income: `income_rates`,
   `gem_income_rate`) and the per-gold saving, crediting trips that are transport anyway (the recall lands nearer the
   next work) and the heal. Keep `shop_gain_scale` out of the new rule unless you can derive it.
2. Then read traces for the next-largest avoidable cost in the Prism's budget (walks past nearer groups, holds that
   nothing in range uses, waits) and fix it if the cause is a mispricing you can state from the rules.
Every quantity must come from the rules or a measurement, not hand-picked constants. On the c7 base a Prism round
is worth more than its raw gems: the gems it farms carry `prism_premium` (economy/capture.cc), so price the trip's
lost rounds in that currency, consistently with the purchase's saving. Note also that a Health purchase is part of
the Prism's duel strength (the duel decides games: first Prism death loses ~88%): don't let fewer trips quietly
starve it of Health; if the saving the shop prices omits survival, say so and measure Prism deaths.

## Base
You build on `variants/c7-pgem` (v4), the programme's current best (chy-ref plus a derived premium on gems carried by a
keeping Prism, `prism_premium` in economy/capture.cc: train 52.8% (51.9-53.8), dev 53.1%, hold 52.7% against
chy-ref). Keep its changes. Your A/Bs are still against `variants/chy-ref`; your piece helps if your variant beats
53.0% on train by more than noise (~1 point at 10k games). Diff against the base for your patch
(`diff -ru bots/variants/c7-pgem/src bots/variants/c6-prism/src`), and also save the full diff against chy-ref.

## Measuring and iterating
- Farming speed (no enemy): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/solo.py variants/c6-prism variants/c7-pgem --name mac13-castor-c6-soloN --suites maps/suites/mac13/study --one-side --fuel 200000`
  (round to 1000 and collected gems @150/300/600, paired per map; chy-ref reaches 1000 at r667 on average). Add
  `--debug` for traces, and compare only debug with debug.
- Win rate: `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c6-prism variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c6-trainN`
  (10,240 games, noise about +-1 point; the box is busy, expect 10-20 minutes). Iterate on `train` only (never
  `dev`, `hold`, `conf` or `x1`). A faster farm that loses fights is no gain: check both.
- Report every full solo and train reading, not only the best; keep each tested variant as a directory or saved diff.
  Run long commands in tmux sessions named `mac13-castor-c6-*`; foreground sleep is blocked. Don't end your run while
  a run you started is in flight: wait for it.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design and your diff
   (`diff -ru bots/variants/c7-pgem/src bots/variants/c6-prism/src`) to check it against the design and the rules
   for bugs. Fix what it finds.
2. Make sure the bot builds and passes the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c6-prism variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c6-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c6-prism.diff`. Don't commit. Kill any tmux session you started.

Stop when the shop timing (and any second fix) is implemented, audited, builds and passes the smoke, with at least
one full train reading of the final variant. Return: what you changed and the derivation, every solo and train
reading, what the traces showed about the Prism's remaining time, and anything you were unsure about.
