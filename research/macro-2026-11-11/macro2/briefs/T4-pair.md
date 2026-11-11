# T4: linked-pair macro (Cassi & Issac) (`bots/variants/macro2-pair`)

Read briefs/common.md (same folder) first and follow it. Candidate dir: `bots/variants/macro2-pair`, created with
`./copybot variants/ocean-ref-b7c87cf variants/macro2-pair`.

## Why (measured on 512 ocean-vs-ocean games)
- Our draft picks Cassi & Issac in 96% of team-games. The rules: one pick, two bodies; if either dies both die,
  giving one kill reward and BOTH bags; both are out ~60 rounds. Cassi has 600 base health (ranged), Issac 900 (melee).
- The pair dies 1.46 times a game (each time both bodies), against Vesper 0.42, Prism 0.69, Varg 0.36: ~37% of all
  champion deaths. 41% of FIRST kills of a game (first kill -> 68% win) are a Cassi or Issac body. Cassi is the
  first body hit in 55% of pair deaths, Issac 45%.
- The bodies are usually apart: pair distance over time median 9 tiles (quartiles 3 / 19); at a pair death the
  partner is >8 tiles away 46% of the time; no other ally within 8 in 27%.
- General death pattern (all champions): healthy (median 85% HP), empty-bag walkers mid-map who saw the killer,
  burst within ~2 rounds by 2+ attackers. Pooled HP share decides engagements.
- Priors: CH 294 pair-yield (pair hold-shy, Cassi farms with the crew) won ~+4; "Cassi & Issac yielding to an
  ally within +2 steps" +0.4-1.0. A pack zone for ALL empty-handed healthy champions lost (48.1%, deaths up),
  because it costs every champion farm time; for the pair the stake is doubled, so the trade-off differs.
  The fight sims already model the link (effective health of the pair = the weaker body's, plus the rest;
  plan.cc drops the partner on a kill); check how far that reaches the macro decisions.

## Principle
A linked body's stake is the pair's: both lives (and both respawn absences) plus both bags. Every self-risk decision
a Cassi or Issac body makes, and every decision about attacking an enemy linked body, should price that stake.

## Design goals (specifics are yours after reading combat/fight.cc want_home/drawn_home/prey, combat/guard.cc
## pack zone, model/safety.cc, economy/farm.cc risk terms (camp_risk/recall line/spare health), capture.cc hold_shy)
1. Own pair, defence: where the pair's bodies decide on risk (leave/retreat zone, recall line, stand verdicts, farm
   targets' exposure), use the pair's stake. Concretely consider: the outmatch/pack zone (guard.cc) also for a
   healthy pair body off its own ground (today healthy champions off own ground have none), with the ratio derived
   from the stake (e.g. the hurt ratio, since a burst there costs two bodies); a farm-target preference for each body
   toward targets its partner (or another ally) can support when credible enemies can reach the target area, and no
   constraint in safe areas (a pricing term, never a summons).
2. Enemy pair, offence: a kill of either enemy linked body is worth two lives + both bags; make prey/chase ranking
   and kill bids (turn_order) and the strike search's target values count that where they don't yet; the more
   killable body (lower effective health, more isolated) is the natural target.
3. Keep everything else unchanged; no draft/emblem changes; bounded cost.
4. debug_block traces: pair-specific retreats, pair-distance, offence target choices.

## Done when
Builds; three local games (maps where both teams have Cassi & Issac: most maps, since both bots use the same draft)
run to completion with no bot errors; auditor's findings addressed. Report what you built and where, and what to
measure (our pair deaths/game vs theirs, total deaths/kills, farm gems).
