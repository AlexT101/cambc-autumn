# Brief C9: the Prism gem premium in kills, risk and turn order (implementer, licence to iterate)

Worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch `main` or
`/home/ubuntu/cambc-autumn` except to read). Follow `AGENTS.md` and `cambc-rules.yaml`. Don't change drafts (`draft/`
picks) or emblem choices.

## Setup
`./copybot variants/c7a-pgem variants/c9-pfight` (never copy `.cambc/`); edit only `bots/variants/c9-pfight/src`.
`variants/c7a-pgem` is the programme's current best: chy-ref plus `prism_premium` (economy/capture.cc), the derived
worth of one more gem in a keeping Prism's bag beyond itself (expm1(dOut x rho x H): Focus per gem -> camp output ->
the team's gems per output-round, compounded over the rounds the bag stays kept). Against chy-ref it reads train
52.8% (51.9-53.8), dev 53.1% (52.1-54.0), hold 52.7%. Its premium is used only in the economy (farm, holders,
leave-for-Prism, handoffs). If the final C7 variant (`variants/c7-pgem`) differs, ask nobody: build on c7a.

## Why
A gem moves between teams only through a champion kill: the killer takes the victim's whole bag (rules
`combat.kill`). So a bag's worth in a fight is not the same for every body:
- a bag our Prism takes by a killing blow joins a kept bag: worth gems x (1 + our Prism's premium);
- the enemy Prism's bag lost is worth gems x (1 + its premium) to them (the same derivation from their side: their
  Focus, their team's pace from the score and what we see);
- our Prism's own bag at risk costs gems x (1 + its premium) lost plus what the killer gains with it.
The fight code prices every bag flat: `params::gem_value` (17.5) a gem against `params::life_value` (277) in
combat/abilities.cc (`hit_worth`, stun value), combat/plan.cc (`x.bag`, strike plans), combat/fight.cc (prey cost
per gem, "a bag worth a life"), model/safety.cc (sides' stakes, `side.focus`), combat/guard.cc, and
`params::turn_gem_value` in model/turn_order.cc (turn priority bids); economy/bank.cc's carrier hazard uses
`bag_swing = 2` (the bag lost plus the killer's gain). Measured in the mirror: the team whose Prism dies first loses
~88%, gems lost at death decide 88% of games (L loses 231 gems a game at death, 165 of them the Prism's), and our
Prism lands 66% of first Prism kills.

## The design
Express every bag value in the fight code as gems x (1 + premium of the bag's next owner and of its loser), using one
helper built on `prism_premium` (and its mirror for an enemy Prism, from what we can read of it: visible gems and
Focus or its last sighting, the enemy score for the room to their win). Specifically:
1. Kill value of an enemy carrier: its bag at gem_value x (1 + premium of our killer if a keeping Prism) plus, for an
   enemy keeping Prism, gem_value x bag x its premium (what they lose beyond the gems).
2. Our side's stake: a keeping Prism's own bag at gem_value x (1 + its premium) wherever own bags are weighed
   (safety sides, "bag worth a life" gates, bank hazard swing for the Prism if it banks at all).
3. Turn-order bids (`turn_gem_value`) with the same weights.
4. Who lands the blow: where the strike plans choose between allies for the killing blow, the premium makes our
   Prism's last hit worth more; let the plan see it (don't add new mechanics).
Keep `gem_value` / `life_value` themselves; only the per-bag multiplier is new, derived. Measure what moves: Prism
kills, Prism deaths, gems lost at death, kills by our Prism.

## Measuring and iterating
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c9-pfight variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c9-trainN`
(10,240 games, ~5-15 minutes, noise ~1 point). It helps if it beats c7a's 52.8% on train by more than noise. Iterate
on `train` only (never `dev`, `hold`, `conf`, `x1`). Debug traces with `--debug` on `maps/suites/mac13/study`
(compare debug with debug); `debug_block({ printf(...); })` only. Report every full train reading; keep each tested
variant as a directory or saved diff. tmux sessions `mac13-castor-c9-*`; no foreground sleep; don't end your run
while a run you started is in flight.

## Before you return
1. A **read-only** auditor subagent (told explicitly not to edit anything) checks your diff
   (`diff -ru bots/variants/c7a-pgem/src bots/variants/c9-pfight/src`) against this design and the rules. Fix what
   it finds.
2. Build and smoke: `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c9-pfight variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c9-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save `research/mac13-castor/patches/c9-pfight.diff` (against c7a) and `c9-pfight-full.diff` (against chy-ref).
   Don't commit. Kill your tmux sessions.

Stop when implemented, audited, built, smoked, with at least one full train reading of the final variant. Return:
the changes (where each bag weight changed), every train reading, the fight measurements, doubts.
