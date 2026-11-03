#include "pathing.h"
#include <algorithm>
#include <array>
#include <initializer_list>
#include "comms.h"
#include "dash_turns.h"
#include "safety.h"
#include "world.h"
#include "../combat/self_abilities.h"

namespace aph {

namespace {

template <class T> T& entry(std::vector<T>& table, std::size_t count, int i) {
    if (table.size() != count) table.resize(count);
    return table[static_cast<std::size_t>(i)];
}

int aim_distance(vec2 p, vec2 aim) { return std::abs(p.x - aim.x) + std::abs(p.y - aim.y); }

// No visible enemy this close for a travel dash: one we could still see from its landing. Nearer,
// the dash is the fight's.
constexpr int travel_dash_clearance = vision_radius + dash_range;

// The tiles a turn of travel reaches, a walk and a dash, as bits of one word: bit (dy + r) * side +
// dx + r for the tile (dx, dy) from us.
namespace window {
constexpr int r = 1 + dash_range, side = 2 * r + 1;
static_assert(side * side <= 64);
constexpr std::uint64_t all = (std::uint64_t{1} << (side * side)) - 1, centre = std::uint64_t{1} << (r * side + r);
constexpr std::uint64_t column(int x) {
    std::uint64_t m = 0;
    for (int y = 0; y < side; ++y) m |= std::uint64_t{1} << (y * side + x);
    return m;
}
// Every tile within a king step of one in m.
constexpr std::uint64_t grow(std::uint64_t m) {
    const std::uint64_t row = m | (m << 1 & ~column(0)) | (m >> 1 & ~column(side - 1));
    return (row | row << side | row >> side) & all;
}
constexpr std::uint64_t bit(vec2 me, vec2 p) { return std::uint64_t{1} << ((p.y - me.y + r) * side + (p.x - me.x + r)); }
inline vec2 tile(vec2 me, int b) { return {me.x + b % side - r, me.y + b / side - r}; }
// The window's tiles on the map.
inline std::uint64_t inside(vec2 me, int width, int height) {
    std::uint64_t cols = 0, rows = 0;
    for (int k = 0; k < side; ++k) {
        if (const int x = me.x + k - r; x >= 0 && x < width) cols |= column(k);
        if (const int y = me.y + k - r; y >= 0 && y < height) rows |= ((std::uint64_t{1} << side) - 1) << (k * side);
    }
    return cols & rows;
}
// The tiles in the window of any of `boards` (null entries skipped). With `across`
// (board_chunks_across) their storage is read in place, as Safety's windows are: the window lies
// within 2x2 of its 8x8 chunks, whose words are or-ed across the boards before one extraction.
inline std::uint64_t bits(std::initializer_list<const bitboard*> boards, vec2 me, int across, int width, int height) {
    std::uint64_t m = 0;
    if (across <= 0) {
        for (const bitboard* b : boards)
            if (b)
                for (const vec2 p : Tiles<side * side>{within(*b, me, r)}) m |= bit(me, p);
        return m;
    }
    const int x0 = me.x - r, y0 = me.y - r;
    const int lo = std::max(0, -x0), hi = std::min(side, width - x0);
    const std::uint32_t columns = ((1u << hi) - 1) & ~((1u << lo) - 1);
    const int a = x0 >> 3, s = x0 - 8 * a, c = y0 >> 3, down = (height + 7) / 8;
    const bool in_c0 = c >= 0 && c < down, in_c1 = c + 1 >= 0 && c + 1 < down, in_a0 = a >= 0 && a < across, in_a1 = a + 1 >= 0 && a + 1 < across;
    const std::size_t i00 = static_cast<std::size_t>(c * across + a);
    std::uint64_t w00 = 0, w01 = 0, w10 = 0, w11 = 0;
    for (const bitboard* b : boards) {
        if (!b) continue;
        const std::uint64_t* words = b->ptr();
        if (in_c0 && in_a0) w00 |= words[i00];
        if (in_c0 && in_a1) w01 |= words[i00 + 1];
        if (in_c1 && in_a0) w10 |= words[i00 + static_cast<std::size_t>(across)];
        if (in_c1 && in_a1) w11 |= words[i00 + static_cast<std::size_t>(across) + 1];
    }
    for (int k = 0; k < side; ++k) {
        const int y = y0 + k;
        if (y < 0 || y >= height) continue;
        const bool second = (y >> 3) != c;
        const int shift = 8 * (y & 7);
        const auto seg = static_cast<std::uint32_t>(((second ? w10 : w00) >> shift) & 0xFF)
                         | static_cast<std::uint32_t>(((second ? w11 : w01) >> shift) & 0xFF) << 8;
        m |= static_cast<std::uint64_t>((seg >> s) & columns) << (k * side);
    }
    return m;
}
} // namespace window

} // namespace

Pathing::Pathing(const World& world) : world_{world} {
    for (auto* b : {&route_labelled_, &kept_routes_[0].labelled, &kept_routes_[1].labelled, &round_labels_.labelled}) {
        clear_board(*b);
        not_into(*b, *b);
    }
}

namespace {
constexpr int pull_radius = 30; // allies farther than this pull nothing
constexpr float pull_near = 2.0f; // nor do those this near
} // namespace

void Pathing::make_pull() {
    if (pull_round_ == world_.round) return;
    pull_round_ = world_.round, pull_n_ = 0;
    const auto& m = map();
    const vec2 me = my_pos();
    for (const auto& a : world_.allies) {
        if (a.is_self || !a.alive || pull_n_ >= static_cast<int>(pull_at_.size())) continue;
        vec2 q{-1, -1};
        int w = 0;
        if (a.visible && in_bounds(a.pos) && !test(m.ally_spawn, a.pos)) q = a.pos, w = 2;
        else if (const int g = comms::claim_of(world_, a.index); g >= 0 && g < static_cast<int>(m.groups.size())) q = m.groups[g].centre, w = 2;
        if (w == 0 || dist(q, me) > pull_radius) continue;
        pull_at_[pull_n_] = q, pull_weight_[pull_n_] = w, ++pull_n_;
    }
}

int Pathing::pull(vec2 p) {
    make_pull();
    int s = 0;
    for (int i = 0; i < pull_n_; ++i) {
        const float dx = static_cast<float>(p.x - pull_at_[i].x), dy = static_cast<float>(p.y - pull_at_[i].y);
        const float d = __builtin_sqrtf(dx * dx + dy * dy);
        if (d > pull_near) s += static_cast<int>(16.0f * (d - pull_near)) * pull_weight_[i];
    }
    return s;
}

const StaticMap& Pathing::map() const { return world_.map(); }

const bitboard& Pathing::static_walls() const {
    const int kind = world_.me().facts().dash_kind();
    return kind == 0 ? map().blocked_for_us : kind == 1 ? map().dash_walls : map().landing_dash_walls;
}

const bitboard& Pathing::foot() const {
    const int kind = world_.me().facts().dash_kind();
    return kind == 0 ? map().foot() : kind == 1 ? map().dash_foot() : map().landing_dash_foot();
}

// foot() is a flood of the whole map (~17k on maze maps); a short one from p that meets the spawn
// proves p on it, as the spawn is (~100-300). The first turns stand near the spawn.
bool Pathing::on_foot_unmade(vec2 p) const {
    constexpr int near_steps = 8;
    const auto& s = map();
    if (!s.foot_made(world_.me().facts().dash_kind()) && in_bounds(p) && dist(p, s.ally_spawn_centre) <= near_steps) {
        static bitboard near{cambc::uninitialized};
        static_walls().reachable_tiles_into(p, near_steps, near);
        near &= s.ally_spawn;
        if (!near.is_empty()) return true;
    }
    foot_made_ = &foot();
    return test(*foot_made_, p);
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
        cost += centre_cap(group) ? static_field_cost_estimate(centre_cap(group)) : full_field_cost_estimate();
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
    // The group's tiles are cardinally connected and hold its centre: off the centre's field (whole,
    // over the same static walls) none is reached, whatever the cap.
    if (const auto* c = range == 0 ? from_centre(group) : nullptr; c && c->at(me) == unreachable && !test(static_walls(), s.groups[group].centre))
        return nullptr;
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
    while (2 * try_cap <= unreachable && fuel_ok(fuel_floor + static_field_cost_estimate(2 * try_cap))) try_cap *= 2;
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
    // A respawning group returns only once its camp tiles are empty: waiting on one held it back
    // for good where allies queued behind in a dead end.
    if (world_.camps[group].state == CampState::respawning) drop(tiles, map().groups[group].tiles());
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

bool Pathing::farmed(int g) const {
    return (!map().groups[g].has_monolith || !map().monolith_only) && map().groups[g].gems + map().groups[g].gold > 0;
}

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
    // centre_cap() reads every group's enemy steps: those not yet decoded cost their decode here,
    // unchecked (all at once without the plan's index).
    if (!map().warm_enemy_steps(fuel_floor) || !map().warm_drafted_steps(fuel_floor)) return false;
    const auto round = cambc::round_number();
    const auto cost = field_cost_estimate();
    const auto bounded_floor = fuel_floor - std::min(fuel_floor, end_reserve - last_reserve);
    // Nearest `near` first: the groups farm weighs first get their fields soonest.
    const int n = static_cast<int>(map().groups.size());
    // The order is unchecked work too (prepare_next_turn's price): it ran turns out on its own.
    if (near >= 0 && near < n && n <= 256 && !map().nearest_groups_ready(near) && !fuel_ok(fuel_floor + 100 * map().groups.size() + 3000)) return false;
    const auto* order = near >= 0 && near < n ? map().nearest_groups(near) : nullptr;
    // Fields once made stay: in the same order, the groups before where the last call stopped are
    // all made or not farmed (~70 fuel a group to pass again, every queue until the centres are done).
    if (near != warm_centre_near_) warm_centre_near_ = near, warm_centre_k_ = 0;
    for (int k = warm_centre_k_; k < n; ++k) {
        const int g = order ? (*order)[k] : k;
        if (!farmed(g)) continue;
        auto& slot = entry(centre_fields_, map().groups.size(), g);
        if (slot) continue;
        warm_centre_k_ = k;
        if (!centre_cap(g)) {
            if (cambc::round_number() != round || !fuel_ok(fuel_floor + cost)) return false;
            cached(slot, single(map().groups[g].centre));
            continue;
        }
        while (!slot) {
            if (cambc::round_number() != round || !fuel_ok(bounded_floor + static_field_cost_estimate(centre_cap(g)))) return false;
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
    // The occupancy board omits unseen camps: a route through one flips each time it comes into sight.
    or_into(out, live_camps(), out);
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
    ++acts_;
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
        const int towards = pull(p) * 256 + (aim ? aim_distance(p, *aim) : 0);
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
        // No first step to guard: a dash or a wait, which travel() guards itself.
        if (bare.count == 0) return bare;
        {
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

// An ally beside us that make_way could free: on a goal, or beside a tile the last search labelled
// (or at the front of a line of allies that is).
bool Pathing::labelled_ally_beside(const bitboard& allies, const bitboard& goals, const bitboard* avoid) {
    const vec2 me = my_pos();
    for (auto d : directions) {
        const vec2 a = me + d;
        if (!in_bounds(a) || !test(allies, a) || (avoid && test(*avoid, a) && !test(*avoid, me))) continue;
        if (test(goals, a) || label_through(a, allies, avoid, me) != unreachable) return true;
    }
    return false;
}

int Pathing::label_through(vec2 a, const bitboard& allies, const bitboard* avoid, vec2 me) {
    // A walk-parted search labelled nothing; the walk through a crowd of allies costs ~5k an ally.
    if (route_label_cap_ < 0) return unreachable;
    int nearest = unreachable;
    for (auto e : directions)
        if (in_bounds(a + e)) nearest = std::min(nearest, route_label(a + e));
    if (nearest != unreachable) return nearest + 1;
    // make_way's callers walk the same line again under the same labels (step_safely with and
    // without avoid, labelled_ally_beside then make_way): the walk reads only route_label (the
    // field by route_gen_, and the cap), allies, avoid, the guard, a and me. A pending guard is
    // not keyed: the walk would work it out.
    if (guard_fn_) return walk_through(a, allies, avoid, me);
    const bitboard* g = guard_;
    for (auto& m : through_memo_)
        if (m && m->gen == route_gen_ && m->cap == route_label_cap_ && m->a == a && m->me == me && m->avoided == (avoid != nullptr)
            && m->guarded == (g != nullptr) && boards_equal(allies, m->allies) && (!avoid || boards_equal(*avoid, m->avoid))
            && (!g || boards_equal(*g, m->guard)))
            return m->result;
    const int result = walk_through(a, allies, avoid, me);
    // Never taken (the guard was worked out before the walk), but keeps the key what the walk read.
    if (guard_fn_ || guard_ != g) return result;
    auto& m = through_memo_[through_next_];
    through_next_ = (through_next_ + 1) % through_memo_.size();
    if (!m) m.emplace();
    m->gen = route_gen_, m->cap = route_label_cap_, m->a = a, m->me = me, m->avoided = avoid != nullptr, m->guarded = g != nullptr;
    m->result = result;
    copy_into(allies, m->allies);
    if (avoid) copy_into(*avoid, m->avoid);
    if (g) copy_into(*g, m->guard);
    return result;
}

int Pathing::walk_through(vec2 a, const bitboard& allies, const bitboard* avoid, vec2 me) {
    // No labelled tile beside a: the allies beside it may stand in the way too. The line holds at
    // most as many allies as there are (a among them), each beside one before it, so every tile it
    // reads lies within that many steps of a: with no labelled tile (route_labelled_) that near, none
    // is reached. The board calls cost about as much as walking two allies: they wait for a longer line.
    constexpr int most = 8;
    std::array<vec2, most> line;
    std::array<int, most> depth;
    int n = 0, best = unreachable;
    line[0] = a, depth[0] = 0, n = 1;
    bool boxed = false;
    for (int i = 0; i < n; ++i) {
        const int d = depth[static_cast<std::size_t>(i)];
        // Lines are listed by depth and a label is at least 0: none later beats best.
        if (best <= d + 1) break;
        if (!boxed && n >= 4) {
            boxed = true;
            static bitboard box{cambc::uninitialized};
            clear_board(box);
            draw_square(box, a, static_cast<float>(std::min<std::uint32_t>(most, board_count(allies))));
            and_into(box, route_labelled_, box);
            if (board_empty(box)) return unreachable;
        }
        for (auto e : directions) {
            const vec2 p = line[static_cast<std::size_t>(i)] + e;
            if (!in_bounds(p) || p == me) continue;
            if (!test(allies, p)) {
                // a's own neighbours were all read above.
                if (i == 0) continue;
                if (const int l = route_label(p); l != unreachable) best = std::min(best, l + 1 + d);
                continue;
            }
            // route() blocks these again once freed.
            if (n == most || (guard() && test(*guard(), p)) || (avoid && test(*avoid, p) && !test(*avoid, me))) continue;
            bool listed = false;
            for (int j = 0; j < n && !listed; ++j) listed = line[static_cast<std::size_t>(j)] == p;
            if (!listed) line[static_cast<std::size_t>(n)] = p, depth[static_cast<std::size_t>(n++)] = d + 1;
        }
    }
    return best;
}

// Out of line, with their origins mirrored in spare_me_: a search from no spare's origin, nearly
// every one, then costs a few tests.
[[gnu::noinline]] bool Pathing::take_spare(const bitboard& goals, const bitboard& walls, vec2 me, int cap) {
    for (std::size_t i = 0; i < spare_routes_.size(); ++i) {
        auto& s = spare_routes_[i];
        if (spare_me_[i] == me && (cap <= s->cap || s->layers < s->cap) && boards_equal(goals, s->goals)
            && boards_equal(walls, s->walls)) {
            swap_spare(i);
            return true;
        }
    }
    return false;
}

// failed_ moves into the least recently used spare (an empty one first).
[[gnu::noinline]] void Pathing::spare_failed() {
    std::size_t oldest = 0;
    for (std::size_t i = 0; i < spare_routes_.size(); ++i) {
        if (!spare_routes_[i]) {
            oldest = i;
            spare_routes_[i].emplace();
            break;
        }
        if (spare_routes_[i]->used < spare_routes_[oldest]->used) oldest = i;
    }
    swap_spare(oldest);
}

void Pathing::swap_spare(std::size_t i) {
    auto& s = *spare_routes_[i];
    auto& f = failed_;
    f.goals.swap(s.goals);
    f.walls.swap(s.walls);
    std::swap(f.me, s.me);
    std::swap(f.cap, s.cap);
    std::swap(f.layers, s.layers);
    std::swap(route_field_, s.field);
    route_labelled_.swap(s.labelled);
    ++route_gen_;
    s.used = ++spare_clock_;
    spare_me_[i] = s.layers >= 0 ? s.me : vec2{-1, -1};
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
    if (walk_parted(goals, me)) {
        route_exhausted_ = true;
        route_label_cap_ = -1;
        return r;
    }
    // Scratch kept between calls: the host overwrites every output in full.
    static bitboard walls{cambc::uninitialized}, origin;
    static vec2 origin_at{-1, -1};
    // A route is mostly followed by a step, which makes blocked() stale: unless it is fresh, the
    // walls are read straight into the route's board.
    if (blocked_fresh_) copy_into(blocked_, walls);
    else occupied_into(walls);
    if (crossing_) drop(walls, crossings());
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
    auto& kept = kept_routes_[crossing_];
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
        if (f.layers >= 0 && f.me == me && (cap <= f.cap || f.layers < f.cap)
            && (boards_equal(goals, f.goals) || (within_ok_ && within_failed(goals, avoid))) && boards_equal(walls, f.walls)) {
            layers = std::min(f.layers, cap);
            here = unreachable;
        } else if (walking_round_ && round_fails(goals, walls, me, cap)) {
            return r;
        } else if ((me == spare_me_[0] || me == spare_me_[1] || me == spare_me_[2]) && take_spare(goals, walls, me, cap)) {
            layers = std::min(f.layers, cap);
            here = unreachable;
        } else {
            if (f.layers >= 0) spare_failed();
            if (in_bounds(origin_at)) set_tile(origin, origin_at, false);
            set_tile(origin, me);
            origin_at = me;
            // Goals on walls are no roots; with none left we stay unreachable. A search that runs dry
            // counts one layer past its last; one cut off at the cap counts the cap.
            layers = route_field_.compute_to_with_expansion_count(walls, goals, origin, route_labelled_, static_cast<std::uint16_t>(cap));
            ++route_gen_;
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
            if (walking_round_) keep_round();
            return r;
        }
        std::swap(route_field_, kept.field);
        route_labelled_.swap(kept.labelled);
        ++route_gen_;
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
    // A crossing is labelled, but only a dash goes onto it (travel()).
    const bool beside_crossing = crossing_ && test(map().near_crossable, me);
    for (int i = 0; i < 8; ++i) {
        const vec2 p = me + directions[i];
        around[i] = inside || in_bounds(p) ? static_cast<std::uint16_t>(steps_at(field, p)) : unreachable;
        if (beside_crossing && around[i] != unreachable && test(crossings(), p)) around[i] = unreachable;
        best = std::min(best, around[i]);
    }
    if (best < here)
        for (int i = 0; i < 8; ++i)
            if (around[i] == best) r.first_steps[r.count++] = me + directions[i];
    if (r.count > 1) {
        std::array<int, 8> towards{};
        for (int j = 0; j < r.count; ++j) {
            const vec2 p = r.first_steps[j];
            const int score = pull(p) * 256 + (aim ? aim_distance(p, *aim) : 0);
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

// A walking route (crossings shut) stays in one region of blocked_for_us, and map().foot() is a
// whole one: off it no goal on it is reached, on it none off it. Then every search fails, a wider
// one too, and labels no tile near us (make_way reads none: route_label_cap_ -1).
bool Pathing::walk_parted(const bitboard& goals, vec2 me) {
    if (crossing_ || !has_crossings() || !map().foot_made(0)) return false;
    const auto& foot = map().foot();
    static bitboard on{cambc::uninitialized};
    and_into(goals, foot, on);
    return test(foot, me) ? board_empty(on) : boards_equal(on, goals);
}

// The kept walk round proves this one fails: the same goals, a cap no higher (or it ran dry), us
// past the cap on its labels, and no tile freed since that a way within the cap could take (a goal,
// or beside a tile labelled below the cap). A way through no freed tile was open to it.
bool Pathing::round_fails(const bitboard& goals, const bitboard& walls, vec2 me, int cap) {
    const auto& k = round_labels_;
    if (k.cap < 0 || (cap > k.cap && !k.dry) || steps_at(k.field, me) <= cap || !boards_equal(goals, k.goals)) return false;
    static bitboard freed{cambc::uninitialized};
    xor_into(walls, k.walls, freed);
    and_into(freed, k.walls, freed);
    constexpr std::uint32_t most = 8;
    std::array<vec2, most + 1> at;
    const auto n = positions_into(freed, at.data(), most + 1);
    if (n > most) return false;
    for (std::uint32_t i = 0; i < n; ++i) {
        if (test(goals, at[i])) return false;
        for (const auto d : directions)
            if (in_bounds(at[i] + d) && steps_at(k.field, at[i] + d) < cap) return false;
    }
    return true;
}

// failed_'s search becomes the kept walk round; its labels leave route_field_, so failed_ is dropped.
void Pathing::keep_round() {
    auto& f = failed_;
    auto& k = round_labels_;
    std::swap(route_field_, k.field);
    route_labelled_.swap(k.labelled);
    ++route_gen_;
    f.goals.swap(k.goals);
    f.walls.swap(k.walls);
    k.cap = f.cap, k.dry = f.layers < f.cap;
    f.layers = -1;
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
            turn_acts.walked = true;
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

Pathing::TravelDash Pathing::travel_dash() {
    TravelDash td;
    const auto& self = world_.me();
    const int slot = self.facts().slot_of(AbilityKind::dash);
    if (slot < 0 || !self.alive || enemy_within(world_, my_pos(), travel_dash_clearance)) return td;
    const int cool = my_cooldown(slot);
    td.slot = slot;
    td.now = cool <= 0 && my_can_cast();
    td.cool = std::max(cool - 1, 0);
    return td;
}

const bitboard& Pathing::crossings() {
    if (world_.me().facts().dash_kind() != 2) return map().crossable;
    if (!crossings_) {
        crossings_.emplace(map().crossable);
        drop(*crossings_, map().landing_dash_walls);
    }
    return *crossings_;
}

bool Pathing::has_crossings() {
    if (has_crossings_ < 0) has_crossings_ = world_.me().facts().has_dash() && !board_empty(crossings());
    return has_crossings_ > 0;
}

// Within the farthest horizon ahead() looks (the dash's whole cooldown and a turn) of a crossing.
const bitboard& Pathing::near_crossings() {
    if (!near_crossings_) {
        static bitboard none, visited{cambc::uninitialized};
        static cambc::distance_field steps;
        steps.compute(none, crossings(), visited, static_cast<std::uint16_t>(max_horizon + 1));
        near_crossings_.emplace(visited);
    }
    return *near_crossings_;
}

// Down the field from us, the direction last stepped tried first, until a crossing beside a tile is
// one step nearer the goals: the route crosses there, and its landing is two nearer. A trace is kept
// for the same field and goals (one per goal board: a turn may route to several) while we stand on it
// at its label: the tiles behind us are dropped and it runs on only as far as the horizon has moved.
Pathing::Ahead Pathing::ahead(const cambc::distance_field& d, const bitboard& goals, int here, int horizon) {
    const vec2 me = my_pos();
    ++trace_clock_;
    Trace* kept = nullptr;
    int k = 0;
    // Equally near tiles abound: one beside the trace at its label, and beside its next tile (or
    // the crossing), joins it in place of the traced one.
    const auto on = [&](const Trace& t, int i) {
        const vec2 at = t.tiles[static_cast<std::size_t>(i)];
        return at == me || (dist(at, me) <= 1 && dist(i + 1 < t.count ? t.tiles[static_cast<std::size_t>(i + 1)] : t.crossing, me) <= 1);
    };
    for (auto& s : traces_)
        if (k = s.top - here; s.field == &d && k >= 0 && k < s.count && (k + 1 < s.count || s.found || s.ended) && on(s, k)
                              && boards_equal(goals, s.goals)) {
            kept = &s;
            kept->tiles[static_cast<std::size_t>(k)] = me;
            break;
        }
    if (kept && kept->found && steps_at(d, kept->crossing) != kept->rest + 1) kept->field = nullptr, kept = nullptr;
    if (!kept) {
        if (!test(near_crossings(), me)) return {};
        kept = &traces_[0];
        for (auto& s : traces_)
            if (s.used < kept->used) kept = &s;
        kept->field = &d, kept->count = 0, kept->top = here, kept->found = kept->ended = false, k = 0;
        copy_into(goals, kept->goals);
    }
    auto& t = *kept;
    t.used = trace_clock_;
    ahead_read_ = &t;
    if (k > 0) {
        std::copy(t.tiles.begin() + k, t.tiles.begin() + t.count, t.tiles.begin());
        t.count -= k, t.top = here;
    }
    const auto& cross = crossings();
    const auto& near = map().near_crossable;
    const int width = map().width, height = map().height;
    // One pass round the last tile: a crossing one step nearer ends the trace there; else the first
    // nearer tile, the direction last stepped tried first, joins it.
    if (t.count == 0) t.tiles[0] = me, t.count = 1, t.ended = here <= 0;
    while (!t.found && !t.ended && t.count <= horizon) {
        const vec2 q = t.tiles[static_cast<std::size_t>(t.count - 1)];
        const int label = t.top - (t.count - 1);
        const bool beside = test(near, q);
        int next = -1;
        for (int i = 0; i < 8; ++i) {
            const int dir = (t.last + i) & 7;
            const vec2 y = q + directions[dir];
            if (y.x < 0 || y.y < 0 || y.x >= width || y.y >= height || steps_at(d, y) != label - 1) continue;
            if (beside && test(cross, y)) {
                t.found = true, t.rest = label - 2, t.crossing = y;
                break;
            }
            if (next < 0) next = dir;
            if (!beside) break;
        }
        if (t.found) break;
        if (next < 0 || t.count == static_cast<int>(t.tiles.size())) {
            t.ended = true;
            break;
        }
        t.last = next;
        t.tiles[static_cast<std::size_t>(t.count++)] = q + directions[next];
        t.ended = label - 1 <= 0;
    }
    if (t.found && t.count - 1 <= horizon) return {t.count - 1, t.rest, t.crossing};
    return {};
}

// A tile past the crossing ahead (fewer steps than its launch) has open ground on the field; one
// before it crosses there, waiting for the dash if need be, or walks round on the walking field.
int Pathing::turns_from(const Labels& l, vec2 q, int c) const { return turns_at(l, q, steps_at(*l.d, q), c); }

int Pathing::turns_at(const Labels& l, vec2 q, int d, int c) const {
    int turns = d == unreachable                                ? 1 << 20
                : l.ahead.launch >= 0 && d >= l.ahead.rest + 2 ? dash_turns::across(d - 2 - l.ahead.rest, l.ahead.rest, c)
                                                                : dash_turns::open(d, c);
    if (l.w)
        if (const int w = steps_at(*l.w, q); w != unreachable) turns = std::min(turns, dash_turns::open(w, c));
    return turns;
}

// Each option ends on a tile with a cooldown, worth turns_from() after this turn. Walks (the routes'
// first steps, the nearest on each field) and waiting keep the dash. Of equally quick options a dash
// is taken: cast now, it is ready again soonest (52.9% against keeping it, EXPERIMENTS).
// No end of a dash is more than `reach` steps nearer on either field (allies are walls to both, so a
// dash over one is not priced), and turns_from never beats open ground at its steps, nor, before a
// crossing this turn cannot take, that crossing: dashes are looked at only if that bound beats the
// best walk. Then the window's ends are worked out in bits, and each read once.
Pathing::Plan Pathing::plan(const TravelDash& td, const Labels& l, int here, std::span<const vec2> walks,
                            std::span<const vec2> around, const bitboard* avoid, std::optional<vec2> aim, bool may_wait) {
    using dash_turns::after_dash;
    using dash_turns::open;
    const vec2 me = my_pos();
    const bool walking = my_can_move();
    Plan best;
    const int stand = turns_from(l, me, td.cool);
    best.turns = stand, best.end = here; // standing: no move
    bool moves = false; // standing waits only if it beats every walk
    const auto offer_walk = [&](Plan::Kind kind, vec2 q) {
        const int e = steps_at(*l.d, q), t = turns_at(l, q, e, td.cool);
        if (!moves || t < best.turns || (t == best.turns && e < best.end)) best.kind = kind, best.turns = t, best.end = e, best.walk = q, moves = true;
    };
    if (walking && !walks.empty()) offer_walk(Plan::Kind::walk, walks[0]);
    if (walking && !around.empty()) offer_walk(Plan::Kind::around, around[0]);
    // Of a wait and a walk round as quick, the wait: else the walk round, then the walk back, repeat.
    if (may_wait && walking && (!moves || stand < best.turns || (stand == best.turns && best.kind == Plan::Kind::around)))
        best = Plan{.kind = Plan::Kind::wait, .turns = stand, .end = here};
    if (!td.now) return best;
    const int reach = walking ? 1 + dash_range : dash_range;
    int bound = open(std::max(0, here - reach), after_dash);
    if (l.ahead.launch >= reach) {
        bound = dash_turns::across(l.ahead.launch - reach, l.ahead.rest, after_dash);
        if (l.w)
            if (const int w = steps_at(*l.w, me); w != unreachable) bound = std::min(bound, open(std::max(0, w - reach), after_dash));
    }
    if (bound > best.turns) return best;

    const auto& walls = blocked();
    const bitboard* cover = nullptr;
    const bitboard* const guard = guard_cover(cover) && !cover ? nullptr : this->guard();
    static bitboard no_dash{cambc::uninitialized};
    const int across = board_chunks_across(map()), width = map().width, height = map().height;
    const auto bits = [&](std::initializer_list<const bitboard*> boards) { return window::bits(boards, me, across, width, height); };
    const std::uint64_t shut = bits({&walls, avoid, guard});
    // The step guard is worked out within a dash of us (guard_steps): with one, every end stays there.
    const std::uint64_t near = guard ? window::grow(window::grow(window::centre)) : window::all;
    const std::uint64_t inside = window::inside(me, width, height) & near, free = inside & ~shut;
    // Dash paths cross holes, altars, allies and unseen units, not walls, visible camps, visible
    // enemies or the enemy spawn (abilities.dash, probe-dash-enemy). No visible enemy is this near
    // (travel_dash_clearance, and travel() after a refused move).
    if (!static_no_dash_) {
        static_no_dash_.emplace(map().walls);
        *static_no_dash_ |= map().enemy_spawn;
    }
    camps_into(no_dash);
    const std::uint64_t passes = inside & ~bits({&no_dash, &*static_no_dash_});
    const bitboard* veto = travel_landing_veto(world_, me);
    const std::uint64_t lands = free & ~(veto ? bits({veto}) : 0);
    // Landings from `from` (one bit): one step, or two by a tile they may cross (map.corners).
    const auto dash_from = [&](std::uint64_t from) {
        const std::uint64_t step = window::grow(from) & ~from;
        return (window::grow(step & passes) | step) & lands & ~from;
    };
    const std::uint64_t dashed = dash_from(window::centre);
    std::uint64_t then_walk = 0, walk_then = 0;
    std::array<std::uint64_t, 8> from_first{}; // landings after the walk to each first step
    const std::uint64_t firsts = walking ? window::grow(window::centre) & free & ~window::centre : 0;
    if (walking) {
        then_walk = window::grow(dashed) & free & ~window::centre;
        int i = 0;
        for (std::uint64_t m = firsts; m; m &= m - 1, ++i) walk_then |= from_first[i] = dash_from(m & -m);
    }
    const bool walk_costs = !world_.me().facts().walk_and_attack_independent();
    // Of equally quick dashes a ranged champion keeps its walk (its attack), then the end nearest, then the aim.
    int best_b = -1;
    bool best_spends = false;
    // Off the walking field an end's turns depend on its steps alone, which lie within `reach` of ours.
    std::array<int, 2 * (1 + dash_range) + 1> by_steps;
    by_steps.fill(-1);
    for (std::uint64_t m = dashed | then_walk | walk_then; m; m &= m - 1) {
        const int b = __builtin_ctzll(m);
        const vec2 q = window::tile(me, b);
        const int e = steps_at(*l.d, q);
        if (e >= here && !l.w) continue; // never sooner than walking down the field
        int turns;
        if (const int k = e - here + reach; !l.w && k >= 0) {
            auto& v = by_steps[static_cast<std::size_t>(k)];
            if (v < 0) v = turns_at(l, q, e, after_dash);
            turns = v;
        } else {
            turns = turns_at(l, q, e, after_dash);
        }
        if (turns > best.turns) continue;
        const bool spends = walk_costs && !(dashed >> b & 1);
        if (turns == best.turns && best_b >= 0
            && (spends != best_spends ? spends : e != best.end ? e > best.end : !aim || aim_distance(q, *aim) >= aim_distance(window::tile(me, best_b), *aim)))
            continue;
        best.turns = turns, best.end = e, best_b = b, best_spends = spends;
    }
    if (best_b < 0) return best;
    const std::uint64_t end = std::uint64_t{1} << best_b;
    const vec2 q = window::tile(me, best_b);
    if (dashed & end) return Plan{.kind = Plan::Kind::dash, .turns = best.turns, .end = best.end, .land = q};
    if (then_walk & end) {
        const std::uint64_t landing = window::grow(end) & dashed;
        return Plan{.kind = Plan::Kind::dash, .turns = best.turns, .end = best.end, .walk = q, .land = window::tile(me, __builtin_ctzll(landing))};
    }
    int i = 0;
    for (std::uint64_t m = firsts; m; m &= m - 1, ++i)
        if (from_first[i] & end)
            return Plan{.kind = Plan::Kind::dash, .turns = best.turns, .end = best.end, .walk = window::tile(me, __builtin_ctzll(m)), .land = q, .walk_first = true};
    return best;
}

Pathing::Travel Pathing::travel(const TravelDash& td, Route& r, const bitboard& goals, const bitboard* avoid, int max_steps,
                                std::optional<vec2> aim) {
    // An enemy a refused move revealed makes the dash the fight's (travel_dash read the beliefs).
    if (bumped_any_ && any_within(live_champion_tiles(team::enemy), my_pos(), travel_dash_clearance)) return Travel::walk;
    const int here = r.steps;
    Labels l;
    l.d = &kept_routes_[crossing_].field;
    Route around;
    // The walking route, with the searches' other state left the crossing route's. A walk round
    // that failed is kept while we stand on the same tile before the same crossing, for no wider a
    // search (goals near each other share it: farm asks for several a turn).
    const auto walk_round = [&](int cap) {
        const vec2 me = my_pos();
        auto& f = round_failed_;
        if (f.at == me && f.crossing == l.ahead.crossing && f.avoided == (avoid != nullptr) && f.round + ability_cooldown > world_.round && cap <= f.cap)
            return;
        const bool exhausted = route_exhausted_, known = failure_known_;
        const vec2 pocket = pocket_at_;
        {
            const Crossing walk{crossing_, false}, proof{walking_round_, true};
            around = route(goals, avoid, cap, aim);
        }
        route_exhausted_ = exhausted, failure_known_ = known, pocket_at_ = pocket;
        if (around.steps != unreachable) {
            l.w = &kept_routes_[0].field;
            return;
        }
        f.at = me, f.round = world_.round, f.cap = cap, f.crossing = l.ahead.crossing, f.avoided = avoid != nullptr;
    };
    if (crossing_) {
        l.ahead = ahead(*l.d, goals, here, horizon(td));
        // Walking round can be sooner only when crossing waits for the dash (this turn counted, the
        // dash as it is now), and then only by a walk that the turns crossing takes would cover.
        const int c = td.now ? 0 : td.cool + 1;
        if (const int crossing = l.ahead.launch < 0 ? 0 : dash_turns::across(l.ahead.launch, l.ahead.rest, c);
            crossing > dash_turns::open(here, c))
            walk_round(std::min(max_steps, dash_turns::reach(crossing - 1, c)));
    }
    const auto plan_with = [&] {
        // A wait is only for the dash: with it ready, a crossing not taken is closed to it this turn.
        return plan(td, l, here, {r.first_steps.data(), static_cast<std::size_t>(r.count)},
                    {around.first_steps.data(), static_cast<std::size_t>(around.count)}, avoid, aim, l.ahead.launch >= 0 && !td.now);
    };
    auto p = plan_with();
    // A crossing in this turn's reach, the dash ready, and no dash across it: a landing it needs is
    // held or refused. Then we walk round, by no longer a walk than crossing after a whole cooldown.
    if (td.now && p.kind != Plan::Kind::dash && l.ahead.launch >= 0 && l.ahead.launch <= (my_can_move() ? 1 : 0) && !l.w) {
        walk_round(std::min(max_steps, dash_turns::reach(dash_turns::across(l.ahead.launch, l.ahead.rest, ability_cooldown) - 1, 0)));
        if (l.w) p = plan_with();
    }
    switch (p.kind) {
    case Plan::Kind::walk: return Travel::walk;
    case Plan::Kind::around: r = around; return Travel::walk;
    case Plan::Kind::wait: return Travel::moved;
    case Plan::Kind::dash: return take(td, p);
    }
    return Travel::walk;
}

// After a dash, a visible enemy within travel_dash_clearance that the landing brought into sight
// ends the travel: the walk is the fight's.
Pathing::Travel Pathing::take(const TravelDash& td, const Plan& p) {
    if (p.walk_first) {
        bool refused = true;
        if (!try_move(p.walk, &refused)) return refused ? Travel::walk : Travel::bumped;
        if (!any_within(live_champion_tiles(team::enemy), my_pos(), travel_dash_clearance)) dash_to(td.slot, p.land);
        return Travel::moved;
    }
    if (!dash_to(td.slot, p.land)) return test(bumped_, p.land) ? Travel::bumped : Travel::walk;
    if (p.walk.x >= 0 && my_can_move() && !any_within(live_champion_tiles(team::enemy), my_pos(), travel_dash_clearance)) try_move(p.walk);
    return Travel::moved;
}

bool Pathing::dash_to(int slot, vec2 land) {
    throw_if_stale();
    bool cast = false;
    try {
        cast = cast_slot(slot, land);
    } catch (const cambc::error&) {
        return false;
    }
    invalidate();
    // A hidden unit was there: the tile is now revealed to us for the rest of the round.
    if (!cast) set_tile(bumped_, land), bumped_any_ = bumped_new_ = true;
    return cast;
}

bool Pathing::step_towards_within(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {
    struct Within {
        bool& on;
        ~Within() { on = false; }
    } within{within_ok_ = true};
    return step_towards(goals, avoid, max_steps, aim);
}

// Goals within the failed search's fail too: fewer goals label no tile lower, and a search that ran
// dry reaches none of them. Its labels then stand in for ours: make_way (and labelled_ally_beside)
// decide under them as under ours, which are no lower, when no ally beside us off the goals has a
// label there, for none then has one of its own. The other state a failed search leaves
// (route_exhausted_, pocket_at_) is read only after the next search, which step_towards_within's
// caller does not read.
[[gnu::noinline]] bool Pathing::within_failed(const bitboard& goals, const bitboard* avoid) {
    static bitboard joined{cambc::uninitialized}, allies{cambc::uninitialized};
    or_into(goals, failed_.goals, joined);
    if (!boards_equal(joined, failed_.goals)) return false;
    const vec2 me = my_pos();
    occupancy_into(team::ally, allies);
    for (auto d : directions) {
        const vec2 a = me + d;
        if (!in_bounds(a) || !test(allies, a) || (avoid && test(*avoid, a) && !test(*avoid, me)) || test(goals, a)) continue;
        if (label_through(a, allies, avoid, me) != unreachable) return false;
    }
    return true;
}

bool Pathing::step_towards(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {
    return step_route(travel_dash(), goals, avoid, max_steps, aim);
}

int Pathing::travel_turns(int steps) {
    const auto td = travel_dash();
    return td.slot < 0 ? steps : dash_turns::open(steps, td.now ? 0 : td.cool + 1);
}

[[gnu::flatten]] bool Pathing::step_route(const TravelDash& td, const bitboard& goals, const bitboard* avoid, int max_steps,
                                          std::optional<vec2> aim) {
    if (!my_can_move() && !td.now) return false;
    const Crossing open{crossing_, td.slot >= 0 && has_crossings()};
    // Only a hidden blocker makes a retry worth its search.
    for (int attempt = 0; attempt < 3; ++attempt) {
        // A dash plan reads blocked(): made first, the route copies it rather than reading it again.
        if (td.now) (void)blocked();
        auto r = route(goals, avoid, max_steps, aim);
        if (td.slot >= 0 && (td.now || crossing_) && r.steps != unreachable && r.steps > 0) {
            const auto t = travel(td, r, goals, avoid, max_steps, aim);
            if (t == Travel::moved) return true;
            if (t == Travel::bumped) continue;
        }
        if (!my_can_move()) return false;
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
    // No goals label no tile, and labels a failed search reused were found beside no ally of ours
    // (within_failed): no ally opens a way (farm's attack tiles all held by allies).
    if (board_empty(goals)) return false;
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
    // Freeing ally tile a (and the allies queued behind it) adds only them to the failed search:
    // a's distance is label_through's (labels run up to the cap), and ours one more than a's. Our
    // own labelled neighbours are all at the cap, so a is then the only first step.
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
        const int through = label_through(a, allies, avoid, me);
        if (through == unreachable) continue;
        opened = true;
        if (through + 1 > cap) continue;
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
    const auto td = travel_dash();
    if ((!my_can_move() && !td.now) || test(goals, my_pos())) return false;
    const Crossing open{crossing_, td.slot >= 0 && has_crossings()};
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
        if (td.now) (void)blocked();
        auto r = route(goals, nullptr, cap);
        if (world_.is_stale()) return false;
        if (td.slot >= 0 && (td.now || crossing_) && r.steps != unreachable && r.steps > 0) {
            const auto t = travel(td, r, goals, nullptr, cap, std::nullopt);
            if (t == Travel::moved) return true;
            if (t == Travel::bumped) continue;
            if (world_.is_stale()) return false;
        }
        if (!my_can_move()) return false;
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
    return step_field(field, avoid, aim, nullptr);
}

bool Pathing::walk_down(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    ahead_read_ = nullptr;
    if (descend(field, avoid, aim)) return true;
    const auto failed = descended();
    return step_field(field, avoid, aim, &failed);
}

bool Pathing::step_field(const Field& field, const bitboard* avoid, std::optional<vec2> aim, const Descended* failed) {
    const int here = field.at(my_pos());
    const auto td = travel_dash();
    if (here == 0 || (!my_can_move() && !td.now)) return false;
    const Crossing open{crossing_, td.slot >= 0 && has_crossings()};
    bool searched = false;
    if (here != unreachable) {
        const int cap = here + max_detour;
        if (!fuel_ok(search_cost_estimate(cap) + end_reserve)) note_shortcut("static-descend");
        else if (step_route(td, field.goals, avoid, cap, aim)) return true;
        else searched = true;
    }
    // The search that failed between moved nothing: the descent, its dash plan included, fails again.
    const bool same = failed && failed->acts == acts_ && failed->guard == guard_ && failed->fn == guard_fn_;
    if (same && failed->trace) failed->trace->used = ++trace_clock_; // keeps the traces' replacement order
    if (!same && descend_with(td, field, avoid, aim)) return true;
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
    return searched && !route_exhausted_ && step_route(td, field.goals, avoid, here + 6 * max_detour, aim);
}

bool Pathing::descend(const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    return descend_with(travel_dash(), field, avoid, aim);
}

bool Pathing::descend_with(const TravelDash& td, const Field& field, const bitboard* avoid, std::optional<vec2> aim) {
    if (!my_can_move() && !td.now) return false;
    const auto steps = my_can_move() ? closer_neighbours(field, avoid, aim) : Neighbours{};
    if (td.now && !(bumped_any_ && any_within(live_champion_tiles(team::enemy), my_pos(), travel_dash_clearance))) {
        const int here = field.at(my_pos());
        if (here != unreachable && here > 0) {
            Labels l;
            l.d = &field.steps;
            if (has_crossings()) l.ahead = ahead(field.steps, field.goals, here, horizon(td));
            const auto p = plan(td, l, here, {steps.tiles.data(), static_cast<std::size_t>(steps.count)}, {}, avoid, aim, false);
            if (p.kind == Plan::Kind::dash && take(td, p) == Travel::moved) return true;
        }
    }
    if (!my_can_move()) return false;
    for (auto p : steps)
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
            || (best && d2 == best_dist && pull(p) * 256 + (aim ? aim_distance(p, *aim) : 0) < pull(*best) * 256 + (aim ? aim_distance(*best, *aim) : 0)))
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
