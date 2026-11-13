# Brief A: the finish window (endgame conversion as a team operation)

You implement one change to our Cambridge Battlecode bot `charybdis` (C++, compiled to WASM). You write the code; the
orchestrator (IAPETUS) plans and judges. Work only in the worktree `/home/ubuntu/wt/mx-iapetus` (branch
`mx-iapetus-20261113`); do not commit, push, or touch any other worktree or `/home/ubuntu/cambc-autumn` (read-only
reference). Do not look at other worktrees under `/home/ubuntu/wt/`.

## Read first
- `/home/ubuntu/wt/mx-iapetus/AGENTS.md` (project rules: fuel, debug_block, testing), `cambc-rules.yaml` (engine-verified
  game rules: tribute, stun, locks, respawn, vision), `docs/api/cpp.md` as needed.
- The bot: `bots/charybdis/src` (a copy of it is yours, below). Endgame code: `economy/bank.cc` (`winning_bag`,
  `race_left`, `closing`, `keeps_gems`, `tribute_safe`, `tribute_ok`, `any_risk`, `can_tribute_safely`,
  `continue_tribute`, `carry_bag`, `bank_gems`, the `wait_altar` logic), `economy/altar_guard.cc` (one-altar maps
  only), the enemy-tribute stop logic (`game_ender`, `holds_hard_stop`, `stop_game_ender`, grep for them),
  `model/enemy_reach.h` (terrain-aware enemy reach: `enemy_reach::distance(world, e, from, p, limit)`),
  `model/world.h` `ChampionBelief` (`alive`, `respawn_earliest`/`respawn_latest`, `visible`, last sighting fields,
  `possible` tracking, `items`, ability readiness).

## What the replays show (mirror of the reference bot, 1,020 games)
- 31% of games are races: both teams reach 1000 wealth (tributed + carried). The first to get there wins only 55%.
  The median gap between the two teams' arrival at 1000 wealth is 25 rounds; the winner's lag from 1000 wealth to
  the win is median 59 rounds, p75 132, p90 458. 40% of the races lost by the first team involve one of its 100+ gem
  bags dying.
- Big tributes (100+ gems, mostly the Prism's hoard, channel ceil(gems/10) turns, x0.67 with a Tribute emblem, so
  40-60 turns) are cancelled about 6 times a game on the winning side (3,088 by stun, 1,226 by lock, 1,692 by our own
  cancel over 1,020 games); the winner spends a mean 88 rounds (median 0: a heavy tail) in channels that are later
  cancelled.
- At the start of a big tribute the nearest enemy is 4-7 tiles away in about 60% of starts. The stunners that cancel
  them are Ryth (1,138), Prism (1,054), Cassi (716), Marcella, Tavi, Ren. Our nearest ally is 1-2 tiles from the
  tributer when the stun lands in most cases: allies stand there but do not stop it.
- Why: `tribute_safe` judges a channel only by whether we could be killed within `min(turns, tribute_window=11)`
  turns (and last round's damage rate). It ignores stuns, which cancel any channel, and a 60-turn channel is judged
  on its first 11 turns only. So a long winning channel starts whenever we would survive 11 turns, and is stunned or
  locked before it completes; while channelling, the Prism (by then usually the strongest unit on the map) cannot
  fight back at the stopper walking in.

## The design
Build one model and use it for the winning (long) channel's start, continuation and preparation.

1. **Stop ETA.** For a tribute at an altar's tribute tile p, the earliest round any enemy could stop it: for each
   enemy champion that can stop a channel (a stun, by unit/ground/landing ability or Marcella's stun attack; or an
   altar lock it may carry: a lock is placed within 2 of the altar), the rounds until it can act within its stop
   reach of p. Dead: from its respawn (`respawn_earliest`, +1 for the respawn turn, on which it cannot act) plus its
   walk from its spawn. Visible: `enemy_reach::distance` from its tile (terrain, dashes). Unseen but alive: that
   distance from its last known tile less the rounds since (a lower bound, at least 0); `possible` tracking where it
   applies. Account for the stopping range of each tool from the rules (unit stun range 4; a ground stun's 3x3 area
   at range 4; a landing stun's radius; lock placement range 2) and for whether its stun can be ready (cooldowns are
   believed for unseen champions too). Keep it cheap (host calls are flat-priced; cache per round).
2. **Start only a channel that can finish.** A long channel (more turns than `tribute_window`) starts only if the
   stop ETA at its tile exceeds the channel's turns (within a small slack derived from turn order, not tuned). The
   existing kill check (`turns_to_kill_idle`) stays. Short channels (within the window) keep today's rule.
3. **Keep one that will finish.** In `continue_tribute`, a running channel whose remaining turns are below the stop
   ETA is kept; otherwise today's logic.
4. **Make the window.** When the winning bag waits for a window, the team works to open it rather than idling at the
   altar: the stoppers whose ETA closes the window are the targets. The tributer waits out of their reach (not on
   the altar tile when it would be stunned there) and fights them with the strike search as usual; allies near the
   altar give the stoppers priority as targets (they are the game). A kill opens a respawn-long window (about 60
   rounds) that fits a 40-60 turn channel. Choose the altar with the most slack (ETA minus channel turns) among those
   reachable, not just the nearest.
5. **Never wait forever.** If the enemy's own clock (its gems short over its recent tribute rate; the bot already
   reads it for `finish_lead`) says it wins before any window we can expect, take today's opportunistic start.

Derive every quantity from the rules or the game state; no new tuned constants beyond a slack you can justify from
turn order. Keep the change inside the existing structure (bank.cc and what it calls, a small module for the ETA if
it is cleaner, e.g. `model/stop_eta.{h,cc}`, added to `unity.cpp`). Do not touch `draft/` or emblem choice
(`economy/shop.cc`'s which-emblem logic). Wrap any trace output in `debug_block({ ... });` only.

## How to work
- Copy the reference: `cd /home/ubuntu/wt/mx-iapetus && ./copybot variants/chy-ref variants/ia-finish` and work in
  `bots/variants/ia-finish/src`. Never edit `bots/variants/chy-ref`.
- Build check: `cambc build bots/variants/ia-finish` is not the interface; the A/B builds it. A quick local game:
  `cambc run --help` (or look at `tools/README.md`). The A/B runner (always from the worktree root, venv shell):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-finish variants/chy-ref --no-test-draft --fuel 200000 --name mx-iapetus-A-<tag> [--suites maps/suites/mxi/train]`
  Without `--suites` it plays the 256 ladder games (the smoke). Run long A/Bs in tmux sessions named
  `mx-iapetus-A-<tag>` (`tmux new -d -s mx-iapetus-A-<tag> '... 2>&1 | tee /tmp/mxi-A-<tag>.log'`) and wait with a
  background until-loop on `replays/ab/mx-iapetus-A-<tag>/summary.json` (foreground sleep is blocked). Results:
  `replays/ab/<name>/summary.md`. `--debug` builds debug builds when you need traces (compare only debug with debug).
- Measure the mechanism on replays: `node tools/replay/extract.mjs <batch dir> --out replays/.an-A` then scripts on
  `replays/.an-A/<dir>/{meta.json,events.jsonl.gz,rounds.json.gz}` (schema: `tools/replay/README.md`). Useful
  checks: big-tribute starts and cancels by cause for the candidate's side, the lag from 1000 wealth to the win,
  wins in races. Example analysis scripts: `/tmp/mxi/stuncancel.py`, `/tmp/mxi/lag.py`, `/tmp/mxi/race.py` (they read
  `/home/ubuntu/wt/mx-iapetus/replays/.an-mirror`; copy and point them at your extract).
- You may iterate: up to 4 A/Bs on `maps/suites/mxi/train` (5,100 maps = 10,200 games, ~15 min each), always the
  candidate against `variants/chy-ref` at `--fuel 200000`. Never use `maps/suites/mx/*` or `maps/suites/mxi/conf`
  (held out for the orchestrator). Keep each read's numbers and what you learned in
  `research/mx-iapetus/logs/A-finish.log` (plain text, append as you go).
- Before returning, spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) that checks the
  change against this design and the rules (`cambc-rules.yaml`) for bugs; fix what it finds. Then make sure the bot
  builds and play the smoke (`... py tools/ab.py variants/ia-finish variants/chy-ref --no-test-draft --fuel 200000
  --name mx-iapetus-A-smoke`): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK` in the output.
- Fuel: we test at 2x fuel; don't optimise, but guard against runaway loops (bounded loops, per-round caching).
- Delete replay batches you have finished studying (`replays/batch-*A-*`) to save disk.

## Stop condition and report
Stop when the design is implemented, audited and smoked, and you have at most 4 train reads (stop earlier if a
version reads clearly above the reference and further changes stop helping, or if two reads in a row show no
gain and you can explain why). Leave the best version in `bots/variants/ia-finish` and any other version you want
kept as `bots/variants/ia-finish-vN`. Report: what you built (as a design), each train read (win %, CI, OOF turns),
the mechanism numbers (big-tribute cancels, lag, race wins) against the reference, what the auditor found, and
your view of what to try next. Kill any tmux session you started before returning.
