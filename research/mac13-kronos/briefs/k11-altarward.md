# Brief k11: a ward on the altars the enemy will end the game at

You are implementing a macro change to the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (win, gems.tribute, altar_locks,
wards, vision). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other
worktrees; do not commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`,
emblem choices. Base: BASE (given below); `./copybot variants/BASE variants/NAME` (never copy `.cambc/`).

## Why
Most games end with one long winning enemy channel (458 of 1,024 mirror games: 200+ gems, median 45 turns; 362 of
them at an altar in the middle band between the spawns). Our stops (`game_ender`, `holds_hard_stop`,
`stop_game_ender` in `combat/fight.cc` ~1175-1300; `place_lock` in `economy/bank.cc`) act only on an enemy channel
the champion SEES (`e.visible`); vision is personal, but a champion's own ward is part of its sight (rules
wards.vision / vision.personal: a 13x13 shadowcast square, never expiring). In 191 of the 458 no champion of ours
saw the channeller at all during it. Today our wards go on bushes (`ward_bushes` in `bot.cc` ~68) or where the draft
plans them (`ward_planned`).

## Design
While the enemy can end the game by tributing what it carries (score.enemy + the gems we believe its living
champions carry, as `game_ender`'s `carried` computes it, >= winning_gems; reuse BASE's helper if it has one), a
champion of ours places its ward so that it sees an altar's tribute tiles (the tiles within submit range of the
altar) that no ward of ours sees yet (`cambc::vision::ward_tiles_into(team::ally, ...)` gives the allied wards'
sight, or use the ward list), choosing the uncovered altar the enemy's carriers reach first (nearest the enemy spawn
by their walk, as their carriers bank at their nearest; ties to the middle). One altar per champion's ward; skip if
our own ward already sees an altar's tribute tiles. Place it only from where we are (placement radius 2, the ward
seeing up to 6, shadowcast: use `sdk_ward_vision` or the static map's shadowcast to test that the candidate sees
the altar's tribute tiles); it is an in-passing action, not a walk. Put it in `place_ward`'s order of preference
before the bush ward while the trigger holds; never while channelling (as now). The ward lets its owner's existing
game_ender / stop_game_ender / place_lock path see the channel from anywhere.

## Stop condition
1. Build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check the
diff against this brief and the rules (no change while the trigger is off, placement within radius 2 on legal tiles
only, no thrown-error loops, fuel: the sight test must not run a host call per tile every turn; cache per altar /
skip when our ward already covers one; release builds unaffected); fix what it finds.
3. Smoke:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK, out-of-fuel turns not above chy-ref's by more
than noise. One `--debug` smoke with a debug-only line `AWARD <round> <id> <altar>` per placement: report placements
per game. Delete the smoke batches afterwards.
4. Save the diff to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as it builds, then audit and smoke. Return
what changed, auditor findings and fixes, smoke results and the firing rate. No large A/Bs.
