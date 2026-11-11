# Camp hits scored by damage prevented

River scores camp hits, splashes, area spells, landings and stuns with one linear score
(`CampFight::removed`, `camp_hit_worth` in `bots/archives/river/map_info.htb`). The turn's first hit is planned by
`plan_camp_attack` in `champions/shared/farm.htb`. Results: research/EXPERIMENTS.md, "river: camp attack planner".

## The score

Awake monsters strike every round, at the camp phase before champion turns, until they die. Take member i with
Strength s_i, current health h_i, and our hit d.

**Kill order.** Killing 1 before 2 costs s_1 h_1 / d + s_2 (h_1 + h_2) / d, and the reverse costs
s_2 h_2 / d + s_1 (h_2 + h_1) / d. So 1 goes first iff s_1 / h_1 > s_2 / h_2. Swapping any two neighbours gives the
same comparison (Smith's rule), so single hits go to the most Strength per current health.

**A hit** of damage x on member i removes min(x, h_i) * s_i / h_i of the camp's Strength: the share of the member it
takes, all of s_i for a kill. For single hits of our own d this ranks members as above.

**A splash, landing or area spell** (Varg's basic, Heart of Ruin's landing, the ground spells) sums this over the
members it hits, so every target is compared by its sum.

**A stun** cancels one attack of a member that survives and would strike us. A tile out of a monster's reach spares
its next attack. Each is one round of s_i. Removed Strength counts for every round the fight has left, so these
weigh s_i / rounds, with rounds = the group's health over our hit.

**Ties.** With nothing to remove (clusters), more damage dealt wins, then the lower health.

## Where to hit from

The options come from the rules:

- **Melee:** walking and attacking are independent, so we may hit from here or from any free step.
- **Ranged:** a walk spends the attack. A ranged champion can walk, reset, then attack, so a ranged step costs the
  reset's second hit.
- **Dash** (a cast, not a walk): ranged can dash and attack; melee can dash, step and attack. The cast is spent, so
  the reset's hit is lost, unless Vendetta's kill readies it again.
- **Area spells** forbid walking before and after, so they are cast from where we stand (`camp_cast`, ranked by the
  same score; the damage floors that decide whether to cast are unchanged).

A tile scores its best target, twice while the reset's hit still follows, plus a landing's worth and the next
phase's damage it spares over standing here. Moves never go deeper into visible enemies' reach, onto the guard or
the pack zone, or (for a landing) onto a group the fight left asleep.

**Ranged walk or attack.** A walk instead of an attack delays every member's death by a round, one round of all
their Strength. It spares at most one phase of the members it leaves. So with an attack possible, attacking wins,
and the planner offers a ranged step only with the reset to buy the attack back.

## Fuel

A tile is scored in full only if its best target and the most a move spares could beat the best so far. A dash and
a step is skipped where even the best landing could not. `allowed` is asked once per group, threats only when a
move is checked, and landings only when an option needs them.
