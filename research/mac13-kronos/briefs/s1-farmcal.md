# Brief s1-farmcal: does charybdis's farm choice predict what it gets? (study, no bot changes kept)

You are doing a bounded measurement study for the orchestrator of a macro refactor of the Cambridge Battlecode C++ bot
`charybdis`. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` first. Work ONLY in
`/home/ubuntu/wt/mac13-kronos` (do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not commit).

## Question
The farm loop (`bots/variants/chy-ref/src/economy/farm.cc`, `farm_turn`) picks the group with the best priced rate
(value over rounds: walk, clear, hold; with camp damage, exposure/home_power, carry bonus, crews...). Champions walk
~50% of their alive rounds and the economy is champion-time bound (groups sit up and asleep ~61% of the time).
Is the chosen rate a good forecast of what the choice actually yields? Systematic biases (by group type, distance,
side of the map, champion type, game phase, crew vs solo, Prism vs others) would show where the farm misprices time.

## Method
1. `./copybot variants/chy-ref variants/s1-trace`. Add ONLY debug-only output (`debug_block({...})`, printf; release
   builds must be unchanged) at the point where farm commits a choice (when `memory.farm_group` changes to a new
   group, or each turn if simpler and you dedupe offline): round, champion id, group, mode char, the priced value,
   the priced rounds and its parts (walk, clear/wait, hold) if available, our position, and the best and second-best
   alternative's group and value. Name the line `FC ...`. Keep it cheap (no new searches).
2. Play a debug mirror: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/s1-trace variants/chy-ref --no-test-draft --fuel 200000 --debug --keep-replays 0 --suites maps/suites/mac13/study --name mac13-kronos-s1`
   (2,048 games; maps/suites/mac13/study is a study-only suite). Then `node tools/replay/extract.mjs <batch dir>`
   (decoded games land in `replays/.analysis/`; `replays/.analysis/index.json` rows have `source`). Replay zips hold
   `team-a.stdout`/`team-b.stdout` with the FC lines; the s1-trace side is the one whose stdout has them.
   Extracted schema: `tools/replay/README.md` (events: capture shares, camp deaths, group clears; rounds: positions).
3. For each FC choice, the outcome: did the champion get a capture share of that group before switching away, how
   many gems/gold, how many rounds from choice to payout (or to abandonment), and what happened (captured by us,
   ally took it, enemy took it, abandoned, died). Compare predicted vs realised rate (value per round) and rounds,
   broken down as above. Also: how often a choice is abandoned, and the rounds sunk into abandoned choices.
4. Write scripts under `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/s1/` and a short README.md there with the
   tables and the 3-6 most important findings, each with numbers (per team-game) and the code location that prices it.

## Stop condition
Return the findings (numbers, biases with their size in rounds or gems per team-game, the pricing code involved).
No bot change is kept; do not run other A/Bs. Delete the s1 batch's replays when done
(`rm -rf replays/batch-*mac13-kronos-s1*`) but keep your scripts and README.
