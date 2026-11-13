# Brief C2: cooldown economy, Willow as the team's medic (implementer)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/chy-ref variants/c2-medic` (never copy `.cambc/`). Edit only
  `bots/variants/c2-medic/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Another implementer is
  working in `bots/variants/c1-casts` (free damage casts on camps): don't touch it.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem a champion builds toward).

## The idea (why)
Willow's heal (ally target, range 4, needs the ally visible, 3x Focus = 420 HP at base Focus 140, cooldown 8 rounds)
is the team's only field healing. Every other heal is a trip home: recall (5 turn ends, cancelled by any damage) to
spawn, heal at the turn end there, then the walk back out. Measured on 1,024 charybdis mirror games (Willow in 62% of
team-games): Willow heals 13,478 HP a game, about 32 heals, against a cap of ~110; she walks 66% of her rounds, hits
camps 13%, holds 1.2%, and earns 60 gold a game (she hands captures to others). The team takes ~32,000 damage a game
(camps ~17,000, champions ~15,000) and completes ~45 recalls a team-game; a recall cycle (channel + walk back out,
median ~25 tiles from spawn) costs ~30 champion-rounds, so each 420-HP heal that replaces part of a trip saves on the
order of 10+ champion-rounds of farm, and a heal in a fight can save a death (60 rounds dead + bag + 100 kill gold).
Her current logic (combat/support.cc: the Prism-Willow support pair, `willow_follow`, `willow_independent_heal_step`;
combat/self_abilities.cc: `heal_ally`, `HealGate`, `heal_value`, `heal_target`) mostly keeps her beside the Prism,
which takes little damage most of the time, so the heal sits ready while crews elsewhere burn health and walk home.
The Willow-Prism support pairing is worth ~3 points in ablations: keep its protection of the Prism when the Prism is
threatened (enemy near or it is hurt), but let her work for the whole team otherwise.

## The design
1. **Measure first** (debug_block traces on the study suite, see below): heals per 100 Willow alive rounds; whom she
   heals (Prism vs others); turns her heal is ready with a damaged ally visible within 4 / within 8 / none; who the
   team's damage-takers are (camp crews' tanks) and how far from Willow. Report these before and after.
2. **Medic positioning:** when the heal is ready or comes back within the walk, Willow moves toward the place where
   her next heal has the most value: for each ally (positions from sight or comms told tiles, `comms::told_ally`;
   health from sight, or the last seen plus expected camp fire while it works a claimed group), value = expected
   missing HP at arrival (capped at her heal amount) x the champion-rounds a HP saves (the bot's `heal_value` already
   prices a heal as the trip home it saves: reuse it) plus fight urgency (`HealGate::urgent`). Cost = her walk there
   (rounds) and the risk of the tile (Safety). Prefer allies working strong camp groups (steady camp fire, predictable
   positions) and the Prism. While the Prism is threatened (seen enemy that can reach it, or the support request
   is on), the current support behaviour wins.
3. **Allies come to the medic:** a damaged ally whose recall line would send it home (`want_home` / recall_line in
   combat/fight.cc) may instead keep farming if Willow is within a few rounds' walk and her heal is ready or nearly
   so (her heal covers the gap to the line), so it doesn't pay the trip. Keep this conservative and threat-free (no
   enemy threat; camp damage only).
4. Willow's own farm stays secondary: she hits camps only when no heal opportunity is worth walking to.
Derive radii/horizons from the rules (cooldown 8, range 4, walk 1 tile/round) and measured quantities, not
hand-picked constants.

## What to measure
Debug traces in the replay zips (`team-a.stdout`; `debug_block({ printf(...); })`, never plain printf):
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c2-medic variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/study --debug --name mac13-castor-c2-dbg`
(`tools/replay/debug_lines.py PREFIX -- replays/batch-...` counts lines). The extracted replays give healing per
champion (`node tools/replay/extract.mjs BATCH --out DIR`; each game's `meta.json` has `stats.healingDone` and
per-round `rounds.json.gz`; see `tools/replay/README.md`). Also a farm check against an idle opponent:
`py tools/solo.py variants/c2-medic variants/chy-ref --name mac13-castor-c2-solo --suites maps/suites/mac13/study --one-side --fuel 200000`.
Run long commands in the background or tmux (sessions named `mac13-castor-c2-*`); foreground sleep is blocked.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design above and your
   diff (`diff -ru bots/variants/chy-ref/src bots/variants/c2-medic/src`) to check it against the design and the rules
   (`cambc-rules.yaml`) for bugs. Fix what it finds.
2. Make sure the bot builds, and play the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c2-medic variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c2-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c2-medic.diff`. Don't commit; don't run the 10k A/B (the
   orchestrator does). Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke. Return: what you changed (files,
functions, gates and their derivations), the before/after measurements (heals per 100 Willow rounds, healing per
game, whom she heals, recalls per game), the solo result, the smoke win rate, and anything you were unsure about.
