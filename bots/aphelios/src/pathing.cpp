#include "pathing.h"
#include <algorithm>
#include <array>
#include "world.h"

namespace aph {

namespace {

vec2 my_pos() { return cambc::self().position(); }

template <class T> T& entry(std::vector<T>& table, std::size_t count, int i) {
    if (table.size() != count) table.resize(count);
    return table[static_cast<std::size_t>(i)];
}

} // namespace

Pathing::Pathing(const World& world) : world_{world} {}

const StaticMap& Pathing::map() const { return world_.map(); }

void Pathing::begin_turn() {
    blocked_.reset();
    if (bumped_round_ != world_.round) {
        bumped_.clear();
        bumped_round_ = world_.round;
    }
}

const Field& Pathing::cached(Slot& slot, const bitboard& goals) {
    if (!slot) {
        FuelMeter meter{"field"};
        // Fill the slot only once computed, so a failure leaves it empty to retry.
        slot = std::make_unique<Field>(make_field(map().blocked_for_us, goals));
    }
    return *slot;
}

Pathing::Slot& Pathing::altar_slot(int altar) { return entry(altar_fields_, map().altars.size(), altar); }

Pathing::Slot& Pathing::group_slot(int group) { return entry(group_fields_, map().groups.size(), group); }

const Field& Pathing::to_ally_spawn() { return map().from_ally_spawn(); }

const Field& Pathing::to_altar(int altar) { return cached(altar_slot(altar), map().altars[altar].tribute_tiles()); }

const Field* Pathing::to_altar(int altar, std::uint64_t fuel_floor) {
    if (!altar_slot(altar) && !fuel_ok(fuel_floor + field_cost_estimate())) return nullptr;
    return &to_altar(altar);
}

const Field& Pathing::to_any_altar() {
    if (any_altar_) return *any_altar_;
    bitboard goals;
    for (const auto& a : map().altars) goals |= a.tribute_tiles();
    return cached(any_altar_, goals);
}

const Field& Pathing::to_group(int group) { return cached(group_slot(group), map().groups[group].tiles()); }

const Field* Pathing::from_centre(int group) {
    const auto& slot = entry(centre_fields_, map().groups.size(), group);
    return slot ? slot.get() : nullptr;
}

std::optional<bitboard>& Pathing::attack_slot(int group, int member, int range) {
    const auto r = static_cast<std::size_t>(range);
    if (attack_tiles_.size() <= r) attack_tiles_.resize(r + 1);
    auto& members = entry(attack_tiles_[r], map().groups.size(), group);
    return entry(members, map().groups[group].members.size(), member);
}

const bitboard& Pathing::member_attack_tiles(int group, int member, int range) {
    auto& slot = attack_slot(group, member, range);
    if (!slot) {
        FuelMeter meter{"attack_tiles"};
        const auto& s = map();
        auto tiles = s.viewers(s.groups[group].members[member].pos, range);
        tiles &= s.standable;
        slot = std::move(tiles);
    }
    return *slot;
}

bitboard Pathing::attack_tiles(int group, int range) {
    const auto& health = world_.camps[group].health;
    bitboard tiles;
    for (int i = 0; i < static_cast<int>(health.size()); ++i)
        if (health[i] > 0) tiles |= member_attack_tiles(group, i, range);
    return tiles;
}

bool Pathing::prepare_member(int group, int member, int range, std::uint64_t fuel_floor) {
    if (attack_slot(group, member, range)) return true;
    // Bush clusters in reach are the costly part; without them a shadowcast or two remain.
    constexpr std::uint64_t viewers_cost = 10000;
    if (!fuel_ok(fuel_floor + viewers_cost)
        || !map().find_bush_clusters(map().groups[group].members[member].pos, range, fuel_floor + viewers_cost))
        return false;
    member_attack_tiles(group, member, range);
    return true;
}

bool Pathing::prepare_attack_tiles(int group, int range, std::uint64_t fuel_floor) {
    const auto& health = world_.camps[group].health;
    for (int i = 0; i < static_cast<int>(health.size()); ++i)
        if (health[i] > 0 && !prepare_member(group, i, range, fuel_floor)) return false;
    return true;
}

bool Pathing::warm_up(int attack_range, std::uint64_t fuel_floor) {
    const auto cost = field_cost_estimate();
    const auto afford = [&](const Slot& slot) { return slot || fuel_ok(fuel_floor + cost); };
    if (!afford(any_altar_)) return false;
    to_any_altar();
    // Farm reads only groups with gems and no monolith.
    const auto farmed = [&](int g) { return !map().groups[g].has_monolith && map().groups[g].gems > 0; };
    for (int g = 0; g < static_cast<int>(map().groups.size()); ++g) {
        if (!farmed(g)) continue;
        auto& slot = entry(centre_fields_, map().groups.size(), g);
        if (slot) continue;
        if (!afford(slot)) return false;
        cached(slot, single(map().groups[g].centre));
    }
    centres_ready_ = true;
    for (int g = 0; g < static_cast<int>(map().groups.size()); ++g)
        for (int i = 0; farmed(g) && i < static_cast<int>(map().groups[g].members.size()); ++i)
            if (!prepare_member(g, i, attack_range, fuel_floor)) return false;
    for (int a = 0; a < static_cast<int>(map().altars.size()); ++a) {
        if (!afford(altar_slot(a))) return false;
        to_altar(a);
    }
    return true;
}

Pathing::Nearest Pathing::nearest(const bitboard& goals, int max_steps) {
    Nearest n;
    const vec2 me = my_pos();
    auto walls = map().blocked_for_us;
    walls.set(me, false);
    const auto open_goals = goals & ~walls;
    if (open_goals.is_empty()) return n;
    FuelMeter meter{"nearest"};
    cambc::distance_field field;
    bitboard visited;
    field.compute_to(walls, single(me), open_goals, visited, static_cast<std::uint16_t>(std::min<int>(max_steps, unreachable)));
    for (auto p : (visited & open_goals).positions()) {
        const int steps = field.get(p);
        if (steps < n.steps) n.steps = steps, n.tiles.clear();
        if (steps == n.steps) n.tiles.push_back(p);
    }
    return n;
}

const bitboard& Pathing::blocked() {
    if (!blocked_) {
        auto b = map().blocked_for_us | cambc::vision::champion_tiles() | cambc::vision::camp_tiles()
                 | cambc::vision::teleport_tiles() | bumped_;
        b.set(my_pos(), false);
        blocked_ = std::move(b);
    }
    return *blocked_;
}

void Pathing::invalidate() { blocked_.reset(); }

std::vector<vec2> Pathing::closer_neighbours(const Field& field, const bitboard* avoid) {
    const vec2 me = my_pos();
    const int here = field.at(me);
    const auto& walls = blocked();
    std::vector<vec2> out;
    out.reserve(8);
    std::array<int, 8> steps_of{};
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!in_bounds(p) || walls.is_set(p) || (avoid && avoid->is_set(p))) continue;
        const int steps = field.at(p);
        if (steps >= here) continue;
        auto i = out.size();
        out.push_back(p);
        for (; i > 0 && steps_of[i - 1] > steps; --i) out[i] = out[i - 1], steps_of[i] = steps_of[i - 1];
        out[i] = p;
        steps_of[i] = steps;
    }
    return out;
}

Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps) {
    Route r;
    const vec2 me = my_pos();
    if (goals.is_set(me)) {
        r.steps = 0;
        return r;
    }
    auto walls = avoid ? blocked() | *avoid : blocked();
    walls.set(me, false);
    const auto open_goals = goals & ~walls;
    if (open_goals.is_empty()) return r;
    // Search outwards from the goals until it reaches us: every tile one layer nearer than ours
    // is then labelled, so each neighbour on a shortest route is known.
    FuelMeter meter{"route"};
    cambc::distance_field field;
    bitboard visited;
    field.compute_to(walls, open_goals, single(me), visited, static_cast<std::uint16_t>(std::min<int>(max_steps, unreachable)));
    const int here = field.get(me);
    if (here == unreachable) return r;
    r.steps = here;
    for (auto d : field.next_moves_from(me)) r.first_steps.push_back(me + d);
    return r;
}

bool Pathing::try_move(vec2 tile) {
    try {
        if (cambc::self().move_absolute(tile)) {
            invalidate();
            return true;
        }
        // A hidden unit was there: the tile is now revealed to us for the rest of the round.
        bumped_.set(tile);
        invalidate();
    } catch (const cambc::error&) {
    }
    return false;
}

bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid, int max_steps) {
    if (!cambc::self().can_move()) return false;
    // Each retry costs a search, and only a hidden blocker makes one worth it.
    const auto retry_cost = search_cost_estimate(std::min(max_steps, map().width + map().height)) + params::end_reserve;
    for (int attempt = 0; attempt < 3; ++attempt) {
        if (attempt > 0 && !fuel_ok(retry_cost)) return false;
        const auto r = route(goals, avoid, max_steps);
        bool bumped = false;
        for (auto p : r.first_steps) {
            if (try_move(p)) return true;
            bumped |= bumped_.is_set(p);
        }
        if (!bumped) return false;
    }
    return false;
}

bool Pathing::step_towards(const Field& field, const bitboard* avoid, int max_detour) {
    const int here = field.at(my_pos());
    if (here == 0 || !cambc::self().can_move()) return false;
    if (here != unreachable) {
        const int cap = here + max_detour;
        if (fuel_ok(search_cost_estimate(cap) + params::end_reserve) && step_towards(field.goals, avoid, cap)) return true;
    }
    return descend(field, avoid);
}

bool Pathing::descend(const Field& field, const bitboard* avoid) {
    if (!cambc::self().can_move()) return false;
    for (auto p : closer_neighbours(field, avoid))
        if (try_move(p)) return true;
    return false;
}

bool Pathing::step_closer(vec2 target) {
    if (!cambc::self().can_move()) return false;
    const vec2 me = my_pos();
    const auto& walls = blocked();
    std::optional<vec2> best;
    int best_dist = dist(me, target);
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!in_bounds(p) || walls.is_set(p)) continue;
        if (const int d2 = dist(p, target); d2 < best_dist) best = p, best_dist = d2;
    }
    return best && try_move(*best);
}

bool Pathing::step_towards(vec2 target, const bitboard* avoid) { return step_towards(single(target), avoid); }

bitboard Pathing::dash_landings() {
    const vec2 me = my_pos();
    const auto camps = cambc::vision::camp_tiles();
    // Dash paths cross holes, altars and champions but not walls or camps.
    auto landings = (map().walls | camps).reachable_tiles(me, 2);
    landings &= ~(map().impassable | map().enemy_spawn | camps | cambc::vision::champion_tiles()
                  | cambc::vision::teleport_tiles() | bumped_);
    landings.set(me, false);
    return landings;
}

bitboard Pathing::teleport_targets() {
    auto targets = square(my_pos(), 3);
    targets &= ~(map().impassable | map().enemy_spawn | map().camp_tiles | cambc::vision::champion_tiles()
                 | cambc::vision::teleport_tiles() | bumped_);
    return targets;
}

bitboard Pathing::ward_targets() {
    auto targets = square(my_pos(), 2);
    targets &= ~(map().impassable | map().enemy_spawn | cambc::vision::ward_tiles(team::ally));
    return targets;
}

} // namespace aph
