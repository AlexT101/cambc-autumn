# Line F: don't leave a won stand into a retreat that can't escape

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 2,720 games; and this programme's A/Bs)
- The first Prism death decides the game (victim's team loses ~92%). Early first Prism deaths: branch R (retreat) at
  death in 87%, R the main branch over the 10 rounds before in 57%. HP above 70% ten rounds before in 75%.
- **A retreat does not open distance.** Everyone walks one tile a turn; a ranged champion's walk costs its basic attack
  (rules: "A walk or a basic attack spends both"), and the pursuer's stun removes a turn. After the first hit, chased
  Prisms made a median 0.125 tiles a round of net progress home; 49% flipped between R and other branches 3+ times.
  Matched on the nearest enemy 5-6 tiles away and not yet hit, Prisms that switched to R died within 15 rounds 3.7% of
  the time against 2.1% for those that kept farming (confounded, but in neither case did the Prism gain distance).
- In this programme, making the Prism leave earlier lost 7.7 points (committed) and 2.5 (uncommitted).
- In the code, `stand_lost_at` (combat/fight.cc) sends a body home (`want_home` -> `leave` -> `retreat()` in
  `bot.cc`, branch R) when the stand is lost, **or when it "falls" in a stand the team wins**: `falls` is true for
  Cassi and Issac (`partner(world) != nullptr`), for the Prism always (`Passive::gem_focus`: "its death hands over the
  bag"), for any carrier with `gem_value * bag >= life_value`, or `lethal()`. So in a fight the team is winning, the
  Prism, the pair and carriers walk out, taking their damage out of the fight, while the pursuers follow at the same
  speed. Whether that walk can actually get them out of reach is not asked.

## Design
Leave a stand the team wins (where only `falls && self_falls` says go) only if the retreat escapes: the walk home (or
to the allies that make it safe) gets out of every pursuer's reach before the pursuers' damage kills us. When it
cannot, stay and fight with the full kit: the team wins the stand, and our damage is part of why. A lost stand
(`t.lost`) still sends us home as now.

- Escape test, from what the safety model already computes: `Safety::stand_walks`, `pursuit_gain(e)`,
  `stand_reach`, `turns_to_kill_us` / `Trade::turns_to_kill_us`, `enemy_reach`, the escape paths in model/escape.cc.
  The retreat escapes if, for every enemy that would pursue, the rounds until it can no longer reach us on our way
  out are fewer than the turns its (and its allies') damage needs to kill us, counting a stun as a lost turn of ours.
  Derive it; no hand-picked margins. If an existing function already answers "can I outrun them", use it.
- Keep everything else in `stand_lost_at` / `want_home` as it is (recall line, camps, pack zone, Willow, finish heal).
- Three versions to read, in this order:
  1. **Prism only**: the escape test applies to the Prism's `falls` case;
  2. **all `falls` cases** (Prism, Cassi/Issac, big-bag carriers, lethal);
  3. whichever of 1-2 reads better, plus: while we stay in a won stand that we would otherwise have left, our attack
     choice prefers the enemy most likely to kill us (the fight sim's threat), if the existing target choice doesn't
     already do that.
- Debug: print one line per turn the new rule keeps a body in a stand it would have left (in `debug_block`), so the
  firing rate can be counted.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-stand` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-stand`, freezing each version as `bots/variants/mx-stand-vN` before changing it. `test_draft`
   stays off.
2. Build: `cambc build bots/variants/mx-stand --release` (without `--release` for debug traces).
3. Read each version with a full A/B on the train suite (10,200 games, about 2-3 minutes of wall):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-stand-vN variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-stand-vN`
   Run each in a tmux session named `mx-tethys-stand-vN`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. `--debug` (both sides debug) when you need traces. Never use the dev, hold, conf1 or fin
   suites. Delete each `replays/batch-*` you create once you have read it (~3 GB each). Other A/Bs share the box; fine.
4. Measure (debug A/B or extracted replays; `node tools/replay/extract.mjs`, `--threads 40` or fewer; scripts in
   `research/mx-tethys/scripts/`: `prism_death.py`, `all_deaths.py`, `kills.py`, `prism_race.py`): how often the rule
   fires a game, Prism and pair deaths a game, kills a game, gems taken by kills, CAND side vs REF side. When a
   version loses, find what changed (deaths up where, kills, farm time) before the next.
5. Watch fuel: OOF turns must stay near chy-ref's.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-stand variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when the three versions are read (or earlier with a version at 52%+ on train), at most five train A/Bs of real
versions in all. Time matters: aim to return within about an hour. Report through SubagentHandback: the variant
paths; each version's change, train read with interval and OOF; the firing rate and the death/kill counts; the
auditor's findings and fixes; the final diff stat. Save the best version's diff with
`diff -ruN bots/variants/chy-ref/src bots/variants/mx-stand/src > research/mx-tethys/patches/mx-stand.diff`, with
`bots/variants/mx-stand` equal to the best version.
