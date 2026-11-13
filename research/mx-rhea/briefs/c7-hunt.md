# C7 `hunt`: let the favoured Prism close

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first (abilities: stun,
exclusive, cooldown; rounds.champion_order; combat.kill). Do not commit, push, touch other worktrees, `bots/charybdis`, or
`bots/variants/chy-ref` (frozen reference). Do not change draft/ or emblem/shard choices. Other implementers work in
variants/c5-race and variants/c6-carry: leave them alone.

## Why
- The first Prism death decides the game: its team wins **8%** of 540 mirror games (also 8% when it happens by r200).
  393 of those deaths are by the enemy Prism; the weaker (by Focus) dies in 69%. (`research/mx-rhea/scripts/prismdeath.py`,
  `early.py` on `replays/ana-mirror`.)
- Duel study (NOTES.md 15:05, scripts pd_*.py): 4.2 hunt episodes a game (stronger Prism S, Focus >= 1.2x, hp >= 60%,
  sees the weaker V at 5-9). S closes to stun range only 33% of the time. When it closes, V dies 17% (Focus ratio 1.2-2),
  31% (2-3), 53% (3+) and S dies under 1%.
- C2 (`bots/variants/c2-duel-ns`, patch research/mx-rhea/patches/c2-duel-ns.diff) built a duel model (combat/duel.{h,cc}:
  duel_edge, net_bodies, hunt_target, hunt_worth) and a hunt through prey()/chase() in combat/fight.cc. It read level
  (49.9 dev) and bound in only 14% of games: the hunt fired 1.4 times a game and was mostly vetoed, by `escapes()`
  (HUNTX escapes, fight.cc ~1081) and by the chase trade (`t.lost`, HUNTX lost, ~1090).

## The design (find out first, then build)
1. Build on c2-duel-ns: `./copybot variants/c2-duel-ns variants/c7-hunt` (copybot leaves out .cambc/).
2. Measure on debug games which veto stops favoured hunts and whether it is right: run
   `py tools/ab.py variants/c7-hunt variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study --debug --keep-replays 0 --name mx-rhea-c7-probe`
   (env prefix below) before changing anything, and for HUNTX escapes / lost cases follow what V actually did next
   (replays; tools/replay/analysis Game API or research/mx-rhea/scripts/tt_follow.py after extracting with
   `node tools/replay/extract.mjs <batch> --out /tmp/mx-rhea/ana-c7`). Check the vetoes' arithmetic against the rules:
   a stun removes the target's next turn (it can neither walk away nor cast), an excludes-walking stun cannot follow our
   walk, cooldown 8, and turn order alternates per round (double moves). If `escapes()` or `chase_trade` ignores our
   stun's lost turn for the target, or our ready stun on arrival, that is a mechanism error: fix it for the hunt (or for
   all chases if it is the same model and the fix is right in general).
3. Let a favoured hunt the corrected model says closes in time go ahead, with the duel model's own verdict (both
   sides' stun cycles) as the safety, not the generic escape heuristic. Keep the C2 pieces that read the same
   model; no new tuned constants.
Add debug_block lines for the hunt decision and its outcome.

## Process
- Comment only counterintuitive behaviour, concisely.
- When it builds, spawn ONE read-only auditor subagent (general-purpose) with the diff against chy-ref and this brief:
  stun / turn-order arithmetic, stale beliefs, fuel. Fix its findings.
- Env prefix for every run: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`
- Smoke: `py tools/ab.py variants/c7-hunt variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c7-smoke` (256
  games; 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially).
- Binding: `py tools/ab.py variants/c7-hunt variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study3 --debug --keep-replays 0 --name mx-rhea-bind-c7`,
  then `py research/mx-rhea/scripts/bind.py replays/batch-20261113-142221-ab-mx-rhea-mirror-study3 <that batch>`; count
  hunts fired / closed / kills / our Prism deaths per game, and first-Prism-death share by side (`prismdeath.py` on the
  extracted batch).
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c7-hunt.diff. Delete your probe and smoke batches
  (keep bind-c7).
- Stop and report: step 2's findings, the design as built (file:line), auditor findings and fixes, smoke (win%, failures,
  OOF both sides), bind.py output and the hunt counts. Do not run larger A/Bs.
