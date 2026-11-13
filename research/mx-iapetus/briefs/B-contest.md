# Brief B: contest judgement (who gives way at contested groups)

You implement one change to our Cambridge Battlecode bot `charybdis` (C++, compiled to WASM). You write the code; the
orchestrator (IAPETUS) plans and judges. Work only in the worktree `/home/ubuntu/wt/mx-iapetus` (branch
`mx-iapetus-20261113`); do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`. Another implementer is working on
`bots/variants/ia-finish` (endgame tributes in `economy/bank.cc`): don't touch that variant.

## Read first
- `/home/ubuntu/wt/mx-iapetus/AGENTS.md` (project rules: fuel, debug_block, testing), `cambc-rules.yaml` (engine-verified
  game rules), `docs/api/cpp.md` as needed.
- Code: `combat/fight.cc` (`want_home`, `drawn_home`, `outmatched`, `stand_lost_at`: the `falls` rule at its end),
  `model/safety.h/.cc` (`stand_trade`, `stand_roster`, the Trade struct: `lost`, `self_falls`, values in enemy health
  points with `params::life_value`, `params::gem_value`), `economy/farm.cc` (farm choice: how a contested group is
  priced and when the farm switches target; `exposure`, mid band), `economy/crew.cc` (crews, proposals), the Prism gem
  premium (`prism_premium`, economy/capture.cc / bot_parts.h).

## What the replays show (mirror of the reference bot, 540 farm-break windows: the 53% of games decided by farming,
median break r230; analysis scripts in /tmp/mxi-study/, read their summaries if useful)
- The loser's capture gap in those windows is 107 gems a game; 56% of it is mid groups (winner 70.5 vs loser 10.2
  gems), 37% its own home half.
- **Giving way at contested mid groups is ~45% of the gap.** Mid cycles the loser targeted or hit but the winner
  captured are 55.9 gems a game (7.1 the other way). Arriving first does not help: the winner takes 78% of contested
  mid cycles, including 183 of 303 the loser targeted first. At equal headcount within 8 of the group (224 cycles) the
  winner still captures 84%, with equal health, stats and gold. What differs is the decision: the loser's bodies near
  the group take the retreat branch in 23% of the next 10 turns against 14%, and drop the target for another group
  (1.34 a game against 0.37). Give-way retreats (no damage in the 5 rounds before, not outnumbered within 8) followed
  by the enemy capturing within 8 tiles inside 20 rounds: 35 gems a game for the loser against 6.9. The Prism is
  concentrated in it: loser Prism retreat turns 5.07 a game against 2.49 (3.85 vs 1.94 with the enemy Prism within 8).
- Knock-on: bodies pulled off home crews by lost mid targets, so home elk/golem crews don't form (another ~25-30% of
  the gap). Example: `/tmp/mxi/narr/games/chy-mirror_vs_chy-ref__-study-521-gen-ladder-6145100100016-12.txt` r260-279:
  the loser reaches Golem.mid (53 gems) first, its Prism retreats at r264, Cassi/Issac drift back to an unfinished
  home Elk; the winner's crew clears and captures the golem and kills Cassi. Also analysis dirs 22a45f7bdb91ec73
  (r1-73: the loser deals all 2,790 damage to a mid group, retreats at r38, the winner captures without hitting it)
  and aa7c6a03b7342e14 (r168-175: the Prism clears its own home gems, retreats as the enemy Prism approaches, the
  enemy captures 78 gems). Narratives: `/tmp/mxi/narr/` (README.txt), extracted games in
  `/home/ubuntu/wt/mx-iapetus/replays/.an-mirror/`.
- Likely driver: the binary `falls` rule in `stand_lost_at`: Prism, Cassi/Issac and any carrier of a bag worth a life
  leave a stand they would fall in *even when the team wins it*. In a mirror whichever side first reads a stand as
  one it falls in gives way and hands over the group, and the other side's investment pays. The second driver is
  the farm dropping a contested target it had invested in.

## The design: price the give-way, commit to what the team holds
1. **Price the fall.** Replace the binary rule (`t.lost || (falls && t.self_falls)`) with a comparison of what the
   stand is worth against what our fall costs, in the Trade's own units (enemy health points): leave a team-won stand
   only if our expected fall (our life plus the bag the killer takes, Prism gems at their premium, both bodies for
   Cassi & Issac) outweighs what holding wins: the trade's gains plus the contested group's worth to us *and* to the
   enemy (in a race a group they take is a loss to us too). A Prism with a big bag at even Focus will still leave;
   a healthy Cassi or a small-bag carrier beside a won stand at a mid group will not. Derive everything from existing
   valuations (life_value, gem_value, the premium, the farm's group worth); no new tuned constants.
2. **Commit to contested work the team holds.** When our bodies are invested in a group (hit it, hold it, or claim it
   with allies nearby) and the team stand there is won, the farm keeps that target rather than switching away;
   allies whose claim is that group treat it as a crew job. When the stand is lost, leave early, before investing
   (the farm should not start a contested group whose stand it already reads as lost when the enemy arrives).
3. Keep everything else: the recall line, camp-damage retreats, pack zones (`outmatched`), the hold keeps.

## How to work
- Copy the reference: `cd /home/ubuntu/wt/mx-iapetus && ./copybot variants/chy-ref variants/ia-contest` and work in
  `bots/variants/ia-contest/src`. Never edit `bots/variants/chy-ref`. Don't touch `draft/` or emblem choice.
- A/B (from the worktree root, venv shell):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-contest variants/chy-ref --no-test-draft --fuel 200000 --name mx-iapetus-B-<tag> [--suites maps/suites/mxi/train]`
  Without `--suites` it plays the 256 ladder games (the smoke). Run long A/Bs in tmux sessions named
  `mx-iapetus-B-<tag>` (`tmux new -d -s mx-iapetus-B-<tag> '... 2>&1 | tee /tmp/mxi-B-<tag>.log'`), wait with a
  background until-loop on `replays/ab/mx-iapetus-B-<tag>/summary.json` (foreground sleep is blocked). Results in
  `replays/ab/<name>/summary.md`. `--debug` for debug_block traces (compare only debug with debug).
- Measure the mechanism: `node tools/replay/extract.mjs <batch dir> --out replays/.an-B`, then e.g.
  `py tools/replay/analyze.py <batch dir> --analysis replays/.an-B --reports macro --team ia-contest` (CAND vs REF
  paired: contest_win, own_lost, mt_dead, captured gems by half) and deaths per game.
- You may iterate: up to 4 A/Bs on `maps/suites/mxi/train` (10,200 games, ~15 min each), always against
  `variants/chy-ref` at `--fuel 200000`. Never use `maps/suites/mx/*` or `maps/suites/mxi/conf`, `x1`, `fin`. Log each
  read and what you learned in `research/mx-iapetus/logs/B-contest.log` (plain text, append).
- Before returning, spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the change
  against this design and the rules for bugs; fix what it finds; make sure the bot builds; play the smoke
  (`--name mx-iapetus-B-smoke`): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
- Fuel: we test at 2x; don't optimise, but no runaway loops. Wrap traces in `debug_block({ ... });`.
- Delete replay batches you have finished studying (`replays/batch-*B-*`).

## Stop condition and report
Stop when the design is implemented, audited and smoked and you have at most 4 train reads (earlier if a version reads
clearly above the reference and changes stop helping, or two reads in a row show nothing and you can explain why).
Best version in `bots/variants/ia-contest`, others as `ia-contest-vN`. Report: the design as built, each read (win %,
CI, games, OOF), the mechanism numbers (contests won, give-way retreats, deaths, captured gems by half, CAND vs REF),
the auditor's findings, and what to try next. Kill tmux sessions you started.
