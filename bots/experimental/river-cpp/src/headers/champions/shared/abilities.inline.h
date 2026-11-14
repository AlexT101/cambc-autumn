// Inline functions and templates, defined after every class: src/unity.cpp includes this after
// every header (the declarations are in them).
#pragma once

namespace aph {
namespace {
// The landing that `keep` accepts whose `radius` around it hits most, nearest `here` on ties.
template <class Keep> Cast best_landing(int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep)
{
    Cast best;
    if (targets.empty()) return best;
    // Dash landings are within 2 of `here`. Each cell adds its targets in their order, as summing per landing would.
    constexpr int reach = 2, side = 2 * reach + 1;
    std::array<float, side * side> value{}, rank{};
    const bool ranked = targets[0].rank >= 0;
    for (const auto& t : targets) {
        const int x0 = std::max(t.pos.x - radius, here.x - reach), x1 = std::min(t.pos.x + radius, here.x + reach);
        const int y0 = std::max(t.pos.y - radius, here.y - reach), y1 = std::min(t.pos.y + radius, here.y + reach);
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) {
                const int i = (y - here.y + reach) * side + (x - here.x + reach);
                value[i] += t.weight * t.worth, rank[i] += t.weight * t.rank;
            }
    }
    int best_dist = 0;
    for (auto p : Tiles<5 * 5>{landings}) {
        const int d = dist(p, here);
        const int i = (p.y - here.y + reach) * side + (p.x - here.x + reach);
        const float v = value[i], k = ranked ? rank[i] : v;
        if (v < min_value || k < best.key() || (k == best.key() && d >= best_dist) || !keep(p)) continue;
        best.slot = slot, best.value = v, best.rank = ranked ? k : -1, best.tile = p, best.dash = true, best_dist = d;
    }
    return best;
}

}
}
