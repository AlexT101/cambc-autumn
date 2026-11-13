# C6 `carry`: a big bag's death priced as what it is

Worktree /home/ubuntu/wt/mx-rhea (branch mx-rhea-20261113). Read AGENTS.md and cambc-rules.yaml first (combat.kill,
recall, tribute, abilities.stun). Do not commit, push, touch other worktrees, `bots/charybdis`, or
`bots/variants/chy-ref` (frozen reference). Do not change draft/ or emblem/shard choices. Another implementer works in
variants/c5-race (the endgame race when BOTH sides hold winning bags): leave it alone and stay out of that situation.

## What the data says (1,020 mirror games of chy-ref; `replays/ana-mirror`, loss report
`replays/ana-mirror/reports/20261113-155331/losses.md` and its csv files)
- Deaths cost 469 gems a game (731 in losses, 182 in wins). The win/loss signature is the **Prism killed carrying 200+
  gems**, walking with gems or fighting, grouped, killer seen 6+ rounds earlier: about 0.19 such deaths a game a side,
  almost only in lost games (top rows of losses-winloss.csv). A kill hands the whole bag to the killer: a 300-gem Prism
  bag lost to the enemy Prism is a 600-gem swing plus +450 Focus for their Prism.
- The report's counterfactual: a recall started in the safe window (the 5-turn channel finishing before the fatal
  damage began, no enemy within 4 meanwhile) would have saved 35-39% of those bags (`cf recall` column).
- Cassi / Issac / Vesper Vale killed with 50-199 gems walking with gems show the same shape at smaller size.
- Prior losses to respect: "Prism avoids enemy Prisms" always (-6) and a spacing rule (-5) both lost: positional freedom
  near the enemy is worth a lot. Banking earlier by bag size (-10 / -14) and later (-9) lost. So no blanket avoidance and
  no bag-size bank thresholds.

## The design (find out first, then build)
1. Measure, on the mirror's debug replays (`replays/batch-20261113-142221-ab-mx-rhea-mirror-study3`, stdout D lines;
   `research/mx-rhea/scripts/tt_follow.py` shows a champion's timeline), the deaths of carriers with 200+ gems (and
   50-199): what the victim's branch was over its last ~10 turns, when the killer was first seen and at what distance,
   whether a recall was started and how it ended (cancelled by damage / stun / manual), and what the safety model
   (want_home, the recall line, tribute_safe, continue_recall) said. Report the split.
2. Then make the decision that put the bag there price the bag's loss as the rules make it: the bag is lost AND given
   to the killer (a swing of twice the bag, and the killer's Focus if it is a Prism), against what staying earns. Find
   where the existing code prices death for a carrier (HoldAt / stand_lost_at / the recall line / any `bag` terms) and
   correct the price there rather than adding a parallel rule; e.g. if death is priced as dead time plus the bag
   once, the swing is missing. If the missing piece is the timing (the recall starts only after the safe window
   closed: a recall is cancelled by any damage), start the recall when the model says the window is closing.
   No magic numbers, no new tuned constants; tie every term to a rule.
Add debug_block lines where the new logic decides.

## Process
- `./copybot variants/chy-ref variants/c6-carry`, edit only there. Comment only counterintuitive behaviour, concisely.
- When it builds, spawn ONE read-only auditor subagent (general-purpose) with the diff and this brief: correctness, rule
  errors, stale beliefs, fuel. Fix its findings.
- Smoke (256 games; 0 failures, no DRAFT-UNFINISHED / PLAN-CHECK, OOF not up materially):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c6-carry variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c6-smoke`
- Binding check: same prefix, `py tools/ab.py variants/c6-carry variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx-rhea/study3 --debug --keep-replays 0 --name mx-rhea-bind-c6`,
  then `py research/mx-rhea/scripts/bind.py replays/batch-20261113-142221-ab-mx-rhea-mirror-study3 <that batch>`; also
  extract that batch (`node tools/replay/extract.mjs <batch> --out /tmp/mx-rhea/ana-c6`) and run
  `py tools/replay/analyze.py <batch> --reports losses --team c6-carry --analysis /tmp/mx-rhea/ana-c6` to compare the
  200+ / 50-199 carrier deaths per game for c6's side against the mirror's numbers above.
- Save the final diff (against chy-ref) to research/mx-rhea/patches/c6-carry.diff. Delete your smoke batch (keep bind-c6).
- Stop and report: step 1's split, the design as built (file:line), auditor findings and fixes, smoke (win%, failures,
  OOF both sides), bind.py output and the carrier-death counts. Do not run larger A/Bs.
