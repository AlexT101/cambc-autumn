# Heart of Ruin on v87: camp dashes with enemies about, and 467/468 retried (v87hor, 2026-11-08)

Base `bots/variants/oc-base25` (= v87). Seeds 1240000-1249999. Scripts in `~/tmp-offload/v87hor/bin/`
(`horlive.py`, `missdash.py`, `earn.py`, `branch.py`), big files in `~/tmp-offload/v87hor/`.

## Rules that matter

- The landing (slot 1) deals 1.5 x Focus x the passive to enemy champions *and camps* within 1 of the landing tile,
  and stuns them; a stunned camp skips its next attack. Cooldown 8 rounds. It is not walk-exclusive.
- Damage or a stun wakes the whole group. Monsters attack the nearest champion of either team.

## Live: what our HoR does that Fish's and Mite's don't (v86-v89 scrims, 1,765 decoded games)

Per HoR body, first 400 rounds, per 100 alive rounds (`horlive.py`; games where both teams have HoR read the same):

| | Fish | Mite | ours vs Fish | ours vs Mite |
|---|---|---|---|---|
| gold earned by r200 | 128 | 176 | 130 | 131 |
| gold earned by r400 | 298 | 393 | 288 | 266 |
| camp dashes | 3.7 | 4.6 | 3.2 | 3.3 |
| travel dashes | 5.1 | 5.6 | 6.9 | 7.0 |
| champion dashes | 0.77 | 0.69 | 1.01 | 0.86 |
| camp damage dealt | 1,669 | 2,000 | 1,594 | 1,623 |
| share of it from dashes | 0.52 | 0.58 | 0.45 | 0.45 |
| camp damage taken | 899 | 829 | 684 | 692 |
| champion damage taken | 487 | 569 | 518 | 468 |

- Mite's HoR camp-damage edge (+~300 per 100 rounds) is about one extra landing (~270 each): all of it dashes.
- **Where the landings are missed** (`missdash.py`): rounds starting with the dash ready within 3 of a live awake
  Wolf/Elk/Golem. With no enemy within 8 every team lands on camps 82-87% of the time. With an enemy about it splits:

  | nearest enemy | Fish | Mite | ours vs Fish | ours vs Mite |
  |---|---|---|---|---|
  | 3-4 tiles | 13% | 31% | 11% | 13% |
  | 5-6 | 31% | 44% | 11% | 16% |
  | 7-8 | 53% | 70% | 52% | 44% |

  Ours spends 64-68% of the 5-6 rounds with no dash at all. The situation comes up ~4 times a game by r400 (301 of
  ~460 HoR games).
- **Why:** `camp_cast` returns nothing while `engagement_near` (an enemy within cast reach + 1, or whose strike
  reaches us) holds, and the fight planner never takes a landing that hits camps but no foe. In a debug check
  (`branch.py`) the missed contested rounds split farm branch 46-52%, chase 18-24%, retreat 16-17%.
- **Earnings** (`earn.py`, r ≤ 400): Mite's HoR holds 5.9 captures (3.3 of attacker groups) against our 4.8 (2.4),
  for 357 capture gold against 232. That is the team's capture routing (carry.md), not a HoR mechanic.

## Arms (each oc-base25 + its diff only)

**cd, contested camp landings** (`combat/abilities.cc` `contested_landing`, `params::hor_contested_*`): with
`engagement_near` true, a HoR may still land on its farm group's monsters when no visible enemy is within `near` of
it or of the landing tile, above a health share. Only the landing slot is considered then.

| arm | near | health |
|---|---|---|
| v87-cd-k4 | 4 | - |
| v87-cd-k3 | 3 | - |
| v87-cd-k3h6 | 3 | ≥ 0.6 |

Mechanism check (fresh-1240000/1, 1,024 games each against oc-base25): k3 moves the 5-6 band from 13% to 19% camp
landings and 7-8 from 40% to 49% (k2 reads the same as k3, so it isn't run). In the farm branch the relaxed check
casts in 133 of 149 contested calls; the rest of the gap is turns spent in chase and retreat.

**nh, 468's hurt landing floor** (`landing_floor`): below `hor_hurt_fraction` of max health a landing on enemies
needs `hor_hurt_landing` x 250. v87-nh-6-2 (468 as merged), -5-2, -7-2, -6-3.

**fs-enemy, 467 for enemy Hearts of Ruin only**: the fight simulation averages the passive over the remaining health
for enemy HoRs only (467 did ours and theirs; ours alone, hor-b-sim, was 50.14% of 80k on oc-base25). v90's loss to
Mite sat in games where only Mite had HoR. 467 itself is v88 = oc-base26 exactly, so it can't be re-gated live.

## Results

Against oc-base25 (v87), own drafts, real fuel, screen suite v87hor-scr-1241 (SPRT 0.50/0.5025, alpha 0.05):
- v87-nh-6-3 (hurt below 0.6, landing floor x3): 50.7% (49.8-51.5) of 13,052, LLR 2.98, H1 (20:22).
- v87-nh-6-2 (= 468, floor x2): H1, LLR 2.96 of 18,543 (20:46).
- Other six screens (cd-k4, cd-k3, cd-k3h6, nh-5-2, nh-7-2, fs-enemy) still running.
Both H1 arms get the same phase 2 on the same suites, own seeds: held out v87hor-held-1242 at alpha 0.01
(bounds ±4.595), 2x-fuel screen, varied v87hor-varied-1243 (0.4975/0.50), panel v87hor-panel-1244 x3, spar.
(pending)
