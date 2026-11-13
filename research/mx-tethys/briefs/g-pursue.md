# Line G: pursue what cannot escape

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 2,720 games)
- Kills decide games: the team with more kills wins 88%; winners take 307 gems a game by kills against 50 for losers
  (rules: the killer takes the victim's whole bag and 100 gold); fewer gems lost at death wins 88%.
- **A retreat does not open distance.** Everyone walks one tile a turn; a ranged champion's walk costs its basic attack,
  and a stun removes a turn. Chased Prisms made a median 0.125 tiles a round of net progress home after the first hit.
  The bot itself leaves stands it would fall in even when its team wins them (`stand_lost_at`, combat/fight.cc, the
  `falls` case: always for the Prism, for Cassi/Issac, for big-bag carriers), so retreating bodies are common.
- The chase gate `preyable()` (combat/fight.cc ~768) refuses an enemy that is out of attack range, off our ground,
  healthy (above `params::hurt_health_fraction`), holding no cleared group, and carrying no bag we can intercept. So a
  healthy enemy walking away across the middle is let go, even when it cannot get out of our reach before we and the
  allies with us kill it. `prey()` / `chase()` / `chase_trade` then decide the chase itself.
- Priors: SELENE's pursuit fix (walking allies count in a pursued stand only if they close by next turn) gained +0.7
  and shipped (charybdis 528). HECATE's "press disarmed enemies" lost ~0.7 with 26% more out-of-fuel turns. So a
  pursuit change must be exact about who can catch whom, and cheap.

## Design
Widen `preyable()` by one test, the escape test from the pursuer's side: an enemy we would otherwise refuse is prey
if it **cannot escape**: along its best way out (to its spawn, or to allies of its that make our stand lost), the
rounds it stays within reach of us (and of the allies of ours that would join the chase in time, as the safety model
counts joiners) are enough for our side's damage to kill it, counting our stuns as lost turns of its own. Derive the
test from what the safety model and pathing already compute (`Safety::stand_walks`, `pursuit_gain`, `stand_reach`,
`enemy_reach`, `intercept_steps`, model/escape.cc, the fight simulation `Trade` with turns_to_kill_them). No
hand-picked margins. Everything else in the chase (`chase_trade`, our stand along the way, `pack_covers`, the enemy
spawn edge) stays as it is, so we still don't chase into a lost fight.

The prize is already priced by the chase (its bag, its life). If the kill would be our Prism's and the prize carries
gems, the gems go to our Prism's bag (`prism_premium` prices that) — only add this if the chase's worth doesn't see
it already.

Versions to read:
1. the escape test as above, for every body;
2. if 1 reads below level, the same restricted to targets carrying a bag or to targets our Prism would kill; if 1
   reads level or above, 1 plus: a body whose chase is on posts it (comms already has a chase bit, `comms::chasing`,
   `ally_chasing`), so that allies who can join in time count as joiners in the escape test.

Debug: print one line per turn the new test admits a target `preyable()` refused (in `debug_block`), so the firing
rate can be counted.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-pursue` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-pursue`, freezing each version as `bots/variants/mx-pursue-vN` before changing it. `test_draft`
   stays off.
2. Build: `cambc build bots/variants/mx-pursue --release` (without `--release` for debug traces).
3. Read each version with a full A/B on the train suite (10,200 games, about 2-3 minutes of wall):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-pursue-vN variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-pursue-vN`
   Run each in a tmux session named `mx-tethys-pursue-vN`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. `--debug` (both sides debug) when you need traces. Never use the dev, hold, conf1 or fin
   suites. Delete each `replays/batch-*` you create once you have read it (~3 GB each). Other A/Bs share the box; fine.
4. Measure (debug A/B or extracted replays; `node tools/replay/extract.mjs`, `--threads 40` or fewer; scripts in
   `research/mx-tethys/scripts/`: `all_deaths.py`, `kills.py`, `prism_death.py`): firing rate a game, kills and deaths
   a game, gems taken by kills, chases that ended in our death, CAND side vs REF side.
5. Watch fuel: OOF turns must stay near chy-ref's.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-pursue variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when the versions above are read (or earlier with a version at 52%+ on train), at most four train A/Bs of real
versions in all. Time matters: aim to return within about an hour. Report through SubagentHandback: the variant
paths; each version's change, train read with interval and OOF; the firing rate and kill/death counts; the auditor's
findings and fixes; the final diff stat. Save the best version's diff with
`diff -ruN bots/variants/chy-ref/src bots/variants/mx-pursue/src > research/mx-tethys/patches/mx-pursue.diff`, with
`bots/variants/mx-pursue` equal to the best version.
