# T16: a heal nearby replaces a heal trip (candidate `bots/variants/macro2-healstay`)

Read /home/ubuntu/wt/macro2/research/macro-2026-11-11/briefs/common.md first and follow it. Base: copy
`variants/macro2-combo` (`./copybot variants/macro2-combo variants/macro2-healstay`). The combo is our best, at
50.53% of 51,200 games. It includes macro2-medic1, Willow's heal order by the farm time each heal saves.

## Evidence
- Willow is drafted by 62% of teams. She heals ~15.5 HP a round against a capacity of ~52: 3 x Focus every 8 rounds,
  and any slot recasts 8 rounds later. So ~30% of her heal is used.
- Heal recalls are ~28% of recalls. Each costs ~33 champion-rounds (the 5-turn channel plus the walk back out).
- Health returns only on our own spawn or from Willow.
- macro2-medic, where Willow walked to attend the top camp-damage ally, lost (48.8%): her own farming halved. So
  Willow should not move more. Instead, her allies should count her heal when deciding to go home.
- Rules: a visible ally exposes its ability cooldowns, health and position (vision.visible_champions). Ally
  abilities have range 4 and need the target in the caster's sight.

## Principle
A champion's heal-recall decision prices the health it gets back by going home against the farm rounds the trip
costs. When a Willow ally is close, with her heal ready or nearly ready, part of that health comes for free within a
few rounds. The deficit that justifies a trip is then smaller by the heal she will land before we'd have to leave.
It is the same quantity medic1 prices from Willow's side: a heal's share of a trip home, per usable health.

## What to build (bounded)
1. Find where ocean decides heal-motivated recalls and trips: the recall line and `farm_recall`'s heal term, home
   trips, `heal_rounds_now`, `usable_health`, and the farm's heal-trip pricing (crew_budget/extra_trips). Find where
   the health deficit or usable health enters.
2. For a champion with a visible, alive Willow ally (not dead, not channelling) whose heal slot is ready within the
   decision's horizon and who is within her ability range plus her walk over those rounds: treat the expected heal
   (3 x her visible Focus, capped at our missing health) as health we will regain. Apply it in the heal-trip pricing,
   i.e. in usable health or the deficit. Don't apply it to the lethal-danger recall line: safety stays as is. If
   medic1's code already has a helper for Willow's heal amount or readiness, reuse it.
3. Only once per heal: if two allies could count the same heal, give it to the one Willow's own heal order (medic1's
   `heal_before`) would choose, if that is cheap to evaluate. Otherwise let each count it and note it as a
   limitation.
4. Keep everything else, including Willow's own behaviour, safety, the draft and emblems. Without a Willow nearby,
   behaviour must be identical to the base.
5. No new tuned constants. Use the heal multiplier 3, cooldown 8, range 4, and the existing trip prices.

## Check
Trace `HEALSTAY round handle deficit heal_credit decision_changed`. In 2-3 local games with Willow drafted, report the
number of heal recalls per game, candidate vs the base, in the same seats. Audit and report as common.md says.
