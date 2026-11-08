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
