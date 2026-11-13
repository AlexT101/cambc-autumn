# Brief k13: every champion's farm shuns a seen enemy Prism that can kill it

You are implementing a macro change to the Cambridge Battlecode C++ bot `charybdis` for the orchestrator of its macro
refactor. Read `/home/ubuntu/wt/mac13-kronos/AGENTS.md`, `cambc-rules.yaml` (Prism, cassi_and_issac, stun,
abilities, death, respawn, vision) and the existing variant `bots/variants/k8-avoid` (its diff against chy-ref is
`research/mac13-kronos/patches/k8-avoid.diff`; the source in `bots/variants/k8-avoid/src` is the post-audit
version: read it, it is your starting point). Work ONLY in `/home/ubuntu/wt/mac13-kronos`; do not touch
`/home/ubuntu/cambc-autumn` or other worktrees; do not commit. Never edit `bots/variants/chy-ref`,
`bots/variants/k8-avoid` or `bots/charybdis`. Off limits: `src/draft/`, emblem choices.
Variant: `./copybot variants/k8-avoid variants/k13-shun` (never copy `.cambc/`), then the edit.

## Why
In 1,024 mirror games the team ahead by 1.5x in gems at r300 wins 95%, and what separates the two by r300 is deaths
(0.83 against 2.89 a team, dead champion-rounds 46 against 153, gems lost 5 against 74). Of the 1,920 deaths by
r300, the enemy Prism killed 734; the Cassi/Issac pair is the most killed (547 pair deaths: both bodies off for 60
rounds, both bags to the killer), 214 of them by the Prism. On our own ground the pair loses both bodies at twice the
rate another champion loses one. The fallen body had seen its killer 2-6 rounds before in 450 of 557 known cases:
not an information problem; the farm keeps it working within the enemy Prism's reach. k8-avoid applied a farm
avoidance only to our Prism (outmatched by the enemy Prism): level. Here it applies to every champion the enemy
Prism can kill.

## Design
Generalise `prism_threat` (in `combat/prism_war.h`) from "our Prism outmatched" to "the enemy Prism's two-turn
burst (`prism_burst`, stun 1.5 x Focus + ground 1.0 x Focus, Durability `taken`) covers our health and shield":
- For a Prism of ours keep k8's test (`prism_outmatched_by`).
- For any other champion: `prism_burst(enemy Prism, us) >= our health + shield` (a kill in its two turns).
- For Cassi or Issac: either body's death kills both (rules), so the test uses the weaker of the two bodies: our own
  health, or the partner's believed health (+shield) if lower (`linked_partner`; an unseen partner: its last
  reading; if no reading, our own). Say what you did.
Everything else as k8-avoid has it: only while that enemy Prism was seen (or posted by comms) within
`capture_time` rounds; the reach is its cast reach + rounds since the sighting; groups with a camp tile in reach
are scaled out of the farm's choice unless every valuable group is in reach; not hit in passing; the takeover and
help paths skip them as in k8. Keep it one well-commented helper; no new constants.

## Stop condition
1. Build (release). 2. Spawn ONE read-only auditor subagent (tell it explicitly not to edit anything) to check the
diff against this brief and the rules (burst arithmetic, the pair's weaker-body test, no change when there is no
living enemy Prism or no recent sighting, the farm never left with no valid choice, fuel: the threat is computed
once per farm call, release builds unaffected); fix what it finds.
3. Smoke:
`source ~/venv/bin/activate && cd /home/ubuntu/wt/mac13-kronos && CAMBC_BIN=/home/ubuntu/cambc-autumn/tools/fastengine/runner/fastrunner FASTRUNNER_MODE=native PATH=$HOME/.cargo/bin:$PATH python tools/ab.py variants/k13-shun variants/chy-ref --no-test-draft --fuel 200000 --name mac13-kronos-k13-shun-smoke`
(256 ladder games): no failed games, no DRAFT-UNFINISHED / PLAN-CHECK, out-of-fuel turns within noise of chy-ref's.
One `--debug` smoke with a debug-only line `SHUN <round> <id> <enemy prism id> <burst> <our health>` printed once
per farm turn while the threat is on: report the share of champion farm turns it is on, by champion type. Delete
the smoke batches afterwards.
4. Save the diff to `/home/ubuntu/wt/mac13-kronos/research/mac13-kronos/patches/k13-shun.diff`
(`diff -ruN bots/variants/chy-ref/src bots/variants/k13-shun/src`) as soon as it builds, then audit and smoke.
Return what changed, auditor findings and fixes, smoke results and the firing rates. No large A/Bs.
