# Line E: take the Monolith as a committed team operation

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 2,720 games on fresh ladder-v4 maps, debug traces)
- The map's gem supply, as gems / (respawn + capture) summed over groups, is ~6.5 gems a round; both teams together
  capture ~2.6 a round in r101-600 (40%). By type, captured share of r101-600 supply: wolf 42%, elk 48%, gem cluster
  51%, gold cluster 56%, golem 39%, **Monolith 3%** (458 gems of supply a game on average across all maps, 14 taken).
- 31% of maps (856 of 2,720) have Monoliths, 2 on average, 70% of them in the middle band, half grouped with other
  monsters. In the 340 of those games where any Monolith was captured, the team with more Monolith captures won 80%.
- Rules: Monolith health 20,000, Strength 200, range 5, reward 200 gems + 300 gold, respawn 150. Each awake monster
  hits the **nearest** champion in range once per camp phase; ties go by turn order. **Camps never regenerate**: damage
  done is never lost. A stunned camp skips its next attack. Allies on the camp tiles at payout split the reward; a
  lone holder takes it all. Abilities: multiplier x Focus, 8-round cooldown, range 4; ranged basic range 3. So every
  attacker stands within the Monolith's range 5, and only the nearest one is hit: the crew chooses who tanks.
- The bot already has a Monolith operation in `economy/farm.cc` (`farm_monolith`, `mono_engage`, `memory.mono_group`,
  the staging ring, `params::mono_gather_share` 0.63, `mono_max_wait` 12, `mono_stickiness` 1.68) and
  `economy/crew.cc` (`farm_monolith`, `mono_trapped`). Its debug traces (`MONO START/STAGE/ENGAGE/VALUE/END`) show it
  **dithering**: in the mirror, 27,264 STARTs and 24,638 ENDs over 1,550 game-sides, most ENDs after 1-5 rounds
  ("MONO END r id g for N taken T state S value V now gX B value W"), each body re-deciding alone: an op is worth
  doing only if the crew comes, and the crew leaves because it isn't there yet.
- Also: `prism_premium` is switched off for Monolith groups (farm.cc ~1031 `G.has_monolith` returns 0) and the holder
  logic skips them (~222). A keeping Prism holding the capture alone would take all 200 gems, +300 Focus at 1.5 a gem
  (rules).

## Design
1. **Diagnose first** (one debug A/B on train, both sides debug, or the existing mirror replays in
   `replays/batch-20261113-142259-ab-mx-tethys-mirror-study`): why operations end. From MONO lines, END reasons (the
   value of the op against the alternative it switched to, who left first, rounds in, damage taken, Monolith health
   left), how many ENGAGEs reach a kill, and captures by our side. Write this down in your report.
2. **One team decision, committed.** Make the Monolith a team operation declared once and shared through comms (the
   8 shared bytes; see `model/comms.h/.cc`, already holding bags, claims, positions; check which bits are free), not
   re-decided by each body each turn. The op's value is the team's: 200 gems (with the Prism's premium when the Prism
   takes the capture alone, as for other groups) + 300 gold at the team's gold price, over the crew's time to kill it
   from the crew's combined output (basic attacks and spells at current Strength and Focus, the Monolith's stun skips),
   against the crew's combined outside rate (what they would farm meanwhile, as farm already prices it) and the
   damage cost (the nearest takes each hit: a rotation with the healthiest nearest, heal trips priced as the bot
   prices them). Commit while the remaining value (remaining health / output, so it improves as work is done, since
   camps never regenerate) beats the outside rate; leave on a real change (threat: enemy force the crew's fight read
   loses to; crew deaths; the end of the game), not on one body's turn-to-turn pick.
3. **Tanking.** The body nearest the Monolith takes every hit. Choose it (most effective health against 200 a phase,
   Durability/Jungle emblems if held) and keep the others farther than it; rotate before the tank falls. Stuns
   (Prism, Cassi and any stun) on the Monolith skip its attack: use them on it when they are not needed elsewhere.
4. **Capture.** After the kill, the capture follows the existing holder logic, with the Prism's premium allowed for
   Monolith groups as for others (only where the Prism keeps its bag).
5. Leave the existing enemy checks (`mono_contested`) in place unless the diagnosis shows they misfire.

Every quantity from the rules and the bot's existing models; no new hand-picked constants. If an old constant
(`mono_gather_share`, `mono_max_wait`, `mono_stickiness`) becomes redundant under the new rule, remove it rather
than retune it.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-mono` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-mono`. `test_draft` stays off.
2. Build: `cambc build bots/variants/mx-mono --release` (without `--release` for debug traces).
3. Only 31% of maps have a Monolith, so the effect is diluted on a full suite. For iteration, build a subset of the
   train suite holding only maps with a Monolith: copy them to `maps/suites/mx/train-mono/` (decode maps with
   `tools/.../mapjson.mjs` or another decoder in tools/, see tools/README.md; or read the camp types from
   `node tools/replay/extract.mjs` output of any game on that map). Iterate there with full A/Bs:
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-mono variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train-mono --name mx-tethys-mono-<tag>`
   and read the full train suite (`maps/suites/mx/train`, 10,200 games, ~2-3 minutes of wall) for each version you
   would hand back, since maps without a Monolith must not lose. Run each in a tmux session named
   `mx-tethys-mono-<tag>`; wait with a background command, never a foreground sleep. Leave `--threads` off.
   `--debug` (both sides debug) when you need traces. Never use the dev, hold, conf1 or fin suites. Delete each
   `replays/batch-*` you create once you have read it (~3 GB a full suite). Another implementer runs A/Bs on the same
   box at the same time; that is fine.
4. Measure: Monolith captures a game by side, kills of it that the enemy then captured, rounds an op takes, crew
   deaths during ops, Prism Focus at r250 and r500 by side; and on non-Monolith maps, that nothing changed.
5. Watch fuel: OOF turns must stay near chy-ref's.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-mono variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when a version reads at least 51.5% on the full train suite over 10,200 games (with the Monolith subset
clearly up), or after at most six versions read on the subset, or when you have a clear diagnosis that the design
fails. Report through SubagentHandback: the variant path; the diagnosis of why operations ended in the reference;
each version's change and its subset and full-train reads with intervals and OOF; the mechanism counts; the
auditor's findings and fixes; the final diff stat. Save the final diff with
`diff -ruN bots/variants/chy-ref/src bots/variants/mx-mono/src > research/mx-tethys/patches/mx-mono.diff`. Keep
earlier versions as `bots/variants/mx-mono-vN` if they matter.
