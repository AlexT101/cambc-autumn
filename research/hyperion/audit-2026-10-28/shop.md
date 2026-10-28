# Audit: economy/shop.cc (shop)

## Changed

**Commit 1, cleanup (a82cec49).** Replays byte-identical (8/8 on 00ambush, 00lanes, 01hooks, 00interlock, test drafts). Fuel: total +0.01% (mean 50161 -> 50168 a turn), most likely from codegen layout. Round 1 is -0.1%.
- `buy_lock` and `buy_crystal` share a new `buy_consumable(type)` instead of two copies of the same try/can_buy/buy/spent block.
- `priced_upkeep(world, others)` replaces the three-line upkeep choice (fold the steps, then siege_upkeep or upkeep) that best_emblem and affordable_prefix both repeated. `mean_spawn_steps(u)` replaces the mean formula that upkeep_cost and spawn_steps both repeated.
- best_emblem: the passive-emblem tail ("five shards in stat a or b plus the best passive"), which Prism's branch and the general branch both repeated, is now the `or_passive(best, a, b)` lambda. Both now go through the families in the order {prospector, capture, treasure, hunter, tribute}; Prism's order had tribute before hunter. That only matters on an exact float tie between those two passives, so it is effectively unreachable, and the replays confirm it.
- Removed dead code: the unused `map` in note_upkeep, the unused `self` in best_emblem, and `!f.heals()` in the Tavi Hunter test (tavi_gold already implies Tavi).
- `income_prior` and `reachable_clusters` now use `static const` lambda initialisation instead of hand-made flags. `reachable_clusters` stops scanning a group's members at its first cluster and still calls `ally_steps` only for cluster groups, so it never builds a field the old code didn't.
- Comments:
  - Removed the "v61" provenance tags and "2.0.0-family".
  - Rewrote main_stat's comment (it was hard to parse) and emblem_begun's (it was wrong: the code also covers Prism's Home and Monster shards and every 3-pick Monster).
  - Moved passive_saved's comment off the IncomeRates struct it was sitting on.
  - Moved the kill-gold constants to the top.
  - Rewrote wants_shop's header.
  - Added a line in home_trip saying what `hurt` means.

**Commit 2, fixes (d2f7c4eb).** `affordable_prefix`'s cache key now includes `main_stat(world)`, as `prices()` already does. Its cached `next` comes from best_emblem, which picks Power, Jungle or Bruiser in the main stat. main_stat follows the attack and cast counts, which change without any stat changing, so the cached quote could name an emblem that best_emblem (and so buy_shards) would no longer buy. Replays stay identical on the 4 bench maps (the main stat never flipped while cached there). Fuel is +0.03% over commit 1.

## Considered, not changed

- **Merging the two arms of wants_shop.** Prism compares with its own `hurt`, rejects an unreachable spawn and rejects ties. The others use home_trip's altar-based `hurt`, accept an unreachable spawn and accept ties. Merging them would change behaviour; see Suggestions 4 and 5.
- **Hoisting `to_ally_spawn()` above the Prism win/closing checks in wants_shop.** That would build the field on turns that don't need it, so I left it.
- **Turning emblem_begun into a by-product of best_emblem's "begun" checks.** The two lists must agree, but best_emblem interleaves those checks with its ordering of forced and passive emblems. A shared helper needs care to stay identical; see Suggestion 6.

## Suggestions

1. **Greed, Skirmish and Collectors are never bought.** `shop.cc:345-370` (best_stat) and the passive loop in `or_passive` never offer them; best_emblem only finishes one that is already begun, which never happens.
   - Greed: 25 shards with the stats of 35, against Power's 30 for 25 (five emblems of 6).
   - Skirmish: +5% to champions.
   - Collectors: +1% to camps and champions per family; with 3-4 families it is close to Monster's camp bonus, and it applies to champions too.
   - Greed cannot simply be added as a candidate, because candidates are compared by `saved` alone, which only works when every one costs 150. Greed costs 750 and pays its bonus only at 25 shards, so it needs a per-gold comparison or a multi-emblem horizon.
   - Skirmish and Collectors' champion side needs a fight-value term; the upkeep model is camp-only.
   - Severity: medium for long games. Effort: medium.
2. **main_stat ignores Focus-scaled heals and shields, and the landing term is inconsistent.** `shop.cc:31-43`.
   - Willow's heal (3x Focus) is her main job, but she has no damage spell, so main_stat gives Strength.
   - Varg's (2.5x) and Heart of Ruin's (1.5x) shields scale with Focus and are uncounted.
   - Heart of Ruin's landing damage (`lands()`) counts in the measured `cast` but not in the `spells` prior (line 41 sets `cast = spells`), so its prior is lower than its measured rate.
   - Severity: medium for Willow, low otherwise. Effort: low (add heal and shield multipliers, weighted by casts, and add landings to `spells`).
3. **affordable_prefix's single-entry cache thrashes.** `shop.cc:499-543`. Calls with `gold_in > 0` (capture.cc:378, Prism capture recall) and with `gold_in = 0` (wants_shop) have different `budget / shard_price` keys. When both happen near each other, each call reruns the full best_emblem chain, about 5-25 best_emblem calls. A two-entry cache, or keying `gold_in = 0` separately, removes that. Severity: fuel only, low-medium. Effort: low.
4. **Prism never takes a shopping trip from where walking can't reach spawn, unlike everyone else.** `shop.cc:618` returns false when `back == unreachable`. The non-Prism arm (line 626) skips the comparison and shops, relying on the per-turn recall that continue_recall keeps (bank.cc:743). A Prism in a crystal pocket with gold never goes home to shop. Severity: low. Effort: low, but it changes behaviour, so it needs an A/B.
5. **The shop trip's `hurt` comes from the altar field.** wants_shop's non-Prism arm uses `home_trip(...).hurt` (`shop.cc:544-556`). That says whether the first step from the recall landing towards an altar stays on spawn, but after shopping we walk back out towards `here`, not an altar. Prism uses `hurt = 1` whenever hurt. The exact test is the same check against `to_ally_spawn`-reversed distances, or a field to `here`. Severity: low (one turn of cost error). Effort: low-medium.
6. **emblem_begun and best_emblem's begun logic are two lists that must agree.** `shop.cc:104-116` against `shop.cc:331-343`, `384-401`. emblem_begun accepts any stat of Jungle, Power, Durability and Bruiser; best_emblem finishes only some of them (for example Durability only in Health, Power in Health only for Prism). They agree today only because best_emblem never starts the others. A single `begun_emblem(world, owned) -> optional<{family, stat}>` used by both would remove the drift risk. Severity: low. Effort: low-medium.
7. **The lock is bought from leftover gold, which can push the next shard back.** `bot.cc:224-226` calls buy_lock after buy_shards. With 35 gold the lock leaves 25, one short of a shard. Whether a lock beats a shard sooner is a judgement call that isn't priced anywhere. Severity: low. Effort: medium (price the lock).
8. **Ryth's Health shards are under-priced.** best_stat (`shop.cc:345`) offers Power only in the main stat, which is Strength or Focus. For Ryth (health_strength) a Health shard gives 100 HP plus 1 Strength, and add_shards already models that, but only Bruiser and Durability Health are candidates, never Power Health. Severity: low. Effort: trivial (add `value(power, health_stat)` when `f.passive == Passive::health_strength`), then A/B.
9. **Retaliation kill gold can be misattributed.** note_income_start (`shop.cc:572`) assumes gold gained between turns is a capture payout. Ren's retaliation can kill during an enemy turn: its 100 gold is then counted as capture gold if we stood on a group, and dropped otherwise. Severity: very low. Effort: low.
10. **Naming: `may_shop` returns false for Tavi**, who can shop anywhere. It really means "may take a shopping trip". Renaming it to `shops_at_home` touches bank.cc and capture.cc callers, so it is a cross-file follow-up.
11. **Tavi's sell-on-spawn passive (full refund) is unmodelled.** Tavi could re-spec begun shards when its main stat flips. Severity: low. Effort: medium.
