# Draft-solved opening farm plan (2026-11-08)

User: "test simulating early game farm plans and routes in draft ... solve to make sure we're in the highest value
spot after some horizon. test different horizons."

## Live data first (v86-v89 vs Fish and r2 Mite, 2295 games; ~/tmp-offload/draftfarm/ana)
- Our gold trails by 11-15% at r50-r100; gems are level or ahead. Win model at r100: 1 gem ~ 3.8 gold, and a net
  early death is -0.24 logit.
- Early deaths vs Fish by r100: 0.46 ours against 0.31 theirs. Most are on our own side and outnumbered. Early
  cohesion (an ally within 2 tiles) is 53% for us, 71% for Fish and 64% for Mite.
- With the same picks (spar), the live opponents earn +16% gold by r100 (+29% by r30). They clear jointly, and the
  carry (Vesper or Marcella) holds the big gold groups.
- osim.py, a round-stepping opening sim, rated the sequences. At H50, ocean's actual sequences score as well as the
  sim's best plan. At H100-150, a team plan (greedy seeds, stacked/paired, then local search) beats them by +14-18%
  against the solved best, or +37-39% against greedy seeds. Fidelity to real games is weak (r ~0.3).
- So the horizons tested are 60, 100 and 150, with per_gold 0.3 (between farm's 0.34 and the win model's 0.26).

## Design (bots/variants/v87-dfp-*)
- draft/open_plan.{h,cc} is an event-driven sim of the expected team (model draft) farming our half, plus an anytime
  local search. Its seeds are greedy per body, the whole team stacked, and pairs.
- It runs at the end of the first turn's analyse(), down to the draft reserve floor. It is never capped: 79-300
  iterations on the heavy ladder maps, ending at ~0.78M fuel.
- The output is 6 bodies x 6 steps in PlanFacts (289 bits, DraftPlan v17).
- In play, farm.cc's open_plan_choice gives the next listed group that still exists, has no holder and has no enemy
  within 8 tiles.
- Candidates are groups strictly nearer our spawn (the model has no enemy).
- A clear that would take anyone past usable health counts as failed, so the plan avoids it.

## Smokes (ladder, 256 games each, vs oc-base25; r100 gold and gems ours/theirs; base mirror 408/408, 69.9/69.9)
| arm | win | r100 gold | r100 gems | deaths by r100 |
|---|---|---|---|---|
| force plan, death model, our-or-equal half | 46.1% | 344/439 | 56.7/87.5 | 0.37/0.25 |
| force, failure-aware sim, strict half | 45.3% | 415/411 | 69.1/80.2 | 0.32/0.33 |
| same, equal-distance groups included | 44.5% | 397/416 | 69.2/77.0 | 0.39/0.34 |
| force first step only | 48.0% | 411/405 | 67.4/78.1 | 0.38/0.39 |
| bias: planned group is farm's sticky choice x1.5 | 52.3% | 410/397 | 67.4/74.7 | 0.35/0.38 |

When the plan is forced, it gains a little gold, but the opponent's gems rise by 5-10 at r100. Their mid captures go
from 1.02 to 1.3 a game, because a plan with no enemy in it leaves the middle to them. The x1.5 bias keeps farm's
pricing and lets its contest logic win, so it is the arm sent to the screens, at all three horizons.

The code is in open-plan-w15h100.patch (diff against oc-base25/src; variants are gitignored).

## Results against oc-base25 (v87)

| arm | gate | win% (CI) of n | SPRT |
|---|---|---|---|
| w15h60 | screen, real budget | 48.66 of 19,858 | H0 |
| w15h60 | screen, 2x fuel | 48.92 of 23,515 | H0 |
| w15h100 | screen, real budget | 48.31 (47.54-49.08) of 16,163 | H0 |
| w15h100 | screen, 2x fuel | 48.94 of 24,531 | H0 |
| w15h150 | screen, real budget | 46.85 of 9,201 | H0 |
| w15h150 | screen, 2x fuel | 46.82 of 8,779 | H0 |
| w15h100 | spar (13 bodies x F/M) | -3.19 ±3.66 pts of 6,656 paired | diagnostic |
| pure (fixed bias) | debug smoke, forensic maps | 49.7 (47.5-51.9) of 2,000 | diagnostic |
| pure | dgate (0.505/0.5075) | 50.63 (50.26-51.00) over 23,296 units (~93k games a bot), LLR +0.07 | undecided, stopped |
| carry | debug smoke, forensic maps | 50.3 (48.1-52.5) of 2,000 | diagnostic |
| carry | dgate (0.505/0.5075) | 50.51 (50.03-50.99) over 14,336 units, LLR -0.49 | undecided, stopped |

The longer the horizon, the more the plan is followed and the more it loses.

## Why it loses (forensics, 2026-11-09)
Paired debug games on 1,000 screen maps (`maps/suites/merged/dfp-forensic-134`): each w15h100-vs-base game against
the base mirror on the same map and side (`tools/fx.py`, `fxsum*.py`). The plan moves the first walk in nearly every
game (median divergence round 1; the base's first group is the plan's 25% of the time, the arm's 73%). Paired deltas,
arm minus mirror, mean ± s.e. over 2,000 games:

| | ours | theirs |
|---|---|---|
| gold earned r100 | +4.9 ±3.3 | +15.0 ±2.9 |
| gems owned r100 | +0.3 ±0.8 | +3.5 ±0.7 |
| captures by r150, middle | -0.11 ±0.04 | +0.20 ±0.03 |
| captures by r150, own half | +0.05 ±0.04 | — |
| deaths by r150 | -0.02 ±0.02 | +0.03 ±0.02 |

Two mechanisms, neither the plan's routing:
1. **Thrash (an implementation flaw).** The arm wrote the planned group into `memory.farm_group` every turn, so the
   plan took farm's stickiness slot: whenever farm's contest logic chose another group, that choice lost its 1.2
   stickiness next turn and the plan's group took 1.5, and farm switched back. A-B-A target flips within 10 rounds
   (r<=100): 5.6 a game against the mirror's 1.3. `farm_group` also steers the post-fight walk, the fuel-short walk
   and the Monolith siege, which all followed the plan.
2. **Ceding the middle (the model's flaw).** Candidates are our half only (the sim has no enemy), so the plan pulls
   bodies off the contested middle in the first rounds, where the base goes. The enemy takes +0.20 middle captures a
   game by r150 and +3.5 gems by r100, three times what we gain.
Loss flips and gain flips (487 and 456 of 2,000) are mirror images of each other (deaths by r150 0.62 against 0.33
in losses, 0.36 against 0.63 in gains): reshuffling the opening reshuffles who loses the first fight, with the
middle tipping it slightly against us.

**Fixed arm, v87-dfp-pure** (`pure-vs-w15h100.patch`: the plan's weight applied on its own, `farm_group`
untouched). Thrash is gone (A-B-A 1.32 against 1.33), the middle concession shrinks (theirs +0.07 ±0.04, ours
-0.09 ±0.05) and the win rate is level (49.7% of 2,000 debug games). In the mirror, what remains is the plan's own value, and it
is nil: our gold +3.8 ±4.2 and gems +0.1 ±1.2 at r100, nothing by r200.

## Against live picks (the gate's opponents) the fixed plan gains a little
Block 0-2 of the gate replayed with replays kept (`fxs-*`, 2,048 pairs: v87 and v91 with Fish's and Mite's live picks,
noise seeds 1-2; `tools/fxspar.py`): pure minus base, our gold +8.3 ±3.7 at r100 and +16 ±7 at r200, their gold
level; their gems +2.5 ±0.9 at r100, with middle captures again given up (ours -0.14, theirs +0.13 a game by r150).
These opponents' drafts differ from ours, so our half is not mirrored by theirs, and the plan's routing there is
worth something; the middle is still the cost. Win rate 71.4% against base 70.6% on those 2,048.

## Carry routing (v87-dfp-carry, `carry-vs-pure.patch`)
The coordinator's fact from the HoR and spread lines is that Mite's HoR earns 357 capture gold by r400 against our
232, and the gap is team routing. So the plan weighs each body's gold as play does: (gold efficiency at base stats /
the team mean)^1.47 times its gold bonus (weights, e.g., 2.2 / 1.6 / 0.56). The plan then sends the efficient
bodies to the gold, and the holder rule picks them. Mirror debug smoke, paired against the base mirror: 50.3% of
2,000. Gold earned by r400: Vesper +35 ±19, HoR +11 ±9, Marcella +31 ±23, team +28 ±18. Its gold moves the right
way, but it is far short of the 125 gap.

## Verdict
- Following an offline plan more (forcing it, longer horizons, the stickiness slot) loses, because the plan, with no
  enemy in its model, gives up the contested middle, and in the thrash arm farm also fought its own choice.
- Fixed so that it only biases farm, the plan is level in the mirror. Against the gate's live-pick opponents it is a
  small, real gain: dgate 50.63% (CI 50.26-51.00), sitting at the bar's midpoint, so the SPRT would not end. That
  puts it in rule 0's 50-50.5 zone.
- Its mechanism is visible: own-half gold +8 at r100 and +16 at r200 against those opponents. It still gives up
  middle gems (+2.5 for them).
- Weighting the plan's gold by efficiency (carry) moves gold to Vesper and HoR in the right direction (+35 and +11 by
  r400) but adds nothing on the gate (50.51%). It closes only a fraction of the 125-gold HoR gap, which is not about
  which own-half group comes first.
- **Merge read (pure): weak no.** The gain is ~+0.6 pts and is level in the mirror. Its cost is ~330 lines of draft
  code, 289 bits of draft memory and a first-turn search down to the draft reserve. Its known flaw, ceding the
  middle, matters most against live Fish and Mite, who contest middles harder than our panel does. If the
  coordinator wants it anyway, it is a candidate for a live pair against v87, not a merge on local evidence.
- The idea's better form would need an enemy model in the plan (contest arrival on middle groups) to stop ceding the
  middle. That is a big build for at most the ~+0.6 pts the middle costs now, so it is not pursued.
- Gate runs are reused by dir name: `dgate.py variants/v87-dfp-pure variants/oc-base25` resumes where it stopped.

## Enemy model in the plan (v87-dfp-race, `race-vs-pure.patch`; user: "yes you can try model asw")
Live data (2,295 v86-89 games against Fish and Mite, `side.pkl`): by r150 each side captures about 3 middle groups
(our 3.1, their 2.0-2.5; value about even). The first middle captures of either side come at r50/72/104 (25/50/75%),
after each side's own half (r26-28/47-49/76). Holders are mostly alone (1.05-1.2 bodies a share). The middle is a
symmetric race, so the enemy is modelled as our mirror:
- Candidates add the middle band (our steps <= 1.353 x theirs, the side >= -0.15 band of the analysis).
- The enemy timeline is our own team's greedy opening, simulated once. The enemy starts on group g when our greedy
  starts on mirror(g), and is paid at that clear's end + 6. Our own half's mirrors are theirs, so those stay ours.
- In the sim, a group the enemy reaches while it is idle is theirs and is back only after their payout + respawn.
  The greedy seeds skip such groups.
- A clear we start no later than they arrive is "raced". Paid before they arrive, it is worth its value plus deny x
  their value (gems are zero-sum). Reached by them first, it is worth contest x its value (0.5, even teams).
- Two forms: race (deny 1) and race-d0 (deny 0).

Mirror (debug pairs on the forensic maps): the middle concession is gone (middle captures ours -0.03, theirs +0.02,
against pure's -0.09/+0.07). Planned middle steps go from 16% to 23%. But our own gain goes with it (gold +2 at r150,
gems -1). Smokes: 49.3% and 48.8% of 2,000.

| arm | gate | result | SPRT |
|---|---|---|---|
| race | dgate vs pure (shared runs) | -0.25 ±0.53 pts over 7,808 units | H0 |
| race-d0 | dgate vs pure | -0.16 ±0.50 pts over 8,960 units | H0 |
| race | dgate vs oc-base25 | 50.16 (49.55-50.77) over 8,960 units, LLR -1.22 | stopped |
| race-d0 | dgate vs oc-base25 | 50.26 (49.66-50.86) over 9,472 units, LLR -0.97 | stopped |

Planning the middle offline doesn't beat leaving it to farm, which sees the enemy. The race the model predicts is
accurate in the mirror, but the plan's middle steps replace live contest decisions that are already about as good,
and they cost the own-half routing that was pure's gain. Pure stays the form.
