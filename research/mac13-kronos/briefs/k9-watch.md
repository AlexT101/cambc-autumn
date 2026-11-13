# Brief k9: watch the altars while the enemy can end the game (three variants)

You are implementing a macro change to the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` (win, gems.tribute, altar_locks, stun,
vision: personal) and `research/EXPERIMENTS.md` "## Altar control (ocean, 2026-11-05)" (an earlier, score-triggered
guard, level). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other
worktrees; do not commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem
choices. Each variant: `./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Why
charybdis's Prism hoards its gems for Focus, so most games end with one long winning channel: in 1,024 mirror
games, 458 were won by a tribute of 200+ gems (median 650 gems, a 45-turn channel). During those winning channels the
losing side's champions were alive 69% of the time but farming 42% of their turns; in **354 of the 458 no champion of
ours came within 5 tiles of the channeller**. Our stop logic (`game_ender`, `combat/fight.cc:1202`;
`holds_hard_stop`, `stop_game_ender`; locks in `place_lock`, `economy/bank.cc`) only acts on an enemy channel a
champion SEES (`e.visible`), and vision is personal. The existing altar control (`economy/altar_guard.cc`:
`guarding`, `guarded_altar`, `guard_rank`, `guard_turn`, `keep_guard_lock`) is triggered by the enemy's TRIBUTED
score (>= 600 and 200 ahead) and works only when all altars form one site; in hoard games the enemy's score is low
(~340) while its Prism carries ~650, so it rarely fires, and most maps have 2+ sites.

## Design
1. **Trigger on what the enemy can tribute.** In `guarding()`, also guard while the enemy can end the game by
   tributing what it carries: `world.score.enemy` + the gems we believe its living champions carry (each living
   enemy's `gems` as last seen; a linked pair counts both bags; see `game_ender`'s `carried` and `pair_gems`) >=
   `winning_gems`. It stops when that no longer holds (a carrier died or tributed). Keep the existing score trigger
   and the escort as they are. Scores are shared, beliefs are not: each champion decides from its own beliefs; say
   how you keep guards from flickering (e.g. hold the trigger for a capture_time after the last time it held).
2. **Every map, not only one-site maps.** Group the altars into sites as `guarded_altar` does (`site_link`). With
   several sites, the guards spread over them: order the sites by the enemy's walk to them (nearest the enemy spawn
   first: their carriers bank at their nearest), and guard rank r takes site r mod (number of sites), each at that
   site's altar nearest the enemy spawn. `keep_guard_lock` keeps our lock on each guarded altar (it cancels an enemy
   channel there and blocks their tributes until broken: a strong stop). Make `stands()` and the field cache in
   `guard_turn` handle several altars.
3. Guards are chosen as now (`guard_rank`: `params::altar_guards` strongest, leaving `altar_farmers_min` farming).
   Everything else in the guard turn stays (fight an enemy within the leash via chase, else hold a stand tile); the
   existing `game_ender` / `stop_game_ender` path takes over once an enemy channel is seen.

Variants:
- `k9-watch`: 1 + 2 + 3.
- `k9-watch1`: 1 only (one-site maps, as today).
- `k9-watch2`: `k9-watch` with `altar_guards` 2 (leaving more farmers).

## Stop condition
1. All three build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to
check the diffs against this design and the rules (no change while the trigger is off, multi-site guard assignment
valid on 1-10 altars, no guard stuck on an unreachable stand, release builds unaffected); fix what it finds.
3. Smoke each in parallel:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as each builds (the orchestrator starts
screening from the diff's appearance: k9-watch first), then audit and smoke. Return what changed, auditor findings
and fixes, smoke results. No large A/Bs.
