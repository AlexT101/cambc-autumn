# Marcella delayed tribute value: isolated source checkpoint

2026-10-24. Source-only prototype following `research/marcella-delayed-tribute-value-source-design-20261024-v2.md`, SHA256 `5e1ad087ab390a804aa2bd3ae77d5d8b58d5622b0dfa22e51a36232518ff9914`. Cambridge Battlecode rules read: Marcella receives2 gold per tributed gem; Treasure raises this to2.4. No build, game, test/helper/script implementation, tooling/SDK change, canonical edit, EXPERIMENTS edit, release or submission.

Frozen parent `provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7` remains aggregate `f475b8521cada611754076822402a266c43be8de76ce0f2b504b268ff3335824`, verified after implementation. Child `bots/variants/willow-v47-marcella-tribute-value-work` contains only src, with no `.cambc`, backup or reject files. Only bot.cpp differs; all other28 files remain byte-identical to f475. Default draft and all other experimental arms remain unchanged.

- All29-file manifest: `research/willow-v47-marcella-tribute-value-source-v1-manifest.sha256`; verified29/29. Manifest SHA256/source aggregate `8701885d1e7d6d3d69c10bcea80289d3e59b3c01824ff4834162062dcf1ab58f`.
- Patch: `research/willow-v47-marcella-tribute-value-source-v1.patch`, SHA256 `baceaeac6b1110832afb18ccaf60cb960b38a7cda569ee6fd631fc424f76c892`; bot.cpp only,34 insertions/5 deletions; whitespace check clean.
- Child bot.cpp SHA256 `31542f4af7b641ea822d9fa46f822235415ffa67fd2a66f383ec285d8d56f0e2`.

## Integration and eligibility

bot.cpp:1964 enables the term only for Marcella (`Passive::stun_immune`, verified champions.h), positive current gold price, ordinary F decision, no banking/siege, and actual `my_gems()==0`. `bankable_bag` alone is insufficient: it can be zero for a carried bag whose altar is unavailable. Existing max/current-health reads are retained in their original order, with current health named for the later heal-delay scalar.

bot.cpp:2224 computes uncached nominal B=`known.weight * (2*q) * per_gold` only for positive ordinary gems, nonwinning capture, one holder and no ally claim in the original current ally_claims mask. It deliberately does not use claimed_bits, which clears a leading self-claim even when another ally also claims the group. Existing group gold, gem reward and HomeTrip budget are untouched. Existing paid/per_gold applies Treasure once; no Vesper/Cassi multiplier is imported into Marcella.

The three solo optimistic prunes at2257,2282 and2359 use old worth+B. Their banking-chain comparison arms retain old expressions: the new term requires an actually empty bag, so banks_bag is false. Claimed crew scoring still continues through the original branch without B. A final bonus is admitted at2374 only after the original solo clear/kite and too_late checks, while damage is independently affordable and before partner rescue can replace damage with zero. A rescued or risky candidate receives no new term. Existing shared/help overrides and winning/siege paths remain authoritative.

The final bounded allied-roster check uses alive+visible nonself records and map.group_at(position), rejecting any ally on a capture tile, including an eligible Prism. This is equivalent to checking membership in group.tiles here, without constructing its lazy bitboard or scanning enemies. Ownership and nominal B are re-evaluated per farm invocation/candidate, never cached.

## Delay, bounds and cost

Final D=`steps+wait+clear+capture + known.to_altar + tribute(q) + recall + H + map.ally_steps(g)`, H=1 for current missing health or positive independent camp damage, else0. The original too_late check alone populates the altar estimate. The spawn scalar is read only when map.drafted or from_ally_spawn_ready is already true. Unavailable/unreachable altar or spawn facts yield zero final bonus. No new path search, field construction, Safety query, enemy scan, allocation, message or fuel gate is added. The current allied roster is bounded by six bodies; holders is already bounded by big_holders. A warm spawn field may incur one existing Field::at native lookup per eligible final candidate; a drafted spawn distance is a scalar read.

The investment horizon is computed once for an eligible Marcella farm invocation as min(existing left,race_left), reusing left=bag_rounds_left. This adds one bounded race_left allied-roster scan, which may read existing comms bags for unseen allies, plus one actual my_gems scalar read. No closing call or new observation occurs. Final D must fit the horizon; the added value is rate(world,B,D), leaving the old rate unchanged. It never enters known.gold/gold_in, HomeTrip, affordability, shopping or actual gold state.

The optimistic denominator is no longer than the old empty-bag cycle, and D adds nonnegative latency to that cycle. Thus old-worth+B over each positive optimistic denominator dominates the sum of the two discounted final rates. Later ownership/health/route/horizon rejection can only lower the bonus. Longer positive D cannot increase the new term. This is a source arithmetic review, not an executed fixture.

## Limits and independent design check

No blocking design flaw found. Actual carried bag and the leadership-cleared claim mask were concrete implementation traps resolved above. Existing drafted/warm route estimates use their ordinary static centre/spawn conventions; they do not guarantee future occupancy, uncontested altar access, recall landing, future ownership or purchases. The final one-holder/current-visibility checks establish an actor-known solo valuation, not a future exclusive-recipient guarantee. Ordinary re-evaluation and existing banking/claim/safety behavior handle later changes.

Nominal B can retain a candidate through an optimistic prune even when final B becomes zero, changing work/candidate coverage under existing fuel cutoffs. Other champions receive zero B but compiled arithmetic/code layout can still affect cost. No fuel-equivalence, runtime activation, economic gain or strength claim is made. The approved Marcella2 r44–45 Gem Fields trace nomination remains for Luna, alongside recipient/tribute/shop/next-work checks after any observed divergence.
