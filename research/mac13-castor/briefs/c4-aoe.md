# Brief C4: an area-aware clear model for the farm (implementer)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/chy-ref variants/c4-aoe` (never copy `.cambc/`). Edit only
  `bots/variants/c4-aoe/src`. Never edit `bots/variants/chy-ref` or `bots/charybdis`; other implementers work in
  other `bots/variants/c*` directories: don't touch them.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem a champion builds toward).

## Why
The farm (economy/farm.cc `farm_turn`, economy/camps.cc `camp_output`, `min_camp_damage`, the crew pricing in
economy/crew.cc and farm's `crew_rate`, the opening plan's `simulate` in draft/open_plan.cc) prices a clear as if
every damage source hit one member at a time: `camp_output` = `ChampionFacts::raw_output(strength, focus)` x
modifiers, i.e. Strength plus each damage spell's multiplier x Focus spread over the 8-round cooldown, once per round.
But camp groups are cardinally connected monsters, and on 1,023 study maps 83% of groups have 2+ members and nearly
all of a group's members fit under one 3x3. So:
- a **ground** spell (Prism slot 1: 1.0x Focus, 3x3; Stellar slot 1: 1.4x; Ryth slot 0: 1.0x + stun) hits every
  member under its 3x3 at once;
- **Varg**'s basic attack also deals its Strength to other camps within 1 of the target;
- **Heart of Ruin**'s dash landing deals 1.5x Focus and stuns everything within 1 of the landing tile.
For a Prism at Focus 400 on a 3-member group the model says ~160 damage a round where the real figure is ~260
(stun 1.5F single + ground 1.0F x 3, over 8 rounds, plus Strength). The Prism is the team's farm engine (a third of
all camp damage; its Focus grows 1.5 a carried gem), so its clear times, the camp fire it takes while clearing, the
crews the farm proposes on its groups and the holder/handoff timing all rest on a clear time that is too long, by a
factor that depends on the group's shape. Gem and gold clusters (120 HP each) under one ground cast die together.
The fix is a rule-derived quantity the decision code never sees: how many live members each area source hits.

## The design
1. A per-group, per-champion **area multiplier**, from the group's member positions (static) and live members
   (beliefs): for each area source of the champion, the most live members one cast (or one cleaving hit) can cover,
   given the source's footprint (3x3 for ground spells, within 1 of the target for Varg, within 1 of the landing for
   HoR) and that the caster must stand within the spell's range. Keep it cheap: groups are small; cache per group and
   live-member mask.
2. Use it wherever the farm models a clear: the group's **clear rounds** (the `fastest` clear, `min_camp_damage`'s
   rounds and the camp fire taken during them), crew pricing (`crew_rate`, crew.cc's expected crew output), and the
   holder/handoff timing that waits on a clear's end. A simple, consistent way: an effective output against group g
   = single-target output + sum over area sources of (members hit - 1) x that source's per-round damage, capped by
   what the members' remaining health can absorb (a cast cannot deal more than the health it covers). Members die at
   different times: you may approximate with the expected number hit over the clear (e.g. the live members' health
   profile), but don't overclaim on 1-member groups.
3. The opening plan (`draft/open_plan.cc` `simulate`, solved in the draft's first turn with the team's base stats):
   apply the same multiplier to its clear model if it is cheap and stays within the draft's first-turn fuel; check
   with `tools/draftlab/firstturn.py --need` (AGENTS.md "Draft precompute"). Leave the picks themselves alone.
4. Don't change how the casts are executed (`combat/abilities.cc` `camp_cast` already aims ground casts at the most
   members), only the planning model.

## Measuring and iterating
A 10k-game release A/B takes ~3 minutes. Iterate against the reference on the **train** suite only (never `dev`,
`hold`, `conf` or `x1`: those are the orchestrator's decision suites):
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c4-aoe variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/train --name mac13-castor-c4-trainN`
(10,240 games, noise about +-1 point). Farming against an idle opponent:
`py tools/solo.py variants/c4-aoe variants/chy-ref --name mac13-castor-c4-soloN --suites maps/suites/mac13/study --one-side --fuel 200000`
(collected gems @150/300/600 are the economy proxy). Debug traces: `debug_block({ printf(...); })` only, never plain
printf; add `--debug` to ab.py and read `team-a.stdout` in the replay zips (`tools/replay/debug_lines.py`). Report
every full train reading, not only the best; keep each tested variant as a directory or saved diff. Run long
commands in the background or tmux (sessions `mac13-castor-c4-*`); foreground sleep is blocked.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design above and your
   diff (`diff -ru bots/variants/chy-ref/src bots/variants/c4-aoe/src`) to check it against the design and the rules
   (`cambc-rules.yaml`) for bugs. Fix what it finds.
2. Make sure the bot builds, and play the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c4-aoe variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c4-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c4-aoe.diff`. Don't commit. Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke. Return: what you changed (files,
functions, the multiplier's derivation), the solo and train readings of each variant, the smoke, and anything you
were unsure about.
