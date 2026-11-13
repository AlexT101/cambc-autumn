# Brief k6: Prism banking cadence and race awareness (four probe variants)

You are building probe variants of the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md` and `cambc-rules.yaml` (gems, tribute, altar_locks, win).
Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not
commit. Never edit `bots/variants/chy-ref` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices. Each
variant: `./copybot variants/chy-ref variants/NAME` (never copy `.cambc/`), then the edit.

## Evidence (1,024 debug mirror games)
- Games end when a team's tributes reach 1,000 (median round 744). The Prism keeps every gem it carries for Focus
  (+1.5 a gem) until its own bag wins or the race closes (`keeps_gems`, `economy/bank.cc:905`; `winning_bag`,
  `closing`, `race_left`, `bag_rounds_left` nearby). Nothing in banking reads the ENEMY's race.
- In 337 of 1,024 games the eventual loser at some point had score + carried bags >= 1,000 (median 84 rounds before
  the end); then its score was ~312 and its bags ~701, 82% on the Prism (a ~575-gem bag needs a 58-turn channel:
  b = ceil(gems/10)). From that point to the end the winner's Prism spent 53% of its turns channelling a tribute and
  the loser's 15% (the loser's farmed 18%, was dead 28%). The loser's Prism started 2.0 tributes and completed 0.28;
  cancels: manual 0.95, stun 0.52, lock 0.31. In 221 games the loser still had score + bags >= 1,000 at the end.
  Example: a Prism at an altar with 885 gems (an 89-turn channel) repeatedly cancelled until round 2000, losing.
- Of 458 winning tributes of 200+ gems, most are a Prism's hoard. A hoard's channel grows with the bag, so the
  window it needs grows too, and a death hands the whole bag to the killer.

## Variants (each a change to when the Prism stops keeping its gems; the normal banking path then takes over)
1. `k6-cap150`: `keeps_gems` is also false once `my_gems() >= 150` (a 15-turn channel). Name the constant.
2. `k6-cap300`: the same at 300 (a 30-turn channel).
3. `k6-erace`: `keeps_gems` is also false while the enemy can win the race first: let
   `enemy_need = winning_gems - world.score.enemy`; the enemy can win soon when the gems we believe its living
   champions carry (each enemy's last-seen `gems` in world.enemies, only for alive ones) reach `enemy_need`, OR when
   `world.enemy_rate() > 0` and `enemy_need / enemy_rate()` is at most our own bank time (walk to the nearest usable
   altar + `tribute_turns(world, my_gems())` + `endgame_margin`). In both cases the Prism banks only if our team can
   still win by banking: `world.score.ally + our bag + allies' bags (as `race_left_now` counts them) >= winning_gems`.
   Otherwise unchanged. Put the test in one well-commented function `enemy_race_close(world, pathing)` in bank.cc.
4. `k6-erace-all`: the same race test also closes the race for every champion: `bag_rounds_left` returns 0 (so
   `closing` is true and every carrier banks) when `enemy_race_close` holds and our team can win by banking.
Check the cache keys of `closing` / `race_left` (`BagKey`, the `closing` Key): the new inputs (enemy score, enemy
beliefs) must invalidate them or be read outside them; say how you handled it.

## Stop condition
1. All four build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to
check the diffs against this brief (cache keys, no effect when the conditions are false, release builds unaffected,
no deadlock: a Prism that cannot reach an altar still behaves as before); fix what it finds. 3. Smoke each in
parallel: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/NAME variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-NAME-smoke`
(256 ladder games each): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK. Delete the smoke batches afterwards.
4. Save diffs to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/NAME.diff`
(`diff -ru bots/variants/chy-ref/src bots/variants/NAME/src`) as soon as each builds (the orchestrator starts
screening from the diff's appearance; do 1 and 2 first), then audit and smoke. Return what changed per variant,
auditor findings and fixes, smoke results. No large A/Bs.
