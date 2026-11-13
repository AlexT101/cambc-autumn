# Line C: the Prism duel in macro (keep clear of an enemy Prism that wins the duel, seek one that loses it)

You are an implementation subagent for TETHYS, the orchestrator of a macro refactor of the Cambridge Battlecode bot
charybdis. Worktree `/home/ubuntu/wt/mx-tethys` (branch `mx-tethys-20261113`). Work only there; never touch
`/home/ubuntu/cambc-autumn` (read-only: you may read its committed files) or other worktrees under `/home/ubuntu/wt/`;
never commit or push. Read `AGENTS.md`, `cambc-rules.yaml` and `docs/api/cpp.md` first. C++ only. Comment only
counterintuitive behaviour, concisely.

## Evidence (charybdis mirror, 2,720 games)
- The enemy Prism lands ~55% of all kills (it kills 60% of our Cassi/Issac, 73% of our first-dead Prisms). The first
  Prism death decides the game (victim's team loses ~92%).
- **Relative Focus decides the duel.** With both Prisms alive at round 250 and the Focus ratio (higher/lower) at 1.6+,
  the lower-Focus Prism dies first in 48% of games, the higher in 11%, and the higher-Focus team wins 80%. At 1.3-1.6:
  32% / 20%, 62%. At 1.0-1.1 it is a coin flip (26 / 22, 50%). Same picture at round 150.
- Prism Focus is 90 + 8 a level plus 1.5 a carried gem (rules); its stun does 1.5x Focus and removes the target's next
  turn, its ground spell 1x Focus. A stun-then-spell combo on a stunned target is 2.5x Focus before the target can act.
- Early first Prism deaths: the victim was on a farm branch at first contact in ~80%, and retreat after contact does
  not open distance (everyone walks one tile a turn; net 0.125 tiles a round). Contact is what has to be decided, in
  macro, before it happens.
- The farm (`economy/farm.cc`, `farm_turn`) prices groups by value over time with static side weights
  (`exposure()`, `home_ground`); it prices no enemy threat at a group. Safety (model/safety.h/.cc) prices the next
  turn or two, after contact. So the enemy Prism's whereabouts and its Focus relative to ours never enter where a body
  chooses to be.
- Priors: unconditional "avoid enemy Prisms" lost 6 points; caution and yielding lose everywhere; a control-map farm
  reweighting by team mass (Line A, this programme) was level at best and lost badly when it scaled risk by stake
  (it starved the Prism). Static side weights sit at their optimum. So this must be **conditional and two-sided**:
  avoidance only where the duel is lost, and the gain side (seeking a losing enemy Prism) is half of the point.

## Design
1. **Enemy Prism belief.** Its position (visible, or last seen plus the set of tiles it may be on, as `World`/`Safety`
   already track unseen enemies), its Focus (last read; a seen bag, and its growth since from what the enemy has been
   collecting, if a clean estimate exists, else the last read), health, and stun cooldown. If the enemy drafted no
   Prism, nothing changes.
2. **Duel read for one of our bodies b against the enemy Prism P**, at a tile and from b's current state: does P's
   combo (stun at 1.5x Focus, b's lost turn, then its next damage) kill b before b and the allies that will be beside it
   kill P? Reuse the fight simulation (`Trade`/`Safety::fight`) or derive it directly from the two champions' stats
   and the rules. For our Prism against theirs it is the Prism duel: whoever's combo kills first, with turn order.
   Cache it per turn (it changes only with health, Focus and cooldowns).
3. **Farm pricing.** For each candidate group, the chance P reaches b's stand during b's stay (travel + clear +
   capture), from P's believed tiles and its walk (`enemy_reach`, `Safety::may_reach_within`-style reach):
   - duel lost: the group's value drops by that chance x what b's death costs (its life and its bag, as the bot already
     prices them; for the Prism its bag with `prism_premium`, the Focus it compounds);
   - our Prism, duel won: the group's value rises by that chance x what P's death is worth to us (P's bag, taken by
     the killer, with our premium if our Prism lands it, and its life);
   - neither when P is dead or certainly too far: the static weights alone, unchanged.
   Keep the static side weights; this is a term on top, not a replacement. Every quantity from the rules and the
   bot's existing models; no new hand-picked constants. Keep the farm's prune bounds valid: anything that can raise a
   group's value must be covered by the bound the prunes use (`exposure_most`, `PreUpper`), or the prunes cut good
   groups.
4. **Hunt (our Prism, duel won).** When the enemy Prism is in sight or recently seen nearby and our Prism wins the duel
   (with the allies beside it counted), it goes for it: the chase branch (`prey()`, `chase()` in combat/fight.cc) may
   already take it; check whether prey() refuses it and why, and widen it only by the duel read.

Measure each part on its own as well as together: (a) avoidance only, (b) hunt + seek only, (a)+(b).

Where to hook: `decide()` in `src/bot.cc` takes the first branch that applies (branch letters in the D lines: - none,
C chase, A attack, R retreat, F farm, B bank, ...). Farm's group values are in `farm_turn`.

## Off limits
`draft/` and which emblem a champion builds toward. Never edit `bots/variants/chy-ref`.

## Work
1. `./copybot variants/chy-ref variants/mx-duel` from the worktree root (it leaves out `.cambc/`); work in
   `bots/variants/mx-duel`. `test_draft` stays off.
2. Build: `cambc build bots/variants/mx-duel --release` (without `--release` for debug traces).
3. Iterate with full A/Bs on the train suite (10,200 games, about 2-3 minutes of wall each):
   `source ~/venv/bin/activate && cd /home/ubuntu/wt/mx-tethys && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/mx-duel variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mx/train --name mx-tethys-duel-<tag>`
   Run each in a tmux session named `mx-tethys-duel-<tag>`; wait with a background command, never a foreground sleep.
   Leave `--threads` off. `--debug` (both sides debug) when you need D lines. Never use the dev, hold, conf1 or fin
   suites. Delete each `replays/batch-*` you create once you have read it (~3 GB each).
4. Check what changed, from replays (`node tools/replay/extract.mjs`, see tools/replay/README.md, `--threads 40` or
   fewer; scripts in `research/mx-tethys/scripts/`: `prism_race.py`, `prism_death.py`, `all_deaths.py`, `kills.py`):
   Prism deaths and kills a game by side, first Prism death split, our Cassi/Issac deaths to the enemy Prism, captures
   by side of the map, and how often the new term changed the farm's choice. When a version loses, find what the
   bodies stopped doing (farm time, captures, deaths, bags) before changing it.
5. Watch fuel: OOF turns must stay near chy-ref's.
6. Before returning: spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) to check the
   change against this design and the rules for bugs; fix what it finds; build; run the smoke
   `py tools/ab.py variants/mx-duel variants/chy-ref --no-test-draft --fuel 200000` (256 ladder games, same env
   prefix): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK.

## Stop condition
Return when a version reads at least 51.5% on train over 10,200 games, or after at most six train A/Bs of real
versions (not counting crash/bug reruns), or when you have a clear diagnosis that the design fails. Report through
SubagentHandback: the variant path; each version's change and train read with interval and OOF; the mechanism
counts above, CAND side vs REF side; the auditor's findings and fixes; the final diff stat. Save the final diff with
`diff -ruN bots/variants/chy-ref/src bots/variants/mx-duel/src > research/mx-tethys/patches/mx-duel.diff`. Keep
earlier versions as `bots/variants/mx-duel-vN` if they matter.
