# Brief k16: our Prism's chase knows its burst (every target, not only the enemy Prism)

You are implementing a macro change (chase and retreat at the large scale) to the Cambridge Battlecode C++ bot
`charybdis` for the orchestrator of its macro refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`,
`cambc-rules.yaml` (Prism, stun, abilities, combat modifiers, death, cassi_and_issac) and the study
`research/mac13-kronos/s2/README.md` (kill conversion; its "most promising fixes" 1 and 2 are this brief). Also read
`bots/variants/k8-hunt` (its diff: `research/mac13-kronos/patches/k8-hunt.diff`): it relaxed `preyable` only for an
enemy Prism our Prism dominates, and keeps `combat/prism_war.h` (the duel model: `prism_burst`, `prism_covers`).
Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch `/home/ubuntu/cambc-autumn` or other worktrees; do not
commit. Never edit `bots/variants/chy-ref`, `bots/variants/k8-hunt` or `bots/charybdis`. Off limits: `src/draft/`,
emblem choices. Variant: `./copybot variants/k8-hunt variants/k16-lethal` (never copy `.cambc/`), then the edit.

## Why
Early deaths decide the mirror: the team ahead 1.5x in gems at r300 wins 95%, and by r300 it has 0.83 deaths against
2.89 and 2.6 kills against 0.7; the enemy Prism makes most kills. s2: our Prism gets 11.2 kill chances a team-game
and converts 2.6; the biggest decision-side miss is `preyable`'s healthy-off-ground clause (`combat/fight.cc` ~756:
a target over 0.45 of its max health, on its own ground, with no bag or hold, is refused), although 6.0 of the 11.2
are at 90%+ health and burst-killable: the clause's logic (a beaten enemy escapes a step across the line) does not
hold for a target our two-turn burst kills before it gets two steps.

## Design
1. In `preyable`, for our Prism: a target counts as hurt for that clause when our two-turn burst covers its
   effective health (`prism_burst(me, e) >= e.health + e.shield`; for Cassi or Issac the weaker body's, as
   `partner_bound` / `useful_damage` model it, if simple; else the target's own). Every other test (enemy spawn edge,
   the fight sim, `escapes`, `pack_covers`, chase verdicts) still applies. k8-hunt's enemy-Prism clause stays.
2. Narrow lethal stun before a retreat (s2 fix 2, narrow version): in decide's `leave` branch (`bot.cc` ~469-478),
   for our Prism only: if a visible enemy within our stun's range now (no walk) is covered by our burst, run the
   strike search (as `follow::binding` does) before the retreat, so the stun lands first. Only when the stun is
   ready.
No new constants.

## Stop condition
1. Build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check the
diff against this brief and the rules (burst arithmetic, the pair test, no change for non-Prism champions, the
leave branch still retreats when the search does not act, no thrown-error loops, release builds unaffected); fix
what it finds.
3. Smoke:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/k16-lethal variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-k16-lethal-smoke`
(256 ladder games): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK, out-of-fuel turns within noise. Delete the
smoke batch afterwards.
4. Save the diff to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/k16-lethal.diff`
(`diff -ruN bots/variants/chy-ref/src bots/variants/k16-lethal/src`) AS SOON AS IT BUILDS (the orchestrator starts
screening from the diff's appearance), then audit, fix (re-save the diff) and smoke. Return what changed, auditor
findings and fixes, smoke results. No large A/Bs. Be quick: this is a bounded change.
