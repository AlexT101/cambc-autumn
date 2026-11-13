# Brief B: efficient crews on strong camp groups (implementation subagent)

You implement one macro change to our Cambridge Battlecode bot charybdis, in C++, and measure it. Work only in
`/home/ubuntu/wt/mx-crius` (a git worktree on branch `mx-crius-20261113`). Do not commit, push or touch any other
worktree or `/home/ubuntu/cambc-autumn`. Do not edit `bots/variants/chy-ref` (the frozen reference), `bots/charybdis`,
or any other variant. Another subagent works in `bots/variants/a-collect` on the Prism's capture hand-overs
(capture.cc's holder / hand-over logic and the allies' premium pricing); stay out of that topic.

## Read first
- `AGENTS.md` (repo rules: fuel, debug_block tracing, testing), `cambc-rules.yaml` (engine-verified rules: camps
  (wake, sleep, attack: each awake monster hits the nearest champion of either team in its range once a camp phase),
  capture, champions), `docs/api/cpp.md` as needed.
- Source: `bots/variants/chy-ref/src`. `economy/crew.cc` (plan_crew, crew_tank, share_damage, crew_available,
  mono_trapped), `economy/farm.cc` farm_turn (the group choice; crew pricing; `mono_engage`, the staging that exists
  only for Monoliths; `passing`, `affordable`; the walk and hits), `economy/camps.cc` (clear-time models, `rate`),
  `model/crew_work.h`, `combat/guard.cc` (guard_work), `bot.cc` `decide()`.

## Why (measured on 1,700 mirror games, chy-ref vs itself)
- Elk and Golem groups (32 and 62 gems a group, plus 270+ gold) sit up and asleep at full health 41% and 54% of
  rounds through r600 (gem clusters 33%): the richest groups are underworked.
- Clears of Elk/Golem groups with 2+ champions each dealing 10%+ of the damage are slower and take more camp damage
  in total than solo clears of the same kind, in every phase. Mid-game (r250-600) Elk groups: solo 13.3 rounds from
  first hit to clear and 469 camp damage taken; 2 strikers 17.6 rounds / 643; 3 strikers 18.3 / 748. Golem: solo
  19.2 / 1053; 2: 24.8 / 1325; 3: 27.8 / 1633. A crew of k should clear in ~1/k of the time and, since each awake
  monster hits only the nearest champion, take ~1/k of the damage in total.
- Crew clears: lag from the first hit to the second striker's first hit has quartiles 0 / 2 / 5 rounds (p90 14); 19%
  of the damage taken lands before the second striker arrives. Even clears where both start in the same round take
  11.5 rounds. Only the Monolith operation stages its crew before waking the group (`mono_engage`).
- Scripts: `research/mx-crius/scripts/crews.py`, `crews2.py`, `crewlag.py`, `supply.py` (each takes an extract
  dir; `replays/an-mirror` holds the mirror games). Prior: ablating crew operations costs ~20 points, so crews matter.

## The task
First find out why crews are inefficient: trace real crew clears (debug traces on `study`: who claims, who arrives
when, who tanks, who leaves early and why, what each striker does each round, whether members stand where the camps
hit them or the tank). Then make the team's work on strong groups efficient, as one design built into the existing
crew and farm logic (not a separate system beside it), for example:
- the start of a clear timed to the crew's arrival (generalise the Monolith's staging to every strong group, with the
  wait priced against what the first-arriving member loses by tanking alone, derived from the camps' strength and
  the members' arrival times, not a constant);
- the tank (the member whose health per camp damage taken is best, crew_tank) standing nearest so the monsters'
  nearest-champion hits find it, the others positioned to hit without being the nearest;
- members not leaving a clear their departure makes slower or costlier than it saves;
- the farm's crew pricing (what a member expects from joining) matching what crews really deliver, so champions
  choose strong groups when a crew makes them pay and leave them when it doesn't;
- whatever else the traces show. Every rule must follow from the camp rules or measured quantities; no magic numbers
  or map-specific cases.
Leave alone: `draft/`, which emblems champions build (`economy/shop.cc` emblem choice), and fuel optimisation (we
test at 2x fuel; a guard against runaway loops is fine).

## How to work
- `./copybot variants/chy-ref variants/b-crew` (never copy `.cambc/`) and work in `bots/variants/b-crew`. `unity.cpp`
  includes every `.cc`: a new one goes there.
- Farm speed without enemies: `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-crius && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/solo.py variants/b-crew variants/chy-ref --suites maps/suites/mx/study --one-side --fuel 200000 --name mx-crius-b-solo-<tag>`
  (both against an idle team; paired per map: round to 1000, collected @150/300/600; `replays/solo/<name>/summary.md`).
- Win rate: `... py tools/ab.py variants/b-crew variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-crius-b-<tag>`
  (10,200 games, ~3-8 min; `replays/ab/<name>/summary.md`). Run long commands in the background
  (`run_in_background`), never a foreground sleep loop. Use only `train` for A/Bs and `study` for solo runs and
  `--debug` traces (`debug_block({ printf(...); })`, output in replays' `team-?.stdout`); never `dev`, `hold`, `x1`,
  `x2` or `fin`. Delete replay batches you no longer need (`replays/batch-*-mx-crius-b-*`).
- Check the mechanism moved: rerun `crews2.py` / `crewlag.py` on your games (`node tools/replay/extract.mjs BATCH --out DIR`).
- Iterate at most ~4 full train A/Bs (fix bugs and missing companion pieces; do not sweep constants).
- Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
  change against this design and the rules for bugs; fix what it finds; make sure the bot builds; play a smoke
  `py tools/ab.py variants/b-crew variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games: no failed games,
  no DRAFT-UNFINISHED / PLAN-CHECK).
- Stop when: the design is built, audited and smoked, and you have its best train A/B; or after ~4 train A/Bs; or if
  the premise proves wrong (then say what the traces showed).

## Report back (concisely)
The variant path; what the traces showed about why crews were slow; what you built (design, files touched); each
solo and train A/B (win %, CI, OOF both sides) and what changed between them; the crew metrics before/after; the
auditor's findings and fixes; the smoke; what you would try next. Save the final diff:
`diff -ruN bots/variants/chy-ref/src bots/variants/b-crew/src > research/mx-crius/patches/b-crew.diff`.
