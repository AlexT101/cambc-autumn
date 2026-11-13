# Line E: altar watch, relay and response (`ia-watch`)

You are an implementer for IAPETUS (orchestrator of the macro refactor of charybdis). Work in the worktree
`/home/ubuntu/wt/mx-iapetus` (branch `mx-iapetus-20261113`). Read `AGENTS.md` and `cambc-rules.yaml` first
(especially vision: sight is personal, "never with teammates' vision"; wards: one per champion, re-placeable every
10 rounds, never expire, radius 6; tribute: stun cancels it; locks).
Do not commit, push, or touch `/home/ubuntu/cambc-autumn` (read-only) or other worktrees.

## Base
`./copybot variants/ia-contest variants/ia-watch` (ia-contest is the current best: 51.1% [50.6-51.7] vs chy-ref
over 30,600 held-out games; its train reads were 50.9 and 50.3). A/B against `variants/chy-ref`.

## Evidence (mirror chy-ref vs itself, 1,020 games, `research/mx-iapetus/scripts/wards.py`, extracted replays at
`replays/.an-mirror`; and line A's notes in `research/mx-iapetus/NOTES.md`)
- Big (100+ gem) tributes: with no enemy body within 8 and no enemy ward within 6 of the bearer they complete
  69-78%; with an enemy ward over them 11-12% (8% with a body near too); with a body near and no ward 11-13%.
- Winners start ~7 big tributes a game, 66% of them under an enemy ward; losers ~1.7.
- Over the last 150 rounds the winner's wards cover 56% of the map's altars, the loser's 47.5%.
- Both teams reach 1000 wealth in 31% of games; the first there wins only 55%. Lag from 1000 wealth to the win:
  median 59 rounds, p90 458.
- `model/comms.cc` shares claims, our bag, a camp respawn record and an ally tile: **no enemy sightings**. A ward's or
  body's sight of an enemy channelling at an altar reaches only its owner. The response to a visible game-ending bag
  (`combat/fight.cc` ~1220-1270, "into reach of the enemy whose bag ends the game") needs the enemy in that body's
  own sight.
- The ward policy (`bot.cc` ~174-420) values sight around our own work site; it never values watching altars.

## Task (yours to refine, in this order, measuring each)
1. **Relay**: post a compact record of an enemy tribute (or a big-bag carrier near an altar) we see: altar index,
   round mod a small period, maybe bag size, in the free comms bits (check the layout's worst case; skip the post when
   it does not fit). Allies fold it into their beliefs (`World` tracking), so the existing responses see it.
2. **Response**: allies that can stop it (a stun or an altar lock reaching the altar before the channel ends, by walk
   and cooldown) go; only when stopping it is worth more than their work (a game-ending or race-deciding bag first).
3. **Watch**: in the race phase (the enemy's wealth plus the bags we know near 1000, or their tribute rate), value
   ward tiles that see the enemy's usable altars' tribute tiles, so the team's wards keep watching every altar the enemy
   can bank at. Derive the stage and the value from the rules and the known quantities.
- Keep fuel in check (OOF turns in each summary) and keep changes tied to these mechanisms; no magic numbers.

## Process
- A/B (train suite only; IAPETUS judges on other suites):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-iapetus && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/ia-watch variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mxi/train --name mx-iapetus-E-r<N>`
  in a tmux session named `mx-iapetus-E-r<N>` (no `--threads`). A 10,200-game read takes under a minute. Wait with a
  background until-loop, never a foreground sleep. Kill only by tmux session name. Up to 10 train reads, one at a
  time; pool 2-3 reads before calling a small difference. Debug smokes (ladder, 256 games, `--debug`) for traces.
  Delete replay batches you've studied.
- For each read find out why it moved: enemy big-tribute completion, our race wins, relayed alerts and responses a
  game, ward coverage of altars, deaths, OOF. Keep each version you A/B as `bots/variants/ia-watch-v<N>`.
- Log each step with times to `research/mx-iapetus/logs/E-watch.log`.
- Before returning: spawn a read-only auditor subagent on your diff and fix what it finds; make sure the bot builds;
  play the smoke `py tools/ab.py variants/ia-watch variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, no
  failed games, no DRAFT-UNFINISHED / PLAN-CHECK).
- Off limits: `draft/`, emblem choice, `bots/variants/chy-ref`, `bots/variants/ia-contest`, `bots/charybdis`.
- Report: what you built (files, mechanism), every read with CI and OOF, why each moved, the best version's path, and
  what you'd try next.
