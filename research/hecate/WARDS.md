# hecate: wards (workstream C)

Why wards have not paid off, and what to change. Measured on 70 ladder games of hecate vs hecate-v7 (both sides;
`replays/orch/research/ward_value.py`, output in `ward_value_ladder.txt`) and on 814 top-10 and ladder games plus
3,362 older bulk games (`replays/orch/research/cdata_*.py`; `cdata_agg.py cdata_A.pkl` prints the team tables).

## Answer in short

- **Wards are a ~10% lever.** Ward-only targets are 9.1% of our attacks (Fish 7.2%, Mite 13.4%, Sneaky Bush Campers
  17.3%), so on attack we are already in the top-team range. The consumers (strike board, casts, stuns, `prey`,
  safety, comms) already read our ward's sight; leave them alone.
- **Our ward adds no range where it goes down.** It goes within 2 and sees radius 6, so all it sees is within 8 of us.
  It adds sight only from another viewpoint (inside a bush cluster, which is opaque from outside; round a wall) or by
  staying after we leave or die.
- **What is wrong is placement churn, mostly from one rule.** Every 20 rounds `place_ward` puts an off-bush ward on
  the tile within 2 farthest from spawn. That replaces 46% of our bush wards and caps ward life at 20 rounds.

## Findings

| | Top-10 teams | hecate |
|---|---|---|
| Wards per 100 alive champion-rounds | 2-4 (Fish 3.4, procless 2.1) | 6.0 (46,105 in 764k) |
| On a bush tile | 76-100% (8 teams 100%) | 48% |
| Ward age at a ward-only attack (quartiles) | 2 / 8 / 42 rounds; 34% older than 20 | 1 / 3 / 8; 3% older than 20 |

- **Value is in bush wards.** 98% of top-team ward-only attacks and 85-87% of ours use a ward on a bush. A bush ward
  enables 0.08-0.37 ward-only attacks; an off-bush ward 0.00-0.05 (our ~100k off-bush wards enabled 325 in all).
- **Churn (70 games):** of 46,105 placements, 21,983 on a bush. Off-bush replaces bush 10,219 times (46% of bush
  wards; 42% of off-bush wards). Bush replaces bush 11,489 times. Every off-bush ward comes from the periodic branch,
  since `ward_bushes` only picks bush tiles.
- **Defence:** 3,170 hits on us came from unseen tiles (413k damage), 2,481 from bushes. 1,111 came from a cluster
  within 2 of the victim, which it could have warded; its ward was ready for 136 (12%). That is about 900 damage a
  team-game: the ceiling for any defensive ward change.
- **Through others, little:** sightings through a ward lead to a hit within 5 rounds 2-7% of the time, against 20-34%
  for the champion's own sight. 25-45% happen while the owner is dead.

## The code today (checked)

- `place_ward` (bot.cpp:1654) runs at turn end (bot.cpp:3163, after `strike_after` at 3156) and first in
  `submit_here`. It tries `ward_bushes` (bot.cpp:1594): the bush cluster within 2 with the most tiles within 4 of here,
  skipping our own cluster and our ward's cluster, and replacing a ward in any other cluster without a comparison.
- If that places nothing, on rounds divisible by `params::ward_period` (20) it wards the tile within 2 farthest from our
  spawn (`Pathing::ward_targets`, used nowhere else). `ward_bushes` places nothing when there are no bushes near us,
  but also when our ward already watches them (`bushes_watched`, or the only candidate is our ward's cluster). In
  that case the periodic ward overwrites a bush ward that is doing its job. That is the churn.

## Proposals, ranked

### 1. Delete the periodic ward (S)

- **Change:** delete the `ward_period` branch of `place_ward`, `params::ward_period` and `Pathing::ward_targets`
  (~15 lines). `place_ward` becomes the guards plus `ward_bushes`.
- **Rests on:** off-bush wards enable 0.00-0.05 attacks each and add no range at placement. The branch causes 46% of
  bush-ward replacements and the 20-round age cap. On bushless maps we would place no wards, as Fish does.
- **Past record:** "a periodic ward rule" was level as an addition (48.7%, nemesis era). The SIMPLIFY keep note gives
  evidence only for bush wards. The removal has never been A/B'd.
- **A/B:** a deletion, kept if level. Expect level to +2, on bushy maps only. In `ward_value.py`: bush share near 100%,
  ward readiness at bush hits above 12%, older wards at ward-only attacks. Watch unseen-tile damage on bushless maps.

### 2. Place the ward at turn start, before `decide` (S-M; needs a probe)

- **Change:** in main.cpp, after "comms receive" and before "decide", call `place_ward` and, if it placed a ward,
  `world->observe()`. Keep the turn-end call; it now acts only when the ward is still ready, for example after a walk
  into reach of a new cluster.
- **Rests on:** where we end turn T is where we start T+1, so the tile choice is the same. But the sight now arrives
  before this turn's strike, casts and step guard instead of a turn later. Basic attacks and unit spells need a
  visible target, and an enemy in a bush is visible only from inside its cluster. There is no trigger condition and no
  model of where unseen enemies might be.
- **Precondition:** a probe that a ward's sight counts on the turn it is placed (no probe tests it; walking and hidden
  blockers do update sight mid-turn). Add the rule to the YAML and the probe to the README's table. If the probe fails,
  drop the proposal.
  **Met:** `probe-ward-sight` shows ward sight counts in the turn it is placed (YAML `wards.vision`).
- **Fuel:** one observe on a ward turn (at most one turn in 10), bounded.
- **Fits workstream A:** STRIKE-SEARCH.md lists "a ward placed first" as out of its scope. This runs before the search
  and only changes what is visible, so it feeds the search more targets.
- **A/B:** on top of 1. Expect +0 to +1 (the defensive ceiling is about 900 damage a team-game). In `ward_value.py`:
  more ward-only attacks at ward age 0, fewer hits from bushes within 2.

### 3. Replace a ward only when the new cluster watches more (S-M; after 1)

- **Change:** in `ward_bushes`, score a cluster by its tiles within 4 (ability range) of here plus its tiles within 4
  of our work tile: the claimed group's centre (`memory.claim`) or `memory.wait_altar`. Score our ward's cluster the
  same way (0 if it is off a bush), stop excluding that cluster, and place only when the best candidate scores higher.
- **Rests on:** one ward, never expiring, so a placement is worth V(new) − V(old). The work-tile term values
  persistence: a ward on our camp's bushes survives the walk to the altar and back.
- **Caveat:** most of the age gap (3% vs 34% of wards older than 20) is the periodic cap that proposal 1 removes.
  Measure 1 first; build this only if bush→bush replacements (11,489 now) remain a large share.
- **A/B:** on top of 1. Expect level to +1, on bushy maps only. Fewer bush→bush replacements and longer ward life.

## Rejected

- **Altar, chokepoint, tribute-denial or scouting wards:** no value in the data; tribute sightings through a ward are
  stopped 2-7% of the time. They would also need named situations.
- **A ward triggered by tracked enemies' possible tiles** (the first draft of 2): it needs a belief model of unseen
  enemies, and the turn-start ward covers the same case with no trigger.
- **Consumer changes** (targeting, safety, comms) and **modelling unseen enemy wards:** the consumers already read ward
  sight, and unseen enemy wards are unknowable (`warded()` covers visible ones).
