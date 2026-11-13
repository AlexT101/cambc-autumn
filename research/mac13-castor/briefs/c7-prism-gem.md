# Brief C7: what a gem in the Prism's bag is worth, priced consistently (implementer, licence to iterate)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/chy-ref variants/c7-pgem` (never copy `.cambc/`). Edit only
  `bots/variants/c7-pgem/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`; other implementers work in
  other `bots/variants/c*` directories: don't touch them.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem a champion builds toward).

## Why (measured)
The Prism gains +1.5 Focus per carried gem (rules `champions.prism.passive`); its spells deal 1.5x and 1.0x Focus, so
its farm rate compounds with its bag, and the Prism duel decides games (first Prism death loses ~88%). A logistic fit
of the winner on each team's gem holdings, 1,023 chy-ref mirror games (debug, study suite), per 100 gems of
difference between the teams (all games with both Prisms):

| round | tributed | carried by others | carried by the Prism |
|---|---|---|---|
| 150 | 0.39 +-0.14 | 0.81 +-0.13 | 1.18 +-0.11 |
| 200 | 0.45 +-0.10 | 0.55 +-0.11 | 1.15 +-0.09 |
| 300 | 0.65 +-0.08 | 0.67 +-0.10 | 1.21 +-0.08 |
| 400 | 0.73 +-0.06 | 0.43 +-0.10 | 0.87 +-0.06 |
| 500 | 0.66 +-0.05 | 0.48 +-0.10 | 0.65 +-0.04 |

So through r300 a gem in the Prism's bag carries about twice the win weight of a gem anywhere else; by r500 the
premium is gone. Also at equal team totals (+-10%), the team whose Prism holds a 10-point larger share of the team's
gems wins 58% (r200), 60% (r300), 61% (r400). (Correlational: a Prism with more gems is also one that lived and
farmed; but the farm-compounding argument below predicts a premium of the same size.)

A rule-derived estimate of the premium: a gem adds 1.5 Focus, i.e. 1.5 x 2.5 / 8 ~ 0.47 spell damage a round at
the cooldowns; at the Prism's measured utilisation and its damage per gem this yields roughly one more gem over the
~400 rounds a bag is kept, before compounding, plus the duel.

The bot prices it as a farm-value shard equivalent, once: `economy/capture.cc` `carried_bonus` = per_gold x
(1.5 / Focus growth) x 30 gold (prism_focus_per_gem / growth Focus shards at shard price), used only by the Prism's
own farm (`economy/farm.cc` `keep_most` / `keep_bonus`). Read its actual size in traces (it depends on
`prices().per_gold`); my guess is well under 1 gem. And it is not used by the allies' side of the same decisions:
`holder_value` / `value_holder` (who should hold a cleared group), `left_for_prism` / `leave_for_prism` (allies
leaving a gem group for the Prism), the takeovers (`prism_takeover`, `prism_carries`, `takeover_gain`), crew pricing
(`economy/crew.cc`) and handoffs all compare gems as gems.

## The design
1. One function for the worth of one more gem in a given Prism's bag at this point of the game, beyond the gem
   itself: derived from the rules and the bot's own measurements (Focus per gem, spell multipliers and cooldowns,
   the Prism's measured farm rate / damage per gem (`income_rates`, `gem_income_rate`, `camp_output`), the rounds the
   bag is expected to stay carried (until the winning bag / `bag_rounds_left`), compounding), and zero when the bag
   won't be kept (`keeps_bag`) or the gems exceed what's needed to win. Check its size against the measured premium
   (~1 extra gem a gem through r300, fading to ~0 by r500); if your derivation can't reach it, you may add the
   duel's share as a measured term, but say so and keep it a single derived/measured quantity, not a knob.
2. Use that one function everywhere the bot weighs who gets a group's gems: the Prism's own farm (replace
   `carried_bonus`), `holder_value` / `value_holder` for a Prism holder, the leave-for-Prism decision (an ally leaves
   a gem group for the Prism when the Prism's premium on its gems beats what the wait/walk costs the team), the
   takeovers and handoffs, and crew shares where the Prism is a sharer (the split's gems in the Prism's bag count
   with the premium). Consistency is the point: today the Prism values its gems more than its allies do.
3. Nothing else changes: safety, fights and the Prism's tribute timing stay as they are.

## Measuring and iterating
- Win rate (the decision for you): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c7-pgem variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c7-trainN`
  (10,240 games, noise about +-1 point; the box is busy: 10-20 minutes). Iterate on `train` only (never `dev`,
  `hold`, `conf` or `x1`).
- Farming against an idle opponent: `py tools/solo.py variants/c7-pgem variants/chy-ref --name mac13-castor-c7-soloN --suites maps/suites/mac13/study --one-side --fuel 200000`
  (round to 1000, collected @150/300/600; add `--debug` for traces). Also check the Prism's share of team gems at
  r200/r300 moved (from replays: `node tools/replay/extract.mjs BATCH --out DIR`, then rounds.json.gz `gems` per
  champion; the analysis script `/tmp/castor-tools/preg.py DIR` reproduces the table above on any extract dir).
- Report every full train and solo reading, not only the best; keep each tested variant as a directory or saved
  diff. Debug traces: `debug_block({ printf(...); })` only, never plain printf. Run long commands in tmux sessions
  named `mac13-castor-c7-*`; foreground sleep is blocked. Don't end your run while a run you started is in flight.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design and your diff
   (`diff -ru bots/variants/chy-ref/src bots/variants/c7-pgem/src`) to check it against the design and the rules
   for bugs. Fix what it finds.
2. Make sure the bot builds and passes the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c7-pgem variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c7-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c7-pgem.diff`. Don't commit. Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke, with at least one full train reading of
the final variant. Return: the premium's derivation and its traced size (before and after), where it is used, every
train and solo reading, the Prism's gem share before/after, and anything you were unsure about.
