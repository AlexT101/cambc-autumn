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

## Generalisation (2026-11-09; the user: "the difference in value of the gold on the best champ and on us plus whatever
## distance they have to travel ... if the best champ was already moving there ... it's essentially free")
- `yields_from(world, pathing, g, who, from)` (sp-dev4): mode 0 is y2; mode 1 yields to an ally whose `holder_value`
  beats ours by (1 + margin)(1 + price x extra steps); mode 2 to the carry. `yield_told` makes receivers stop counting
  a yielding ally as ahead or as the claimer; `yield_free_only` takes only receivers already coming (claim g, none, or a
  group within 6); `willow_follows_carry`.
- Data (bin/yieldvalue.py, bin/yieldzero.py): a better ally no farther at the clear in 3.8 captures a game (the
  value is there: ~210 gold x efficiency gap a game), but it was heading there in only ~19%; most of these have both
  bodies 4+ away and the receiver bound for another group. Yields one or more steps longer are rarer (0.5 a game a
  step) and pass the receiver near the tile less often (23% at +0 down to 4% at +7).
- Results on dgate, all H0: y2t -0.94, yh -1.19, yv -1.43, yc -1.67, ycw -1.53 pts. The cost the model left out is
  the receiver's own plan: telling receivers alone turns y2's screen +1.0 into -0.9. y2's own gain doesn't show in gold
  (team capture gold -1.4%), held out 50.4% (50.0-50.8) of 51k: real but under rule 0's 50.5 bar at best.

## Reopened: y2's gate, generalised only in who yields (2026-11-09)
- Arms (sp-dev4, yield_mode 1, yield_step_price 0, no telling): vg2 (value ratio >= 2, +2 steps), vg0 (ratio 2, no
  farther), vg2w (ratio 1.5, +2). Sanity: the ratio-2 model makes y2's C&I yields (base-stat table above, and in games
  C&I give up a bit more gold than under y2) and adds non-shy low-efficiency holders' yields to the carries.
- dgate, all H0: vg2 -1.56, vg0 -0.95, vg2w -1.39 pts; y0 +0.19 (H0), y2 +0.45 ±0.36 (undecided, diverse agent's run).
- Reading: the C&I yield pays because the pair is shy (one death takes both bodies and bags), not because its stats
  grow slowly. Under the same gate, every yield the efficiency model adds loses, so stat-growth efficiency overrates
  the carry's gold against a walk. What the value model leaves out: the holder's risk (which drives C&I's) and
  what the gold buys next (build order, passives); gold_efficiency counts five stat points and only Ryth's passive.

## Reading
- Reweighting the split, in any direction, is H0 or level; the current power sits at an optimum. Holder-side
  funnels can't move gold to the carry because the carry is elsewhere, and pulling another ally to a yielded group
  costs it more than the efficiency gap is worth. The open lever is farm choice (route the carry to big gold groups),
  which the draftfarm line covers. The spread line is closed.
