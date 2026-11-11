You are the lead on a macro refactor of our Cambridge Battlecode bot, `bots/ocean` (C++). You own this effort for the next 8+ hours on a 96-core machine. You are an orchestrator: you think, analyse, plan, study replays, run A/B tests and judge the results. You do not edit bot code yourself. Implementation goes through subagents (details below).

## Your workspace

- Your git worktree is `/home/ubuntu/wt/macro1` (branch `macro1-20261111`). Work only inside it. Other checkouts and worktrees on this box (`/home/ubuntu/cambc-autumn`, everything else under `/home/ubuntu/wt/`, other branches) belong to other people's unrelated work. Don't read them, edit them, or build on them. Don't touch the main branch and don't push. Commit on your own branch as often as you like.
- Read `/home/ubuntu/wt/macro1/AGENTS.md` first and follow it, along with `cambc-rules.yaml` (the engine-verified rules), `docs/api/cpp.md`, `sdk/cpp/cambc.h` and `tools/README.md`. `research/hyperion/CHANGES.md`, `research/EXPERIMENTS.md`, `research/hyperion/TODO.md`, the rest of `research/` and `git log` record what has been tried before.
- The reference bot is `bots/variants/ocean-ref-b7c87cf`, a frozen copy of the current ocean. Never edit it. Your candidates are bot directories you create under `bots/variants/` with the prefix `macro1-` (`./copybot` copies a bot without its build cache). When you finish, `bots/ocean` in your worktree should hold your best version.
- The box is shared with other heavy jobs, so A/Bs run slower than they would on an empty machine. Don't kill processes you didn't start. (`pgrep -f`/`pkill -f` match their own `bash -c` line, so be careful with them.)
- Don't write to the user's Claude memory directory. Keep a running log of your plan, hypotheses, results and decisions at `/home/ubuntu/wt/macro1/research/macro-2026-11-11/macro1-log.md`, and commit it as you go. Your context will be summarised several times over 8 hours, and this log is how you keep your bearings.

## The task

Improve ocean's *macro*: how it approaches the game strategically. That covers:
- target selection for farms, camps and monsters;
- explicit or implicit coordination between allied champions;
- adversarial planning around enemy champions: what they have been seen doing, what they are predicted to do, how they play;
- movement, zone control, and when to stay together with allies or spread out;
- economy: gold, gems, when champions tribute or spend, and how they prioritise these over the game and by map;
- risk against reward, protecting allies, enemy threats, how the enemy thinks;
- positioning relative to map structures, chokepoints, champions, camps and monsters;
- the balance between farming and fighting, and how the bot prioritises or combines them;
- which kinds of camps and locations the bot prefers;
- how the bot thinks about combat at the larger scale: team fights, retreat and chase, cornering.

Ocean is already strong, but it still loses many games, mostly from poor coordination and map control. Earlier attempts included champions "summoning" allies to help take a camp and champions moving as a pack. Those failed mostly because champions were busy, wasted turns walking to each other, or declined to come. Rigid concepts like that don't work. The macro needs a real *refactor*: something versatile and well integrated into the main decision system, not a separate system bolted on top. Don't assume the current implementation is optimal anywhere. Comms (the 8 shared bytes, priorities, and anything else the rules allow) can be extended or repurposed.

**Off limits:** draft choices and emblem choices. Leave the draft (`draft/`, the draft model, and which champions get picked) and emblem selection exactly as they are. Everything else is open: shopping other than emblem choice, tributing, targeting, movement, comms, combat macro.

**Target:** your finished bot should beat `variants/ocean-ref-b7c87cf` 60%+ of the time over 10k+ games. This is achievable. A teacher bot we don't have access to wins 65%+ against ocean through better macro alone: farming, gold and gems, champion movement and coordination. So a flat result means the approach isn't there yet, not that the problem can't be solved. Don't give up, and don't settle for +1-2 points of tuning.

## How to work

- **Think before building.** Use logic, reasoning and higher-order thinking about the game. Watch actual replays (tools are in `tools/README.md`, including the replay tools) to see what ocean does in the games it loses and what goes wrong turn by turn. Ground every design in a mechanic or strategic principle you can state.
- **Go big and coherent.** Avoid local maxima, where every small tweak seems to do nothing. Prefer large refactors, or sets of behaviour changes designed to work together, over isolated knobs. Don't ablate meaningless details or chase rabbit holes. If a direction is clearly losing after an honest attempt to fix it (understand *why* it lost: study the replays and look for second- and third-order effects, since a drop often comes from something nobody considered), move on quickly to a different one.
- **Priors are input, not verdicts.** Past attempts in the commit history, `EXPERIMENTS.md` and `research/` are useful. But don't reject an idea just because it was tried and failed. Look for the new angle or the missing piece that makes an ordinary idea work.
- **Robust, not overfit.** Every change should make conceptual sense and be tied to a mechanic or strategy. It has to work on maps nobody has seen. Avoid magic numbers, special cases, patches for one map or matchup, and workarounds for symptoms you haven't explained. Prefer quantities derived from the rules or from measurement.
- **Fuel: test with 2x fuel, always.** Every A/B runs with `--fuel 200000`. This is essential. Stay reasonably aware of fuel cost, but never spend time on fuel optimisation before an approach has shown it wins. If it can't win with double fuel, optimisation won't save it. Fuel work comes last, and only for a proven winner.

## Delegating implementation

You don't write bot code. For each piece of work:
1. Spawn an **implementation subagent** (general-purpose) with a complete brief: the design, its rationale, the files involved, the candidate directory to create or edit (`bots/variants/macro1-...` in `/home/ubuntu/wt/macro1`), and how to know it's done (it compiles; a quick local game or two runs without crashing; nothing else). It must work only in `/home/ubuntu/wt/macro1`. It must not run A/Bs, must not touch `bots/variants/ocean-ref-b7c87cf`, and must not write to Claude memory.
2. The implementation subagent spawns a **read-only auditor subagent** (Explore or Plan type) to check its diff against the brief and look for bugs and unintended behaviour changes. It fixes what the audit finds, then reports back to you with a summary of the diff.
3. You run the tests and judge them.

Keep at most 1-2 implementation subagents running at a time. Tell each one to keep scope bounded and to state its stop condition. You can also use read-only subagents for heavy analysis, such as replay studies or code surveys, so you keep the conclusions without the file dumps.

## Testing

Test only against `variants/ocean-ref-b7c87cf`. Run no gates, no `fgate.py`, no live tests or scrims, and no other opponents.

Run from `/home/ubuntu/wt/macro1` with this prefix:
```
source /home/ubuntu/venv/bin/activate && export PATH=$HOME/.cargo/bin:$PATH CAMBC_SLOTS=86 CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native
py tools/ab.py variants/macro1-X variants/ocean-ref-b7c87cf --no-test-draft --fuel 200000 --suites DIR1,DIR2,... --name macro1-X
```
- `ab.py` takes the machine-wide CPU slot pool automatically: leave `--threads` off. Concurrent A/Bs split the pool fairly, so you can run a couple at once.
- Make your map suites outside git, under `/home/ubuntu/wt/macro1-maps/`. Use `node tools/mapgen/mapgen.mjs suite --mix ladder-v2 --seed A-B --out '/home/ubuntu/wt/macro1-maps/s-{seed}'`. Each suite has 256 maps (512 games), so 20 suites make a 10k-game A/B. Keep each mapgen call to at most 30k maps. Use seeds in your own range, 100001-109999. You can add the ladder maps (`ladder`) too. A decision needs 10k+ games. Small samples are noise (±1 point at 10k). `--sprt` with its own `--sprt-seed` can kill clear losers early. Use fresh suites to confirm a result you will rely on.
- **Games are plentiful:** the box plays a very large number of games an hour, so lean on big samples (10k+ games for any decision, more to confirm). `--sprt` with its own `--sprt-seed` can still kill a clear loser early.
- Long runs go in tmux (`tmux new -d -s macro1-X '... 2>&1 | tee LOG'`). To wait for one, run a background bash loop such as `while tmux has-session -t macro1-X 2>/dev/null; do sleep 60; done` with run_in_background, so you are notified when it ends. Don't sit in foreground sleeps.
- `--debug` plays debug builds whose `debug_block` traces appear in replays. Compare only like with like. Use the stock runner (unset `CAMBC_BIN`) only if you need debug drawings.
- Disk: each 10k-game A/B keeps up to ~3 GB of replays. Delete your own old `replays/` dirs once you've recorded their results.
- Record results in your log, and in `research/EXPERIMENTS.md` in your worktree.

## Finishing

Keep working for the full 8+ hours. Iterate on what you learn. When you are done:
- `bots/ocean` in `/home/ubuntu/wt/macro1` holds your best bot (a copy of your best candidate), committed on `macro1-20261111`;
- `/home/ubuntu/wt/macro1/research/macro-2026-11-11/macro1.md` describes the design, the reasoning behind it, every A/B result (games, win rate, CI) and what failed and why.

Your final reply must give: the best candidate's path, its win rate against `ocean-ref-b7c87cf` (games, suites, 95% CI), a concise description of the macro design, and the main lessons.

## Your angle

Start from evidence. Before you design anything, spend real time on ocean's lost games (ocean against the reference, at 2x fuel). For winner and loser, catalogue where their champion-turns went and what each team's turns bought. Let a failure taxonomy you've measured, not assumptions, decide what the architecture has to do.
