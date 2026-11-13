# rk1: shared team knowledge for the farm (charybdis macro, DIONE programme)

You are an implementation subagent for DIONE, an orchestrator improving the macro of the Cambridge Battlecode bot
charybdis. Work ONLY in the git worktree `/home/ubuntu/wt/mac13-dione` (branch `mac13-dione-20261113`). Never touch
`/home/ubuntu/cambc-autumn` (read only; you may read its files), other worktrees under `/home/ubuntu/wt/`,
`bots/charybdis`, `bots/variants/chy-ref` (frozen reference: never edit), or any variant you did not create. Do not
commit or push. Read `AGENTS.md` and `cambc-rules.yaml` first (engine-verified rules; C++ only; comment only
counterintuitive behaviour; `unity.cpp` includes every `.cc`). Off limits: the draft (`draft/`, picks) and emblems.

## Setup and running
`./copybot variants/chy-ref variants/rk1` (never copy `.cambc/`); edit only `bots/variants/rk1/src`. Python:
`source ~/venv/bin/activate`. Prefix every ab.py run with
`CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH`.
Every A/B is `py tools/ab.py variants/X variants/chy-ref --no-test-draft --fuel 200000 --suites <suite> --name
mac13-dione-rk1-<tag>`, long ones in a tmux session of the same name, waited on with background until-loops on
`replays/ab/<name>/summary.json` (foreground sleep is blocked; commands over ~3 min get backgrounded). Only ever kill
or delete things carrying exactly the prefix `mac13-dione-rk1-`. No `--threads`, no fgate.py, gates, live tests or
other opponents. Iterate only on `maps/suites/mac13/study` (2,048 games; `--debug` for traces) or
`maps/suites/mac13/screen` (10,240 games); never `dev`, `hold` or `conf`. Delete your replay batches when done.

## Why
- Turns in safe space decide games: idling the farm branch 1 turn in 20 when no enemy is within 10 lost 6.7 points;
  the same idle near enemies cost nothing measurable.
- ~17% of non-Prism farm turns are walks toward a target later abandoned without hitting it (~47 trips, ~390 turns a
  team-game). An instrumented mirror (another agent, fc1) tagged the causes, turns per team-game: respawning target
  came due elsewhere (mates already on it 46, unclaimed 31); a mate's claim left the new group 31; the old group's
  respawn wait grew when a new timer was read 27; help calls 24; joining a mate's claim ~48 (mate unseen 18); drift
  with no new information 15; mate claimed the new group 11; excluded by the claim rule 10; mate left/joined the old
  group ~19. Most switches follow **new information that teammates already had or could have had**: claims that
  flicker to -1 whenever a mate retreats, shops or dies; stale positions of unseen mates (charybdis lacks ocean's
  CHANGES 507 comms slots: told tiles; teammates are in sight in only ~40% of pairs); respawn timers read only on sight.
  Rules that try to arbitrate ownership on stale data lost badly (ETA ownership 33-44%), because the data were stale.
- Comms are 8 shared bytes (`model/comms.{h,cc}`): bags, claims, camp records. Ocean's 507 port is
  `/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/comms/cm2-k3.patch` (against ocean 506; charybdis branched from
  ocean 506, so it should mostly apply; read research/hyperion/CHANGES.md "507-ocean" and
  `/home/ubuntu/cambc-autumn/research/ideas-2026-11-11/comms/README.md`).

## Task
1. Port 507's comms slots (told tiles; an unseen claimer counts in its group's crew by its told tile) into rk1,
   adapting to charybdis's comms (it also posts bags and the Prism carry claims: keep all of that working).
2. Claims that mean intent: a champion that retreats, shops, recalls or heals and intends to return to its farm target
   keeps posting that claim (it still owns the job), and drops it only when it abandons the job (dies, picks another).
   Check every consumer of claims (crew counts, carry 'G'/'L'/'Q' logic, yield rules) still reads them correctly.
3. If the bits allow, share what one of us saw about a group that changes others' pricing: its respawn round (payout +
   longest member respawn, known from a capture we saw or a respawn timer we read), so a teammate does not walk to a
   group that will not be back, or skip one that will. Use the existing camp records if they already carry this;
   measure first which information is missing.
4. Diagnose before and after with a debug batch: switched-walk trips and turns (a trip = a run of farm turns on one
   farm_group in D lines `D <round> <handle> <branch> <farm_group> <claim>`, bot.cc:764; one that ends without our hit
   or capture and is followed by a different group), by cause; captured / camp time; still time; deaths; OOF turns.
   A script that computes these from an extracted mirror is `/tmp/dione/trips5.py` (it reads
   `replays/.analysis-dione`; adapt the root; extract with `node tools/replay/extract.mjs <batch> --out <dir> --threads 24`).
5. When it first builds and a 256-game smoke (`py tools/ab.py variants/rk1 variants/chy-ref --no-test-draft --fuel
   200000 --name mac13-dione-rk1-smoke`) is clean, freeze `./copybot variants/rk1 variants/rk1-s1` and continue.
6. Spawn a **read-only** auditor subagent (tell it explicitly: do not edit any file) to check the diff (comms bit
   layout overflow, both sides of the turn order reading writes correctly, claims consumers, Memory reset on death,
   fuel). Fix findings unless a study read shows the fix loses; say which.
7. Final: builds; smoke clean (no failed games, no DRAFT-UNFINISHED / PLAN-CHECK); save
   `diff -ruN -x .cambc bots/variants/chy-ref/src bots/variants/rk1/src > research/mac13-dione/patches/rk1.diff`.
   Kill your tmux sessions; delete your batches except summaries.

## Stop condition, deadline, report
Stop when the final checks pass, and in any case report by **08:15 UTC** with your best variant so far. Report: what
changed, the before/after diagnosis, every variant you read (name, change, suite, games, win %), the auditor's
findings and what you did, and suspected leaks.
