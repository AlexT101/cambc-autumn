// Inline functions and templates, defined after every class: src/unity.cpp includes this after
// every header (the declarations are in them).
#pragma once

namespace aph {
namespace {
// Each camp member whose strike reaches p, as f(group, member index, member), in groups_near order;
// stops at the first f that returns false.
template <class F> bool each_camp_striker(const World& world, vec2 p, F&& f)
{
    for (const int g : world.map().groups_near(p, world.map().max_camp_reach)) {
        const auto& members = world.map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (members[i].strength > 0 && dist(p, members[i].pos) <= members[i].reach && !f(g, i, members[i])) return false;
    }
    return true;
}

// The neighbouring station `ok` accepts from which a heal lands best: the most restored, then on
// the lowest ally, then the least `cost`. `here` if none.
template <class Ok, class Cost> vec2 heal_station(const World& world, Pathing& pathing, Safety& safety, vec2 here, const std::array<HealView, 8>& views,
                  int n, Ok&& ok, Cost&& cost)
{
    vec2 best = here;
    float best_gain = 0, best_fraction = 0;
    int best_cost = unreachable;
    for (int k = 1; k < 9; ++k) {
        const auto& tile = stations(world, safety, here).tiles[k];
        if (!station_legal(pathing, tile, here) || !ok(tile)) continue;
        const int g = world.map().group_at(tile.p);
        if (g >= 0 && world.camps[g].state == CampState::cleared) continue;
        const int c = cost(tile);
        for (int t = 0; t < n; ++t) {
            const auto& target = views[t].target;
            if (!support_view(views[t].viewers, target.pos, tile.p)) continue;
            if (target.gain > best_gain || (target.gain == best_gain && target.fraction < best_fraction)
                || (target.gain == best_gain && target.fraction == best_fraction && c < best_cost))
                best = tile.p, best_gain = target.gain, best_fraction = target.fraction, best_cost = c;
        }
    }
    return best;
}

}
}
