# Audit: main.cc, unity.cpp (2026-10-28)

## Changed

Commit `astraeus audit (main): cleanup`. The bench replays are byte-identical (8/8). Fuel went down 0.09% in total (mean 50161 -> 50118, round-1 max 266236 -> 264403), from codegen only.

- **Allocator** (`main.cc:30-84`): the core allocator is now nothrow (`heap_take`, `try_take` return null on failure), and the throwing `operator new`s wrap it in `or_throw`, which calls a noinline, noreturn `out_of_memory()`. This removes four `try/catch` blocks from the nothrow overloads. I also dropped a dead clamp in the aligned path: `align < sizeof(void*) ? sizeof(void*) : align` could never apply, because any alignment up to 16 already goes to `malloc`.
- **Includes**: the list is down to the headers main.cc actually uses (`safety.h` and `champions.h` are gone) and is sorted. I added `<bit>` (for `std::countr_zero`), `<algorithm>` and `<vector>`. This has no effect in the unity build.
- **Queue budget**: `TurnEndQueue::run` now works out the real budget itself (2x on `first_round`), so the caller passes only `start`. I also dropped `using aph::end_reserve;`, which had been used inconsistently with the qualified name.
- **Comments**: I removed the FUEL-GATES and EXPERIMENTS references and the bench-measurement detail, and condensed the `turn_fuel` and arena comments. unity.cpp now says that every `.cc` must be listed and that the include order changes codegen. The list is complete: 21 `.cc` files.

There is no fixes commit.

## Considered, not changed

- **Arena rounding `(n | 1)`** (`main.cc:35`): this is wasteful. Any `n` that is a multiple of 16 takes 32 bytes more than the rounded `n` needs (16 -> 32, 1280 -> 1296), not just the zero-byte case it is meant for. I tried `(n + 15 + (n == 0)) & ~15`. The replays were identical and fuel was +0.08%, which is codegen noise. On these 4 maps the 2 MiB arena never fills, so the waste costs nothing there. I reverted it. Revisit only if the arena is shown to fill: see suggestion 4.
- **Reordering unity.cpp alphabetically**: this changes codegen and so fuel. It isn't worth the risk for readability alone.

## Suggestions

1. **A ward placed this turn never refreshes comms vision** (`main.cc:266-270`, `bot.cc:217`). `refresh` (and so `world.observe()` in `comms::send`) is triggered only by `moved`. A ward placed this turn adds up to 13x13 of vision that `send` never reads, so a sighting the new ward makes isn't posted until next turn. Fix: also refresh when `cambc::self().ward_cooldown()` shows a placement this round (or `Memory` records one). Severity low to medium, effort small.
2. **While dead, the queue warms around the death tile** (`main.cc:221`). A dead belief keeps its last `pos` (`world.cc:1581` doesn't reset it), so 60 dead turns warm a radius-20 ring around where we died. The next walk starts from spawn. Warming around `spawn()`, then along the walk to `memory.farm_group`, is probably more useful. This changes fuel only (and therefore real-budget play), so it needs an A/B. Severity low, effort small.
3. **The queue's budget scaling ignores start-up** (`main.cc:147-149`). The comment says it "fills the same at any budget", but on the first turn the real budget has already paid start-up before `start` is read, and the 100M run hasn't. So bench/100M runs warm slightly more on turn 1 than the ladder does. This matters only if bench results are meant to mirror the ladder exactly. One fix is to read `start` at the top of `main()` for the first turn. Severity low.
4. **Arena capacity is unmeasured.** It would help to add a `debug_block` that prints `arena_used` at round 2000 on a 100x100 map with a long game. If the arena ever fills, fix the `(n | 1)` waste from "Considered" and maybe size the arena from that measurement. Effort small.
5. **A resumed out-of-fuel turn inside the queue** (`main.cc` `TurnEndQueue::run`). If the queue ever overran (its estimates were wrong), the resumed round would keep warming, down to `floor`, from the new round's fresh 100k before the real turn runs. Only `prepare_next_turn` is followed by an `is_stale()` check; `around()`, `warm_up` and `warm_centres` aren't. A cheap `world.is_stale()` test inside `room()` (one host call per tile) would bound this. Severity low (it needs a misestimate first), effort trivial.
6. **`print_fuel_log` is skipped on every early return** in `play_turn`, so debug fuel samples pile up and print under a later turn. This is debug-only. An RAII guard would fix it. Severity cosmetic.
7. **`comms::send`'s `moved` vs `sight_pos_`**: these are equivalent today, because `observe()` updates `me().pos`. If that ever changes, `moved` should compare against World's `sight_pos_` (it is private now). There's nothing to do now.
