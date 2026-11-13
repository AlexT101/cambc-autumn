# Brief C3: the stun screen, stunners cover our Prism when the enemy Prism can engage (implementer)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/chy-ref variants/c3-screen` (never copy `.cambc/`). Edit only
  `bots/variants/c3-screen/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`; other implementers work in
  other `bots/variants/c*` directories: don't touch them.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem a champion builds toward).

## Why (mechanics and measurements)
The game is decided by the Prism duel: the team whose Prism dies first loses ~88% (1,023 charybdis mirror games).
Prism damage spells exclude walking: a champion must *start* its turn within range (unit 4; ground 4, its 3x3 hits
5) to cast. So the Prism that walks into range gives the other the first cast, unless something acts in between.
Teams alternate champion turns, so between the enemy Prism's approach (turn t) and its cast (turn t+1) our champions
act. A stun "removes the target's next turn" and does not stack; one landing after that turn removes the following
one. Cassi's stun (slot 1) is a unit spell that does **not** exclude walking and needs no damage; Tavi, Ren,
Marcella (reset + stunning next basic), Ryth (ground stun) and our own Prism also stun. If an allied stunner with its
stun ready is within 4 of the enemy Prism when the enemy Prism ends a turn near our Prism, the stun takes the enemy
Prism's next turn and our Prism gets two turns of casts (its stun and its ground spell, 2.5x Focus) before the enemy
Prism acts again.
Measured: in Prism-on-Prism openers at Focus parity (0.8-1.25x), an allied ready stunner was within 4 of the enemy
Prism in only 35 of 564; with the opener covered (23 cases) its Prism died 0% vs 12% uncovered and the victim 35% vs
22% (small n, but the mechanism is exact). Cassi & Issac are in ~98% of our drafts; Cassi is within 4 of our Prism
32% of the time, within 8 48%; the enemy Prism is within 8 of ours 15% of the time. Prior programmes' bodyguards (a
non-stunner ally following the Prism all the time: ~112 idle/trailing turns a game) and avoidance rules were level:
following when there is no threat wastes farm time, and giving way cedes ground. So the screen must be **conditional
on a real threat** and **use stunners**.

## The design
1. **Threat window:** our Prism is threatened when an enemy Prism (alive) could be within its cast range (5) within the
   next few rounds: seen now or recently, using the bot's enemy tracking (`World::enemies[]` `possible` boards,
   `pos_round`, `model/enemy_reach.h`, Safety). Derive the horizon from the walk speed (1 tile a round) and how many
   rounds a screener needs to reach its station, not a fixed radius.
2. **Screeners:** our champions with a stun (Cassi first; also Tavi, Ren, Marcella, Ryth) whose stun is ready or ready
   by the time the threat can arrive, within reach of a station in time, and not busy with something more valuable
   (holding a capture about to pay, a channel, their own retreat). One screener is enough; a second only if free.
3. **Station:** a tile 2-4 from our Prism, toward the enemy Prism's approach (its last sighting / possible tiles), off
   tiles where the enemy Prism's own burst (1.5x + 1.0x its Focus) or other threats would kill the screener before
   it acts if that can be avoided (the bot's `Safety` lethal/bound helpers), so that any tile from which the enemy
   Prism could cast at ours is within 4 of the screener. Keep it cheap: a handful of candidate tiles scored by
   coverage of the enemy's approach tiles.
4. **Integration:** the screen is a goal step (like `willow_follow` / `support_work` in `combat/support.cc`, or a
   branch in `bot.cc` `decide()` before the farm), taken only in the threat window. The strike search and turn order
   already cast stuns on enemies in reach: check that a screener's stun on an enemy Prism that ends within 4 is
   actually taken (the strike search's valuation of stunning the enemy Prism should include the turn it takes from
   the enemy Prism and the cast it enables for our Prism; fix if it isn't), and that the turn order lets the
   screener act before the enemy Prism's next turn where it can. Cassi & Issac are linked (if either dies both
   die): Issac should not be dragged along needlessly, but the pair moving together is fine.
5. Outside the threat window nothing changes.
Derive the horizons and distances from the rules (ranges, walk 1 tile a round, cooldown 8), not hand-picked values.

## What to measure
Debug traces in replay zips (`team-a.stdout`; `debug_block({ printf(...); })`, never plain printf): threat-window
rounds per game, screen turns per game, how often a screener was within 4 of the enemy Prism at a Prism-Prism
engagement, stuns landed on the enemy Prism, and Prism deaths. Debug A/B on the study suite:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c3-screen variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/study --debug --name mac13-castor-c3-dbg`
(`tools/replay/debug_lines.py PREFIX -- replays/batch-...`; `node tools/replay/extract.mjs BATCH --out DIR` then the
per-game `events.jsonl.gz` / `rounds.json.gz`, see `tools/replay/README.md`). Run long commands in the background or
tmux (sessions `mac13-castor-c3-*`); foreground sleep is blocked.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design above and your
   diff (`diff -ru bots/variants/chy-ref/src bots/variants/c3-screen/src`) to check it against the design and the rules
   (`cambc-rules.yaml`) for bugs. Fix what it finds.
2. Make sure the bot builds, and play the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c3-screen variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c3-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c3-screen.diff`. Don't commit; don't run the 10k A/B (the
   orchestrator does). Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke. Return: what you changed (files,
functions, gates and their derivations), the measurements, the smoke win rate, and anything you were unsure about.

## Iterating on real win rates (allowed and encouraged)
A 10k-game release A/B now takes ~3 minutes. You may iterate the design against the reference on the **train**
suite only (never `dev`, `hold`, `conf` or `x1`: those are the orchestrator's decision suites):
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c3-screen variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c3-trainN`
(10,240 games; noise about +-1 point). Use it to check that the mechanism helps and to fix what loses (read why from
debug traces and replays, not by twiddling constants). Every reading you report must be a full train run. Keep
each variant you test as a separate directory or a saved diff, and report every reading, not only the best. The
final variant you hand back is the one the orchestrator will test on its own suites.
