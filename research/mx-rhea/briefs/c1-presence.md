# C1 `presence`: what the enemy can provably reach, in the macro

You implement one candidate for the RHEA macro programme on our Cambridge Battlecode bot charybdis (C++). Work only in
`/home/ubuntu/wt/mx-rhea` (git worktree, branch mx-rhea-20261113; never push, never touch /home/ubuntu/cambc-autumn or
other worktrees). Read `AGENTS.md` (repo root) first, then `cambc-rules.yaml` (engine-verified rules), and the C++ API
in `docs/api/cpp.md` / `sdk/cpp/cambc.h` as needed. Do not commit; the orchestrator commits.

## Setup
`./copybot variants/chy-ref variants/c1-presence` (from `/home/ubuntu/wt/mx-rhea/bots`... run `./copybot` from the repo
root: `cd /home/ubuntu/wt/mx-rhea && ./copybot variants/chy-ref variants/c1-presence`). Edit only
`bots/variants/c1-presence/src`. Never edit `bots/variants/chy-ref`. Leave `draft/` and emblem choices alone (off limits).

## Why
- Enemy respawn timers (`ChampionBelief::respawn_earliest/latest`, model/world.h, set in model/world.cc ~1887) are
  written and never read by any decision. A dead enemy cannot contest anything until it respawns at its spawn and walks.
- An enemy's last sighting (`pos`, `pos_round`) bounds where it can be: it walks one step a turn (a dasher gains 2
  more once per ability cooldown). Unseen enemies are forgotten by the safety model after 3 rounds
  (`params::track_horizon`), which is right for tile-level danger, but the macro has no notion of "provably far".
- The farm's territorial terms are static: `home_ground(map, g)` (economy/camps.cc:665, weight share^home_power by walk
  distance from both spawns, the hazard of working near the enemy) and farm.cc's `exposure(g)` (the middle band worth
  `mid_exposure` = 1.36x: contested groups are worth more because the enemy would otherwise take them). Both assume
  every enemy is alive and unlocated, always.
- Mirror data (1,020 games): while half or more of the enemy team is dead, a team's capture gems per round stay flat
  (1.48 -> 1.53 for the winner); the winner/loser capture gap is mostly mid and enemy-side groups.

## Design
1. One shared model, `EnemyPresence` (new file `model/presence.{h,cc}`; add the .cc to `unity.cpp`), answering:
   `int earliest_arrival(const World&, const ChampionBelief& e, vec2 target, int reach)` = the earliest round enemy e
   could stand within Chebyshev `reach` of `target`, as a provable lower bound:
   - dead: `respawn_earliest` + max(0, walk steps from its spawn to within reach of target) (use the map's enemy-spawn
     walking fields if there is a cheap one; else Chebyshev from the nearest enemy spawn tile, which is still a valid
     lower bound);
   - alive, visible: now + max(0, cheb(pos, target) - reach) turns, with a dasher's steps (has_dash) counted at up to
     2 extra tiles per `ability_cooldown` rounds (a ready dash counts now);
   - alive, unseen: from its last fix (`pos`, `pos_round`), subtracting the turns already elapsed at the same speed
     (so the bound decays to "now" as it goes stale); never seen: its spawn at round 1 (equivalently: treat as present).
   Keep it cheap: per turn, per enemy, O(1) arithmetic; no new fields or floods inside the farm loop.
   And `float presence(const World&, int group, int horizon_rounds)`: the share of the enemy team (each pick weighs
   1; Cassi and Issac 0.5 each) whose earliest_arrival at the group's centre, with reach = that champion's one-turn
   strike reach (safety.h `one_turn_reach` / facts), is at most now + horizon. 1 = everyone could be there (today's
   assumption), 0 = provably nobody.
2. Farm territory (economy/farm.cc where `known.home` / `exposure(g)` are combined, ~line 1856-1882, and the same
   weights in the crew/claim valuations if they read home_ground): with f = presence(g, T), T = a cheap job-length
   estimate (Chebyshev trip from us + fastest clear + capture rounds, or whatever farm already has for that group),
   - hazard weight = home_ground(g)^f (unchanged at f = 1, none at f = 0);
   - contested bonus = 1 + (exposure(g) - 1) * f (the enemy cannot take what it cannot reach).
   The Monolith's doubled side weight follows the same rule. With every enemy alive and unlocated nothing changes:
   the tuned static values are the f = 1 case.
   Farm's prunes (`PreUpper`, `known_weights`, `rated_below`, `exposure_most`, max_exposure) must stay upper bounds of
   the values they prune: any group whose f can be below 1 this turn needs a bound that covers the dynamic weight
   (home^f * (1 + (e-1) f) <= max(1, e)). It is fine to loosen the bound to 1 x exposure_most for such groups (we play
   at 2x fuel); do not make the prunes cut groups the full test would pick. Kept per-group facts (`known.*`) that
   cache the weight must be refreshed when f changes (e.g. key the weight's cache by a per-turn presence version).
3. Endgame: a winning-bag channel longer than `params::tribute_window` is refused today unless the round limit forces
   it (economy/bank.cc `any_risk`, `tribute_ok`, `tribute_safe`). Allow it when it is provably uninterruptible: every
   alive or respawning enemy's earliest_arrival at our tile with reach = its interrupt reach (max of its stun reach,
   kill reach and lock placement range 2 + 1 walk; when in doubt use one_turn_reach + 1) is later than the channel's
   end (now + channel turns). Same rule for starting (submit_here / can_tribute_safely / the bank branch) and keeping
   (continue_tribute). Also use the bound to prefer, among altars, one whose provable window covers the channel, if
   the altar choice has a natural place for it; skip that if not.
4. Debug: one `debug_block` line `PRES <round> <handle> <group> <f>` when the farm's chosen group has f < 1, and
   `PSAFE <round> <handle> <gems> <turns>` when a channel starts because of rule 3 (debug builds only).

Leave everything else as it is. Keep comments short (AGENTS.md: comment only counterintuitive reasoning).

## Build, audit, smoke
- Build: `cd /home/ubuntu/wt/mx-rhea && source ~/venv/bin/activate && cambc build bots/variants/c1-presence` (and
  `--release` is what A/Bs use; ab.py builds for you).
- When the change is done, spawn ONE read-only auditor subagent (general-purpose). Tell it explicitly: do not edit
  any file, only read and report. Give it this brief's path and the diff (`diff -ru bots/variants/chy-ref/src
  bots/variants/c1-presence/src`), and ask it to check the change against the design and `cambc-rules.yaml` for bugs:
  wrong bounds (an arrival bound that is not a lower bound), stale caches, prune bounds that no longer bound, sign
  errors, Cassi/Issac handling, unseen/never-seen enemies, fuel blow-ups in the farm loop. Fix what it finds.
- Smoke: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-rhea && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c1-presence variants/chy-ref --no-test-draft --fuel 200000 --name mx-rhea-c1-smoke`
  (256 ladder games). Required: no failed games, no DRAFT-UNFINISHED / PLAN-CHECK lines, out-of-fuel turns not
  wildly above chy-ref's (report both). The smoke's win rate is noise (±6); do not tune on it.
- You may also run one debug check on `maps/suites/mx-rhea/study` (`--suites maps/suites/mx-rhea/study --debug`, a few
  hundred games are enough with `--sprt` off; that suite is for smokes and traces only) to confirm the PRES / PSAFE
  lines fire sensibly (how often f < 1, typical f, PSAFE count per game). Do not run large A/Bs; the orchestrator does.

## Stop condition and report
Stop when the variant builds, the auditor's findings are fixed, and the smoke passes. Report: what you changed (files,
functions), any design decision you had to make, the smoke result (win %, OOF turns both sides, failures), the trace
counts if you ran them, and anything suspicious. Keep the report concise. Do not start further experiments.
