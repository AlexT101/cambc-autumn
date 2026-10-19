#include "pathing.h"
#include <algorithm>
#include <array>
#include "world.h"

namespace aph {

namespace {

template <class T> T& entry(std::vector<T>& table, std::size_t count, int i) {
    if (table.size() != count) table.resize(count);
    return table[static_cast<std::size_t>(i)];
}

} // namespace

Pathing::Pathing(const World& world) : world_{world} {}

const StaticMap& Pathing::map() const { return world_.map(); }

void Pathing::begin_turn() {
    guard_ = nullptr; // a turn abandoned as stale left its guard set
    blocked_fresh_ = false;
    pos_fresh_ = false;
    if (bumped_round_ != world_.round) {
        bumped_.clear();
        bumped_any_ = false;
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

const Field& Pathing::to_ally_spawn() { return map().from_ally_spawn(); }

const Field& Pathing::to_altar(int altar) { return cached(altar_slot(altar), map().altars[altar].tribute_tiles()); }

const Field& Pathing::to_any_altar() {
    if (any_altar_) return *any_altar_;
    bitboard goals;
    for (const auto& a : map().altars) goals |= a.tribute_tiles();
    return cached(any_altar_, goals);
}

int Pathing::centre_to_altar(int group) {
    auto& steps = entry(centre_to_altar_, map().groups.size(), group);
    if (!steps) steps = map().drafted_altar_steps(group);
    if (!steps) steps = to_any_altar().at(map().groups[group].centre);
    return *steps;
}

const bitboard& Pathing::live_camps() {
    if (live_camps_version_ != world_.camps_version) {
        live_camps_version_ = world_.camps_version;
        // Only the groups whose belief changed are rewritten.
        const auto& groups = map().groups;
        if (live_versions_.size() != groups.size()) live_versions_.assign(groups.size(), ~0u);
        for (std::size_t g = 0; g < groups.size(); ++g) {
            const auto& c = world_.camps[g];
            if (live_versions_[g] == c.version) continue;
            live_versions_[g] = c.version;
            for (std::size_t i = 0; i < groups[g].members.size(); ++i)
                live_camps_.set(groups[g].members[i].pos, c.state == CampState::alive && c.health[i] > 0);
        }
    }
    return live_camps_;
}

std::unique_ptr<Pathing::Approach>& Pathing::approach_slot(int group, int range) {
    const auto r = static_cast<std::size_t>(range);
    if (approach_fields_.size() <= r) approach_fields_.resize(r + 1);
    return entry(approach_fields_[r], map().groups.size(), group);
}

bool Pathing::approach_ready(int group, int range) {
    const auto& slot = approach_slot(group, range);
    if (!slot) return false;
    const vec2 me = my_pos();
    auto& c = ready_check_;
    if (c.slot != slot.get() || c.round != world_.round || c.at != me)
        c = {slot.get(), world_.round, me, slot->field.at(me) != unreachable && slot->camps == live_camps()};
    return c.ready;
}

// About our distance to the group: from the approach field it replaces, the group's centre field,
// or by way of our spawn. Walking around live camps can add a few layers.
// Negative when no field bounds it.
int Pathing::approach_steps(int group, int range) {
    const auto& s = map();
    const vec2 me = my_pos();
    const vec2 centre = s.groups[group].centre;
    int steps = -1;
    if (const auto& old = approach_slot(group, range); old && old->field.at(me) != unreachable) steps = old->field.at(me);
    else if (const auto* from = from_centre(group)) steps = from->at(me);
    else if (s.from_ally_spawn_ready() && s.from_ally_spawn().at(me) != unreachable && s.from_ally_spawn().at(centre) != unreachable)
        steps = s.from_ally_spawn().at(me) + s.from_ally_spawn().at(centre);
    else if (s.drafted() && s.ally_spawn.is_set(me) && s.ally_steps(group) != unreachable)
        steps = s.ally_steps(group);
    return std::min(steps, s.width + s.height);
}

// Unbounded, walls seldom double the distance as the crow flies.
std::uint64_t Pathing::approach_cost(int group, int range) {
    if (approach_ready(group, range)) return 0;
    const int steps = approach_steps(group, range);
    return search_cost_estimate(steps >= 0 ? steps : std::min(2 * dist(my_pos(), map().groups[group].centre), map().width + map().height));
}

const Field* Pathing::approach(int group, int range, std::uint64_t fuel_floor) {
    if (approach_ready(group, range)) return &approach_slot(group, range)->field;
    // Searched out to our tile only: it costs by our distance rather than the map's, and every
    // tile of a walk down it is labelled, so it lasts the whole way unless we leave it or a camp
    // dies or returns.
    const int steps = approach_steps(group, range);
    if (!fuel_ok(fuel_floor + approach_cost(group, range))) return nullptr;
    const auto& s = map();
    const vec2 me = my_pos();
    // Unbounded, the search goes as deep as the fuel above the floor allows.
    const auto per_layer = static_cast<int>(search_chunks());
    const int affordable = (static_cast<int>(fuel() - fuel_floor) - static_cast<int>(search_cost_estimate(0))) / per_layer;
    const int layers = steps >= 0 ? steps + max_detour : std::clamp(affordable, 1, s.width + s.height);
    FuelMeter meter{"approach"};
    if (!spare_approach_) spare_approach_ = std::make_unique<Approach>();
    auto& made = *spare_approach_;
    static bitboard walls{cambc::uninitialized}, open{cambc::uninitialized}, origin{cambc::uninitialized},
        visited{cambc::uninitialized};
    copy_into(live_camps(), made.camps);
    or_into(s.blocked_for_us, made.camps, walls);
    auto& goals = made.field.goals;
    if (range == 0) {
        copy_into(s.groups[group].tiles(), goals);
    } else {
        goals.clear();
        for (const auto& m : s.groups[group].members) goals.draw_chebyshev(m.pos, static_cast<float>(range));
        not_into(walls, open);
        goals &= open;
    }
    walls.set(me, false);
    origin.clear();
    origin.set(me);
    made.field.steps.compute_to(walls, goals, origin, visited, static_cast<std::uint16_t>(layers));
    if (made.field.at(me) == unreachable) return nullptr;
    auto& slot = approach_slot(group, range);
    std::swap(slot, spare_approach_);
    ready_check_.slot = nullptr;
    return &slot->field;
}

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
    if (!slot && map().attack_tiles_drafted(group, range)) slot = map().drafted_attack_tiles(group, member, range);
    if (!slot) {
        FuelMeter meter{"attack_tiles"};
        const auto& s = map();
        auto tiles = s.viewers(s.groups[group].members[member].pos, range);
        tiles &= s.open_for_us;
        slot = std::move(tiles);
    }
    return *slot;
}

void Pathing::attack_tiles(int group, int range, bitboard& tiles) {
    const auto& health = world_.camps[group].health;
    static bitboard freed{cambc::uninitialized};
    tiles.clear();
    bool any_freed = false;
    for (int i = 0; i < static_cast<int>(health.size()); ++i) {
        if (health[i] > 0) {
            tiles |= member_attack_tiles(group, i, range);
            continue;
        }
        if (!any_freed) copy_into(map().standable, freed);
        any_freed = true;
        freed.set(map().groups[group].members[i].pos);
    }
    tiles &= any_freed ? freed : map().standable;
}

bool Pathing::prepare_member(int group, int member, int range, std::uint64_t fuel_floor) {
    if (attack_slot(group, member, range) || map().attack_tiles_drafted(group, range)) return true;
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

bool Pathing::prepare_member_tiles(int group, int range, std::uint32_t members, std::uint64_t fuel_floor) {
    const int n = static_cast<int>(map().groups[group].members.size());
    for (int i = 0; i < n && i < 32; ++i)
        if ((members >> i & 1) && !prepare_member(group, i, range, fuel_floor)) return false;
    return true;
}

bool Pathing::farmed(int g) const { return !map().groups[g].has_monolith && map().groups[g].gems + map().groups[g].gold > 0; }

int& Pathing::centre_cap(int group) {
    auto& cap = entry(centre_caps_, map().groups.size(), group);
    if (!cap && map().drafted()) {
        const int steps = std::max(map().ally_steps(group), map().enemy_steps(group));
        // Off the spawns' walking routes, a centre is on an island: its field is shallow.
        cap = (steps == unreachable ? 0 : steps) + centre_depth_margin;
    }
    return cap;
}

bool Pathing::warm_centres(std::uint64_t fuel_floor) {
    if (centres_ready_) return true;
    const auto round = cambc::round_number();
    const auto cost = field_cost_estimate();
    for (int g = 0; g < static_cast<int>(map().groups.size()); ++g) {
        if (!farmed(g)) continue;
        auto& slot = entry(centre_fields_, map().groups.size(), g);
        if (slot) continue;
        if (!centre_cap(g)) {
            if (cambc::round_number() != round || !fuel_ok(fuel_floor + cost)) return false;
            cached(slot, single(map().groups[g].centre));
            continue;
        }
        while (!slot) {
            auto& cap = centre_cap(g);
            if (cambc::round_number() != round || !fuel_ok(last_reserve + search_cost_estimate(cap))) return false;
            FuelMeter meter{"field"};
            slot = make_field(map().blocked_for_us, single(map().groups[g].centre), cap);
            if (!slot) cap *= 2;
        }
    }
    centres_ready_ = true;
    return true;
}

bool Pathing::warm_up(int attack_range, std::uint64_t fuel_floor) {
    const auto cost = field_cost_estimate();
    const auto round = cambc::round_number();
    const auto afford = [&](const Slot& slot) { return slot || (cambc::round_number() == round && fuel_ok(fuel_floor + cost)); };
    if (!warm_centres(fuel_floor) || !afford(any_altar_)) return false;
    to_any_altar();
    for (; warm_group_ < static_cast<int>(map().groups.size()); ++warm_group_, warm_member_ = 0) {
        if (!farmed(warm_group_) || map().attack_tiles_drafted(warm_group_, attack_range)) continue;
        for (; warm_member_ < static_cast<int>(map().groups[warm_group_].members.size()); ++warm_member_)
            if (cambc::round_number() != round || !fuel_ok(fuel_floor + small_cost_estimate) || !prepare_member(warm_group_, warm_member_, attack_range, fuel_floor)) return false;
    }
    for (int a = 0; a < static_cast<int>(map().altars.size()); ++a) {
        if (!afford(altar_slot(a))) return false;
        to_altar(a);
    }
    return true;
}

const bitboard& Pathing::blocked() {
    if (!blocked_fresh_) {
        static bitboard t{cambc::uninitialized};
        cambc::vision::champion_tiles_into(team::ally, blocked_);
        blocked_ |= map().blocked_for_us;
        cambc::vision::champion_tiles_into(team::enemy, t);
        blocked_ |= t;
        cambc::vision::camp_tiles_into(t);
        blocked_ |= t;
        cambc::vision::teleport_tiles_into(t);
        blocked_ |= t;
        if (bumped_any_) blocked_ |= bumped_;
        blocked_.set(my_pos(), false);
        blocked_fresh_ = true;
    }
    return blocked_;
}

void Pathing::invalidate() {
    blocked_fresh_ = false;
    pos_fresh_ = false;
}

vec2 Pathing::my_pos() {
    const auto round = cambc::round_number();
    if (!pos_fresh_ || pos_round_ != round) {
        pos_ = my_position();
        pos_round_ = round;
        pos_fresh_ = true;
    }
    return pos_;
}

Pathing::Neighbours Pathing::closer_neighbours(const Field& field, const bitboard* avoid) {
    const vec2 me = my_pos();
    const int here = field.at(me);
    const auto& walls = blocked();
    Neighbours out;
    std::array<int, 8> steps_of{};
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!in_bounds(p) || walls.is_set(p) || (avoid && avoid->is_set(p)) || (guard_ && guard_->is_set(p))) continue;
        const int steps = field.at(p);
        if (steps >= here) continue;
        auto i = out.count++;
        for (; i > 0 && steps_of[i - 1] > steps; --i) out.tiles[i] = out.tiles[i - 1], steps_of[i] = steps_of[i - 1];
        out.tiles[i] = p;
        steps_of[i] = steps;
    }
    return out;
}

Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, vec2 through) {
    world_.throw_if_stale();
    Route r;
    const vec2 me = my_pos();
    if (goals.is_set(me)) {
        r.steps = 0;
        return r;
    }
    // Scratch kept between calls: the host overwrites every output in full.
    static bitboard walls{cambc::uninitialized}, open_goals{cambc::uninitialized}, origin, visited{cambc::uninitialized};
    static vec2 origin_at{-1, -1};
    static cambc::distance_field field;
    copy_into(blocked(), walls);
    if (in_bounds(through)) walls.set(through, false);
    if (avoid && avoid->is_set(me)) {
        // Inside danger every neighbour is in it too: free the connected region we stand in.
        auto danger = *avoid;
        danger &= ~(~danger).reachable_tiles(me, static_cast<std::uint16_t>(map().width + map().height));
        walls |= danger;
    } else if (avoid) {
        walls |= *avoid;
    }
    if (guard_) walls |= *guard_;
    walls.set(me, false);
    not_into(walls, open_goals);
    open_goals &= goals;
    if (open_goals.is_empty()) return r;
    // Search outwards from the goals until it reaches us: every tile one layer nearer than ours
    // is then labelled, so each neighbour on a shortest route is known.
    FuelMeter meter{"route"};
    if (in_bounds(origin_at)) origin.set(origin_at, false);
    origin.set(me);
    origin_at = me;
    field.compute_to(walls, open_goals, origin, visited, static_cast<std::uint16_t>(std::min<int>(max_steps, unreachable)));
    const int here = field.get(me);
    if (here == unreachable) return r;
    r.steps = here;
    // As distance_field::next_moves_from, without its vector: the nearest neighbours, north first.
    std::array<std::uint16_t, 8> around{};
    std::uint16_t best = unreachable;
    for (int i = 0; i < 8; ++i) {
        const vec2 p = me + directions[i];
        around[i] = in_bounds(p) ? field.get(p) : unreachable;
        best = std::min(best, around[i]);
    }
    if (best < here)
        for (int i = 0; i < 8; ++i)
            if (around[i] == best) r.first_steps[r.count++] = me + directions[i];
    return r;
}

bool Pathing::try_move(vec2 tile) {
    if (guard_ && guard_->is_set(tile)) return false;
    try {
        if (cambc::self().move_absolute(tile)) {
            invalidate();
            return true;
        }
        // A hidden unit was there: the tile is now revealed to us for the rest of the round.
        bumped_.set(tile);
        bumped_any_ = true;
        invalidate();
    } catch (const cambc::error&) {
    }
    return false;
}

bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid, int max_steps) {
    if (!my_can_move()) return false;
    // Each retry costs a search, and only a hidden blocker makes one worth it.
    const auto retry_cost = search_cost_estimate(std::min(max_steps, map().width + map().height)) + end_reserve;
    for (int attempt = 0; attempt < 3; ++attempt) {
        if (attempt > 0 && !fuel_ok(retry_cost)) {
            note_shortcut("route-retry");
            return false;
        }
        const auto r = route(goals, avoid, max_steps);
        bool bumped = false;
        for (int i = 0; i < r.count; ++i) {
            if (try_move(r.first_steps[i])) return true;
            bumped |= bumped_.is_set(r.first_steps[i]);
        }
        if (!bumped) return r.steps == unreachable && make_way(goals, avoid, max_steps);
    }
    return false;
}

bool Pathing::make_way(const bitboard& goals, const bitboard* avoid, int max_steps) {
    const vec2 me = my_pos();
    static bitboard allies{cambc::uninitialized};
    cambc::vision::champion_tiles_into(team::ally, allies);
    for (auto d : directions) {
        const vec2 a = me + d;
        if (!in_bounds(a) || !allies.is_set(a)) continue;
        const auto r = route(goals, avoid, max_steps, a);
        if (r.steps == unreachable || r.steps < 2 || std::find(r.first_steps.begin(), r.first_steps.begin() + r.count, a) == r.first_steps.begin() + r.count) continue;
        auto& self = cambc::self();
        const auto ally = cambc::vision::champion_at(a);
        const auto mine = self.gem_count(), theirs = ally.gem_count();
        if (mine > theirs || (mine == theirs && self.champion_name() > ally.champion_name())) return false;
        const auto& walls = blocked();
        std::optional<vec2> best;
        int best_dist = 0;
        for (auto e : directions) {
            const vec2 p = me + e;
            if (!in_bounds(p) || walls.is_set(p) || (avoid && avoid->is_set(p)) || (guard_ && guard_->is_set(p))) continue;
            if (const int d2 = dist(p, a); d2 > best_dist) best = p, best_dist = d2;
        }
        return best && try_move(*best);
    }
    return false;
}

bool Pathing::step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor) {
    const auto round = cambc::round_number();
    if (world_.round != round) return false;
    if (!my_can_move() || goals.is_set(my_pos())) return false;
    const auto fixed = search_cost_estimate(0) + small_cost_estimate;
    const auto chunks = search_chunks();
    for (int attempt = 0; attempt < 3; ++attempt) {
        const auto remaining = fuel();
        if (remaining < fuel_floor || remaining - fuel_floor < fixed + chunks) {
            note_shortcut("siege-route-fuel");
            return false;
        }
        // A shortest simple path cannot exceed the map's tile count. Budget every search at
        // its actual cap, including hidden-blocker retries, and never substitute other goals.
        const int cap = static_cast<int>(std::min<std::uint64_t>(
            static_cast<std::uint64_t>(map().width) * map().height,
            (remaining - fuel_floor - fixed) / chunks));
        if (cambc::round_number() != round) return false;
        const auto r = route(goals, nullptr, cap);
        if (cambc::round_number() != round) return false;
        bool bumped = false;
        for (int i = 0; i < r.count; ++i) {
            if (cambc::round_number() != round) return false;
            const auto before_move = fuel();
            if (before_move < fuel_floor || before_move - fuel_floor < last_reserve) return false;
            if (try_move(r.first_steps[i])) return true;
            bumped |= bumped_.is_set(r.first_steps[i]);
        }
        if (!bumped) return false;
    }
    return false;
}

bool Pathing::step_towards(const Field& field, const bitboard* avoid) {
    const int here = field.at(my_pos());
    if (here == 0 || !my_can_move()) return false;
    if (here != unreachable) {
        const int cap = here + max_detour;
        if (!fuel_ok(search_cost_estimate(cap) + end_reserve)) note_shortcut("static-descend");
        else if (step_towards(field.goals, avoid, cap)) return true;
    }
    return descend(field, avoid);
}

bool Pathing::descend(const Field& field, const bitboard* avoid) {
    if (!my_can_move()) return false;
    for (auto p : closer_neighbours(field, avoid))
        if (try_move(p)) return true;
    return false;
}

bool Pathing::step_closer(vec2 target) {
    if (!my_can_move()) return false;
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

bitboard Pathing::dash_landings() {
    static bitboard camps{cambc::uninitialized}, excluded{cambc::uninitialized}, t{cambc::uninitialized};
    const vec2 me = my_pos();
    cambc::vision::camp_tiles_into(camps);
    // Dash paths cross holes, altars and champions but not walls or camps.
    or_into(map().walls, camps, excluded);
    auto landings = excluded.reachable_tiles(me, 2);
    landings &= map().open_for_us;
    copy_into(camps, excluded);
    cambc::vision::champion_tiles_into(team::ally, t);
    excluded |= t;
    cambc::vision::champion_tiles_into(team::enemy, t);
    excluded |= t;
    cambc::vision::teleport_tiles_into(t);
    excluded |= t;
    if (bumped_any_) excluded |= bumped_;
    if (guard_) excluded |= *guard_;
    excluded &= landings;
    landings ^= excluded;
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
    static bitboard excluded{cambc::uninitialized};
    auto targets = square(my_pos(), 2);
    targets &= map().open_for_us;
    cambc::vision::ward_tiles_into(team::ally, excluded);
    excluded &= targets;
    targets ^= excluded;
    return targets;
}

} // namespace aph
