# Brief A: a team control map (influence map) that drives where charybdis farms and walks

You are an implementation agent for TETHYS, who owns a macro refactor of our Cambridge Battlecode bot charybdis.
Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`; never push, never touch `main` or
`/home/ubuntu/cambc-autumn` except to read its committed files). Do not look at other worktrees under `/home/ubuntu/wt/`.
First read `AGENTS.md`, `cambc-rules.yaml` (engine-verified rules), `docs/api/cpp.md` as needed, then the
charybdis source in your copy (see below): `bot.cc` (the turn), `economy/farm.cc` (the farm choice, a large priced
optimiser with prune bounds), `economy/camps.cc` (`home_side`), `model/world.h` (beliefs: `ChampionBelief` has
`visible`, `pos`, `pos_round`, `possible` boards for enemies, `tracked`), `model/comms.h` (`told_ally` gives an ally's
posted tile), `model/safety.h` (threats, pack zone), `params.h`.

## Why

Mirror study of charybdis 529 (5,440 games; winner W vs loser L):
- More middle-group captures wins 78% of games; W takes 5.9 middle and 5.8 enemy-side captures a game (285 gems),
  L 3.7 and 3.5 (145 gems); own-side captures are close (43.6 vs 40.9).
- Supply is not binding: own-side groups sit asleep (alive, unworked) 58% of the time, middle groups 69% (78% in
  rounds 1-300), enemy-side 59%. Even against an idle opponent the team works 62% of its own side's supply, 42% of
  the middle's and 16% of the enemy side's: walking cost and the static exposure keep it home.
- Deaths decide: L dies 10.5 times a game against W's 3.3, most of them to the enemy Prism, most in fights with 3+
  enemies within 8; L dies outnumbered (more enemies within 8 than allies + 1) 4.3 times a game, W 0.7.
- Head-count advantage turns fights: at +2/+3 bodies within 8 the side wins 21-26% of fights on kills against
  10-11% at -2/-3.

Today the farm prices a group's place only through a static side share (`exposure()` in farm.cc: groups in a middle
band of `home_side` are worth `params::mid_exposure` = 1.36x; NYX raised it to 1.70 for about +1 on ladder-mix
maps) plus the safety model's reactions to enemies in sight. Nothing tells a champion where the team is strong or
weak right now. The team has no notion of territory.

## Design

A **control map**: once a round per bot instance (cached; all champions of a team compute it from what they know),
estimate for each camp group (and, if cheap, each altar) how strongly our team and theirs can bring force there in
the next few rounds:

- Our presence at a site: the sum over living allies (us included) of a fight-strength weight times a reach
  kernel of the walking or Chebyshev distance from the ally's best-known tile (in sight, else `comms::told_ally`,
  else its claim's group, else skip) to the site. A kernel that falls to 0 at the distance an ally walks in a
  horizon of H rounds (pick H from a mechanic you can state, e.g. the rounds a clear plus capture takes, ~12-15;
  or the camp's own clear time).
- Their presence: the same over living enemies from their beliefs: in sight at their tile; tracked but unseen
  spread over their `possible` board (or last tile with the uncertainty radius grown by rounds since seen); never
  seen or long unseen, a prior at their own side (their spawn's region), so the enemy's home stays theirs. Dead
  enemies count 0 until respawn (dead time is readable: `alive` only; respawn is 60 rounds after death).
- Fight strength: something the bot already prices or a rules-derived proxy (e.g. effective health x damage a
  round, Prism's Focus counted through its spell damage, so a big-bag Prism weighs what it can do). Keep it simple
  and consistent for both sides.
- `control(site) = ours / (ours + theirs)` in [0, 1].

Use it in the macro, replacing the static middle band rather than adding a bolt-on beside it:
1. **Farm valuation:** a group's weight becomes a function of its control, not of its static side. Where we
   control a group strongly it is safe to farm; where the enemy controls it, it is dangerous; a middle or
   enemy-side group we control is worth more than its own reward, because taking it also denies the enemy (state
   the denial term from the rules: the gems it does not capture, at most its share of the race). Keep it bounded so
   the farm loop's prune bounds stay valid (the loop uses `params::max_exposure` / `exposure_most` as upper bounds on
   the weight: whatever the new weight's maximum is, the bounds must use it, or prunes become wrong).
2. **Movement:** optional, if it fits: walks between work sites avoid passing through enemy-controlled sites when an
   equal route through ours exists. Do not build a new pathing system; skip this if it is not cheap.
3. Make the effect versatile, not a rule: no champion is ordered anywhere; the map only changes how each one prices
   its options. It should make the team expand into the middle and the enemy side where and when it holds the
   ground (more bodies or a stronger Prism there, enemies dead or seen far away) and stay off ground the enemy
   holds.

Leave alone: `draft/` and which champion is picked; which emblem a champion builds toward (`emblem_table.h`,
the emblem choice in `shop.cc`). The safety model and fight code (`model/safety.*`, `combat/`) are not your target;
you may read their outputs.

Fuel: A/Bs run at 2x fuel (200k a turn), so do not optimise fuel, but keep the map's cost bounded (once a round,
per group not per tile unless cheap; a guard against runaway loops). A turn that runs out of fuel loses the rest.

## Work

- `./copybot variants/chy-ref variants/mx-ctl` (from the worktree root; never copy `.cambc/`), and work only in
  `bots/variants/mx-ctl`. Never edit `bots/variants/chy-ref` or `bots/charybdis`.
- Build: `cd bots/variants/mx-ctl && cambc build` (or as AGENTS.md / tools/README.md show). `unity.cpp` includes
  every `.cc`: a new `.cc` goes there.
- Iterate on the training suite `maps/suites/mx/train` (5,100 maps; if it is not there yet, use
  `maps/suites/mx/study`), never on `dev` or `hold`. A 10k-game A/B (run from the worktree root, in tmux):
  `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-ctl variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-ctl-<tag>`
  with `tmux new -d -s mx-tethys-ctl-<tag> '...'`; results in `replays/ab/<name>/summary.md`. Leave `--threads` off.
  Kill only sessions you started. Delete a run's `replays/batch-*` once you have studied it (about 3 GB each).
  Noise is about ±1 point at 10k games. `--debug` builds give `debug_block` traces (compare debug only with debug).
- Check what moved: middle/enemy captures per game, deaths, captures (e.g. `research/mx-tethys/scripts/cohesion.py`
  needs `node tools/replay/extract.mjs <batch> --threads 40` first; `research/mx-tethys/scripts/turn_budget_wt.py
  <batch> --by-bot` gives the turn budget and captures by side per bot). If it loses, find out why (which phase,
  map class, behaviour) and fix the reason if it is a bug or a missing companion piece; up to ~3 iterations.
- Before returning, spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) that checks your
  change against this design and the rules for bugs (prune-bound validity, stale beliefs, dead allies, Cassi/Issac
  as two bodies, out-of-range indices, fuel). Fix what it finds. Make sure the bot builds, and play a smoke:
  `py tools/ab.py variants/mx-ctl variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games): no failed games,
  no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
- Stop when you have a build whose train A/B you believe in (or after ~3 iterations without one). Save the diff:
  `diff -ruN bots/variants/chy-ref/src bots/variants/mx-ctl/src > research/mx-tethys/patches/mx-ctl.diff`.
  If you keep intermediate builds worth comparing, freeze them as `variants/mx-ctl-v<N>` (copybot).
- Do not commit; TETHYS commits.

## Report (your final message)

What you built (design, files), each A/B you ran (name, win %, CI, games), what moved in the replays, what the
auditor found and what you fixed, the final variant path and diff path, and your judgement of what to try next.
