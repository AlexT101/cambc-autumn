# Heart of Ruin's passive: farming low, fight timing, exact valuation (ocean = oc-base25, 2026-11-08)

Heart of Ruin (HoR) deals all its damage x (1 + 0.5 x missing health fraction); shields don't count as health. The
idea: play to the passive, farming lower and engaging hurt, and put the passive into every estimate.

## How ocean plays HoR now (oc-base25)

- **The passive at current health is already in every immediate estimate.** `ChampionBelief::scale` =
  `damage_scale(health) x dealt` feeds `hit_strength`/`hit_focus` (strikes, lethal checks, the fight simulation),
  `camp_scale` (camp clear times), plan.cc's own strength, and the engine's `my_damage` (landing values). plan.cc
  also raises an enemy HoR's damage on leaves that hurt but don't kill it.
- **Not modelled:** the passive rising *during* a clear or a fight. The fight simulation holds a HoR's damage at its
  start-of-fight passive; averaged over the health it has left (a fight to the death) the passive is
  1 + 0.5 (1 - h / 2 max): 1.25 from full health against 1.0 now. Farm clear estimates hold it at the current health.
- **Thresholds** (no HoR-specific ones): recall line 0.315 while an enemy may reach within 8 steps, else 0.109
  (`recall_line`); farm spends health above that line / `camp_risk` 0.457; `finish_camp_health_fraction` 0.688;
  `hurt_health_fraction` 0.453 (own retreats, dash chases); `heal_trip_fraction` 0.536 (siege heal trips).
- **Shield:** cast at the first enemy blow that reaches us, or as soon as an awake camp reaches us / we hit one
  (`shield_if_needed`). **Dash:** a landing on enemies needs 250 enemy-health points of value
  (`min_landing_value`); travel dashes avoid landings that would wake a group or draw a killing retaliation.
- **Shop:** HoR's shard values don't see the passive. Analytically they shouldn't: in a health x damage exchange the
  passive's life average (1.25 from full) is the same whatever the max health, so it scales Health and Strength
  shards alike and leaves their ratio unchanged. No shop arm was run.

## Data

`~/tmp-offload/hor/` (scripts in `bin/`: `horfeat.py`, `horrep.py`; tables `ladder-rep.txt`, `all-rep.txt`).
- Ladder: the behaviour-gaps set (18,599 decoded games, `~/tmp-offload/gaps/analysis/`), every HoR body: Fish 3,193,
  Mite 4,082, other 2290+ teams 15,994, ours (v82) 2,103.
- Ocean now: oc-base25-td against proteus-td (the s2 panel, 700 HoR bodies), both on test drafts.
- Farm rounds: HoR hit a camp, no enemy within 5. Fight rounds: it dealt or took champion damage. Health is the
  snapshot before the round.

| measure | Fish | Mite | top | v82 | oc-base25-td |
|---|---|---|---|---|---|
| health farming, median | 0.93 | 0.90 | 0.92 | 0.94 | 0.94 |
| health farming, p10 | 0.58 | 0.55 | 0.58 | 0.58 | 0.54 |
| farming below 0.3 | 0.6% | 0.3% | 0.6% | 1.5% | 1.4% |
| health fighting, median | 0.79 | 0.76 | 0.74 | 0.76 | 0.72 |
| passive, damage-weighted, on champions | 1.106 | 1.109 | 1.123 | 1.124 | 1.145 |
| passive, damage-weighted, on camps | 1.072 | 1.075 | 1.071 | 1.070 | 1.076 |
| dashes onto champions /100 rounds | 0.82 | 1.02 | 0.98 | 1.20 | 1.70 |
| health at a champion dash, median | 0.89 | 0.86 | 0.86 | 0.86 | 0.81 |
| champion dashes below 0.6 health | 15% | 15% | 19% | 21% | 25% |
| dashes onto camps /100 | 3.55 | 4.11 | 3.46 | 2.71 | 2.44 |
| travel dashes /100 | 5.0 | 5.7 | 4.7 | 7.0 | 6.5 |
| shield left at expiry | 0.59 | 0.71 | 0.72 | 0.66 | 0.65 |
| recalls /100 | 0.88 | 1.09 | 0.91 | 1.18 | 1.00 |
| health at recall start, median | 0.71 | 0.60 | 0.67 | 0.86 | 0.77 |
| gems at recall start, mean | 14.5 | 15.1 | 10.4 | 7.1 | 9.0 |
| deaths to camps /100 | 0.017 | 0.015 | 0.014 | 0.005 | 0.004 |
| kill share of team kills | 0.15 | 0.16 | 0.18 | 0.16 | 0.13 |
| kill participation (kills + assists) / team kills | 0.52 | 0.56 | 0.60 | 0.56 | 0.67 |
| camp damage dealt /100 | 1,913 | 2,113 | 1,802 | 1,516 | 1,272 |
| camp damage taken /100 | 968 | 758 | 672 | 607 | 547 |

- **Nobody plays to the passive.** Top teams farm at the same health as ours (median 0.92-0.93 against 0.94) and
  farm low *less* often (0.3-0.6% of farm rounds below 0.3 against our 1.4-1.5%). Their passive on champion damage
  is *lower* than ours (Fish 1.106, ours 1.124-1.145): they fight and dash healthier (Fish's champion dashes: median
  0.89, 15% below 0.6; ours 0.81-0.86, 21-25%).
- **Ocean's HoR already farms low when it's safe:** with no enemy within reach the recall line is 0.109, and farm
  spends health down to it.
- **The real gaps are elsewhere.** Fish and Mite deal 25-65% more camp damage and land 30-70% more dashes on camps
  (a camp landing is 1.5x Focus and a stun that skips the camp's attack), with fewer travel dashes. They recall
  less often, lower, and with twice the bag (Fish 14.5 gems, ours 7-9).

The data argues against branches A and B as framed (they move us away from the top teams), but the A/B decides.

### Against Fish (v82, 77 HoR bodies; the counter analysis's largest effect, -0.51 ±0.20 logit)

Our HoR against Fish dies 2.6x as often as against the rest (0.27 deaths /100 rounds against 0.10), fights lower
(p10 0.27, 11% of fight rounds below 0.3 against 7.5%) and dashes onto champions hurt (19% below 0.6; Fish's own
HoR against us 15%). Fish's HoR against us fights healthier (median 0.76), recalls lower (median 0.57) with twice
our bag (15 gems), and takes 45% more camp damage. What goes wrong is fighting hurt, the opposite of branch B's idea.

### Recalls

| per 100 alive rounds | Fish | Mite | v82 | oc-base25-td |
|---|---|---|---|---|
| recalls | 0.88 | 1.09 | 1.18 | 1.00 |
| heal recalls (start below 0.5 health) | 0.33 | 0.42 | 0.29 | 0.33 |
| below 0.35 | 0.19 | 0.24 | 0.19 | 0.22 |
| recalls at 0.7+ health (bank or move) | 0.45 | 0.46 | 0.75 | 0.54 |
| their mean bag | 16.9 | 18.8 | 7.6 | 8.2 |

We don't heal-recall more than the top teams; our extra recalls are healthy ones with small bags (a banking
question, not HoR's).

## Method notes (written before the screens; TEST-STANDARD.md "Method")

- **A, farming low.** Mechanism: scale HoR's recall lines, heal-trip and hurt lines down (and finish-camp up) so it
  farms on at lower health, where its passive is higher; the shield waits until health is low against camps.
  Failure case looked for: HoR going home early or heal-tripping while it could farm on. *Not found*: our heal
  recalls (0.29-0.33 /100) match Fish's (0.33) and Mite's (0.42), and top teams farm low less often than we do.
  Prediction: level to negative (a risk change; dying to camps loses the bag). Kept to three arms (x0.8, x0.6, a
  shield held to 0.8); the camp-type and bag-gate subvariants (built: `hor-a-r60-elk`, `-wolf`, `-bag20`,
  `hor-a-sh60`) run only if x0.6 or x0.8 shows a gain.
- **B, fight timing.** The user's mechanism (dash in hurt: `hor-b-hurt`, landing floor x0.5 below 0.6; hold the
  dash while healthy: `hor-b-hold`) runs against the data: our champion dashes are already hurter than Fish's, and
  against Fish our HoR dies fighting hurt. Failure case found for the opposite: HoR dashing in hurt (21-25% of its
  champion dashes below 0.6 against Fish's 15%) and dying (0.16 /100 against Fish's 0.10). Arms: `hor-b-hurt`
  (the user's; predicted negative), `hor-b-nohurt` (landing floor x2 below 0.6; predicted +0 to +0.4, mostly
  against Fish-like opponents), `hor-b-early` (x0.6 above 0.8: dash healthy, as Fish; predicted level to +0.2),
  `hor-b-sim` (our HoR's passive averaged in the fight simulation; it makes our HoR bolder, predicted level to
  negative). `hor-b-hold` not run (contrary to the data on both counts).
- **C, valuation.** Exact model fixes; no replay can show a misjudged simulation directly, so the bar is a
  non-negative panel. `hor-c-fight`: every HoR's passive averaged over its remaining health in the fight simulation
  (our fear of enemy HoRs rises as much as our own HoR's confidence; enemy HoR is in ~93% of Fish and Mite comps);
  `hor-c-fighthalf`: half of that correction; `hor-c-farm`: camp clears priced at the passive halfway through the
  clear's damage; `hor-c-both`. Predicted +0 to +0.3, showing in games with an enemy HoR.
- Shop: no arm (the passive scales Health and Strength shards alike; above).

## Phase 1 screens (2026-11-08, against oc-base25 on hor-scr-1050a, own drafts, `--sprt 0.50,0.5025`)

| arm | win % (CI) | games | SPRT | changed games | HoR games: win, changed |
|---|---|---|---|---|---|
| hor-a-r80 | 50.2 (49.8-50.6) | 51,200 | undecided, LLR +0.67 | 51% | 51.2, 66% |
| hor-a-r60 | 49.9 (49.5-50.4) | 51,200 | undecided, LLR -1.68 | 56% | 50.8, 75% |
| hor-a-sh80 | 49.5 (48.9-50.1) | 28,092 | H0 | 62% | 49.6, 92% |
| hor-b-hurt | 49.2 (48.3-50.1) | 12,522 | H0 | 39% | 48.3, 51% |
| hor-b-nohurt | 50.1 (49.7-50.5) | 51,200 | undecided, LLR -0.53 | 41% | 50.0, 52% |
| hor-b-early | 49.8 (49.2-50.4) | 29,391 | H0 | 32% | 49.8, 37% |
| hor-b-sim | 50.2 (49.8-50.6) | 51,200 | undecided, LLR +0.62 | 61% | 51.0, 75% |
| hor-c-farm | 50.0 (49.6-50.5) | 51,200 | undecided, LLR -0.65 | 64% | 50.6, 88% |
| hor-c-fight | 50.5 (50.1-51.0) | 47,390 | **H1** | 68% | 50.3, 89% |
| hor-c-fighthalf | 50.3 (49.9-50.7) | 51,200 | undecided, LLR +1.46 | 66% | 50.9, 85% |
| hor-c-both | 50.7 (50.2-51.2) | 38,425 | **H1** | 75% | 52.1, 97% |

Changed games and HoR games: against a base mirror on the suite's first 20 seeds (10,240 games; `bin/chg.py`).
26-47% of games without our HoR change too (fuel: the arms cost a few instructions more, which moves fuel-gated
choices). As predicted, the user's branch B (`hor-b-hurt`) and the shield hold lose; the exact valuation (C) wins.
The six undecided arms rerun on hor-scr-1050b with their own seeds (10531-10536).

## Camp dashes: why we land fewer (`bin/campdash.py`, `bin/cdrep.py`)

Per Heart of Ruin body, ladder (Fish 3,193, Mite 4,082, top 15,994, v82 2,103) and local oc-base25 (vs proteus /
astraeus, 1,180 / 1,156). An engagement is an attacker group woken by this HoR.

| measure | Fish | Mite | top | v82 | oc-base25 |
|---|---|---|---|---|---|
| engagements opened by a dash | 44% | 63% | 49% | 7% | 10% |
| dash ready at the opening | 58% | 67% | 70% | 36% | 37% |
| ready but not opened by a dash | 13% | 4% | 21% | 29% | 28% |
| a travel dash in the 8 rounds before | 47% | 29% | 27% | 81% | 76% |
| farm rounds with the dash ready: dashed onto camps | 83% | 93% | 74% | 77% | 74% |
| the same: shield cast instead | 0.6% | 0.3% | 3.0% | 3.3% | 3.6% |
| farm rounds /100 alive | 23.6 | 22.3 | 21.1 | 21.0 | 18.5 |
| camp damage per camp dash | 306 | 308 | 303 | 275 | 242 |

Mid-clear we use the dash as often as anyone. The gap is the opening: Fish walks adjacent, hits (waking the group)
and lands in the same turn (0% of its camp dashes follow a walk), so the stun takes the group's first attack. Ours
has spent the dash travelling there (travel dashes tie or save a turn, so the planner always takes them), and when
it is ready the shield takes the turn's one cast first (bot.cc's farm-turn `shield_if_needed` fires as soon as a
group we are about to hit reaches us).

Arms (`params::hor`, D): `hold_steps` (no travel dash while walking to an attacker group within that many steps;
10, since a dash 9 steps out is back on arrival) and `shield_defer` (on farm turns a camp-only shield waits for the
end-of-turn call while the landing dash is ready: camps fire before our turn, so a shield at its end covers the same
camp phase). Check on 512 games (fresh-1055000, hor-d-both against the base in the same games): opened by a dash
65% (base 7%), ready at the opening 66% (32%), travel dash before 29% (82%). Screens on hor-scr-1050b: hor-d-hold
10541, hor-d-shield 10542, hor-d-both 10543, hor-cd-both (C + D) 10544.

## Phase 2: gates (2026-11-08; merged hor-c-fight as CHANGES 467, `variants/oc-base26`)

Results against oc-base25 (own drafts unless panel; `--sprt 0.50,0.5025` unless noted):

| arm | gate | result |
|---|---|---|
| hor-c-fight | held out (1051a then 1051b, pooled) | 50.43% (50.12-50.75) of 61,812; H1 (1051a alone: 50.38% of 40,960, LLR +1.59) |
| hor-c-fight | varied (1052 + 1052b, 0.4975/0.50) | 50.57% (50.03-51.11) of 20,478; LLR +2.27, not H0 |
| hor-c-fight | panel (0.4975/0.50, pooled) | +0.57 pts; H1 at 23,598 of 30,720 units |
| hor-c-both | held out 1051a | 49.9% (49.4-50.4) of 40,960; LLR -1.29; 0.48 ±0.45 below c-fight on the same maps |
| hor-c-both | panel / varied | +0.39, H1 / 50.45% of 20,478, LLR +1.65 |
| hor-c-farm | screen 1050b | 49.5% (49.0-50.1) of 30,186; H0 |
| hor-a-r80 | screen 1050b | 50.34% of 70,382; H1 (1050a: 50.2% of 51,200, undecided) |
| hor-b-nohurt | screen 1050b | 50.33% of 57,887; H1 (1050a: 50.1% of 51,200, undecided) |

The pooled held-out reads hor-held-1051a's pairs (in a seeded order), then hor-held-1051b's in completion order (ab.py's
`--shuffle`), with ab.py's LLR over the joined list (`hor-tools/pooled_held.py`); the second run was stopped at the
crossing. c-both's held-out drop is its farm half: c-farm alone is H0, and c-both trails c-fight on the same maps, so
c-both is superseded rather than run on. The merged code is c-fight alone (`fight_scale` in model/safety.cc, no switch),
replay-identical to the arm at 100M fuel. a-r80 and b-nohurt (risk changes: panel H1 needed at 0.50/0.5025) go to held
out on hor-held-1056 (ladder-v2, seeds 1056000-079), panel and varied; they were screened on oc-base25 without c-fight.
