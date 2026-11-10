// Enemy turn windows (see turn_window.h).
#include "turn_window.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include "world.h"

namespace aph {

namespace {

constexpr int window_cap = 16, slot_cap = 32, far_off = 99;

struct Windows {
    int round = -1;
    std::uint32_t observations = 0;
    int n = 0;
    std::array<std::int8_t, window_cap> early{}, late{};
    int unseen_after = 0; // this round's enemy turns after ours not held by a visible enemy yet to act
    std::uint16_t after_mask = 0; // the unseen enemies given those turns
    // Next-round sets of enemies with a turn before ours, per projected slot of ours.
    std::uint32_t second_known = 0;
    std::array<std::uint16_t, slot_cap> second{};
};

Windows windows;

int unseen_distance(const ChampionBelief& e, vec2 from);

bool settled(const World& world, const ChampionBelief& e) {
    return !world.enemy_priorities_change || (e.visible && e.acted && e.priority_round == world.round);
}

SlotLayout layout_of(const World& world, bool ally, int r) {
    const int others = static_cast<int>(ally ? world.enemies.size() : world.allies.size());
    const bool first = ally == (world.map().team_a == (r % 2 == 1));
    return {others, first};
}
// Enemy ranks (0..count-1) whose slot in a layout comes before `slot`: the slots rise with the rank,
// so the first rank at or past it, in closed form (a loop here was vectorised, ~0.5k a call).
int ranks_before(const SlotLayout& l, int count, int slot) {
    const int x = slot - (l.first ? 0 : 1);
    const int alternating = x <= 0 ? 0 : (x + 1) / 2;
    if (alternating < std::min(l.others, count)) return alternating;
    if (count <= l.others) return count;
    return std::min(count, std::max(l.others, slot - l.others));
}

[[gnu::noinline]] void build_windows(const World& world) {
    auto& w = windows;
    w.round = world.round;
    w.observations = world.observations;
    w.second_known = 0;
    const int size = static_cast<int>(world.enemies.size());
    const int n = std::min(size, window_cap);
    w.n = n;
    // Read each belief once: the beliefs are large, scattered records.
    std::array<int, window_cap> prio;
    std::array<std::uint32_t, window_cap> handle;
    unsigned settled_bits = 0;
    int pending = 0;
    for (int i = 0; i < n; ++i) {
        const auto& e = world.enemies[static_cast<std::size_t>(i)];
        if (settled(world, e)) settled_bits |= 1u << i;
        prio[static_cast<std::size_t>(i)] = e.next_priority, handle[static_cast<std::size_t>(i)] = static_cast<std::uint32_t>(e.handle);
        pending += e.alive && e.visible && !e.acted;
    }
    for (int i = n; i < size; ++i) {
        const auto& e = world.enemies[static_cast<std::size_t>(i)];
        pending += e.alive && e.visible && !e.acted;
    }
    const int unsettled = n - std::popcount(settled_bits);
    for (int i = 0; i < n; ++i) {
        if (!(settled_bits >> i & 1)) {
            w.early[static_cast<std::size_t>(i)] = 0;
            w.late[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(n - 1);
            continue;
        }
        const int pi = prio[static_cast<std::size_t>(i)];
        const auto hi = handle[static_cast<std::size_t>(i)];
        int above = 0;
        for (unsigned b = settled_bits & ~(1u << i); b; b &= b - 1) {
            const int j = std::countr_zero(b);
            const int pj = prio[static_cast<std::size_t>(j)];
            above += pj > pi || (pj == pi && handle[static_cast<std::size_t>(j)] < hi);
        }
        w.early[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(above);
        w.late[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(std::min(n - 1, above + unsettled));
    }
    const int ours = world.slot(world.me(), world.round);
    const int after = size - ranks_before(layout_of(world, false, world.round), size, ours + 1);
    w.unseen_after = std::max(0, after - pending);
    // The turns go to the unseen enemies nearest our turn's start (then the strongest): the others
    // keep acting before us. Every unseen one would widen each threat check for a turn few can take.
    w.after_mask = 0;
    if (w.unseen_after > 0) {
        const vec2 from = in_bounds(world.turn_start) ? world.turn_start : world.me().pos;
        struct Unseen {
            int d, i;
            float strength;
        };
        std::array<Unseen, window_cap> u;
        int k = 0;
        for (int i = 0; i < n; ++i)
            if (const auto& e = world.enemies[static_cast<std::size_t>(i)]; e.alive && !e.visible)
                u[static_cast<std::size_t>(k++)] = {unseen_distance(e, from), i, e.strength};
        // A strict order, so any sort gives std::sort's result; a few items, so by insertion.
        if (k > w.unseen_after) {
            const auto before = [](const Unseen& a, const Unseen& b) {
                return a.d != b.d ? a.d < b.d : a.strength != b.strength ? a.strength > b.strength : a.i < b.i;
            };
            for (int j = 1; j < k; ++j) {
                const Unseen x = u[static_cast<std::size_t>(j)];
                int m = j;
                for (; m > 0 && before(x, u[static_cast<std::size_t>(m - 1)]); --m) u[static_cast<std::size_t>(m)] = u[static_cast<std::size_t>(m - 1)];
                u[static_cast<std::size_t>(m)] = x;
            }
        }
        for (int j = 0; j < std::min(k, w.unseen_after); ++j) w.after_mask |= static_cast<std::uint16_t>(1u << u[static_cast<std::size_t>(j)].i);
    }
}

const Windows& current(const World& world) {
    if (windows.round != world.round || windows.observations != world.observations) build_windows(world);
    return windows;
}

// An unseen enemy's distance to `from`, by where it was last placed (a possible-set search costs too much fuel).
int unseen_distance(const ChampionBelief& e, vec2 from) {
    if (!e.tracked || !in_bounds(e.pos)) return far_off;
    return dist(from, e.pos);
}

[[gnu::noinline]] std::uint16_t pick_second(const World& world, const Windows& w, int ours) {
    const SlotLayout l = layout_of(world, false, world.round + 1);
    int room = ranks_before(l, static_cast<int>(world.enemies.size()), ours);
    std::uint16_t chosen = 0;
    if (room <= 0) return chosen;
    struct Maybe {
        int i, d;
        float strength;
    };
    std::array<Maybe, window_cap> maybe;
    int k = 0;
    for (int i = 0; i < w.n; ++i) {
        const auto& e = world.enemies[static_cast<std::size_t>(i)];
        if (!e.alive) continue;
        if (l.of(w.early[static_cast<std::size_t>(i)]) >= ours) continue;
        if (l.of(w.late[static_cast<std::size_t>(i)]) < ours) {
            if (room > 0) chosen |= static_cast<std::uint16_t>(1u << i), --room;
            continue;
        }
        maybe[static_cast<std::size_t>(k++)] = {i, -1, e.strength};
    }
    if (room <= 0 || k == 0) return chosen;
    if (k <= room) {
        for (int j = 0; j < k; ++j) chosen |= static_cast<std::uint16_t>(1u << maybe[static_cast<std::size_t>(j)].i);
        return chosen;
    }
    const vec2 from = in_bounds(world.turn_start) ? world.turn_start : world.me().pos;
    for (int j = 0; j < k; ++j) {
        auto& m = maybe[static_cast<std::size_t>(j)];
        const auto& e = world.enemies[static_cast<std::size_t>(m.i)];
        m.d = e.visible ? dist(from, e.pos) : unseen_distance(e, from);
    }
    // The `room` first by (distance, strength descending, index): a strict order, picked one by one.
    const auto before = [](const Maybe& a, const Maybe& b) {
        return a.d != b.d ? a.d < b.d : a.strength != b.strength ? a.strength > b.strength : a.i < b.i;
    };
    unsigned taken = 0;
    for (int r = 0; r < room; ++r) {
        int best = -1;
        for (int j = 0; j < k; ++j)
            if (!(taken >> j & 1) && (best < 0 || before(maybe[static_cast<std::size_t>(j)], maybe[static_cast<std::size_t>(best)]))) best = j;
        taken |= 1u << best;
        chosen |= static_cast<std::uint16_t>(1u << maybe[static_cast<std::size_t>(best)].i);
    }
    return chosen;
}

} // namespace

int slot_of_rank(const World& world, bool ally, int rank, int r) {
    return layout_of(world, ally, r).of(rank);
}

int enemy_earliest_rank(const World& world, const ChampionBelief& e) {
    if (e.side != team::enemy || e.index < 0 || e.index >= window_cap) return e.next_rank;
    return current(world).early[static_cast<std::size_t>(e.index)];
}

int enemy_latest_rank(const World& world, const ChampionBelief& e) {
    if (e.side != team::enemy || e.index < 0 || e.index >= window_cap) return e.next_rank;
    return current(world).late[static_cast<std::size_t>(e.index)];
}

int enemy_earliest_slot(const World& world, const ChampionBelief& e, int r) {
    if (e.side != team::enemy || r <= world.round) return world.slot(e, r);
    return slot_of_rank(world, false, r == world.round + 1 ? enemy_earliest_rank(world, e) : 0, r);
}

int enemy_latest_slot(const World& world, const ChampionBelief& e, int r) {
    if (e.side != team::enemy || r <= world.round) return world.slot(e, r);
    const int last = static_cast<int>(world.enemies.size()) - 1;
    return slot_of_rank(world, false, r == world.round + 1 ? enemy_latest_rank(world, e) : last, r);
}

bool enemy_may_act_after_us(const World& world, const ChampionBelief& e) {
    if (e.side != team::enemy) return world.slot(e, world.round) > world.slot(world.me(), world.round);
    if (e.visible) return !e.acted;
    return e.alive && e.index >= 0 && e.index < window_cap && (current(world).after_mask >> e.index & 1);
}

bool enemy_turn_before_ours_next(const World& world, const ChampionBelief& e) {
    const int ours = world.slot(world.me(), world.round + 1);
    if (e.side != team::enemy || e.index < 0 || e.index >= window_cap) return world.slot(e, world.round + 1) < ours;
    auto& w = const_cast<Windows&>(current(world));
    if (ours < 0 || ours >= slot_cap) return enemy_earliest_slot(world, e, world.round + 1) < ours;
    if (!(w.second_known >> ours & 1)) w.second[static_cast<std::size_t>(ours)] = pick_second(world, w, ours), w.second_known |= 1u << ours;
    return w.second[static_cast<std::size_t>(ours)] >> e.index & 1;
}

} // namespace aph
