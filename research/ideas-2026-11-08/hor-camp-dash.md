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

Against oc-base25 (v87), own drafts, real fuel, release, screen suite v87hor-scr-1241 (SPRT 0.50/0.5025, alpha 0.05).
Decisive = map pairs whose two games the same bot won (`~/tmp-offload/v87hor/bin/flips.py`); spar = `spar_ab.py`
against a release oc-base25 copy (live drafts, ladder maps).

| arm | screen | decisive pairs (+ -) | spar |
|---|---|---|---|
| v87-cd-k4 | 49.9% of 21,100, H0 | 378 395 | - |
| v87-cd-k3 | 49.8% of 16,952, H0 | 323 349 | -0.12 (±0.97), flips +116 -124 |
| v87-cd-k3h6 | 50.0% of 25,634, H0 | 431 439 | - |
| v87-nh-6-3 | 50.7% of 13,052, H1 | 431 344 | -0.53 (±1.06), flips +215 -250 |
| v87-nh-6-2 (= 468) | 50.5% of 18,543, H1 | 518 434 | -0.92 (±1.20), flips +167 -228 |
| v87-nh-5-2 | 50.3% of 33,744, H1 | 795 700 | -0.24 (±0.97), flips +142 -158 |
| v87-nh-7-2 | 50.24% of 60,475, H1 | | -0.96 (±1.17), flips +176 -240 |
| v87-fs-enemy | running (50.30% at 83k, LLR +2.67) | | -0.83 (±3.15), flips +804 -859 |

**Contested camp landings: rejected.** The mechanism does what it should (k3 takes the 5-6 band from 13% to 19% camp
landings, 7-8 from 40% to 49%), but it doesn't win. Each cd arm changes 7-8% of map pairs and splits them evenly, on
ladder-shaped and other maps alike. The one spar agrees. Health gating (k3h6) and a wider clearance (k4) don't help.
Mite's higher contested-landing rate is a habit, not a lever: on our bot, the extra contested landings don't turn
into results, so the stand-down costs little.

**468's hurt floor, a threshold family:** stricter is better on the screen (x3 at 0.6 > x2 at 0.6 > x2 at 0.5 >
x2 at 0.7). The gain sits mostly off ladder-shaped maps: ladder pairs net +0.36/+0.59/+0.59 pair points, against
+1.1 to +2.5 on other generators. The spar (ladder maps, live drafts) is slightly negative for both arms read so far.
nh-5-2 gets no gates: it is the weakest sibling of the same mechanism, and at most one of the family goes live.
nh-6-3 leads, with nh-6-2 as its comparison. At 22:00, interim: held out nh-6-3 50.43% of 19.8k (LLR +2.50 of the
±4.595 needed) and nh-6-2 50.09% of 14.5k (-0.23). Direct panel: 51.0% and 50.75%. Varied: 50.0% and 50.2%,
not H0. 2x fuel: 50.3% for both.

**nh-6-3's gates (2026-11-09 00:27): it meets the live bar, queued** (live-queue priority 48, "base oc-base25; pair vs v87").

| gate (nh-6-3 against oc-base25) | result |
|---|---|
| screen v87hor-scr-1241 | 50.67% of 13,052, H1 |
| held out v87hor-held-1242, alpha/beta 0.01 | 50.30% of 62,879, LLR 4.62 of 4.595, **H1** |
| 2x fuel, scr-1241 | 50.23% of 65,018, H1 |
| varied v87hor-varied-1243, 0.4975/0.50 | 50.05% of 20,480 (suite done), LLR +1.35, undecided, not H0 |
| old panel (astraeus-td/proteus-td + direct), 0.4975/0.50 | pooled +0.93 pts of 61,440 units, LLR 30.2, H1; direct 51.15% of 40,960 |
| spar (live drafts, ladder maps) | -0.53 (±1.06) |

The ladder-map caveat doesn't replicate on the held out: ladder-shaped pairs net +0.71 pair points (12.1% decisive),
other generators +0.60, mutants +0.43; at 2x fuel ladder +0.15. Only the spar stays slightly negative, inside its noise.
nh-6-2 (= 468) runs behind it everywhere: held out 50.20% of 63k (LLR +2.23, still running), 2x 50.18%, panel
+0.80 pts (H1), varied H1, spar -0.92. **nh-7-2 gets no gates:** its screen (50.24% of 60k) and spar (-0.96) are the
family's weakest after nh-5-2, and the family has one live slot, now nh-6-3's. The floor's constants are left to
the live verdict: if nh-6-3 wins live, an SPSA fit of (fraction, multiple) is the next step, not more single arms.
fs-enemy's screen is near a decision; on H1, chain5.sh gives it held out (held2-1245, alpha 0.01), 2x, varied and
dpanel.
