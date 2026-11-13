# Brief F: farm throughput, more gems a champion-round at equal risk (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference), `bots/charybdis`,
or any other variant. Another subagent works in `bots/variants/e-denial` on pricing contested middle groups (the
farm's mid_exposure / home_ground weights); stay out of that.

## Why
Four lines this afternoon (Prism collector, crew staging, contact-risk pricing, fight stakes) each moved their
mechanism and read level against chy-ref: the bot sits on an optimised risk/farm frontier, where trading farm for
safety or back reads ~50%. A gain needs a Pareto move: more gems per champion-round with no more risk. Early economy
decides games (mirror: a Prism bag lead of 20-50 gems at r150 wins 63%, 50-100 72%; median Prism bag 105 at r150), so
a few percent of farm speed is worth points. Measured on chy-ref (study suite; scripts in research/mx-crius/scripts):
- Solo against an idle team (`replays/solo/mx-crius-solo-base`): reaches 1000 tributed at r620.4 (mean),
  collected @150 / 300 / 600 = 222.9 / 524.7 / 934.2.
- Even solo, groups sit up and asleep at full health 52-72% of rounds (`supply.py`): the farm is champion-time bound,
  not supply bound.
- Time, rounds <= 600, solo (`budget.py`): every body moves ~55% of its rounds (Prism 55.7% moving, 35% standing at
  camps, 6.1% tributing, 2.8% on spawn). The Prism's walking (`legs.py`): camp -> camp 46.5%, spawn -> first camp
  33.8%, camp -> spawn 10.2%, camp -> altar 4.2%: about 19% of the Prism's time is the spawn cycle (~5.6 home visits
  by r600, mostly shop recalls at high health).
- Jobs that pay nothing (`waste.py`, a champion's rounds attributed to the next group it damages): 6.2% of champion
  time solo goes to groups nobody captures within 30 rounds (abandoned).
- Priors (research/EXPERIMENTS.md and research/macro-2026-11-11/*/): a chain lookahead lost (45.6, macro2), a
  follow-up end-position value was level (macro6), keeping the farm target until news lost (48.6), shop EOQ for
  non-Prism level (49.4); CASTOR's Prism shop EOQ shipped in 527; crystals for travel level. Learn from them: an
  earlier failure is not proof, but know why each lost before repeating it.

## The task
First find where solo farm time is wasted, with traces (`--debug` solo games on `study`: `debug_block({ printf(...);
})` in your copy; the farm's choice, its rate, the alternatives' rates, walks, waits), against what a better plan
would have done: walks past groups to farther ones, groups left to idle near a body that walks away, home trips that
could ride on another trip, two bodies crossing each other's paths, waiting, abandoned walks, holds that could
overlap clearing. Then fix the biggest addressable waste inside the existing farm (`economy/farm.cc` farm_turn,
`economy/camps.cc` clear and rate models, `economy/shop.cc` trips, `economy/bank.cc` banking trips), as a consistent
price, not a rule bolted beside it. For example, a job's rate that counts where it leaves us (the best next job from
its end tile, at 2x fuel a bounded lookahead is affordable), or a home trip priced with everything it can carry. No
magic numbers: quantities from the rules or measured.
Leave alone `draft/`, which emblems champions build (`economy/shop.cc` emblem choice), fuel optimisation (we test at
2x fuel; a guard against runaway loops is fine), the risk and fight logic (combat/, safety), and the middle-band
weights (line E).

## How to work
- `./copybot variants/chy-ref variants/f-thru` (never copy `.cambc/`) and work in `bots/variants/f-thru`.
- Solo speed first (both against an idle team, paired per map, ~5 min): `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/solo.py variants/f-thru variants/chy-ref --suites maps/suites/mx/study --one-side --fuel 200000 --name mx-crius-f-solo-<tag>`
  (`--debug` for traces; `replays/solo/<name>/summary.md`). Aim for a clear gain in round to 1000 and collected
  @150/300 before spending A/Bs on it.
- Win rate: `... py tools/ab.py variants/f-thru variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-f-<tag>`
  (10,200 games, ~3-8 min; `replays/ab/<name>/summary.md`). Run long commands in the background
  (`run_in_background`), never a foreground sleep loop. Use only `train` for A/Bs and `study` for solo runs and
  traces; never `dev`, `hold`, `x1`, `x2`, `x3`, `scr` or `fin`. Delete replay batches you no longer need.
- Iterate at most ~4 full train A/Bs (solo runs are free to repeat; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs (prune soundness in farm_turn above all); fix what it finds;
  make sure the bot builds; play a smoke `py tools/ab.py variants/f-thru variants/chy-ref --no-test-draft --fuel 200000`
  (256 ladder games: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: built, audited and smoked with its best train A/B; or after ~4 train A/Bs; or if the traces show no
  addressable waste (then report what they showed).

## Report back (concisely)
Variant path; what the traces showed (where solo time goes, the wastes ranked by gems); what you built (files); each
solo run (round to 1000, collected @150/300/600 with CIs) and train A/B (win %, CI, OOF both sides); the auditor's
findings and fixes; the smoke; what you would try next. Save the final diff:
`diff -ruN bots/variants/chy-ref/src bots/variants/f-thru/src > research/mx-crius/patches/f-thru.diff`.
