#include "pathing.h"
#include <array>
#include "world.h"

namespace aph {

namespace {

vec2 my_pos() { return cambc::self().position(); }

// Entry `i` of a table with one entry per static object, sized on first use.
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

// ----- Static fields -------------------------------------------------------------------------

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

Pathing::Slot& Pathing::attack_slot(int group, int range) {
    const auto r = static_cast<std::size_t>(range);
    if (attack_fields_.size() <= r) attack_fields_.resize(r + 1);
    return entry(attack_fields_[r], map().groups.size(), group);
}

// Walking to our spawn is walking back along the field from it.
const Field& Pathing::to_ally_spawn() { return map().from_ally_spawn(); }

const Field& Pathing::to_altar(int altar) { return cached(altar_slot(altar), map().altars[altar].tribute_tiles()); }

const Field& Pathing::to_any_altar() {
    if (any_altar_) return *any_altar_;
    bitboard goals;
    for (const auto& a : map().altars) goals |= a.tribute_tiles();
    return cached(any_altar_, goals);
}

const Field& Pathing::to_group(int group) { return cached(group_slot(group), map().groups[group].tiles()); }

const Field& Pathing::to_group_attack(int group, int range) {
    auto& slot = attack_slot(group, range);
    if (slot) return *slot;
    const auto& g = map().groups[group];
    bitboard goals;
    for (const auto& m : g.members) goals.draw_chebyshev(m.pos, static_cast<float>(range));
    return cached(slot, goals & ~g.tiles());
}

bool Pathing::warm_up(int attack_range, std::uint64_t fuel_floor) {
    // Start a field only if its estimated cost still leaves `fuel_floor`; cached ones are free.
    const auto cost = field_cost_estimate();
    const auto afford = [&](const Slot& slot) { return slot || fuel_ok(fuel_floor + cost); };
    if (!afford(any_altar_)) return false;
    to_any_altar();
    for (int a = 0; a < static_cast<int>(map().altars.size()); ++a) {
        if (!afford(altar_slot(a))) return false;
        to_altar(a);
    }
    for (int g = 0; g < static_cast<int>(map().groups.size()); ++g) {
        if (!afford(attack_slot(g, attack_range))) return false;
        to_group_attack(g, attack_range);
        if (!afford(group_slot(g))) return false;
        to_group(g);
    }
    return true;
}

// ----- Per-turn routing ----------------------------------------------------------------------

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
    // Insertion into a sorted list (at most 8 entries), keeping direction order among ties.
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

std::optional<vec2> Pathing::route(const bitboard& goals, const bitboard* avoid) {
    const vec2 me = my_pos();
    if (goals.is_set(me)) return std::nullopt;
    auto walls = avoid ? blocked() | *avoid : blocked();
    walls.set(me, false);
    const auto open_goals = goals & ~walls;
    if (open_goals.is_empty()) return std::nullopt;
    cambc::distance_field field;
    bitboard visited;
    field.compute_to(walls, open_goals, single(me), visited);
    const int here = field.get(me);
    if (here == unreachable) return std::nullopt;
    std::optional<vec2> best;
    int best_steps = here;
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!in_bounds(p) || walls.is_set(p)) continue;
        const int steps = field.get(p);
        if (steps < best_steps) best = p, best_steps = steps;
    }
    return best;
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

bool Pathing::step_towards(const Field& field, const bitboard* avoid) {
    if (field.at(my_pos()) == 0 || !cambc::self().can_move()) return false;
    for (auto p : closer_neighbours(field, avoid))
        if (try_move(p)) return true;
    return step_towards(field.goals, avoid);
}

bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid) {
    if (!cambc::self().can_move()) return false;
    // Each hidden blocker found costs one retry; give up after a few. Any other failure would
    // repeat on the same route.
    for (int attempt = 0; attempt < 3; ++attempt) {
        const auto step = route(goals, avoid);
        if (!step) return false;
        if (try_move(*step)) return true;
        if (!bumped_.is_set(*step)) return false;
    }
    return false;
}

bool Pathing::step_towards(vec2 target, const bitboard* avoid) { return step_towards(single(target), avoid); }

// ----- Legal destinations ----------------------------------------------------------------------

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
