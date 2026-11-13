# Brief C1: cooldown economy, free casts on camps (implementer)

You are an implementation agent for the CASTOR macro programme on the Cambridge Battlecode bot `charybdis` (C++).
Work only in the worktree `/home/ubuntu/wt/mac13-castor` (branch `mac13-castor-20261113`; never push, never touch
`main` or `/home/ubuntu/cambc-autumn` except to read). Read `/home/ubuntu/wt/mac13-castor/AGENTS.md` first and follow
it (it says to read `cambc-rules.yaml`: do). The C++ API is `docs/api/cpp.md` and `sdk/cpp/cambc.h`.

## Setup
- `cd /home/ubuntu/wt/mac13-castor && ./copybot variants/chy-ref variants/c1-casts` (never copy `.cambc/`). Edit only
  `bots/variants/c1-casts/src`. Never edit `bots/variants/chy-ref` (the frozen reference) or `bots/charybdis`.
- Don't change drafts (`draft/` picks) or emblem choices (which emblem a champion builds toward).

## The idea (why)
Abilities are the champions' strongest output and are cooldown-limited (cast in round t, ready again t+8; one cast a
turn; damage spells exclude walking: not after a walk, and no walk after). Camps never regenerate, so damage on a
group we will clear is never wasted. Measured on 1,024 charybdis mirror games: Prism (in ~90% of games, the team's
farm engine and weapon: ground 1.0x Focus 3x3, unit stun 1.5x Focus, Focus = base + shards + 1.5 per carried gem)
casts 9.1 times per 100 alive rounds against a cap of 25; when a slot is ready a live camp is within 4 on 32% of its
turns, and it casts on only 31% of those. Prism's turns: walking 48%, hitting camps 13%, holding captures 8.8%,
idle 4.6%. So most of the spell capacity is unused while the Prism stands still (holds, waits) next to live camps it
is not currently farming. The farm only casts at its own target group (`combat/abilities.cc` `camp_cast` via
`cast_at_camp` from `economy/farm.cc`; `cast_at_camp_on_approach`).
A prior attempt (jn-art, another programme) cast at own-side or claimed camps on *walking* turns: casts rose only
8.0 -> 8.8 per 100 rounds and it read 47.9% on 795 games (pre-audit, noisy). A cast on a walking turn costs the step;
that is the part to avoid.

## The design
Add a "free cast" step for every champion with damage spells (Prism, Stellar, Cassi, Marcella's unit spell, Tavi,
Ren, Ryth's ground stun, Heart of Ruin's landing only if natural), taken on turns where the cast costs no walk:
- **When:** the turn will not walk anyway: holding a capture (the cast keeps the tile, so it keeps the hold),
  waiting (beside an ally's tribute, at an altar, for a respawn, for a crew), already attacked in place, guard turns,
  channels excluded (none can be cast while channelling). Also on a walking turn only when the cast's value beats the
  step's (the step's value = one round of our income rate on the goal; the repo has income-rate helpers in
  `economy/shop.cc` / `farm_step_value`); keep this conservative.
- **Target value (from the rules, not hand-set):** damage dealt (min(raw x modifiers, member health)) times the
  group's reward per health point (gems + gold at the bot's gold price, over the group's live health), only for
  groups our team will clear: our claim, an ally's claim, or groups on our side / mid that are not claimed by enemies
  visibly working them. A kill of a harmless member (gem/gold cluster) counts fully.
- **Wake cost:** damage wakes every asleep member of its group, and awake monsters hit the nearest champion within
  their own range each camp phase. Prefer tiles/targets where no woken striker reaches us (ground spells reach
  range 4 + radius 1; most strikers reach 3-5); otherwise price the fire we would take until we leave, using the
  existing camp-damage helpers (`Safety::camp_damage`, `min_camp_damage`). Never wake a group that would hit an ally
  holding a capture or a fragile ally.
- **Readiness cost (keep the duel weapon):** a slot on cooldown is unavailable for 8 rounds. The Prism's duel
  opener is its stun; keep any stun slot (and for Prism both slots) ready while an enemy champion could be in our
  strike reach before the slot is back (use the bot's enemy reach / possible-position machinery:
  `model/enemy_reach.h`, `Safety`, `World::enemies[].possible`, the `engagement_near` check in camp_cast). Derive the
  horizon from the cooldown (8 rounds) and enemy walk/dash speed, not a guessed radius. A ground spell without a
  stun can be spent more freely, but not when an enemy is already within its reach horizon.
- Don't break holds, the strike search's own casts, heals/shields, or the Prism-Willow support code; run the free
  cast after the strike search and the turn's goal step, in `act()`'s turn-end steps (see `bot.cc`), guarded by the
  usual fuel checks (`fuel_ok`, `room(...)`).

## What to measure
Use debug traces (`debug_block({ printf(...); })`, never plain printf) for: free casts per champion type, their
target kind and value, wake fire taken, and Prism casts per 100 alive rounds. On the study suite
(`maps/suites/mac13/study`), a debug A/B gives traces in the replay zips (`team-a.stdout`):
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-castor && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c1-casts variants/chy-ref --no-test-draft --fuel 200000 --suites maps/suites/mac13/study --debug --name mac13-castor-c1-dbg`
(`tools/replay/debug_lines.py PREFIX -- replays/batch-...` counts lines). A farming check against an idle opponent:
`py tools/solo.py variants/c1-casts variants/chy-ref --name mac13-castor-c1-solo --suites maps/suites/mac13/study --one-side --fuel 200000`.
Run long commands in the background or tmux (sessions named `mac13-castor-c1-*`); foreground sleep is blocked.

## Before you return
1. Spawn a **read-only** auditor subagent (tell it explicitly not to edit anything) with the design above and your
   diff (`diff -ru bots/variants/chy-ref/src bots/variants/c1-casts/src`) to check it against the design and the rules
   (`cambc-rules.yaml`) for bugs. Fix what it finds.
2. Make sure the bot builds, and play the smoke:
   `CAMBC_BIN=... FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH py tools/ab.py variants/c1-casts variants/chy-ref --no-test-draft --fuel 200000 --name mac13-castor-c1-smoke`
   (256 ladder games): no failed games, no `DRAFT-UNFINISHED` / `PLAN-CHECK`.
3. Save the diff to `research/mac13-castor/patches/c1-casts.diff`. Don't commit; don't run the 10k A/B (the
   orchestrator does). Kill any tmux session you started.

Stop when the design is implemented, audited, builds and passes the smoke. Return: what you changed (files,
functions, the gates and their derivations), the debug measurements (casts per 100 rounds by type before/after, wake
damage, free casts by turn kind), the solo result, the smoke win rate, and anything you were unsure about.
