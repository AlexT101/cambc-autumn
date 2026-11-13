# cr1: capture recalls that agree with the bag's chain decision (charybdis macro, DIONE programme)

You are an implementation subagent for DIONE. Work ONLY in `/home/ubuntu/wt/mac13-dione` (branch
`mac13-dione-20261113`). Never touch `/home/ubuntu/cambc-autumn` (read only), other worktrees, `bots/charybdis`,
`bots/variants/chy-ref` (frozen), or variants you did not create. Do not commit or push. Read `AGENTS.md` and
`cambc-rules.yaml` first (C++ only; comment only counterintuitive behaviour). Off limits: draft and emblems.

Setup: `./copybot variants/chy-ref variants/cr1` (never copy `.cambc/`); edit only `bots/variants/cr1/src`. Runs:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-dione && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/X variants/chy-ref --no-test-draft --fuel 200000 --suites <suite> --name mac13-dione-cr1-<tag>`
in tmux sessions of the same name; wait with background until-loops on `replays/ab/<name>/summary.json` (foreground
sleep is blocked). Only kill/delete things with exactly the prefix `mac13-dione-cr1-`. Iterate only on
`maps/suites/mac13/screen` (10,240 games, ~10-15 min on this loaded machine) or `maps/suites/mac13/study` (2,048,
`--debug` for traces); never dev/hold/conf. No --threads, fgate, gates, live tests or other opponents.

## Why
Turns in safe space decide games (idling 1 farm turn in 20 in safe space lost 6.7 points). The home cycle costs ~1,000
rounds a team-game. A diagnosis of the ~42 completed recalls a team-game (another agent, hc1) found ~17 are capture
recalls (`capture_recall`, branch 'Q': a champion holding a capture starts the recall so it rides home with the share,
to bank at a spawn-side altar), followed by ~445 rounds a team-game of walking out from spawn. `capture_recall` runs
ahead of carry_bag's chain test (`economy/bank.cc` `carry_bag`, the chain decision, `params::chain_bag_limit`, the EOQ
`bank_floor`), so it never weighs chaining another capture before banking: two layers decide the same bag differently.

## Task
1. Read how capture recalls are decided (`economy/capture.cc` / `bank.cc` / `bot.cc`: find `capture_recall`,
   `continue_recall`, and the carry/chain/bank-floor logic). Add a debug trace and measure on a debug study batch how
   many capture recalls happen with a bag below the bank floor, or when carry_bag's own test would chain another
   capture from the payout tile.
2. Make the capture recall consult the same decision carry_bag would make at payout with the bag it will hold: ride
   home only when carry_bag would bank now and the ride is the sooner way to an altar (as it already prices); otherwise
   stay out and let farm/carry continue. No new constants.
3. Smoke (256 ladder games via ab.py without --suites): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Then one
   screen read. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check the diff;
   fix findings. Save `diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/cr1/src >
   research/mac13-dione/patches/cr1.diff`. Kill your sessions; delete your batches except summaries.

Report by **09:10 UTC** at the latest: the measurement, what changed, every read (name, suite, games, win %, OOF),
auditor findings.
