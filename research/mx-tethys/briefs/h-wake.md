# Line H: wake a Monolith only when the crew in range can finish it

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 856 games on maps with Monoliths; an earlier line in this programme)
- chy-ref's opportunistic Monolith farming is worth ~1.7 points on Monolith maps (never farming them: 48.3% on a
  Monolith-map subset). A committed team operation lost (it spent more time for less).
- **Abandoned wakes waste it:** 3.35 wake episodes a game, only 32% reach a kill. Abandoned wakes had a median 1.46 of
  our bodies in range (kills: 3.1) and left a median 15.8k of the Monolith's 20k health, which the enemy can then finish
  (rules: camps never regenerate) — in the committed version the enemy's captures rose with our wakes. Each awake
  Monolith hits the nearest champion in range 5 for 200 a camp phase.
- The wake rule (`mono_engage` in `economy/farm.cc` ~716-731): a sleeping Monolith is woken once
  `params::mono_gather_share` (0.63) of the crew's output stands within a step of the staging ring, **or after
  `params::mono_max_wait` (12) rounds staged there** whatever has gathered. The timeout is the likely source of
  under-crewed wakes; the share is of the planned crew's output, not of what a kill needs.

## Design
Replace the two hand-tuned wake conditions with one derived from the rules: wake (deal the first damage to) a sleeping
Monolith only if the bodies now within reach of it can kill it before its hits exhaust them: the crew's output a
round (basic attacks and spells at current Strength and Focus, as farm's crew output already computes; stuns on it
skip its attack) gives the rounds to kill, and 200 a phase on the nearest body, rotated over the crew's health above
the line at which each would go home (the bot's recall/heal lines), gives the rounds they can hold. Wake when hold
>= kill. No timeout: if the crew never gathers, the op doesn't start, and farm's existing pricing moves bodies on.
Leave everything else in the Monolith operation as it is. If `mono_gather_share` / `mono_max_wait` become unused,
remove them.

Version 2, only if version 1 reads level or better: once a Monolith we woke is awake and damaged, the bodies in
range keep at it while the same test, on its remaining health, still holds (progress is never lost), rather than
leaving for a farm pick that the per-turn pricing prefers.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-wake` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-wake`, freezing each version as `bots/variants/mx-wake-vN`. `test_draft` stays off.
2. Build: `cambc build bots/variants/mx-wake --release`.
3. Read on the Monolith-map subset `maps/suites/mx/train-mono` (1,553 maps, 3,106 games, under a minute) and on the
   full train suite `maps/suites/mx/train` (10,200 games, ~2-3 minutes):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-wake-vN variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train-mono --name mx-tethys-wake-vN`
   Run each in a tmux session named `mx-tethys-wake-vN`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. Never use the dev, hold, conf1 or fin suites. Delete each `replays/batch-*` you create once
   read. A script from the earlier line, `research/mx-tethys/scripts/mono_diag.py`, counts wakes, kills, abandoned
   wakes and captures from extracted debug replays (`--debug` A/B, then `node tools/replay/extract.mjs`).
4. Watch fuel: OOF turns near chy-ref's.
5. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-wake variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
At most three versions. **Return within about 50 minutes**: time is short. Report through SubagentHandback: the
variant path; each version's subset and full-train reads with intervals and OOF; wakes, kills, abandoned wakes and
captures a game by side; the auditor's findings; the diff stat. Save the best version's diff to
`research/mx-tethys/patches/mx-wake.diff` (`diff -ruN bots/variants/chy-ref/src bots/variants/mx-wake/src`), with
`bots/variants/mx-wake` equal to it.
