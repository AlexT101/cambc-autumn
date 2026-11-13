# Line B: the team answers a threat to its Prism (muster or early leave)

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 2,720 games, early first Prism deaths, r <= 300, 552 deaths)
- The first Prism death decides the game: the victim's team loses 91-92%.
- Mechanism: our Prism keeps farming after enemies near it outnumber our bodies near it. At the moment it became
  outnumbered it was on F (farm) in 81%; it stayed outnumbered a median 6 rounds (IQR 3-11) before the first hit. Its
  nearest ally was a median 2 tiles away; 1.9 allies within 8 against 3.2 enemies. **Allies within 16 plus the Prism
  could have matched the enemies within 8 in 91% of cases**, but 55% of those allies' branches were F, and in 83% of
  deaths allies dealt under a third of the enemy's champion damage in the last 15 rounds.
- After the first hit, retreat does not open distance (everyone walks one tile a turn; a stun or an exclusive attack
  costs a step): median net progress home 0.125 tiles a round; 49% flip between R and other branches 3+ times.
- Base rates (Prism-rounds r <= 300, death within 15): no enemy within 8 0.1%; 2+ enemies, not outnumbered 1.9%;
  outnumbered within 8 5.8%. Being outnumbered nearby, not exposure as such, is what kills.
- Earlier programmes: static escorts (allies always guarding a bag) lost or were level because they idled the strong
  bodies; "caution and yielding" lost. So the response must be **on demand** (only while the threat exists, only by
  allies that can arrive in time) and must prefer restoring the majority (fighting with numbers) over yielding.

## Design
Three pieces, one mechanism: the team reacts to a local majority against its Prism before the first stun.

1. **Threat read (Prism's turn).** From the safety model, not a body count alone: the local fight around our Prism
   with the enemies that could strike it within the next few turns (visible, and credible unseen ones as safety
   already weights them) against our bodies that can be within `safety_params::fight_ally_radius` of it in the same
   time. Use the existing fight simulation (`Trade`, `Safety` in model/safety.h/.cc) where it fits; the horizon is the
   enemy's turns to reach striking range of the Prism (walk + its reach: stun range 4 + one step), so the read is
   made while the enemy is still closing, not once in range. Three outcomes:
   - fight won with the allies already near: nothing changes;
   - won only with allies that must come (they can arrive before the enemy strikes): **muster**;
   - lost even with every ally that can arrive in time: **leave now**.
2. **Muster (allies' turns).** The Prism posts a muster call through comms (the 8 shared bytes or the priority
   payload, see model/comms.h/.cc; positions are already posted, so the call may only need a fresh bit and the round).
   An ally that reads a fresh call and can reach the Prism's fight radius before the enemy can strike it (its path
   steps against the enemy's turns, both from beliefs) drops farming and walks to the Prism, then lets the existing
   combat code fight. Allies that cannot arrive in time, or that are in a tribute channel, carrying a winning bag, or
   otherwise committed by a higher branch in `decide()`, ignore it. Cassi and Issac count as two bodies but die
   together: an ally that is itself outnumbered on the way does not come. A muster ends when the Prism stops posting
   it (threat gone, fight joined and won, or the Prism has left).
3. **Leave now (Prism's turn).** When the read says lost, the Prism leaves before it is struck: it walks toward the
   nearest allies who restore the majority, else home (existing escape/retreat pathing, model/escape.cc and the R
   branch, is the tool), and it stays committed while the threat stands (no flip back to F because one turn reads
   quiet: keep it until the enemies' reach no longer covers it for as many turns as an ability cooldown, read from the
   champion facts, not a hand-picked number). It does not trade hits on the way unless the trade kills.

Every quantity comes from the rules and the bot's models (reach, walk speed, cooldowns, fight simulation, path steps).
No magic numbers. If a threshold is unavoidable, derive it and say how in one comment.

Where to hook: `decide()` in `src/bot.cc` takes the first branch that applies (branch letters in the D lines). Add one
branch letter for the muster walk (e.g. `M`) and reuse R for the leave, or add a letter, and print it in the D line so it
shows in debug replays. Look at how `combat/support.cc` (Willow's support mailbox), `comms::chasing` and farm's
`help_radius` work before writing new plumbing: reuse what exists. The muster also applies to any other body the
read flags (e.g. Cassi and Issac, half of all deaths) only if it falls out of the same code for free; the Prism is the
target of this line.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-must` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-must`. `test_draft` stays off.
2. Build: `cambc build bots/variants/mx-must --release` (and without `--release` for debug traces).
3. Iterate with full A/Bs on the train suite (10,200 games, about 2-3 minutes of wall each):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-must variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-must-<tag>`
   Run each in a tmux session named `mx-tethys-must-<tag>`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. Add `--debug` when you need D lines. Never use the dev, hold, conf1 or fin suites.
   Delete each `replays/batch-*` you create once you have read it (each is ~3 GB).
4. Check the mechanism fires: count muster calls, joins and leaves per game in a debug A/B, and compare Prism deaths
   (and early Prism deaths) per game against chy-ref's side. Research scripts in `research/mx-tethys/scripts/`
   (`prism_death.py`, `prism_mech.py`, `prism_mech_rates.py`, `cohesion.py`) read the `.analysis` output of
   `node tools/replay/extract.mjs` (see tools/replay/README.md; use `--threads 40` or fewer).
5. Watch fuel: OOF turns in the summary must stay near chy-ref's. Cache per-turn reads; a fight simulation per ally
   per turn is too costly, so the Prism computes the read once and posts it.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-must variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when a version reads at least 51% on train over 10,200 games, or after at most six train A/Bs of real
versions (not counting crash/bug reruns), or when you have a clear diagnosis that the design fails. Report through
SubagentHandback: the variant path; what each version changed and its train read with interval and OOF; mechanism
counts (musters, joins, leaves a game; Prism deaths and early Prism deaths a game, CAND side vs REF side); the
auditor's findings and fixes; and the final diff stat. Leave the best version in `bots/variants/mx-must` (keep
earlier versions as `bots/variants/mx-must-vN` if they matter).
