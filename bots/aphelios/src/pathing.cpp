#include "pathing.h"
#include <algorithm>
#include "world.h"

namespace aph {

namespace {

enum FieldKind : std::uint32_t { any_altar_field, altar_field, group_field, group_attack_field };

constexpr std::uint32_t key(FieldKind kind, int index = 0, int range = 0) {
    return kind << 24 | static_cast<std::uint32_t>(index) << 8 | static_cast<std::uint32_t>(range);
}

vec2 my_pos() { return cambc::self().position(); }

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

const Field& Pathing::cached(std::uint32_t k, const bitboard& goals) {
    auto& slot = fields_[k];
    if (!slot) {
        FuelMeter meter{"field"};
        slot = std::make_unique<Field>();
        slot->goals = goals & ~map().blocked_for_us;
        bitboard visited;
        slot->steps.compute(map().blocked_for_us, slot->goals, visited);
    }
    return *slot;
}

// Walking to our spawn is walking back along the field from it.
const Field& Pathing::to_ally_spawn() { return map().from_ally_spawn(); }

const Field& Pathing::to_altar(int altar) { return cached(key(altar_field, altar), map().altars[altar].tribute_tiles()); }

const Field& Pathing::to_any_altar() {
    if (auto it = fields_.find(key(any_altar_field)); it != fields_.end()) return *it->second;
    bitboard goals;
    for (const auto& a : map().altars) goals |= a.tribute_tiles();
    return cached(key(any_altar_field), goals);
}

const Field& Pathing::to_group(int group) { return cached(key(group_field, group), map().groups[group].tiles()); }

const Field& Pathing::to_group_attack(int group, int range) {
    const auto k = key(group_attack_field, group, range);
    if (auto it = fields_.find(k); it != fields_.end()) return *it->second;
    const auto& g = map().groups[group];
    bitboard goals;
    for (const auto& m : g.members) goals.draw_chebyshev(m.pos, static_cast<float>(range));
    return cached(k, goals & ~g.tiles());
}

bool Pathing::warm_up(int attack_range, std::uint64_t fuel_floor) {
    // Start a field only if its estimated cost still leaves `fuel_floor`; cached ones are free.
    const auto cost = field_cost_estimate();
    const auto afford = [&](std::uint32_t k) { return fields_.contains(k) || fuel_ok(fuel_floor + cost); };
    if (!afford(key(any_altar_field))) return false;
    to_any_altar();
    for (int a = 0; a < static_cast<int>(map().altars.size()); ++a) {
        if (!afford(key(altar_field, a))) return false;
        to_altar(a);
    }
    for (int g = 0; g < static_cast<int>(map().groups.size()); ++g) {
        if (!afford(key(group_attack_field, g, attack_range))) return false;
        to_group_attack(g, attack_range);
        if (!afford(key(group_field, g))) return false;
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
    std::vector<std::pair<int, vec2>> found;
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!in_bounds(p) || walls.is_set(p) || (avoid && avoid->is_set(p))) continue;
        const int steps = field.at(p);
        if (steps < here) found.push_back({steps, p});
    }
    std::stable_sort(found.begin(), found.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
    std::vector<vec2> out;
    for (const auto& f : found) out.push_back(f.second);
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
    if (field.at(my_pos()) == 0) return false;
    for (auto p : closer_neighbours(field, avoid))
        if (try_move(p)) return true;
    return step_towards(field.goals, avoid);
}

bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid) {
    // Each hidden blocker found costs one retry; give up after a few.
    for (int attempt = 0; attempt < 3; ++attempt) {
        const auto step = route(goals, avoid);
        if (!step) return false;
        if (try_move(*step)) return true;
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
