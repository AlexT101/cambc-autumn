# Audit 2026-10-28: bot (`src/bot.cc`, `src/bot.h`)

Bench: `tools/fuel/bench.py`, `--test-draft`, maps 00ambush 00lanes 01hooks 00interlock, 100M fuel.

## Changed

### Cleanup (`astraeus audit (bot): cleanup`): byte-identical, 8/8 replays
Total fuel +0.04%: the mean went from 50161 to 50181 a turn (about +20). That is codegen drift from the new helper boundaries, with no extra host calls.

- **File header.** The old one summarised the bot's whole strategy ("fights are taken whatever the numbers", ...), which I can't verify from here and which no longer describes this file. It now describes the turn: decide's branch order, act's wrap-up and play_turn's bookkeeping.
- **`search_strikes()`.** The 25-line strike-search block moved out of `decide()`, which now reads as its list of branches. Same calls, same order.
- **`note_search()` / `search_priced_end()`.** These replace the three loose globals `searched`, `searched_at` and `searched_hit` (now the `search` struct). The condition in `act()` (`!searched || pos != at || hit mismatch`) is now a named predicate. The host calls are made in the same order and short-circuit the same way.
- **`banks_bag()`.** Names `bankable_bag > 0 && !retaining_gems`, which appeared three times in bot.cc (and once negated in decide's first line).
- **`shop()`.** One helper for the dead branch and the alive branch. It encodes the rule: consumables need our spawn or death, shards need the same or Tavi. Purchase order unchanged: crystal, then shards, then lock.
- **`willow_free`.** Factors `willow && !mend && !leave` out of the two support conditions. The boolean algebra was checked term by term.
- **`camps_reach_spawn()`.** Uses `any_within(ally_spawn, m.pos, m.reach)` instead of hand-rolled rectangle-distance maths, and stops at the first hit. It still runs once a game.
- **`count_use()`.** Uses `my_cooldown(s)` instead of the raw duplicate SDK call.
- **Smaller edits.**
  - `decide`'s and `start_recall`'s single-use `auto& me` were inlined.
  - In `ward_bushes`, `tiles` (an int that shadowed the `.tiles` boards) was renamed `s`/`best_score`, and its comments say what the boards hold.
- **Comments.**
  - "A ward shares the recall's channel" was wrong in wording: a channel *refuses* a ward. That is why the early ward comes after the channel checks.
  - The `home` comment now says what it caches: want_home's answer, until a ward or shards change it.
  - The shield-before-search condition now says why: the shield would take the one cast.
  - The StaleTurn note sits where it applies to both catches.
  - Willow's formation reset in play_turn is now explained.
- **`bot.h`.**
  - Documented the undocumented `recovery_*` fields (the protected mate's heal stops beside Willow) and `formation_*` fields (Willow's wait), checked against `combat/support.cc`.
  - `wants_crystal` is sticky all game (nothing clears it), and its comment now says so.
  - `damage` is net of heals.

### Fix (`astraeus audit (bot): fixes`): behaviour change, though the 8 bench replays stay identical
`memory.health` (bot.cc, end of `play_turn`) was the health at the end of our code. But the engine heals a champion on its own spawn to full at turn end (rules: `rounds.turn_end`). So `memory.damage = max(0, memory.health - health)` read 0 for any hit taken on spawn. Example: end at 500/1000 on spawn, healed to 1000, a camp hits for 120, start at 880: damage read max(0, 500 - 880) = 0.

Ending on our spawn now records max health. Readers that now see such damage:
- `note_upkeep`: camp/champion upkeep accounting.
- `bank.cc:94,704,777`
- `capture.cc:198,232,269`
- `fight.cc:180`
- `shop.cc:605`

Only the rare case of enemies attacking into our spawn, or a camp reaching it, is affected. Fuel: +0.07% (+36 a turn) for one `test` host call. Needs an A/B before keeping, like any behaviour change.

## Considered, not changed

- **Double refresh.** `see_stuns(...)`, `safety.refresh()` in decide refreshes twice when a stun was read: see_stuns already refreshes the rebuilt Safety. The second call returns early on an unbuilt Safety, so it is cheap. Left alone.
- **Redundant guards.** `world.me().alive &&` before `see_revealed` in `act` repeats a check inside see_revealed, but the outer check saves a host call for dead champions.
- **Bush-ward tile choice.** `ward_bushes` drops our own cluster from the candidates, because we see it from inside. A ward there would still help once we step out. That's a judgement call, not a bug.
- **Mend under a camp.** `mend` refuses to mend under a camp that reaches spawn even when badly hurt. In practice `want_home` then sends us to `retreat`, and ending on spawn heals anyway, so the outcome is mostly the same. See the suggestion below for an exact version.
- **Function-local static.** I kept `camps_reach_spawn`'s `static int known` instead of a function-local `static const bool` initialiser, to avoid the guard-variable cost on every call.

## Suggestions

1. **The mend turn stands still, but `home_trip` prices it as free when a spawn tile is a step closer.** (bot.cc decide's `mend` branch; `economy/shop.cc:543-555`.) Medium value, small to moderate effort.
   - `home_trip` sets `hurt = 0` when a landing tile one step nearer the altar exists. Its reasoning: we step there and the turn end on spawn still heals.
   - `decide`'s `'H'` branch only attacks and casts; it never walks.
   - So the recall's value assumes a step the bot never takes, and every hurt recall arrival costs a full turn (or a step).
   - Fix: in the mend branch, when `my_can_move()` (and for ranged champions, when we didn't attack), step to a spawn tile nearer the next goal: the altar field when carrying, else the farm group's approach.
2. **Mend on a 1-HP deficit.** `mend = on_spawn && my_health() < my_max_health() && ...` (bot.cc decide). Small value, small effort.
   - Any deficit costs a whole turn on spawn; a recall arriving at 990/1000 waits a turn for 10 HP.
   - Making suggestion 1's step removes most of the cost. Otherwise, compare the gain with `heal_rounds_now()`.
   - Also, the camp condition could be exact: mend while `my_max_health() - my_health() > safety.camp_damage(p)`, so a mend turn nets health. That ends the "mend forever" case without refusing to mend at all.
   - `camp_damage` also ignores that a monster hits only the nearest champion, so an ally on spawn nearer the camp takes the hit.
3. **A ranged champion with a dash gives it up after attacking.** `if (attacked && !walk_and_attack_independent()) return;` (bot.cc decide, before wants_shop). Low-medium value, small effort.
   - The ranged attack spends the walk, but no ability spends the walk (rules: `abilities.exclusive`).
   - So Vesper Vale (ranged plus dash) skips shop/chase/contest/siege/farm, and their dash hops, whenever she has attacked.
   - The farm's own dash hops (`take_hop`) could still run with `!my_can_move()`.
   - Check what farm does with a spent walk before relaxing the return for dash holders.
4. **`count_use` misses casts when Vendetta's passive readies both slots on a kill** (bot.cc count_use). Low value, trivial effort.
   - A slot cast this turn then shows cooldown 0, so the cast, and for her reset the extra attack, go uncounted. This feeds `shop.cc:35-40`'s focus-or-strength choice.
   - A related small over-count: for Vesper Vale, walk + dash + reset + attack counts 2 attacks, because `dashed` cancels `walked`.
   - Fix: count casts by comparing `my_cooldown` with the turn-start cooldowns, or set a flag at each cast site.
5. **Bush ward tile choice** (bot.cc `ward_bushes`, the `Tiles<3>{best}` loop). Low-medium value, moderate effort.
   - The ward goes on the first of up to 3 cluster tiles in scan order (those not beside us preferred).
   - A ward's sight is the 13x13 square around its tile even inside its cluster (rules: `vision.occlusion`, `wards.vision`), so in a big cluster the tile decides which part we see.
   - Better: pick the tile whose radius-6 square covers the most cluster tiles within ability range of here and of our work. That is the same score the cluster choice already uses.
   - I couldn't find a reason for the "not beside us" preference. If it has one, it deserves a comment.
6. **An ally's ward on our drafted tile** (bot.cc `ward_planned`). Low value, small effort.
   - A visible allied ward on the drafted tile makes us fall back to a bush ward, but its vision is not ours (rules: `vision.personal`). A neighbour of the drafted tile would give nearly the same sight.
   - An *unseen* allied ward there is a hidden blocker: we retry, and fail, every turn while in range. That's one wasted host call a turn.
7. **Fuel gate in `ward_bushes`.** `if (!fuel_ok(floor)) note_shortcut("ward-no-bushes-fuel")`, plus the `find_bush_clusters(..., floor)` refusals. Low value, moderate effort.
   - The cost is only a ward a turn late, and main.cc's turn-end queue already grows clusters around us.
   - To remove the gate, make the end-of-turn bush ward choose only from clusters already grown, so its cost is bounded. A missing cluster then waits for the queue instead of for fuel.
8. **Cross-file: move `banks_bag` to bank.cc next to `bankable_bag`.** Trivial effort.
   - The same expression is spelled out in `fight.cc:717`, `shop.cc:605` and `support.cc:335`.
   - Also `may_shop()` (shop.cc) returns true for everyone but Tavi. It means "shopping needs a trip home", and the name reads as the opposite: rename it, e.g. `shops_at_home`.
9. **`memory.damage` is net of a teammate's heal between our turns** (bot.cc play_turn). Low value, moderate effort. Willow healing us hides damage taken in the same gap. Reading heals would need buff or heal events; I'm noting it only because several branches read `damage > 0` as "under fire".
10. **Recall started at every turn end** (bot.cc `start_recall`). Unknown value; needs an A/B or a look at enemy bots. The trick makes a wanted recall a turn shorter, but it shows us as `recalling` to every enemy that sees us (rules: `vision.visible_champions` exposes state). An enemy bot that hunts recalling champions, or reads it as retreat, gets a free signal every turn. Worth weighing against the turn saved.
