# Camp aggro (2026-11-02/03)

Waking sleeping camp groups onto enemies: camps attack at the next round's start the nearest champion in reach, before
anyone walks off, so an enemy that has already acted (or is channelling) takes the first hit. Each `.diff` is a variant
against astraeus 38aa25ce (`bots/variants/astraeus-38aa25c`); apply with `patch -p3` inside a copy's `src/`... or rebuild
with `./copybot -r 38aa25ce astraeus variants/X && patch -d bots/variants/X/src -p3 < research/aggro-2026-11-03/X.diff`.

- `aggro-s`: turn end only (bot.cc `aggro_camp`): an unused basic attack, or a damage/stun cast (unit or ground 3x3),
  when every woken striker's nearest champion is a held enemy, never us (we stay out of every woken reach) or an ally
  (seen, or seen within 5 rounds near).
- `aggro-s6`: aggro-s with the same decisions, cheaper (one record read, held-enemy and per-group prechecks).
- `aggro-x2`: the strike search credits a woken hit on a held enemy with `hit_worth` (combat/plan.cc `wake`), and may
  basic-attack or ground-cast such groups; `-nomono` leaves sleeping Monoliths banned; `-safe` bans a credited wake
  while an ally seen within 5 rounds may be in the woken reach.
- `aggro-x3`: aggro-x2 with bounded work: one attack target per group, ground centres on at most two members a group,
  camp members read only while a held enemy is visible.

Results: research/EXPERIMENTS.md, "camp aggro".
