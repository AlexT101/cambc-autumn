#include <array>
#include <cassert>
#include <cstdint>
#include <utility>
#include "../../bots/hyperion/src/gold_value.h"

using aph::gold_value::incoming;
using aph::gold_value::inventory_stamp;
using aph::gold_value::percent;
using aph::gold_value::share;
using aph::gold_value::treasure_owned;

int main() {
    // Partial Treasure shards are not an emblem; any one of its three completed stats is.
    assert(!treasure_owned({0, 0, 0})); // Production queries emblem counts; partial shard counts do not enter.
    assert(treasure_owned({1, 0, 0}));
    assert(treasure_owned({0, 1, 1})); // Multiple Treasure stats still add the bonus once.
    assert(percent(0, false) == 100);
    assert(percent(33, false) == 133);
    assert(percent(33, true) == 153);

    // Conservative integer budget: observed shares are split first, then multiplied once.
    assert(incoming(20, 100) == 20);
    assert(incoming(20, 133) == 26);
    assert(incoming(20, 120) == 24);
    assert(incoming(20, 153) == 30);
    assert(incoming(100, 153) == 153); // additive +33 and +20, never compounded
    assert(incoming(1, 133) == 1); // The unobservable fraction is conservatively discarded.
    assert(share(70, 3, true) == 24);
    assert(share(70, 3, false) == 23);
    assert(incoming(share(70, 3, true), 153) == 36);
    assert(incoming(share(70, 3, false), 153) == 35);

    // These are the live inventory stages that can occur around one same-turn shop call.
    std::array<std::uint8_t, 21> inventory{};
    const auto ordinary_power_strength = 1u * 3u + 0u; // family power=1, strength=0
    const auto treasure_strength = 3u * 3u + 0u;       // family treasure=3, strength=0
    inventory[ordinary_power_strength] = 2;
    const auto ordinary_begun = inventory_stamp(inventory);
    inventory[treasure_strength] = 1;
    const auto ordinary_then_treasure = inventory_stamp(inventory);
    inventory[treasure_strength] = 0;
    const auto treasure_complete = inventory_stamp(inventory);
    assert(ordinary_begun != ordinary_then_treasure);
    assert(ordinary_then_treasure != treasure_complete);
    assert((std::pair{false, ordinary_begun} != std::pair{true, treasure_complete}));
    assert(treasure_owned({1, 0, 0})); // Completion is separately represented by the existing key bit.
    inventory[ordinary_power_strength] = 0; // The ordinary chooser resumes after Treasure.
    const auto ordinary_exit = inventory_stamp(inventory);
    assert(ordinary_exit != treasure_complete);
    assert(inventory_stamp(inventory) == ordinary_exit); // Repeated lookup is stable.

    // Actual gold-only preferred-holder gate: these negatives must never qualify.
    using aph::gold_value::gold_only_holder;
    assert(gold_only_holder(true, true, true, true, false, false, false, false));
    assert(!gold_only_holder(false, true, true, true, false, false, false, false));
    assert(!gold_only_holder(true, false, true, true, false, false, false, false));
    assert(!gold_only_holder(true, true, false, true, false, false, false, false));
    assert(!gold_only_holder(true, true, true, false, false, false, false, false));
    assert(!gold_only_holder(true, true, true, true, true, false, false, false));
    assert(!gold_only_holder(true, true, true, true, false, true, false, false));
    assert(!gold_only_holder(true, true, true, true, false, false, true, false));
    assert(!gold_only_holder(true, true, true, true, false, false, false, true));
}
