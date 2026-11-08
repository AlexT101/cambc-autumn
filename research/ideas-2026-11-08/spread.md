# Spread: per-champion capture and gold allocation on v87 (2026-11-08)

Base `bots/variants/oc-base25` (v87). Scripts, logs and analyses in `~/tmp-offload/spread/` (bin/, an-*/).
Results table: EXPERIMENTS.md, "Spread".

## Mechanism (economy/capture.cc)
- Holder: `holder_value` = gems + 0.3 x gold x rate x `relative_efficiency`, argmax among allies on or next to the
  group when someone multiplies, else lowest id; `outvalues_holders` lets a better holder take over.
- `relative_efficiency` = (gold_efficiency / team mean)^1.47, which also scales farm's per_gold: already a soft
  proportional split by stat growth. At base stats: Ryth 1.92, Vesper 1.67, Vendetta 1.61 ... Issac .68, Cassi .57,
  Willow .46 (bin/efftable.py).

## What the data said before arms
- Cassi/Issac teams: Cassi 5.1%, Issac 10.9% of team capture gold by r400 (others 22.9% each; equal per body 18.6%).
  Both stat models (ours, Lanchester) already give them less than an equal split, so deep cuts were unsupported.
- At a group's clear, another living ally was within +0 steps of C&I's hold tile for 56% of their capture gold, +2
  for 70%, +5 for 80%: the curve flattens past +2, so the yield arms used k = 0 and k = 2 (bin/cidist.py).
- Carry (bin/carryhold.py): of captures paying >= 80 gold by r400 on Vesper teams (18,596), Vesper holds 45.3%;
  for the rest it was within 2 steps at the clear in 2.6%, 3-6 in 8.0%, further in 42%. The holder rule is not why
  Fish and Mite's carry out-earns ours: ours isn't at those groups.

## Arms (each oc-base25 + one diff)
- h15 / g15: Heart of Ruin's holder value / gold efficiency x1.5 (HoR in 54% of our team-games). Mechanism: HoR cap
  gold 209 -> 254 (h15), 219 -> 281 (g15), taken from Prism and others; team gold flat.
- lanch: a fixed Lanchester table (output gain x team hp) times gold rate in place of stat growth.
- p1 / p2: the power 1.47 -> 1 (proportional) / 2 (concentrates: Vesper +20% share at e/mean 1.4, Fish-like).
- ci05: C&I share x0.5 after the power. Team capture gold -3% (freed gold partly not taken).
- y0 / y2 (`params::ci_yield_steps`, `shy_yields`): Cassi or Issac, partner alive, skip a cleared one-holder gold
  group when a visible ally (not shy, not tributing or held back, healthy, not inside its own claimed group's
  threat) reaches it within k extra steps. Yields are rare; y2 team capture gold -1.4%, C&I deaths flat.

## Reading
- Reweighting the split, in any direction, is H0 or level; the current power sits at an optimum. Holder-side
  funnels can't move gold to the carry because the carry is elsewhere; the open lever is farm choice (route the carry
  to big gold groups, others leave them), which the draftfarm line covers. No v87-sp-rand fit: nothing moved.
- y2 passed its screen; its gain isn't visible in gold totals at 488 games, so it rests on the gates. If it holds,
  the generalisation is a distance-priced yield (value - lambda x extra steps) with the receiver told over comms,
  since many yielded groups go unclaimed.
