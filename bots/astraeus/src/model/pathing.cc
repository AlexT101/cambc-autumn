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

int aim_distance(vec2 p, vec2 aim) { return std::abs(p.x - aim.x) + std::abs(p.y - aim.y); }

} // namespace

Pathing::Pathing(const World& world) : world_{world} {}

const StaticMap& Pathing::map() const { return world_.map(); }

const bitboard& Pathing::static_walls() const {
    const int kind = world_.me().facts().dash_kind();
    return kind == 0 ? map().blocked_for_us : kind == 1 ? map().dash_walls : map().landing_dash_walls;
}

const bitboard& Pathing::foot() const {
    const int kind = world_.me().facts().dash_kind();
    return kind == 0 ? map().foot() : kind == 1 ? map().dash_foot() : map().landing_dash_foot();
}

void Pathing::begin_turn() {
    guard_ = nullptr, guard_fn_ = nullptr; // a turn abandoned as stale left its guard set
    blocked_fresh_ = false;
    pos_fresh_ = false;
    if (bumped_round_ != world_.round) {
        if (bumped_any_) bumped_.clear();
        bumped_any_ = bumped_new_ = false;
        bumped_round_ = world_.round;
    }
}

const Field& Pathing::cached(Slot& slot, const bitboard& goals) {
    if (!slot) {
        FuelMeter meter{"field"};
        // Fill the slot only once computed, so a failure leaves it empty to retry.
        slot = make_field(static_walls(), goals);
    }
    return *slot;
}

Pathing::Slot& Pathing::altar_slot(int altar) { return entry(altar_fields_, map().altars.size(), altar); }

const Field& Pathing::to_ally_spawn() {
    return world_.me().facts().has_dash() ? cached(ally_spawn_, map().ally_spawn) : map().from_ally_spawn();
}

const Field& Pathing::to_altar(int altar) { return cached(altar_slot(altar), map().altars[altar].tribute_tiles()); }

const Field& Pathing::to_any_altar() {
    if (any_altar_) return *any_altar_;
    bitboard goals;
    for (const auto& a : map().altars) goals |= a.tribute_tiles();
    return cached(any_altar_, goals);
}

const Field& Pathing::to_hop(int hop) { return cached(entry(hop_fields_, map().hops().size(), hop), map().hops()[hop].sources); }

int Pathing::hop_landing_steps(int hop) {
    auto& steps = entry(hop_landing_steps_, map().hops().size(), hop);
    if (!steps) {
        const auto& h = map().hops()[hop];
        const auto& field = to_altar(h.altar);
        int best = unreachable;
        for (const vec2 l : h.landings.positions()) best = std::min(best, field.at(l));
        steps = best;
    }
    return *steps;
}

const Field& Pathing::from_landings(int hop) {
    return cached(entry(landing_fields_, map().hops().size(), hop), map().hops()[hop].landings);
}

bool Pathing::hop_ready(int hop) const {
    const auto h = static_cast<std::size_t>(hop);
    return h < hop_fields_.size() && hop_fields_[h] && h < landing_fields_.size() && landing_fields_[h];
}

const Field& Pathing::to_group(int group) { return cached(entry(group_fields_, map().groups.size(), group), map().groups[group].tiles()); }

int Pathing::centre_to_altar(int group) {
    auto& steps = entry(centre_to_altar_, map().groups.size(), group);
    // Draft steps use walking walls; a dasher keeps its own field's graph, as for spawn steps.
    if (!steps && (!world_.me().facts().has_dash() || map().crossable.is_empty() || map().dash_altar_steps_drafted()))
        steps = map().drafted_altar_steps(group);
    if (!steps) steps = to_any_altar().at(map().groups[group].centre);
    return *steps;
}

// The group's centre field if made, else the draft's spawn steps, else a field from our spawn's centre.
int Pathing::centre_to_spawn(int group) {
    auto& steps = entry(centre_to_spawn_, map().groups.size(), group);
    if (steps) return *steps;
    const vec2 tile = map().ally_spawn_centre;
    if (const auto* centre = from_centre(group)) steps = centre->at(tile);
    else if (!world_.me().facts().has_dash() || map().crossable.is_empty() || map().dash_spawn_steps_drafted())
        steps = map().drafted_spawn_steps(tile, group);
    if (!steps) steps = cached(spawn_centre_, single(tile)).at(map().groups[group].centre);
    return *steps;
}

// The first build draws every member alive in one board copy, as a belief at version 0 is, rather
// than setting each tile. live_flips_ then counts from another start: it is only compared with itself.
[[gnu::noinline]] void Pathing::draw_all_camps() {
    const auto& groups = map().groups;
    live_versions_.assign(groups.size(), 0), live_members_.assign(groups.size(), 0);
    copy_into(map().camp_tiles, live_camps_);
    for (std::size_t g = 0; g < groups.size(); ++g)
        if (const auto n = groups[g].members.size(); n <= 64) live_members_[g] = n == 64 ? ~std::uint64_t{0} : (std::uint64_t{1} << n) - 1;
}

const bitboard& Pathing::live_camps() {
    if (live_camps_version_ != world_.camps_version) {
        live_camps_version_ = world_.camps_version;
        const auto& groups = map().groups;
        if (live_versions_.size() != groups.size()) draw_all_camps();
        for (std::size_t g = 0; g < groups.size(); ++g) {
            const auto& c = world_.camps[g];
            if (live_versions_[g] == c.version) continue;
            live_versions_[g] = c.version;
            const auto& members = groups[g].members;
            if (members.size() > 64) {
                for (std::size_t i = 0; i < members.size(); ++i) live_camps_.set(members[i].pos, c.state == CampState::alive && c.health[i] > 0);
                ++live_flips_;
                continue;
            }
            std::uint64_t alive = 0;
            if (c.state == CampState::alive)
                for (std::size_t i = 0; i < members.size(); ++i) alive |= static_cast<std::uint64_t>(c.health[i] > 0) << i;
            for (std::uint64_t flipped = alive ^ live_members_[g]; flipped; flipped &= flipped - 1) {
                const int i = __builtin_ctzll(flipped);
                live_camps_.set(members[i].pos, (alive >> i & 1) != 0);
            }
            live_flips_ += alive != live_members_[g];
            live_members_[g] = alive;
        }
    }
    return live_camps_;
}

std::unique_ptr<Pathing::Approach>& Pathing::approach_slot(int group, int range) {
    const auto r = static_cast<std::size_t>(range);
    if (approach_fields_.size() <= r) approach_fields_.resize(r + 1);
    return entry(approach_fields_[r], map().groups.size(), group);
}

[[gnu::flatten]] bool Pathing::approach_ready(int group, int range) {
    const auto& slot = approach_slot(group, range);
    if (!slot) return false;
    const vec2 me = my_pos();
    auto& c = ready_check_;
    if (c.slot != slot.get() || c.round != world_.round || c.at != me) {
        bool ready = slot->field.at(me) != unreachable;
        if (ready) {
            const auto& live = live_camps();
            ready = slot->flips == live_flips_ || slot->camps == live || same_labels(*slot, group, range, live);
        }
        c = {slot.get(), world_.round, me, ready};
    }
    return c.ready;
}

// A search labels every tile nearer the goals than the last layer it finished, so a labelled tile's
// shortest walk runs through labelled tiles only. A camp tile that changed off them, and off the
// group's goal squares, cannot change a label: a new camp cuts no labelled walk, and a dead one is
// at least two layers past the labelled tiles unless it touches one. Over 8 changed tiles: searched.
bool Pathing::same_labels(Approach& slot, int group, int range, const bitboard& live) {
    static bitboard changed{cambc::uninitialized};
    xor_into(slot.camps, live, changed);
    if (board_count(changed) > 8) return false;
    const auto& members = map().groups[group].members;
    const auto& field = slot.field;
    for (const vec2 c : Tiles<8>{changed}) {
        for (const auto& m : members)
            if (dist(c, m.pos) <= range) return false;
        if (test(live, c)) {
            if (field.at(c) != unreachable) return false;
            continue;
        }
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx)
                if (const vec2 q{c.x + dx, c.y + dy}; in_bounds(q) && field.at(q) != unreachable) return false;
    }
    copy_into(live, slot.camps);
    slot.flips = live_flips_;
    return true;
}

// About our distance to the group: from the approach field it replaces, the group's centre field,
// or by way of our spawn. Walking around live camps can add a few layers.
// Negative when no field bounds it.
int Pathing::approach_steps(int group, int range, bool make) {
    const auto& s = map();
    const vec2 me = my_pos();
    const vec2 centre = s.groups[group].centre;
    int steps = -1;
    if (const auto& old = approach_slot(group, range); old && old->field.at(me) != unreachable) steps = old->field.at(me);
    else if (const auto* from = make ? centre_field(group) : from_centre(group)) steps = from->at(me);
    // On spawn the drafted steps are the spawn field's sum, without the field.
    else if (s.drafted() && test(s.ally_spawn, me)) steps = s.ally_steps(group) == unreachable ? -1 : s.ally_steps(group);
    else if ((make || s.from_ally_spawn_ready()) && s.from_ally_spawn().at(me) != unreachable && s.from_ally_spawn().at(centre) != unreachable)
        steps = s.from_ally_spawn().at(me) + s.from_ally_spawn().at(centre);
    return std::min(steps, walk_cap());
}

int Pathing::walk_cap() const { return walk_cap_ ? walk_cap_ : map().width + map().height; }

// Unbounded, walls seldom double the distance as the crow flies. At most search_cost_estimate(walk_cap()).
std::uint64_t Pathing::approach_cost(int group, int range) {
    if (approach_ready(group, range)) return 0;
    const int steps = approach_steps(group, range, false);
    return search_cost_estimate(steps >= 0 ? steps : std::min(2 * dist(my_pos(), map().groups[group].centre), walk_cap()));
}

[[gnu::flatten]] const Field* Pathing::prepare_approach(int group, int range, std::uint64_t fuel_floor) {
    approach_skipped_ = false;
    if (approach_ready(group, range)) return &approach_slot(group, range)->field;
    const int steps = approach_steps(group, range, false);
    // With no distance known, the search may run to walk_cap() layers; approach_steps may first
    // make the centre field.
    auto cost = search_cost_estimate(steps >= 0 ? steps : walk_cap());
    if (const auto& old = approach_slot(group, range); !(old && old->field.at(my_pos()) != unreachable) && farmed(group) && !from_centre(group))
        cost += centre_cap(group) ? search_cost_estimate(centre_cap(group)) : full_field_cost_estimate();
    if (!fuel_ok(fuel_floor + cost)) {
        approach_skipped_ = true;
        return nullptr;
    }
    return search_approach(group, range, approach_steps(group, range, true));
}

const Field* Pathing::approach(int group, int range) {
    if (approach_ready(group, range)) return &approach_slot(group, range)->field;
    return search_approach(group, range, approach_steps(group, range, true));
}

// Searched out to our tile only: it costs by our distance rather than the map's, and every tile of
// a walk down it is labelled, so it lasts the whole way unless we leave it or a camp dies or returns.
const Field* Pathing::search_approach(int group, int range, int steps) {
    const auto& s = map();
    const vec2 me = my_pos();
    const int layers = steps >= 0 ? steps + max_detour : walk_cap();
    FuelMeter meter{"approach"};
    if (!spare_approach_) spare_approach_ = std::make_unique<Approach>();
    auto& made = *spare_approach_;
    static bitboard walls{cambc::uninitialized}, open{cambc::uninitialized}, origin{cambc::uninitialized},
        visited{cambc::uninitialized};
    copy_into(live_camps(), made.camps);
    made.flips = live_flips_;
    or_into(static_walls(), made.camps, walls);
    auto& goals = made.field.goals;
    if (range == 0) {
        copy_into(s.groups[group].tiles(), goals);
    } else {
        clear_board(goals);
        // Live members only: standing in range of a dead one gains nothing.
        const auto& members = s.groups[group].members;
        const bool any_live = std::any_of(members.begin(), members.end(), [&](const auto& m) { return test(made.camps, m.pos); });
        for (const auto& m : members)
            if (!any_live || test(made.camps, m.pos)) draw_square(goals, m.pos, static_cast<float>(range));
        // A respawning group waits for its tiles to empty before it returns.
        if (!any_live) drop(goals, s.groups[group].tiles());
        // Not static_walls(): a dasher cannot stand on the tiles it jumps.
        or_into(s.blocked_for_us, made.camps, open);
        not_into(open, open);
        and_into(goals, open, goals);
    }
    set_tile(walls, me, false);
    clear_board(origin);
    set_tile(origin, me);
    const int reached = made.field.steps.compute_to_with_expansion_count(walls, goals, origin, visited, static_cast<std::uint16_t>(layers));
    if (made.field.at(me) == unreachable) {
        if ((steps < 0 || steps == walk_cap()) && reached >= layers) walk_cap_ = std::min(2 * walk_cap(), s.width * s.height);
        return nullptr;
    }
    auto& slot = approach_slot(group, range);
    std::swap(slot, spare_approach_);
    ready_check_.slot = nullptr;
    return &slot->field;
}

const Field* Pathing::from_centre(int group) {
    const auto& slot = entry(centre_fields_, map().groups.size(), group);
    return slot ? &*slot : nullptr;
}

const Field* Pathing::centre_field(int group) {
    if (!farmed(group)) return nullptr;
    auto& slot = entry(centre_fields_, map().groups.size(), group);
    if (!slot) make_centre(slot, group);
    return &*slot;
}

void Pathing::make_centre(Slot& slot, int group) {
    auto& cap = centre_cap(group);
    if (!cap) {
        cached(slot, single(map().groups[group].centre));
        return;
    }
    // Nothing checks fuel between doubling tries here, so one uncapped search makes the same field
    // without the failed tries; the cap ends where the doubling would have left it.
    FuelMeter meter{"field"};
    int layers = 0;
    slot = make_field(static_walls(), single(map().groups[group].centre), unreachable, &layers);
    while (cap <= layers) cap *= 2;
}

void Pathing::grow_centre(Slot& slot, int group, std::uint64_t fuel_floor) {
    auto& cap = centre_cap(group);
    // The doubling tries in one, at the deepest doubled cap the fuel left pays for: a field complete
    // within a cap is the same at any larger one, and the cap ends where the tries would leave it.
    int try_cap = cap;
    while (2 * try_cap <= unreachable && fuel_ok(fuel_floor + search_cost_estimate(2 * try_cap))) try_cap *= 2;
    FuelMeter meter{"field"};
    int layers = 0;
    slot = make_field(static_walls(), single(map().groups[group].centre), try_cap, &layers);
    if (!slot) cap = 2 * try_cap;
    else
        while (cap <= layers) cap *= 2;
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

[[gnu::flatten]] bool Pathing::warm_centres(std::uint64_t fuel_floor, int near) {
    if (centres_ready_) return true;
    const auto round = cambc::round_number();
    const auto cost = field_cost_estimate();
    const auto bounded_floor = fuel_floor - std::min(fuel_floor, end_reserve - last_reserve);
    // Nearest `near` first: the groups farm weighs first get their fields soonest.
    const int n = static_cast<int>(map().groups.size());
    const auto* order = near >= 0 && near < n ? map().nearest_groups(near) : nullptr;
    for (int k = 0; k < n; ++k) {
        const int g = order ? (*order)[k] : k;
        if (!farmed(g)) continue;
        auto& slot = entry(centre_fields_, map().groups.size(), g);
        if (slot) continue;
        if (!centre_cap(g)) {
            if (cambc::round_number() != round || !fuel_ok(fuel_floor + cost)) return false;
            cached(slot, single(map().groups[g].centre));
            continue;
        }
        while (!slot) {
            if (cambc::round_number() != round || !fuel_ok(bounded_floor + search_cost_estimate(centre_cap(g)))) return false;
            grow_centre(slot, g, bounded_floor);
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
    for (int a = 0; a < static_cast<int>(map().altars.size()); ++a) {
        if (!afford(altar_slot(a))) return false;
        to_altar(a);
    }
    for (; warm_group_ < static_cast<int>(map().groups.size()); ++warm_group_, warm_member_ = 0) {
        if (!farmed(warm_group_) || map().attack_tiles_drafted(warm_group_, attack_range)) continue;
        for (; warm_member_ < static_cast<int>(map().groups[warm_group_].members.size()); ++warm_member_)
            if (cambc::round_number() != round || !prepare_member(warm_group_, warm_member_, attack_range, fuel_floor)) return false;
    }
    for (int h = 0; h < static_cast<int>(map().hops().size()); ++h) {
        if (!afford(entry(hop_fields_, map().hops().size(), h))) return false;
        to_hop(h);
        if (map().hops()[h].altar >= 0) continue;
        if (!afford(entry(landing_fields_, map().hops().size(), h))) return false;
        from_landings(h);
    }
    return true;
}

void Pathing::occupied_into(bitboard& out) {
    static bitboard t{cambc::uninitialized};
    occupancy_into(team::ally, out);
    or_into(out, map().blocked_for_us, out);
    occupancy_into(team::enemy, t);
    or_into(out, t, out);
    camps_into(t);
    or_into(out, t, out);
    teleports_into(t);
    or_into(out, t, out);
    if (bumped_any_) or_into(out, bumped_, out);
}

const bitboard& Pathing::blocked() {
    if (dashes_seen_ != outside_dashes()) invalidate();
    if (!blocked_fresh_) {
        occupied_into(blocked_);
        set_tile(blocked_, my_pos(), false);
        blocked_fresh_ = true;
    }
    return blocked_;
}

void Pathing::invalidate() {
    blocked_fresh_ = false;
    pos_fresh_ = false;
    dashes_seen_ = outside_dashes();
}

vec2 Pathing::my_pos() {
    const auto round = round_now();
    if (dashes_seen_ != outside_dashes()) invalidate();
    if (!pos_fresh_ || pos_round_ != round) {
        pos_ = my_position();
        pos_round_ = round;
        pos_fresh_ = true;
    }
    return pos_;
}

[[gnu::always_inline]] inline bool Pathing::steppable(vec2 p, const bitboard& walls, const bitboard* avoid) const {
    return in_bounds(p) && !test(walls, p) && !(avoid && test(*avoid, p)) && !(guard() && test(*guard(), p));
}

Pathing::Neighbours Pathing::closer_neighbours(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    const vec2 me = my_pos();
    const int here = field.at(me);
    const auto& walls = blocked();
    Neighbours out;
    std::array<int, 8> steps_of{};
    std::array<int, 8> aim_of{};
    for (auto d : directions) {
        const vec2 p = me + d;
        // The field first: steppable() may work out a deferred guard.
        if (!in_bounds(p)) continue;
        const int steps = field.at(p);
        if (steps >= here || !steppable(p, walls, avoid)) continue;
        const int towards = aim ? aim_distance(p, *aim) : 0;
        auto i = out.count++;
        for (; i > 0 && (steps_of[i - 1] > steps || (steps_of[i - 1] == steps && aim_of[i - 1] > towards)); --i)
            out.tiles[i] = out.tiles[i - 1], steps_of[i] = steps_of[i - 1], aim_of[i] = aim_of[i - 1];
        out.tiles[i] = p;
        steps_of[i] = steps;
        aim_of[i] = towards;
    }
    return out;
}

// The guard (step_guard, up to ~50k) only adds walls, and walls only lengthen routes. With none found
// around the other walls, none is found around the guard's too: it stays deferred, and what the
// failed search leaves (its labels, route_exhausted_) is worked out with it only if read. A deferred
// guard lies within its cover: when the route around the cover is as long as the route around
// neither, with as many first steps, it is the guarded route, and its steps are off the cover.
constexpr std::uint64_t cheap_guard = 15000;
Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {
    failure_known_ = true;
    // Without a cover (Willow's guard) the search runs once, guarded; so it does while placing the
    // guard has lately cost less than the searches that could spare it.
    if (guard_fn_ && guard_cover_ && step_guard_costliest() >= cheap_guard && !test(goals, my_pos())) {
        if (const auto round = round_now(); route_cover_round_ != round) {
            route_cover_ = guard_cover_(world_, *guard_safety_, guard_here_, guard_radius_);
            route_cover_round_ = round;
        }
        const bitboard* cover = route_cover_;
        // No tile coverable, no guard: one search, exact whatever it finds.
        if (!cover) {
            guard_skipped_ = true;
            auto r = route_around(goals, avoid, max_steps, aim, nullptr);
            r.unguarded = true;
            return r;
        }
        const vec2 me = my_pos(), pocket = pocket_at_;
        auto bare = route_around(goals, avoid, max_steps, aim, nullptr);
        if (bare.steps == unreachable) {
            guard_skipped_ = true;
            // Enclosed is enclosed with more walls, and no ally is beside us: the search ran dry,
            // whatever its labels, and make_way reads none.
            if (pocket_at_ == me) return bare;
            failure_known_ = false;
            pocket_at_ = pocket;
            return bare;
        }
        // As if it had not run.
        pocket_at_ = pocket;
        if (bare.count > 0) {
            auto r = route_around(goals, avoid, max_steps, aim, cover);
            pocket_at_ = pocket;
            if (r.steps == bare.steps && r.count == bare.count) {
                r.unguarded = guard_skipped_ = true;
                return r;
            }
            // The guarded first steps hold the cover's and lie within the bare ones, in the same order:
            // when the first bare step is the cover's first too, it is the guarded first. Only a hidden
            // unit refusing it would make the next one count, and a tile seen this turn hides none.
            if (r.steps == bare.steps && r.count > 0 && r.first_steps[0] == bare.first_steps[0] && test(world_.visible, r.first_steps[0])) {
                r.count = 1;
                r.unguarded = guard_skipped_ = true;
                return r;
            }
        }
    }
    return route_around(goals, avoid, max_steps, aim, guard());
}

// An ally beside us that make_way could free: on a goal, or beside a tile the last search labelled.
bool Pathing::labelled_ally_beside(const bitboard& allies, const bitboard& goals, const bitboard* avoid) {
    const vec2 me = my_pos();
    for (auto d : directions) {
        const vec2 a = me + d;
        if (!in_bounds(a) || !test(allies, a) || (avoid && test(*avoid, a) && !test(*avoid, me))) continue;
        if (test(goals, a)) return true;
        for (auto e : directions)
            if (in_bounds(a + e) && route_label(a + e) != unreachable) return true;
    }
    return false;
}

// A failed route() that left the guard deferred, searched again with it as it would have been.
void Pathing::know_failure(const bitboard& goals, const bitboard* avoid, int max_steps) {
    if (failure_known_) return;
    failure_known_ = true;
    (void)route_around(goals, avoid, max_steps, std::nullopt, guard());
}

[[gnu::flatten]] Pathing::Route Pathing::route_around(const bitboard& goals, const bitboard* avoid, int max_steps,
                                                      std::optional<vec2> aim, const bitboard* guard) {
    world_.throw_if_stale();
    Route r;
    route_exhausted_ = false;
    const vec2 me = my_pos();
    if (test(goals, me)) {
        r.steps = 0;
        return r;
    }
    // Scratch kept between calls: the host overwrites every output in full.
    static bitboard walls{cambc::uninitialized}, origin, visited{cambc::uninitialized};
    static vec2 origin_at{-1, -1};
    // A route is mostly followed by a step, which makes blocked() stale: unless it is fresh, the
    // walls are read straight into the route's board.
    if (blocked_fresh_) copy_into(blocked_, walls);
    else occupied_into(walls);
    if (avoid && test(*avoid, me)) {
        // Inside danger, walling it all would leave no way out: free the connected part we stand in
        // (outside is the wall board for that fill). Kept for the next route from this tile around
        // the same danger.
        static bitboard outside{cambc::uninitialized}, region{cambc::uninitialized}, danger{cambc::uninitialized},
            danger_of{cambc::uninitialized};
        static vec2 danger_at{-1, -1};
        if (me != danger_at || !boards_equal(*avoid, danger_of)) {
            not_into(*avoid, outside);
            outside.reachable_tiles_into(me, static_cast<std::uint16_t>(map().width + map().height), region);
            copy_into(*avoid, danger);
            drop(danger, region);
            copy_into(*avoid, danger_of);
            danger_at = me;
        }
        or_into(walls, danger, walls);
    } else if (avoid) {
        or_into(walls, *avoid, walls);
    }
    if (guard) or_into(walls, *guard, walls);
    set_tile(walls, me, false);
    const int cap = std::min<int>(max_steps, unreachable);
    auto& kept = kept_route_;
    int here = kept_steps(kept, goals, walls, me, cap);
    if (here == unreachable) {
        // A search fails only at its cap, having labelled all the goals reach, so in a pocket (holes a
        // dash crossed, units) it costs a whole map; a standoff repeats it every turn. Once a failed
        // search finds us enclosed, that tile is tested first.
        if (me == pocket_at_) {
            if (enclosed(walls, goals, me)) {
                route_exhausted_ = true;
                return r;
            }
            pocket_at_ = {-1, -1};
        }
        // Search outwards from the goals until it reaches us: every tile one layer nearer than ours
        // is then labelled, so each neighbour on a shortest route is known.
        FuelMeter meter{"route"};
        // The failed search again (a blocked walk tries several ways to the same goals): its labels
        // up to a cap no higher, or all of them past where it ran dry.
        auto& f = failed_;
        int layers;
        route_label_cap_ = cap;
        if (f.layers >= 0 && f.me == me && (cap <= f.cap || f.layers < f.cap) && boards_equal(goals, f.goals)
            && boards_equal(walls, f.walls)) {
            layers = std::min(f.layers, cap);
            here = unreachable;
        } else {
            if (in_bounds(origin_at)) set_tile(origin, origin_at, false);
            set_tile(origin, me);
            origin_at = me;
            // Goals on walls are no roots; with none left we stay unreachable. A search that runs dry
            // counts one layer past its last; one cut off at the cap counts the cap.
            layers = route_field_.compute_to_with_expansion_count(walls, goals, origin, visited, static_cast<std::uint16_t>(cap));
            here = steps_at(route_field_, me);
            f.layers = -1;
            if (here == unreachable) {
                copy_into(goals, f.goals);
                walls.swap(f.walls);
                f.me = me, f.cap = cap, f.layers = layers;
            }
        }
        if (here == unreachable) {
            route_exhausted_ = layers < cap;
            if (!route_exhausted_ && enclosed(f.walls, goals, me)) route_exhausted_ = true, pocket_at_ = me;
            return r;
        }
        std::swap(route_field_, kept.field);
        copy_into(goals, kept.goals);
        walls.swap(kept.walls);
        kept.layer = here;
    }
    const auto& field = kept.field;
    r.steps = here;
    // As distance_field::next_moves_from, without its vector: the nearest neighbours, north first.
    std::array<std::uint16_t, 8> around{};
    std::uint16_t best = unreachable;
    const bool inside = me.x > 0 && me.y > 0 && me.x < map().width - 1 && me.y < map().height - 1;
    for (int i = 0; i < 8; ++i) {
        const vec2 p = me + directions[i];
        around[i] = inside || in_bounds(p) ? static_cast<std::uint16_t>(steps_at(field, p)) : unreachable;
        best = std::min(best, around[i]);
    }
    if (best < here)
        for (int i = 0; i < 8; ++i)
            if (around[i] == best) r.first_steps[r.count++] = me + directions[i];
    if (aim) {
        std::array<int, 8> towards{};
        for (int j = 0; j < r.count; ++j) {
            const vec2 p = r.first_steps[j];
            const int score = aim_distance(p, *aim);
            int i = j;
            for (; i > 0 && towards[i - 1] > score; --i)
                r.first_steps[i] = r.first_steps[i - 1], towards[i] = towards[i - 1];
            r.first_steps[i] = p;
            towards[i] = score;
        }
    }
    return r;
}

// make_way reads the failed search's labels, but only beside an ally next to us: with none there, no
// cap reaches a goal from a closed walkable region that holds none.
bool Pathing::enclosed(const bitboard& walls, const bitboard& goals, vec2 me) {
    static bitboard region{cambc::uninitialized}, wider{cambc::uninitialized}, allies{cambc::uninitialized};
    walls.reachable_tiles_into(me, pocket_radius, region);
    walls.reachable_tiles_into(me, pocket_radius + 1, wider);
    if (!boards_equal(region, wider)) return false;
    and_into(region, goals, wider);
    if (!board_empty(wider)) return false;
    occupancy_into(team::ally, allies);
    for (auto d : directions)
        if (in_bounds(me + d) && test(allies, me + d)) return false;
    return true;
}

// Labels below our steps survive walling a tile labelled at or past them, and freeing a non-goal
// tile whose neighbours are all labelled at or past one less (it would land at or past ours).
int Pathing::kept_steps(const KeptRoute& k, const bitboard& goals, const bitboard& walls, vec2 me, int cap) {
    if (k.layer < 0) return unreachable;
    const int steps = steps_at(k.field, me);
    if (steps == unreachable || steps > k.layer || steps > cap || !(goals == k.goals)) return unreachable;
    static bitboard changed{cambc::uninitialized};
    xor_into(walls, k.walls, changed);
    constexpr std::uint32_t most = 4;
    if (board_empty(changed)) return steps;
    std::array<vec2, most + 1> at;
    const auto n = positions_into(changed, at.data(), most + 1);
    if (n > most) return unreachable;
    for (std::uint32_t i = 0; i < n; ++i) {
        const vec2 t = at[i];
        if (test(walls, t)) {
            if (steps_at(k.field, t) < steps) return unreachable;
            continue;
        }
        if (test(goals, t)) return unreachable;
        for (const auto d : directions)
            if (in_bounds(t + d) && steps_at(k.field, t + d) + 1 < steps) return unreachable;
    }
    return steps;
}

[[gnu::flatten]] bool Pathing::try_move(vec2 tile, bool* refused) {
    if (refused) *refused = true;
    if (guard() && test(*guard(), tile)) return false;
    return move_to(tile, refused);
}

bool Pathing::move_to(vec2 tile, bool* refused) {
    if (refused) *refused = true;
    throw_if_stale();
    try {
        if (cambc::self().move_absolute(tile)) {
            invalidate();
            return true;
        }
        // A hidden unit was there: the tile is now revealed to us for the rest of the round.
        if (refused) *refused = false;
        set_tile(bumped_, tile);
        bumped_any_ = bumped_new_ = true;
        invalidate();
    } catch (const cambc::error&) {
    }
    return false;
}

[[gnu::flatten]] bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {
    if (!my_can_move()) return false;
    // Only a hidden blocker makes a retry worth its search.
    for (int attempt = 0; attempt < 3; ++attempt) {
        const auto r = route(goals, avoid, max_steps, aim);
        bool bumped = false;
        for (int i = 0; i < r.count; ++i) {
            if (r.unguarded ? move_to(r.first_steps[i], nullptr) : try_move(r.first_steps[i])) return true;
            bumped |= test(bumped_, r.first_steps[i]);
        }
        if (!bumped) return r.steps == unreachable && make_way(goals, avoid, max_steps);
    }
    return false;
}

bool Pathing::make_way(const bitboard& goals, const bitboard* avoid, int max_steps) {
    const vec2 me = my_pos();
    static bitboard allies{cambc::uninitialized};
    occupancy_into(team::ally, allies);
    // The guard only skips allies below, and its walls only raise labels: an ally off the goals with
    // no labelled neighbour unguarded has none guarded. With only such allies beside us nothing
    // below opens, and route_exhausted_ stands.
    if (!failure_known_) {
        if (!labelled_ally_beside(allies, goals, avoid)) return false;
        know_failure(goals, avoid, max_steps);
    }
    // Freeing ally tile a adds only a to the failed search: a's distance is one more than its
    // nearest labelled neighbour's (labels run up to the cap), and ours one more than a's. Our own
    // labelled neighbours are all at the cap, so a is then the only first step.
    const int cap = std::min<int>(max_steps, unreachable);
    bool opened = false;
    for (auto d : directions) {
        const vec2 a = me + d;
        if (!in_bounds(a) || !test(allies, a)) continue;
        // route() blocks these again after freeing a; inside danger, a is in our own region.
        if ((guard() && test(*guard(), a)) || (avoid && test(*avoid, a) && !test(*avoid, me))) continue;
        if (test(goals, a)) {
            opened = true;
            continue;
        }
        int nearest = unreachable;
        for (auto e : directions)
            if (in_bounds(a + e)) nearest = std::min(nearest, route_label(a + e));
        if (nearest == unreachable) continue;
        opened = true;
        if (nearest + 2 > cap) continue;
        route_exhausted_ = false;
        auto& self = cambc::self();
        const auto ally = cambc::vision::champion_at(a);
        const auto mine = self.gem_count(), theirs = ally.gem_count();
        if (mine > theirs || (mine == theirs && self.champion_name() > ally.champion_name())) return false;
        const auto& walls = blocked();
        std::optional<vec2> best;
        int best_dist = 0;
        for (auto e : directions) {
            const vec2 p = me + e;
            if (!steppable(p, walls, avoid)) continue;
            if (const int d2 = dist(p, a); d2 > best_dist) best = p, best_dist = d2;
        }
        return best && try_move(*best);
    }
    // A search that ran dry reaches a free ally's tile only to open a way through it.
    route_exhausted_ &= !opened;
    return false;
}

bool Pathing::step_towards_funded(const bitboard& goals, std::uint64_t fuel_floor) {
    if (world_.is_stale()) return false;
    if (!my_can_move() || test(goals, my_pos())) return false;
    const auto fixed = search_cost_estimate(0) + small_cost_estimate;
    const auto chunks = search_chunks();
    for (int attempt = 0; attempt < 3; ++attempt) {
        const auto remaining = fuel();
        if (remaining < fuel_floor || remaining - fuel_floor < fixed + chunks) {
            note_shortcut("siege-route-fuel");
            return false;
        }
        // Each try, hidden-blocker retries included, searches as deep as the fuel left pays for; no
        // shortest path is longer than the map's tile count.
        const int cap = static_cast<int>(std::min<std::uint64_t>(
            static_cast<std::uint64_t>(map().width) * map().height,
            (remaining - fuel_floor - fixed) / chunks));
        if (world_.is_stale()) return false;
        const auto r = route(goals, nullptr, cap);
        if (world_.is_stale()) return false;
        bool bumped = false;
        for (int i = 0; i < r.count; ++i) {
            if (world_.is_stale()) return false;
            const auto before_move = fuel();
            if (before_move < fuel_floor || before_move - fuel_floor < last_reserve) return false;
            if (r.unguarded ? move_to(r.first_steps[i], nullptr) : try_move(r.first_steps[i])) return true;
            bumped |= test(bumped_, r.first_steps[i]);
        }
        if (!bumped) return false;
    }
    return false;
}

bool Pathing::step_towards(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    const int here = field.at(my_pos());
    if (here == 0 || !my_can_move()) return false;
    bool searched = false;
    if (here != unreachable) {
        const int cap = here + max_detour;
        if (!fuel_ok(search_cost_estimate(cap) + end_reserve)) note_shortcut("static-descend");
        else if (step_towards(field.goals, avoid, cap, aim)) return true;
        else searched = true;
    }
    if (descend(field, avoid, aim)) return true;
    if (searched && !failure_known_) {
        // Whether the guarded search ran dry decides only whether the wider one below runs. If that
        // fails unguarded with no ally make_way could free, it fails guarded and frees none.
        const vec2 pocket = pocket_at_;
        const bool wide = route_around(field.goals, avoid, here + 6 * max_detour, aim, nullptr).steps != unreachable;
        pocket_at_ = pocket;
        static bitboard allies{cambc::uninitialized};
        occupancy_into(team::ally, allies);
        if (!wide && !labelled_ally_beside(allies, field.goals, avoid)) return false;
        know_failure(field.goals, avoid, here + max_detour);
    }
    // Live camps can block the static way for longer than max_detour (a dead-end pocket whose way
    // out a camp holds): a wider search walks round them, unless the last ran dry.
    return searched && !route_exhausted_ && step_towards(field.goals, avoid, here + 6 * max_detour, aim);
}

bool Pathing::descend(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    if (!my_can_move()) return false;
    for (auto p : closer_neighbours(field, avoid, aim))
        if (try_move(p)) return true;
    return false;
}

bool Pathing::step_closer(vec2 target, const bitboard* avoid, std::optional<vec2> aim) {
    if (!my_can_move()) return false;
    const vec2 me = my_pos();
    const auto& walls = blocked();
    std::optional<vec2> best;
    int best_dist = dist(me, target);
    for (auto d : directions) {
        const vec2 p = me + d;
        if (!steppable(p, walls, avoid)) continue;
        if (const int d2 = dist(p, target); d2 < best_dist
            || (best && d2 == best_dist && aim && aim_distance(p, *aim) < aim_distance(*best, *aim)))
            best = p, best_dist = d2;
    }
    return best && try_move(*best);
}

const bitboard& dash_landings_from(const StaticMap& map, vec2 from, const bitboard* also) {
    static bitboard camps{cambc::uninitialized}, excluded{cambc::uninitialized}, t{cambc::uninitialized},
        landings{cambc::uninitialized};
    camps_into(camps);
    // Dash paths cross holes, altars, allies and unseen enemies, but not walls, camps, visible
    // enemies (probe-dash-enemy) or the enemy spawn.
    occupancy_into(team::enemy, t);
    or_into(map.walls, camps, excluded);
    or_into(excluded, t, excluded);
    or_into(excluded, map.enemy_spawn, excluded);
    excluded.reachable_tiles_into(from, dash_range, landings);
    and_into(landings, map.open_for_us, landings);
    or_into(camps, t, excluded);
    occupancy_into(team::ally, t);
    or_into(excluded, t, excluded);
    teleports_into(t);
    or_into(excluded, t, excluded);
    if (also) or_into(excluded, *also, excluded);
    and_into(excluded, landings, excluded);
    xor_into(landings, excluded, landings);
    set_tile(landings, from, false);
    return landings;
}

const bitboard& Pathing::dash_landings() {
    static bitboard off{cambc::uninitialized};
    const bitboard* also = nullptr;
    if (bumped_any_ && guard()) or_into(bumped_, *guard(), off), also = &off;
    else if (bumped_any_) also = &bumped_;
    else if (guard()) also = guard();
    return dash_landings_from(map(), my_pos(), also);
}

bitboard Pathing::teleport_targets() {
    static bitboard t{cambc::uninitialized};
    const vec2 here = my_pos();
    auto targets = square(here, teleport_crystal_range);
    // Dead camps' tiles (teleport_crystal.target), read only for the groups within range: one host
    // call a member tile, telling an empty seen tile from a hidden one. In a live group, only a
    // member believed dead and seen empty (probe-teleport-dead-member).
    bool dead = false;
    for (const int g : map().groups_near(here, teleport_crystal_range)) {
        const auto& c = world_.camps[g];
        const bool alive = c.state == CampState::alive;
        // Unseen, a respawning group may be back once due.
        const bool gone = !alive && (c.state == CampState::cleared || c.respawn_round > world_.round);
        const auto& members = map().groups[g].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            const auto& m = members[i];
            if (dist(here, m.pos) > teleport_crystal_range || (alive && c.health[i] > 0)) continue;
            std::int32_t camp = 0;
            const bool seen = cambc::detail::sdk_has_camp(m.pos.x, m.pos.y, &camp) == 0;
            if (seen ? camp != 0 : !gone) continue;
            if (!dead) copy_into(map().standable, t), dead = true;
            set_tile(t, m.pos);
        }
    }
    targets &= dead ? t : map().standable;
    occupancy_into(team::ally, t);
    drop(targets, t);
    occupancy_into(team::enemy, t);
    drop(targets, t);
    teleports_into(t);
    drop(targets, t);
    if (bumped_any_) drop(targets, bumped_);
    return targets;
}

} // namespace aph
