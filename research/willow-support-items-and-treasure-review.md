# Willow items and role-dependent Treasure

2026-10-23. Read-only research against canonical a67, `cambc-rules.yaml`, SDK item definitions and the existing probe index; no new games, extraction, probes or gameplay edits. The shop has a real missing support objective. This does not establish that every Willow should buy Focus or Health first.

**Correction:** v1 incorrectly excluded Marcella's tribute-generated gold from Treasure's bonus. Exact existing replay balance/earned deltas contradict that assumption in two a67 games. See `willow-marcella-treasure-income-correction.md`; a dedicated probe is pending with the runtime owner. The original v1 is preserved as `willow-support-items-and-treasure-review-v1-superseded.md`, SHA256 `3268e10708d63d98c1a0e35ecde08233ad4dddc295ea906d2a7f8d8bc22280b4`. This strengthens Treasure's rationale for Marcella and does not change the two isolated Willow item arms.

## What current shopping optimizes

`bots/hyperion/src/bot.cpp:113–124` chooses a main stat from basic attacks and damaging casts/landings. Willow's Heal never contributes, so her main stat is always Strength. `raw_output:833–839` includes her basic and attack reset, not healing. `upkeep_cost:1195–1206` values faster own clearing and fewer own recovery trips using observed camp/champion damage, usable HP and return distance. It does not price ally healing, recipient continuation, service uptime, or surviving a discrete burst. Adding healing to raw damage would corrupt farm/crew clear estimates; the missing service value belongs in item valuation.

`best_emblem:1253–1293` finishes begun builds, compares Power/Jungle/Bruiser main-stat alternatives and Durability/Bruiser Health, and additionally permits Willow Jungle Health. It then forces Treasure first for non-Prism champions, in the chosen stat. Thus Willow is not literally Strength-only, but Focus is absent from her fresh candidates. Prism returns through its separate health/focus branch before Treasure. Quotes, farm gold value and shopping use this chooser (`prices:1329`, `affordable_prefix:1356`); a new support preference must describe the actual selected item's stats and price throughout, rather than quote Strength savings and silently buy Focus.

## Marginal tradeoffs

Rules give Willow 700 HP/55 Strength/120 Focus, growth50/3/5. Heal restores up to3F to another ally; it cannot heal Willow herself. A30-gold Strength shard adds3 per real basic, including reset attacks; Focus adds at most15 HP per real heal; Health adds50 maximum HP and heals that50 when bought on spawn. Heal spends the turn's cast, preventing a reset that turn; it does not itself exclude walking. A ranged walk does spend the basic.

At150 gold, Bruiser Strength gives15S/5F/50HP; Bruiser Focus gives3S/25F/50HP; Bruiser Health gives3S/5F/250HP. Therefore a single Strength→Focus swap sacrifices12S for60 nominal heal capacity, with equal HP/cost. Strength→Health sacrifices12S for200 HP, with equal Focus/cost. A first Jungle emblem reduces camp damage30%; Durability reduces all incoming damage10%; together the camp multiplier is0.7×0.9=0.63. These are completed-emblem effects, not partial-shard effects.

Added Focus helps only when the recipient deficit exceeds the old heal cap. `self_abilities.cpp:419–420` also raises the ordinary worthwhile-heal threshold with heal size (60% of amount, or recipient below50% HP), so more Focus can suppress previously accepted smaller heals. Future healing must not become borrowed HP for camp admission. Health/mitigation can preserve the healer's own uptime, but cannot repair a range/vision/service-allocation gap.

## Current exact-source evidence

Existing a67 Release metadata/events in `replays/willow-sustainable-crew-fish-panel-20261023-v2/extract16/`:

| Physical A game | Willow own gold earned | Healing | Camp damage dealt / taken | Basics / resets / heals | Exported heals360 |
|---|---:|---:|---:|---:|---:|
| BigWorld, `937e49df38e49207` |300|6695.8|14338 /3160|239 /37 /20|14|
| Boss, `b3fc46242dae948d` |770|17162.0|20493.0 /2960|329 /49 /53|31|

Both had zero Willow deaths. Healing/damage totals are native final counters; cast/basic counts and per-cast amounts come from the existing event export, whose damage/healing amounts are rounded. BigWorld Willow bought Treasure Strength and only four Jungle Strength shards: she never received Jungle's mitigation before the game ended. Boss Willow completed Treasure Strength, Jungle Strength and three Power Strength emblems. Focus stayed120 in both. These are useful farming and service roles, not an idle healer.

Holding the entire recorded schedule fixed, one extra Focus shard owned from the start could add at most210/465 total healing respectively; the true amounts can be zero even on a full heal if deficit was exactly360. No such from-start purchase was affordable, and later purchases have a smaller opportunity set. Extra basic damage from a Strength shard would be717/987 before modifiers. These are diagnostic quantities, not an equivalence between damage and restored HP. Metadata gives actual healing, not unabsorbed demand or the number of recalls prevented.

The older policy-wonk opponent Willow also delivered much more healing without a Focus build (`willow-heal-aware-item-options.md`); service access is an established competing explanation. The validated early BigWorld split delivered real Marcella heals while Prism was too far away. Extra Focus would not fix that separation.

## Why Treasure is not only for Vesper

`gold_paid:1315–1319` correctly adds bonuses: Vesper1.33→1.53, others1.00→1.20. Both gain the same0.20 per future base capture/kill gold; relative growth is about15.0% for Vesper and20% for another champion. Existing replay evidence also shows Treasure multiplying Marcella's tribute-generated gold: her effective gold per tributed gem becomes2.4. The important variable is who actually receives future eligible gold, not Vesper's passive alone.

Treasure still gives the five purchased shards' stats. Against Power it gives up the sixth shard; against Jungle/Durability it delays protection. Treating all150 gold as a pure income investment overstates its cost. An extra30 gold requires150 future base gold, but that simple payback is not a complete opportunity-cost model.

Historical CHANGES101 reports Treasure-first52.5%/1104 and fresh52.7%/512 against its then-parent; this supports retaining it as a serious baseline, not a universal theorem. CHANGES104's additional Treasure-return pricing did not survive (50.7%, OOF+24%). Generic forced Health builds also failed to improve prior broad tests (`EXPERIMENTS.md`, builds3). The exact a67 BigWorld case has Vesper2735 earned gold versus Willow300, showing why their investment horizons differ. It does not prove other roles should stop buying Treasure.

## Two small, separate experiments

1. **First protection before Treasure for an exposed Willow.** Before any new Treasure shard, if the existing own-upkeep chooser's winner is Jungle or Durability, allow that one protective emblem first; then resume Treasure. Finish all begun partials, including Treasure. This uses actual observed injury/travel already priced, adds no forecast coefficient, and may select Jungle Strength rather than force Health. No change to Vesper, Prism or other roles. Test whether earlier completed protection buys productive/healing turns worth the delayed income; zero deaths alone is not the success metric.
2. **One support-stat item comparison.** In a separate arm, substitute one newly chosen completed Bruiser Strength with Bruiser Focus for Willow after initial economy/protection, keeping all begun items and survival alternatives. Price its actual stats consistently; do not fabricate own-DPS or recall savings. This is an explicit role-preference experiment, not a proven scalar utility improvement. Measure actual additional absorbed healing at casts and lost farming output. A later conditional version should use real above-cap demand collected at existing successful heal selection, not offered healing or unseen ally injury. The present data do not justify a universal Focus-first rule.

For Vesper allocation, preserve another worker's safe productive clear and transfer only a genuinely available capture-holding opportunity when it will not reset or delay capture and the recipient can afford the route/hold. Bonus income from moving base rewardG from a nonbonus holder to Vesper is0.33G when both have the same Treasure status; delayed whole capture/gem conversion can cost much more. Existing BigWorld evidence already shows Vesper's payout varies far more than his damage between drafts. This is a coordination hypothesis, not a reason to remove everyone else's Treasure or to divert all farm routes toward Vesper.
