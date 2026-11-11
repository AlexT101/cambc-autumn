// Enemy turn windows (see turn_window.h).
#include "turn_window.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include "world.h"

namespace aph {

namespace {

constexpr int window_cap = 16, slot_cap = 32, far_off = 99, unseen_probe = 24;

struct Windows {
    int round = -1;
    std::uint32_t observations = 0;
    int n = 0;
    std::array<std::int8_t, window_cap> early{}, late{};
    int unseen_after = 0; // this round's enemy turns after ours not held by a visible enemy yet to act
    // Next-round sets of enemies with a turn before ours, per projected slot of ours.
    std::uint32_t second_known = 0;
    std::array<std::uint16_t, slot_cap> second{};
};

Windows windows;

bool settled(const World& world, const ChampionBelief& e) {
    return !world.enemy_priorities_change || (e.visible && e.acted && e.priority_round == world.round);
}

bool outranks(const ChampionBelief& o, const ChampionBelief& e) {
    return o.next_priority > e.next_priority || (o.next_priority == e.next_priority && o.handle < e.handle);
}

[[gnu::noinline]] void build_windows(const World& world) {
    auto& w = windows;
    w.round = world.round;
    w.observations = world.observations;
    w.second_known = 0;
    const int n = std::min(static_cast<int>(world.enemies.size()), window_cap);
    w.n = n;
    int unsettled = 0;
    for (int i = 0; i < n; ++i) unsettled += !settled(world, world.enemies[static_cast<std::size_t>(i)]);
    for (int i = 0; i < n; ++i) {
        const auto& e = world.enemies[static_cast<std::size_t>(i)];
        if (!settled(world, e)) {
            w.early[static_cast<std::size_t>(i)] = 0;
            w.late[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(n - 1);
            continue;
        }
        int above = 0;
        for (int j = 0; j < n; ++j)
            if (const auto& o = world.enemies[static_cast<std::size_t>(j)]; j != i && settled(world, o) && outranks(o, e)) ++above;
        w.early[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(above);
        w.late[static_cast<std::size_t>(i)] = static_cast<std::int8_t>(std::min(n - 1, above + unsettled));
    }
    const int ours = world.slot(world.me(), world.round);
    int after = 0, pending = 0;
    for (int k = 0; k < static_cast<int>(world.enemies.size()); ++k) after += slot_of_rank(world, false, k, world.round) > ours;
    for (const auto& e : world.enemies) pending += e.alive && e.visible && !e.acted;
    w.unseen_after = std::max(0, after - pending);
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
    const int next = world.round + 1;
    int room = enemy_turns_before(world, ours, next);
    std::uint16_t chosen = 0;
    struct Maybe {
        int i, d;
        float strength;
    };
    std::array<Maybe, window_cap> maybe;
    int k = 0;
    for (int i = 0; i < w.n; ++i) {
        const auto& e = world.enemies[static_cast<std::size_t>(i)];
        if (!e.alive) continue;
        if (slot_of_rank(world, false, w.early[static_cast<std::size_t>(i)], next) >= ours) continue;
        if (slot_of_rank(world, false, w.late[static_cast<std::size_t>(i)], next) < ours) {
            if (room > 0) chosen |= static_cast<std::uint16_t>(1u << i), --room;
            continue;
        }
        maybe[static_cast<std::size_t>(k++)] = {i, -1, e.strength};
    }
    if (room <= 0 || k == 0) return chosen;
    if (k > room) {
        const vec2 from = in_bounds(world.turn_start) ? world.turn_start : world.me().pos;
        for (int j = 0; j < k; ++j) {
            auto& m = maybe[static_cast<std::size_t>(j)];
            const auto& e = world.enemies[static_cast<std::size_t>(m.i)];
            m.d = e.visible ? dist(from, e.pos) : unseen_distance(e, from);
        }
        std::sort(maybe.begin(), maybe.begin() + k, [](const Maybe& a, const Maybe& b) {
            return a.d != b.d ? a.d < b.d : a.strength != b.strength ? a.strength > b.strength : a.i < b.i;
        });
    }
    for (int j = 0; j < std::min(k, room); ++j) chosen |= static_cast<std::uint16_t>(1u << maybe[static_cast<std::size_t>(j)].i);
    return chosen;
}

} // namespace

bool enemy_settled(const World& world, const ChampionBelief& e) { return settled(world, e); }

int slot_of_rank(const World& world, bool ally, int rank, int r) {
    const int others = static_cast<int>(ally ? world.enemies.size() : world.allies.size());
    const bool first = ally == (world.map().team_a == (r % 2 == 1));
    return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
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

int enemy_turns_before(const World& world, int our_slot, int r) {
    int count = 0;
    for (int k = 0; k < static_cast<int>(world.enemies.size()); ++k) count += slot_of_rank(world, false, k, r) < our_slot;
    return count;
}

bool enemy_may_act_after_us(const World& world, const ChampionBelief& e) {
    if (e.side != team::enemy) return world.slot(e, world.round) > world.slot(world.me(), world.round);
    if (e.visible) return !e.acted;
    return e.alive && current(world).unseen_after > 0;
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
