You are improving fuel usage of bots/charybdis, as measured by:
- # of out of fuel turns
- # of shortcuts taken

Prioritize reducing these even if average fuel used gets slightly worse.

Do not spawn subagents; work by yourself. You should use the bench tool to verify byte identical. If something only triggers on certain maps/champions, make sure the bench tests under those conditions. The exception to byte identical is if exact ordering/decision is arbitrary, or if the new version is unambiguously better (in other words: don't try to maintain unintended quirks of the bot or bugs).

There are documents in /research showing past instances of trying to reduce fuel usage. Make sure we learn from these lessons to help us know what's been tried, what's been successfully implemented, and what to look for.

Some improvements might be straightforward; others might require you to bridge logic across multiple files, understand higher-order intentions or game rules, or understand where cases are impossible. Fuel usage improvements could also entail early exits, iterating in a better order, smart calculations or formulas instead of simulation, etc. You are allowed to rework how logic is calculated if it would improve fuel usage without changing gameplay; for example, precomputing something that multiple consumers could use.

Make sure you think outside the box. The end goal is to reduce out of fuel turns by at least 10%.

## Setup (from the coordinator)

- **Where:** worktree `/home/ubuntu/wt/fuel-530`, branch `fuel-530-20261113`, at main `705870058` (charybdis 530). Work and commit only there. Never push, never touch `main`, the primary checkout `/home/ubuntu/cambc-autumn` (read only) or any other worktree under `/home/ubuntu/wt/`.
- **Bots:** edit `bots/charybdis` (or copies under `bots/variants/`, made with `./copybot SRC DST`, which leaves out `.cambc/`). `bots/variants/chy-530` is a frozen copy of 530 and the reference for every comparison: never edit it.
- **Read first:** `AGENTS.md` (its Fuel section especially), `cambc-rules.yaml`, `tools/README.md` (bench.py and fuel tools, host-call prices), `research/fuel-527/README.md` (the last charybdis fuel pass, shipped as 529, and how it was measured), `research/hyperion/FUEL-GATES.md`, the fuel entries in `research/EXPERIMENTS.md` and `research/hyperion/CHANGES.md`, `research/fuel-2026-11-13/`, `research/charybdis-fuelC/`, `research/charybdis-fuelD/`. CHANGES 530 describes the newest code (`economy/contest.cc`, `stop_due` in `combat/fight.cc`): 530 has +3% out-of-fuel turns against 529.
- **Shell:** `source ~/venv/bin/activate` (python is `py`). Prefix every `ab.py`, `bench.py`, `solo.py` or `run_batched.py` with `CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`. Leave `--threads` off (a machine-wide slot pool shares the 96-core box with other jobs); `bench.py --jobs 86` at most; `extract.mjs --threads 8`. Run anything long in tmux, in sessions named `fuel530-<tag>`. Delete replay batches you're done with.
- **Measuring:** identity with `tools/fuel/bench.py` (100M quantum) against `variants/chy-530`, covering the champions and map features your change touches. Out-of-fuel turns and win rate with `py tools/ab.py CAND variants/chy-530 --no-test-draft --suites DIR` at the real budget (no `--fuel`), release builds, which reports both sides' out-of-fuel turns; shortcuts from a debug bench as in `research/fuel-527/README.md`. For fresh maps use only seeds 61496000-61496999: `node tools/mapgen/mapgen.mjs suite --out DIR/{seed} --seed A-B --mix ladder-v4 --jobs 16` (340 maps a seed, at most ~80 seeds per command), then move the `.map26a` files into one flat directory. Confirm the final result on seeds no earlier run of yours used.
- **Record and commit as you go:** keep `research/fuel-530/README.md` current (each change, its identity result, out-of-fuel and shortcut numbers with intervals, rejected attempts and why) and commit to your branch regularly, so an interruption loses nothing.
- **Finish** when the target is met and confirmed on unused seeds, or when further cuts stop paying. Leave `bots/charybdis` on the branch equal to your final version, kill every `fuel530-*` tmux session you started, commit, and end with a summary: the changes, identity results, out-of-fuel turns and shortcuts before and after (with intervals) and the release win rate against chy-530.
