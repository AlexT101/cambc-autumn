# Brief C12: the Prism's bag must still be tributed: price the final channel (implementer, licence to iterate)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `AGENTS.md` first and follow it (it says to read
`cambc-rules.yaml`: do; the tribute rules are `gems.tribute` and `altar_locks`). C++ API: `docs/api/cpp.md`,
`sdk/cpp/cambc.h`. Don't change drafts or emblem choices. Never edit `bots/variants/chy-ref`, `bots/charybdis` or
another implementer's `bots/variants/c*` directory.

## Setup
`./copybot variants/c11-int variants/c12-end` (never copy `.cambc/`); edit only `bots/variants/c12-end/src`.
c11-int is the programme's integrated best: chy-ref plus `prism_premium` (economy/capture.cc: the worth of one more
gem in a keeping Prism's bag beyond itself, expm1(k rho H), used wherever the bot decides who gets a group's gems),
a Willow medic, a stun screen (combat/screen.cc) and the Prism's shop timing (economy/shop.cc). Its pieces read on
train against chy-ref (10,240 games, 2x fuel): premium alone 53.0, + medic 53.8, + screen 53.5, + shop 54.1; the
integrated train reading is running now (`replays/ab/mac13-castor-c11-train1/summary.md` once done).

## Why (measured on 1,000 replays of c7 vs chy-ref, both sides alike)
A tribute is one channel of b = ceil(gems/10) turns (x0.67 with a Tribute emblem) that scores the whole bag at its
end; a stun or an enemy lock on the altar cancels it, and it restarts from zero. The Prism keeps its whole bag
(`keeps_bag`, `keeps_gems`: until the team's score plus its bag wins, or `closing`), so the race ends on one long
channel:
- At R1000 (the first round the team's score plus living bags reach 1,000) the winning Prism holds a median 580
  gems (58% of the total); the win comes a median 73 rounds later (mean 150) with a Prism, 18 rounds without one.
- The winning Prism's final tribute (first start a median 11 rounds before R1000) completes on the first try in
  about half of games. The top quarter takes 5+ starts, 41+ cancelled channel turns and 151+ rounds from R1000 to the
  win; the top tenth takes 20 starts, 245 cancelled turns and 436 rounds. Cancels near the end average 3.1 stuns,
  1.3 locks and 1.4 own cancels a game.
- Of all Prism tribute starts with 100+ gems, those with the nearest enemy within 8 completed 4% of the time (most
  ended in our own cancels within ~4 turns, i.e. opportunistic starts); 9-15 tiles away 23%; 16-25 tiles 50%; 26+
  tiles 38%. The mean channel is 70 turns, so the restart hazard far from enemies is about 0.01-0.015 a turn.
- The team that reaches R1000 first wins 87-88% of games with a Prism and 94% without. When both teams reach it,
  the first wins only 51% (224 of 1,000 games). Losers held 800+ in score plus bags in 36% of games.
Scripts: `research/mac13-castor/scripts/{endlag,endstarts,endprism,tstart,endfirst}.py EXTRACT_DIR`. The extract
is `replays/.analysis-castor-c7`.

## The design
The bag has to be tributed in the end. Each gem kept adds 0.1 turn (0.067 with Tribute) to a final channel the
win waits on. Under a restart hazard lambda, a b-turn channel takes an expected (e^(lambda b) - 1) / lambda turns,
so a turn added at length b costs e^(lambda b) turns. At the end, a race round is worth the whole team's
collection (its gems a round, `team_farm`), not the Prism's. Mid-game, a channel turn costs only the Prism's own
round (its rate x (1 + premium)).
1. **Installment banking for a keeping Prism.** Compare the bag's expected end cost (its share of the final
   channel at the team's rate, with restarts) with banking it now (the trip and the channel at the Prism's rate x
   (1 + premium), plus the premium on the banked gems, which their Focus no longer earns). When banking now is
   cheaper, the Prism banks at its next safe altar visit. Measure lambda in game, as `carrier_hazard` does for
   carriers: a Gamma prior from the numbers above, updated with our own channels' cancels per channel turn. Put
   the rule where `keeps_bag` / `keeps_gems` / the bank floor live, so the allies' reading of `keeps_bag`
   (`prism_premium`, holders) stays consistent with what the Prism does.
2. **Then, if traces show it:** the final tribute's start. Only start a long channel where it can complete (an
   altar no enemy stunner or lock carrier reaches within the channel, from what Safety knows); otherwise clear,
   wait or pick another altar, priced by the expected completion time. Opportunistic starts that cost nothing
   (a turn with nothing better to do) are fine; don't remove them.
Derive every quantity from the rules or the bot's measurements. No hand-picked thresholds.

## Measuring and iterating
- Win rate: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c12-end variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c12-trainN`
  (10,240 games, ~8 minutes, noise ~1 point). The piece helps if it beats c11-int's train reading by more than noise.
  Iterate on `train` only (never `dev`, `hold`, `conf`, `x1`).
- Mechanism: extract a train batch (`node tools/replay/extract.mjs BATCH --out DIR`; batches keep 1,000 replays)
  and rerun the scripts above. Look at the lag from R1000 to the win, the Prism's bag at R1000, cancels, and Prism
  first deaths.
- Debug traces: `--debug` (`debug_block({ printf(...); })` only); compare debug with debug.
- tmux sessions `mac13-castor-c12-*`; no foreground sleep; don't end your run while a run you started is in
  flight. Report every train reading; keep each tested variant as a directory or a saved diff.

## Before you return
1. A **read-only** auditor subagent (told explicitly not to edit anything) checks
   `diff -ruN bots/variants/c11-int/src bots/variants/c12-end/src` against this design and the rules. Fix what it
   finds.
2. Smoke: `... py tools/ab.py variants/c12-end variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c12-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`, OOF near chy-ref's.
3. Save `research/mac13-castor/patches/c12-end.diff` (against c11-int, `-ruN`). Don't commit. Kill your tmux
   sessions.

Stop when piece 1 (and piece 2 if pursued) is implemented, audited, built and smoked, with at least one full train
reading of the final variant, and no later than 09:15 UTC. Return: the rule and its derivation, lambda's prior and
in-game values, every train reading, the endgame measures before and after, and your doubts.
