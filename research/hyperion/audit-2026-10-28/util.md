# Audit: util (`bots/astraeus/src/util.h`)

## Changed

Commit `astraeus audit (util): cleanup`. The bench replays are byte-identical (8/8) and the fuel is unchanged: total 2211802776 -> 2211802776, 0 turns cheaper or dearer.

- **`my_handle_value`:** split its comment from the raw-read block above it. The new comment states the real constraint: it is initialised after `cambc::detail::cached_self` because cambc.h defines that first, and the ordering of inline variables depends on that.
- **`record_of` block:** dropped "so callers catch what they caught before", which was a transient migration detail.
- **`stun_pending`:** the comment is now about `c`, and still says it must be in sight.
- **`my_stunned`:** the six chained `contains` calls are now one `state.intersects(mask)`. The "a stun cancels channels" reasoning moved into the function comment, which now says what the function returns.
- **Raw reads grouped:** moved `fuel()` and `checked_round()` up beside `round_now()`, under the "imports read raw" comment that covers all three. They had been sitting between the two `make_field` overloads and the cost estimates.
- **Bitboard wrappers:** `test()` now sits under the shared "without check()'s call" comment. Before, it had a duplicate of that comment.
- **Field cost section:**
  - `search_cost_estimate` moved next to `search_chunks`, so the cost comment ("~1.5k + (20 + layers) per chunk") sits beside the formula. The comment now notes that the 4k base is a margin over the measured ~1.5k.
  - Added a comment to `max_field_layers`.
  - Documented `Field::goals` as the roots (the goals minus walls).

## Considered, not changed

- **Merging the three buff loops** (`has_stun`, `stun_pending`, `shield_value`) into one `buff_of(c, type)` helper that returns a pointer. It is cleaner, but the bench showed it costs ~2 fuel per turn (+90k over 44k turns, 34.9k turns dearer). That stayed true with `[[gnu::always_inline]]`. I reverted it.
- **`make_field` measuring with `cambc::fuel_remaining()`** (checked) rather than `fuel()`: this would save a few fuel per uncapped field. But it shifts `costliest_field()` and with it `full_field_cost_estimate()`, so it is not a pure cleanup. The effect is negligible.
- **`note_shortcut` / `print_fuel_log` using `cambc::self()`** where `my_handle()` would do: they are debug-only and free in release builds. Leaving them alone kept the declaration order simple.
- **The `- 1000` in `field_cost_estimate`** (giving an effective 3k base) is unexplained. It is a tuned constant that feeds fuel gates, so I left it as is.

## Suggestions

1. **Emblem factor declarations live in the wrong header.** `util.h:111-115` declares `camp_hit_factor`, `camp_dealt_factor` and `champion_dealt_factor`, which are defined in `economy/camps.cc:149-155`. They are game logic (emblem passives), not utilities, and belong in `economy/camps.h` or a small emblems header. Low severity, trivial effort, cross-file.
2. **The capped `make_field` heap-allocates its result.** `util.h:483` (`std::unique_ptr<Field>`) costs about 130 + 290 fuel for the allocation and free, on top of the `Field`'s own buffers. `Pathing::Slot` is `std::unique_ptr<Field>` (`model/pathing.h:185`). Making it `std::optional<Field>` (`Field` is movable) and returning `std::optional<Field>` would save ~420 fuel per capped or cached field, including `pathing.cc:48`'s `make_unique<Field>(make_field(...))`. Low to medium (fields are cached, so this is per recompute), small effort, cross-file.
3. **The capped `make_field` boundary cases.** `util.h:488`:
   - `static_cast<std::uint16_t>(max_layers)` wraps above 65535. `Pathing::make_centre` doubles `cap` until the field completes, but a field can never need more layers than the map has tiles (≤ 10000), so this can't happen in practice. Clamping to `unreachable - 1` would make it robust.
   - `layers >= max_layers` also rejects a field whose deepest step is exactly `max_layers - 1`, which is complete. That costs one wasted recompute at twice the cap. Using `layers > max_layers` would only be safe if the engine reports a cut-short search as `max_layers + 1` layers. That needs a probe, so I left it.

   Low severity.
4. **Combined buff read.** `stun_pending` and `shield_value` each make a `sdk_champion_buff_data` host call (~15-19 fuel). Some places read both for the same champion: `combat/plan.cc:1165-1166` and `combat/self_abilities.cc:201,210`. A `buffs(c)` returning `{shield, stun_pending}` from one call would save one host call per enemy evaluated. Small saving, small effort.
5. **`round_now()` and `checked_round()` are two raw reads of the same import** (`util.h:230-241`). The only difference is that `round_now` swallows a failure as round 0, which makes `throw_if_stale` throw. One function would do, and `checked_round`'s name hides that it is also just the round. Cosmetic, cross-file rename.
6. **`Tiles<N>` truncates silently.** `positions_within` (`util.h:416`) is documented "r <= 8". A caller passing a larger r gets a truncated set and no error. A `debug_block` assert on `r <= 8`, or a count check, would catch misuse. Low.
7. **Modelling check, no issue found.** `my_stunned` treats any listed stun buff at turn start as taking this turn. That matches `rounds.turn_start`: buffs that reached 0 expire before the turn runs. Marcella (stun-immune) never has the buff, and a champion on its respawn turn has no `can_*` bits but no stun buff either, so neither is misread. `stun_pending` (`duration > 0`) and `camp_stunned` (`timer > 0`) also agree with `abilities.stun` and probe-campstun.
