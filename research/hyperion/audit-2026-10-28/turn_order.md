# Audit: turn_order (`bots/astraeus/src/model/turn_order.{cc,h}`)

Line numbers are for the file after both commits.

## Changed

**Cleanup (55f45b56): byte-identical 8/8, fuel +0.01% (about +3 per turn, from the new call boundaries).**
- `set_turn_order` was one long nested function. Its bidding body is now `bid(world, safety) -> Wish` (turn_order.cc:383), with early returns instead of two levels of nesting. The teacher-priority fallback, which appeared twice (the fuel-short path and the no-bid path), is now `plain_priority(world)` (:138). `set_turn_order` is 10 lines.
- `unacted_share` now sits with the band constants instead of between the type static_asserts and `Wish`.
- Comments: dropped "(v61)". `enemy_next_rank` said "At most `e`'s rank", which reads backwards; it now says "A lower bound on". Reworded `live_self`'s comment ("moved. The fields read here only:").

**Fix (17e140ad): not byte-identical (2/8 games differ: 00ambush b, 00lanes b); fuel -0.01%.**
- `packed_priority` mapped raw 0 to engine priority 0 so that it would "keep its sign", but `comms::payload_of` (comms.cc:253) reads `next_priority == 0` as "no payload". Raw 0 has exactly one source: an idle Prism with no gems at 80-90% effective health (`role 0 + 8 - 8*1`). In that state Prism's payload was dropped: the claim mirror and, more importantly, the support-mailbox bits Willow reads (`support_protected` is Prism). That is a common state while farming, because camp damage never enters the danger band. Raw 0 is now encoded like any other raw. The rank `(code - code0)*8 + 7 - index` is never 0 (index <= 5, so `7 - index >= 2`), and signs and order are unchanged. The only side effect is that raw-0 ties between allies now go by index, which matches the engine's id tie order.

## Considered, not changed

- **The 13 type static_asserts:** these could be folded into one constexpr loop, but they read clearly as they are.
- **`Strikes`' union:** it looks odd, but it avoids zeroing about 320 bytes per use, and the engine charges per byte.
- **The `rank_code` compression:** I checked it is order-preserving for every value the bands can produce. Protect values are 0 or 10 mod 15 (life 300, recall 60, tribute 100, plus 15 per gem). Kill values are 0, 7 or 10 mod 15 (halved kills give 7.5 per odd gem, truncated to 7). The clamped 9999 codes above all of them. Headroom: the maximum rank is (3358\*8+7) = 26871 < 2^15, and the minimum is -584 << 16. If `params` values change, the static_assert catches it.
- **`next_slot`:** checked against rules.champion_order (alternation, with the larger team's extras in a row).
- **The `ours.stuns[d]` index in `offer_kills`:** it is safe because `!ours.hits(d)` skips first, and `reach <= max_reach`.

## Suggestions

1. **`offer_escape` bids even when it cannot save us** (turn_order.cc:346-361, severity medium, effort small). It bids `protect` if *total* damage (camps, plus unacted enemies doubled, plus everyone's next-round blow) reaches our health. Camp damage and unacted enemies' this-round turns land before our next turn whatever the order, so the bid only helps if that unavoidable part alone does **not** kill us. Splitting the sum (unavoidable < hp <= total) would stop doomed champions outranking allies' useful bids (another ally's kill, Willow's heal). `may_escape` (:324) would need the same split.
2. **`offer_channel` bids for threats that ordering cannot deny** (:295-310, severity low-medium, effort small). Any threat from `threats_at` triggers the bid. An enemy that has not acted this round gets a turn before our channel completes whatever our rank. So if every threat comes from such an enemy whose one-turn strike already reaches us, the bid is wasted. `offer_escape`'s `turns_before_ours` logic is the model to reuse. Separately, our own recall and teleport add `15 x gems` to the value, while the enemy-side recall and teleport cancels in `offer_kills` (:279-282) don't. A recall cancel doesn't cost gems, so one side is inconsistent.
3. **`side_damage` misses allies yet to act this round** (:248-255, severity low-medium, effort small). An ally acting after us this round strikes the enemy before the enemy's next-round turn whatever the order. Only allies' next-round turns (ranked before `their`) are counted, so kill bids are under-offered in team fights. The caveat is that the enemy (if unacted) also moves in between.
4. **`offer_heal` ignores the ally's shield, Durability, turn order and the second blows from unacted enemies** (:364-379, severity low, effort small). It compares raw summed strikes with `ally.health`. `ally.shield` (Varg/HoR) and `ally.taken` exist on the belief and should enter (`damage * taken >= health + shield`). It also never checks `can_act_before` against the enemies concerned, unlike `offer_kills`.
5. **Fuel-short path keeps last turn's rank** (:425-429, a fuel gate, severity low, effort trivial). When `fuel < end_reserve` we keep the previous turn's rank, possibly a stale kill or protect bid. Yet the same branch already computes `plain_priority` when no rank exists, so it is affordable. Always taking `plain_priority` (one `priority_self` plus a few teacher strikes, a few thousand fuel at most) would remove the gate. The bids themselves are what is expensive (threats, refresh). Needs an A/B: it changes behaviour only on short turns.
6. **Enemies on their spawn are never kill targets** (:263, severity low). Rules let us attack into the enemy spawn. A champion standing there has healed to full at its turn end, but a big burst (e.g., Stellar/Prism spell plus basic, or allies) can still kill it from outside. This is a judgement call, but `test(enemy_spawn, ...)` could become a check that some tile from which we can hit it is reachable.
7. **Teacher champions (Prism, Vesper, Ryth, Vendetta, Marcella, HoR) never bid** (:386). A teacher-champion Marcella or Vendetta at kill range of a low enemy is ranked only by `teacher_priority`'s danger buckets, which compare strike to health but with no "act before that enemy" condition. Consider letting every champion bid `kill` (and Prism `protect` for its tribute) on the shared scale; the band scale is already above every teacher value. Needs an A/B.
8. **Header nit** (turn_order.h:10-12): "None in a priority of 0" is now true only before a champion's first publish.
