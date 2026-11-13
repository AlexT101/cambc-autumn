# Brief B: no body ends a turn where the enemy Prism kills it (diagnose, then fix at the root)

You are an implementation agent for PHOEBE, who owns a macro refactor of our Cambridge Battlecode bot `charybdis`
(C++, compiled to WASM). Work only in the worktree `/home/ubuntu/wt/mx-phoebe` (branch `mx-phoebe-20261113`); never
touch `/home/ubuntu/cambc-autumn` (read-only reference) or any other worktree, never push, never commit (PHOEBE commits).
Another implementer works in `bots/variants/phb-hub` at the same time: do not touch it.

## Read first
- `/home/ubuntu/wt/mx-phoebe/AGENTS.md`, `cambc-rules.yaml` (engine-verified rules; Prism spells, stun, casting being
  exclusive with walking), `docs/api/cpp.md` as needed.
- The bot: `bots/variants/chy-ref/src` (= charybdis 529). `bot.cc` is the turn (`decide`, branch order); `model/safety.*`
  (threat model, `threat_strike`, two-turn widening), `model/enemy_reach.h`, `combat/guard.cc` (step guards),
  `combat/fight.cc` (stands, retreat, `prey`, chase), `economy/farm.cc` (farm choice), `economy/capture.cc` (holds).
- Prior attempt: `research/macro-icarus/NOTES.md` E7 `mo7-shy` (Cassi, Issac, Willow treat tiles within a lethal ready
  enemy Prism stun's reach as guarded steps): level over 24,320 games. Also `research/macro-boreas/NOTES.md` b-duel
  (Prism burst lethality in guard/retreat, +0.7, merged later in some form) and CHANGES 525 ("bag focus": the
  enemy's simulated turns aim at our richest bag carrier).

## What a replay study found (1,360 charybdis mirror games, debug; PHOEBE's study agent)
- The Prism cannot cast after walking; its stun reaches 4 tiles (1.5 x Focus), its ground spell 5 (range 4 + the 3x3
  area, 1 x Focus). Call a body **lethal-exposed** when it ends a round within 5 of an enemy Prism whose ground spell is
  ready with HP <= Focus, or within 4 of a ready stun with HP <= 1.5 x Focus (for Cassi & Issac, the weaker body: either
  death kills both). A stun also removes the victim's next turn, so with both spells ready the enemy Prism lands
  1.5F now and 1F next turn on a body that cannot walk away: 2.5F over two turns.
- Before the first kill of a game, a lethal-exposed body dies **the next round** 39% of the time (C&I, 666 body-rounds),
  46% (other bodies, 432), 55% (our Prism, 143). Within reach but not lethal: 0.4-0.8%. At 6-7 tiles: 0.0-0.3%.
- 222 of the 267 C&I first deaths with a Prism killing blow (83%) were lethal-exposed at the end of the previous round;
  in 218 our Prism was more than 5 tiles from the enemy Prism (no cover).
- Who closed the distance for the killing cast (C&I / Prism / other victims): the enemy Prism walked in, usually the round
  before, 132 / 54 / 150 (its own branch mostly chase; the victim was retreating on its turn in between 80 / 43 / 99
  times: at equal speed one step back from inside reach does not get out). The victim walked in itself 107 / 33 / 101:
  on farm (F) 54 / 15 / 36, on stopping the enemy's game-ending tribute (E) 22 / 10 / 20, on retreat (R) 20 / 1 / 12.
  Example: game dir `0edfb61a4044a8f3` (map gen-ladder-6142100100098) r108-117: the enemy Prism walked to 5 tiles of
  Issac twice; Issac stayed on its group and was killed. 1048aac960c3d5f1 r487: our Prism on E stepped from 6 to 5 of a
  1,330-Focus Prism.
- Farming with the enemy Prism at 6-8 tiles: 3.2% die within 10 rounds against 0.32% with it far away.
- The first death decides a lot: the victim's team wins 34% (C&I first victims 37%); a team whose Prism dies first
  loses ~92%.

## Your job
1. **Diagnose first (bounded).** Find *why* charybdis ends turns lethal-exposed: is the threat underestimated (which
   Focus, which cooldowns, the two-turn stun lock, the enemy's simulated aim at another target under bag focus, an
   unseen-but-recent enemy Prism dropped from the threat set), or is it seen and accepted (which branch, which value
   beats it: a hold's payout, a farm target, E, a retreat path with no better tile), or is it a staying problem (guarded
   steps block walking in, but nothing makes a body leave a tile the enemy Prism walked into reach of)? Use debug traces:
   the mirror batch `replays/batch-20261113-142239-ab-mx-phoebe-mirror-study` (2,720 debug replays with
   `team-a.stdout`/`team-b.stdout` D lines; extracted form in `replays/.mxp-mirror/<hash>/`), or a fresh debug study
   `bash research/mx-phoebe/ab.sh lethdbgN phb-lethal maps/suites/mx-phoebe/study --debug` (2,720 games, ~3 min) with
   your own debug_block traces. Tools: `tools/replay/` (README there), `research/mx-phoebe/scripts/*.py`. Classify a
   sample of lethal-exposed turns by cause. Keep this step to what you need to choose the fix.
2. **Fix it where the cause is**, as one coherent rule every branch obeys (farm and hold choices, E, chase, retreat
   paths, waits, the Prism's own moves when it is the weaker one): a body does not end its turn lethal-exposed to an enemy
   Prism unless that turn is worth its life and bag by the bot's own existing valuations (e.g. a stand the fight model
   wins, a kill, a tribute's last chance). Where the threat model is wrong, correct the model rather than bolting a
   parallel check on top. Where bodies are caught because they leave too late, make the leave happen while it is still
   possible (the enemy Prism can only cast from where it starts its turn: a body that keeps one walk beyond its reach
   cannot be hit; derive the margin from walk speeds and reach, not a constant). Keep it general: all champions, all
   enemy Prisms; if the diagnosis shows the same mechanism for other burst casters (Stellar, Cassi's stun pair), cover
   them by the same rule only if it falls out naturally.
3. Leave alone: the draft (`draft/`), emblem choices, `model/turn_order.cc` rank codes, `bots/variants/chy-ref`.

Measure the mechanism: lethal-exposed body-rounds per game (before the first kill and overall), next-round deaths from
that state, C&I and Prism deaths per game, and gems captured per team-game (the cost in farm output), for CAND vs REF.
A 2,720-game debug study on `study` (PHOEBE's mirror numbers above are the baseline) is the right size for this.

## How to work
1. `./copybot variants/chy-ref variants/phb-lethal` (from the worktree root; never copy `.cambc/`), edit only
   `bots/variants/phb-lethal/src`. Build: `source ~/venv/bin/activate && cambc build bots/variants/phb-lethal`.
2. Win-rate reads only on the `train` suite:
   `tmux new -d -s mx-phoebe-lethN 'bash research/mx-phoebe/ab.sh lethN phb-lethal maps/suites/mx-phoebe/train'`
   (10,200 games, ~5-15 min), wait on `replays/ab/mx-phoebe-lethN/summary.json` with a background until-loop (never a
   foreground sleep). Results in `replays/ab/mx-phoebe-lethN/summary.md`. At most 3 such reads. Noise is about +-1 point.
   If a read loses, find out why (which bodies, which phase, farm output) before changing anything.
3. Fuel: tests run at 2x fuel, but the bot must stay sane at 1x: no unbounded loops, reuse the threat model's existing
   caches, one evaluation per tile per turn.
4. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit any file) to check your diff
   against this brief and the rules (reach, cast-after-walk, stun removing a turn, C&I linked deaths, fuel); fix what it
   finds; make sure the bot builds; play the smoke
   `source ~/venv/bin/activate && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/phb-lethal variants/chy-ref --no-test-draft --fuel 200000 --name mx-phoebe-leth-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
5. Kill every tmux session you started (`tmux ls | grep mx-phoebe-leth`). Delete your A/B replay batches
   (`replays/batch-*mx-phoebe-leth*`) once read, except the last train one.

## Stop condition and report
Stop when the fix is implemented, audited, smoke-clean, and you have at most 3 train reads (or earlier if the diagnosis
shows there is nothing to fix, which is a valid result: report it). Report: the diagnosis (causes with counts), what
you changed (files, functions, as a design), each train read (win %, CI, OOF CAND/REF), the mechanism numbers CAND vs
REF, the auditor's findings, open doubts. Leave the final version in `bots/variants/phb-lethal` and write its diff to
`research/mx-phoebe/patches/phb-lethal.diff` (`diff -ruN bots/variants/chy-ref/src bots/variants/phb-lethal/src`).
