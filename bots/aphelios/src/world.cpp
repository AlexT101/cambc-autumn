#include "world.h"
#include <algorithm>
#include <iostream>
#include <string>

namespace aph {

namespace {

// Thin readers over the raw host imports. The typed SDK views re-query the engine on every
// accessor and throw for hidden units; one raw read per unit per turn is cheaper and lets
// "not in vision" be a value instead of an exception.
namespace engine {
using namespace cambc::detail;

constexpr std::int32_t not_in_vision = static_cast<std::int32_t>(cambc::error_code::api_not_in_vision);
constexpr std::int32_t not_found = static_cast<std::int32_t>(cambc::error_code::api_not_found);

std::uint32_t id(cambc::handle_champion_t h) { return static_cast<std::uint32_t>(h); }

std::optional<champion_info> champion(std::uint32_t h) {
    champion_info info{};
    const auto code = sdk_champion(h, &info);
    if (code == not_in_vision) return std::nullopt;
    check(code);
    if (info.x < 0 || info.y < 0) return std::nullopt; // dead
    return info;
}

bool alive(std::uint32_t h) {
    std::int32_t value{};
    check(sdk_champion_is_alive(h, &value));
    return value != 0;
}

int cooldown(std::uint32_t h, std::uint32_t slot) {
    std::int32_t value{};
    check(sdk_champion_cooldown(h, slot, &value));
    return value;
}

int gems(std::uint32_t h) {
    std::uint32_t value{};
    check(sdk_champion_gems(h, &value));
    return static_cast<int>(value);
}

int items(std::uint32_t h) {
    cambc::enum_map<cambc::item_type> counts;
    check(sdk_champion_items(h, counts.ptr()));
    int total = 0;
    for (auto n : counts) total += static_cast<int>(n);
    return total;
}

// Static camp data, read through the raw imports: map::camp_groups() builds an SDK object graph
// that costs more fuel than the data itself.
std::vector<std::uint32_t> camp_group_ids() {
    std::uint32_t count{};
    check(sdk_map_num_camp_groups(&count));
    std::vector<std::uint32_t> ids(count);
    check(sdk_map_camp_groups(ids.data(), count, &count));
    ids.resize(count);
    return ids;
}

std::vector<std::uint32_t> camp_ids(std::uint32_t group) {
    std::uint32_t count{};
    check(sdk_map_camp_group_num_camps(group, &count));
    std::vector<std::uint32_t> ids(count);
    check(sdk_map_camp_group_camps(group, ids.data(), count, &count));
    ids.resize(count);
    return ids;
}

// Every champion handle of a side, visible or not, in id (= pick) order.
std::vector<cambc::handle_champion_t> handles(team side) {
    std::uint32_t count{};
    check(side == team::ally ? sdk_num_allies(&count) : sdk_num_enemies(&count));
    std::vector<std::uint32_t> raw(count);
    check(side == team::ally ? sdk_allies(raw.data(), count, &count) : sdk_enemies(raw.data(), count, &count));
    raw.resize(count);
    std::sort(raw.begin(), raw.end());
    std::vector<cambc::handle_champion_t> out;
    for (auto h : raw) out.push_back(static_cast<cambc::handle_champion_t>(h));
    return out;
}

// Remaining channel turn ends, or nullopt if not channelling.
std::optional<int> channel_time(std::uint32_t h) {
    std::int32_t value{};
    if (sdk_champion_channel_time(h, &value) != 0) return std::nullopt;
    return value;
}

// Visible camp health, or nullopt if the engine has no live camp to show.
std::optional<float> camp_health(std::uint32_t h) {
    camp_state state{};
    const auto code = sdk_camp(h, &state);
    if (code == not_in_vision || code == not_found) return std::nullopt;
    check(code);
    return state.health;
}

// Camp-group state code (1 alive, 2 reward available, 3 respawning) and the respawn timer.
std::pair<std::uint32_t, int> group_state(std::uint32_t h) {
    std::uint32_t state{};
    check(sdk_camp_group_state(h, &state));
    std::int32_t timer = 0;
    if (state == 3) check(sdk_camp_group_cooldown(h, &timer));
    return {state, timer};
}
} // namespace engine

// First round whose turn sees a timer read now at zero. Timers tick at the owner's turn end, so
// one that has not had its turn yet this round gets there a round sooner; an owner that already
// acted this round cannot use anything before next round, even at zero.
int fire_round(int round, int remaining, bool acted) {
    return round + std::max(remaining, 0) + (acted ? 1 : 0);
}

// The tile of `tiles` nearest their mean.
vec2 central_tile(const std::vector<vec2>& tiles) {
    long sx = 0, sy = 0;
    for (auto p : tiles) sx += p.x, sy += p.y;
    const vec2 mean{static_cast<int>(sx / static_cast<long>(tiles.size())), static_cast<int>(sy / static_cast<long>(tiles.size()))};
    return *std::min_element(tiles.begin(), tiles.end(), [&](vec2 a, vec2 b) {
        return (a - mean).length_squared() < (b - mean).length_squared();
    });
}

int min_steps(const Field& field, const bitboard& tiles) {
    int best = unreachable;
    for (auto p : tiles.positions()) best = std::min(best, field.at(p));
    return best;
}

int min_steps(const Field& field, const std::vector<CampMember>& members) {
    int best = unreachable;
    for (const auto& m : members) best = std::min(best, field.at(m.pos));
    return best;
}

// Map draft picks to champion types in handle (= pick) order.
std::vector<cambc::champion_type> types_from_draft(team side) {
    std::vector<cambc::champion_type> types;
    for (auto pick : cambc::draft::current_draft(side))
        for (auto t : bodies(pick)) types.push_back(t);
    return types;
}

const char* name(CampState s) {
    switch (s) {
    case CampState::alive: return "alive";
    case CampState::cleared: return "cleared";
    case CampState::respawning: return "respawning";
    }
    return "?";
}

const char* name(Channel c) {
    switch (c) {
    case Channel::none: return "";
    case Channel::recall: return " recalling";
    case Channel::tribute: return " tributing";
    case Channel::teleport: return " teleporting";
    }
    return "?";
}

std::string str(vec2 p) { return cambc::to_string(p); }

// Run one part of the update; a failure there is logged and the rest still runs.
template <class F> void guard(const char* what, F&& f) {
    try {
        f();
    } catch (const std::exception& e) {
        std::cout << "world " << what << " error: " << e.what() << '\n';
    }
}

} // namespace

// ---------------------------------------------------------------------------------------------
// StaticMap
// ---------------------------------------------------------------------------------------------

vec2 StaticMap::mirror(vec2 p) const {
    switch (symmetry) {
    case cambc::symmetry::horizontal: return {width - 1 - p.x, p.y};
    case cambc::symmetry::vertical: return {p.x, height - 1 - p.y};
    case cambc::symmetry::rotational180: return {width - 1 - p.x, height - 1 - p.y};
    }
    return p;
}

bitboard StaticMap::mirror(const bitboard& b) const { return b.reflect(symmetry); }

int StaticMap::group_at(vec2 p) const { return static_cast<int>(group_lookup_[tile_index(p)]) - 1; }

int StaticMap::altar_at(vec2 p) const {
    for (int i = 0; i < static_cast<int>(altars.size()); ++i)
        if (altars[i].pos == p) return i;
    return -1;
}

const Field& StaticMap::from_ally_spawn() const {
    if (!ally_field_) {
        FuelMeter meter{"ally_spawn_field"};
        ally_field_ = make_field(blocked_for_us, ally_spawn);
    }
    return *ally_field_;
}

const Field& StaticMap::from_enemy_spawn() const {
    if (!enemy_field_) {
        FuelMeter meter{"enemy_spawn_field"};
        enemy_field_ = make_field(blocked_for_them, enemy_spawn);
    }
    return *enemy_field_;
}

const BushCluster& StaticMap::bush_cluster(vec2 p) const {
    for (const auto& c : bush_clusters_)
        if (c.tiles.is_set(p)) return c;
    FuelMeter meter{"bush_cluster"};
    // The host floods 8-connected. That cluster is edge-connected too unless it holds a pair of
    // bushes joined only diagonally; then grow from p by edge steps within it.
    auto tiles = (~bushes).reachable_tiles(p, static_cast<std::uint16_t>(width * height));
    if (!(tiles & diagonal_links()).is_empty()) {
        auto grown = single(p);
        for (;;) {
            auto next = (grown | grown.shift_right(1) | grown.shift_right(-1) | grown.shift_up(1) | grown.shift_up(-1)) & tiles;
            if (next == grown) break;
            grown = std::move(next);
        }
        tiles = std::move(grown);
    }
    BushCluster c;
    c.size = static_cast<int>(tiles.count());
    c.tiles = std::move(tiles);
    bush_clusters_.push_back(std::move(c));
    return bush_clusters_.back();
}

const bitboard& StaticMap::diagonal_links() const {
    if (!diagonal_links_) {
        // Bit a: bushes at a and a+(dx,dy) with neither tile between them a bush.
        const auto at = [&](int dx, int dy) { return bushes.shift_right(-dx).shift_up(-dy); };
        const auto rise = bushes & at(1, 1) & ~at(1, 0) & ~at(0, 1);
        const auto fall = bushes & at(-1, 1) & ~at(-1, 0) & ~at(0, 1);
        diagonal_links_ = rise | fall;
    }
    return *diagonal_links_;
}

bitboard StaticMap::viewers(vec2 p, int radius) const {
    // Sight is symmetric for a fixed opaque set, so the tiles that see p are those p would see
    // with each kind of viewer's opaque set. A viewer outside bushes sees through none, and never
    // into one; a viewer in a cluster sees through that cluster only.
    const auto r = static_cast<std::uint16_t>(radius);
    const auto cast_from_inside = [&](const bitboard& cluster) {
        return (walls | (bushes & ~cluster)).shadow_cast(p, r) & cluster;
    };
    if (bushes.is_set(p)) return cast_from_inside(bush_cluster(p).tiles);
    auto out = (walls | bushes).shadow_cast(p, r);
    // Each cluster in reach, once: take its tiles off the remaining bushes as it is cast.
    auto left = bushes & square(p, radius);
    while (!left.is_empty()) {
        const auto& cluster = bush_cluster(left.positions().front()).tiles;
        out |= cast_from_inside(cluster);
        left &= ~cluster;
    }
    return out;
}

bool StaticMap::warm_up(std::uint64_t fuel_floor) const {
    // Start an item only if its estimated cost still leaves `fuel_floor`.
    const auto afford = [&](std::uint64_t cost) { return fuel_ok(fuel_floor + cost); };
    const auto field = field_cost_estimate();
    if (!ally_field_ && !afford(field)) return false;
    from_ally_spawn();
    for (const auto& g : groups) {
        if (!afford(small_cost_estimate)) return false;
        g.tiles();
        g.ally_steps();
    }
    for (const auto& a : altars) {
        if (!afford(small_cost_estimate)) return false;
        a.tribute_tiles();
        a.ally_steps();
    }
    if (!enemy_field_ && !afford(field)) return false;
    from_enemy_spawn();
    for (const auto& g : groups) {
        if (!afford(small_cost_estimate)) return false;
        g.enemy_steps();
        g.adjacent();
        g.threat();
    }
    for (const auto& a : altars) {
        if (!afford(small_cost_estimate)) return false;
        a.enemy_steps();
        a.lock_tiles();
    }
    return true;
}

const bitboard& Altar::tribute_tiles() const {
    if (!tribute_) tribute_ = square(pos, cambc::constants::submit_gems_range) & ~map_->blocked_for_us;
    return *tribute_;
}

const bitboard& Altar::lock_tiles() const {
    if (!lock_) lock_ = square(pos, 2) & ~map_->blocked_for_us;
    return *lock_;
}

int Altar::ally_steps() const {
    if (!ally_steps_) ally_steps_ = min_steps(map_->from_ally_spawn(), tribute_tiles());
    return *ally_steps_;
}

int Altar::enemy_steps() const {
    if (!enemy_steps_)
        enemy_steps_ = min_steps(map_->from_enemy_spawn(),
                                 square(pos, cambc::constants::submit_gems_range) & ~map_->blocked_for_them);
    return *enemy_steps_;
}

cambc::camp CampGroup::camp(int member) const {
    const auto& m = members[member];
    return cambc::detail::handle_access::make_camp(static_cast<cambc::handle_camp_t>(m.handle),
                                                   static_cast<cambc::handle_camp_group_t>(handle), m.type, m.pos);
}

const bitboard& CampGroup::tiles() const {
    if (!tiles_) {
        bitboard b;
        for (const auto& m : members) b.set(m.pos);
        tiles_ = std::move(b);
    }
    return *tiles_;
}

const bitboard& CampGroup::adjacent() const {
    if (!adjacent_) {
        bitboard b;
        for (const auto& m : members) b.draw_chebyshev(m.pos, 1);
        b &= ~(tiles() | map_->blocked_for_us);
        adjacent_ = std::move(b);
    }
    return *adjacent_;
}

const bitboard& CampGroup::threat() const {
    if (!threat_) {
        bitboard b;
        for (const auto& m : members) b.draw_chebyshev(m.pos, 3);
        threat_ = std::move(b);
    }
    return *threat_;
}

int CampGroup::ally_steps() const {
    if (!ally_steps_) ally_steps_ = min_steps(map_->from_ally_spawn(), members);
    return *ally_steps_;
}

int CampGroup::enemy_steps() const {
    if (!enemy_steps_) enemy_steps_ = min_steps(map_->from_enemy_spawn(), members);
    return *enemy_steps_;
}

// The eager core: what the first turn needs.
void World::build_static() {
    FuelMeter meter{"build_static"};
    auto s = std::make_unique<StaticMap>();
    s->width = cambc::map::width();
    s->height = cambc::map::height();
    s->symmetry = cambc::map::symmetry();
    s->team_a = cambc::detail::sdk_my_team() == 0;

    s->walls = cambc::map::walls();
    s->holes = cambc::map::holes();
    s->bushes = cambc::map::bushes();
    s->altar_tiles = cambc::map::altars();
    s->ally_spawn = cambc::map::spawn_region(team::ally);
    s->enemy_spawn = cambc::map::spawn_region(team::enemy);
    s->ally_spawn_tiles = s->ally_spawn.positions();
    s->enemy_spawn_tiles = s->enemy_spawn.positions();
    s->ally_spawn_centre = central_tile(s->ally_spawn_tiles);
    s->enemy_spawn_centre = central_tile(s->enemy_spawn_tiles);

    s->impassable = s->walls | s->holes | s->altar_tiles;
    s->blocked_for_us = s->impassable | s->enemy_spawn;
    s->blocked_for_them = s->impassable | s->ally_spawn;

    const auto altar_positions = s->altar_tiles.positions();
    s->altars.resize(altar_positions.size());
    for (std::size_t i = 0; i < altar_positions.size(); ++i) {
        s->altars[i].pos = altar_positions[i];
        s->altars[i].map_ = s.get();
    }
    for (auto& a : s->altars) a.mirror = s->altar_at(s->mirror(a.pos));

    // Camp groups, through the raw imports. Member stats come from the camp designs, read once
    // per camp type.
    namespace raw = cambc::detail;
    std::array<std::optional<cambc::camp_stats>, 5> design{};
    s->group_lookup_.assign(static_cast<std::size_t>(s->width * s->height), 0);
    const auto group_ids = engine::camp_group_ids();
    s->groups.resize(group_ids.size());
    for (std::size_t gi = 0; gi < group_ids.size(); ++gi) {
        auto& g = s->groups[gi];
        g.handle = group_ids[gi];
        g.map_ = s.get();
        raw::camp_group_info reward{};
        raw::check(raw::sdk_map_camp_group(g.handle, &reward));
        g.gold = static_cast<int>(reward.gold);
        g.gems = static_cast<int>(reward.gems);
        raw::check(raw::sdk_bc_camp_group_max_respawn(g.handle, &g.respawn));
        const auto ids = engine::camp_ids(g.handle);
        g.members.reserve(ids.size());
        std::vector<vec2> positions;
        positions.reserve(ids.size());
        for (auto id : ids) {
            raw::camp_info info{};
            raw::check(raw::sdk_map_camp_info(id, &info));
            const auto type = static_cast<cambc::camp_type>(info.type);
            auto& stats = design[static_cast<std::size_t>(info.type)];
            if (!stats) {
                raw::camp_design d{};
                raw::check(raw::sdk_camp_design(info.type, &d));
                stats = d.base_stats;
            }
            const vec2 pos{info.x, info.y};
            g.members.push_back({id, pos, type, stats->base_health, stats->base_strength});
            g.strength += stats->base_strength;
            g.has_monolith |= type == cambc::camp_type::monolith;
            positions.push_back(pos);
            s->camp_tiles.set(pos);
            s->group_lookup_[tile_index(pos)] = static_cast<std::uint8_t>(gi + 1);
        }
        g.centre = central_tile(positions);
    }
    for (auto& g : s->groups) g.mirror = s->group_at(s->mirror(g.centre));

    static_ = std::move(s);
}

// ---------------------------------------------------------------------------------------------
// Beliefs
// ---------------------------------------------------------------------------------------------

void World::init_beliefs() {
    FuelMeter meter{"init_beliefs"};
    const auto& s = map();
    plan = read_draft_plan();
    const auto self_handle = static_cast<cambc::handle_champion_t>(cambc::self());

    for (const auto side : {team::ally, team::enemy}) {
        auto& list = side == team::ally ? allies : enemies;
        auto handles = engine::handles(side);
        const auto types = types_from_draft(side);
        for (std::size_t i = 0; i < handles.size(); ++i) {
            ChampionBelief b;
            b.handle = handles[i];
            b.side = side;
            b.index = static_cast<int>(i);
            b.is_self = handles[i] == self_handle;
            // Draft picks are readable in play and handles follow pick order; a visible champion's
            // own type overrides this below if they ever disagree.
            b.type = b.is_self ? cambc::self().champion_name() : i < types.size() ? types[i] : cambc::champion_type::ryth;
            b.pos = side == team::ally ? s.ally_spawn_centre : s.enemy_spawn_centre;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health = b.facts().health.base;
            b.strength = b.facts().strength.base;
            b.focus = b.facts().focus.base;
            if (b.is_self) self_index = static_cast<int>(i);
            list.push_back(b);
        }
    }

    camps.assign(s.groups.size(), CampBelief{});
    for (std::size_t g = 0; g < s.groups.size(); ++g)
        for (const auto& m : s.groups[g].members) camps[g].health.push_back(m.max_health);
    altars.assign(s.altars.size(), AltarBelief{});
}

void World::update() {
    round = static_cast<int>(cambc::round_number());
    // First turn; a failure part-way is retried next turn from scratch.
    if (!ready()) {
        first_round = round;
        if (!static_) build_static();
        allies.clear();
        enemies.clear();
        init_beliefs();
    }
    FuelMeter meter{"update"};
    visible = cambc::vision::visible_tiles();
    const auto tributing = tributing_enemies(); // before update_champions ends their channels
    update_champions(true);
    guard("camps", [&] { update_camps(); });
    guard("altars", [&] { update_altars(); });
    guard("wards", [&] { update_wards(); });
    guard("scores", [&] { update_scores(tributing); });
}

void World::observe() {
    FuelMeter meter{"observe"};
    visible = cambc::vision::visible_tiles();
    update_champions(false);
}

void World::update_champions(bool full) {
    for (auto& b : allies) guard("champion", [&] { update_champion(b, full); });
    for (auto& b : enemies) guard("champion", [&] { update_champion(b, full); });
}

// `full` reads liveness, cooldowns and bags too; observe() refreshes positions and health only.
void World::update_champion(ChampionBelief& b, bool full) {
    const auto& s = map();
    const auto h = engine::id(b.handle);
    const vec2 spawn = b.side == team::ally ? s.ally_spawn_centre : s.enemy_spawn_centre;

    if (full) {
        const bool alive_now = engine::alive(h);
        if (!alive_now) {
            if (b.alive) {
                // Died since our last turn: in round-1 after our turn, or this round before it.
                // Death in round D respawns in D+61, or D+60 if it died before its own turn.
                b.died_round = round;
                b.respawn_earliest = round - 1 + cambc::constants::respawn_time;
                b.respawn_latest = round + cambc::constants::respawn_time + 1;
            }
            b.alive = false;
            b.visible = false;
            b.gems = 0;
            b.channel = Channel::none;
            return;
        }
        if (!b.alive) {
            // Respawned on its spawn, at its turn start this round or (after our turn) last round.
            // The respawn turn allows no casting, so abilities are ready this round or next.
            b.alive = true;
            b.died_round = b.respawn_earliest = b.respawn_latest = -1;
            b.pos = spawn;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health;
            b.gems = 0;
            b.ready_round = {round, round};
        }
    }

    const auto info = engine::champion(h);
    b.visible = info.has_value();
    if (!info) {
        if (b.channel != Channel::none && round >= b.channel_end_round) {
            if (b.channel == Channel::recall) {
                b.pos = spawn;
                b.pos_round = b.channel_end_round;
                b.pos_source = Source::inferred;
                b.health = b.max_health;
            }
            b.channel = Channel::none;
        }
        return;
    }

    const auto seen_type = static_cast<cambc::champion_type>(info->type);
    if (debug_log && seen_type != b.type)
        std::cout << "world: " << cambc::to_string(b.side) << b.index << " drafted as " << b.facts().name << " but is "
                  << facts(seen_type).name << '\n';
    b.type = seen_type;
    const int last_seen = b.stats_round;
    b.pos = {info->x, info->y};
    b.pos_round = round;
    b.pos_source = Source::seen;
    b.health = info->health;
    b.max_health = info->max_health;
    b.strength = info->strength;
    b.focus = info->focus;
    b.stats_round = round;
    const auto state = cambc::champion_state::from_bits_retain(static_cast<std::uint32_t>(info->state));
    b.acted = !b.is_self && state.contains(cambc::champion_state::completed_turn);
    if (!full) return;

    b.gems = engine::gems(h);
    b.gems_round = round;
    b.items = engine::items(h);
    for (int slot = 0; slot < 2; ++slot) {
        const int cd = engine::cooldown(h, static_cast<std::uint32_t>(slot));
        const int ready = fire_round(round, cd, b.acted);
        // Self-check of the projection: without a cast it must match exactly; it can only be
        // later (a cast we missed) unless Vendetta reset it with a kill.
        if (debug_log && !b.is_self && last_seen >= 0 && ready != b.ready_round[slot]
            && (ready < b.ready_round[slot] || last_seen < round - 1))
            std::cout << "cdcheck " << cambc::to_string(b.side) << b.index << ' ' << b.facts().name << " slot" << slot
                      << " last seen r" << last_seen << " projected r" << b.ready_round[slot] << " read r" << ready
                      << (ready < b.ready_round[slot] ? " EARLIER" : " (cast while unseen)") << '\n';
        // A cooldown that restarted means a cast: the slot is ready again 8 rounds after it.
        if (cd > 0 && b.ready_round[slot] <= round) b.last_cast_round[slot] = ready - 8;
        b.ready_round[slot] = ready;
    }

    b.channel = state.contains(cambc::champion_state::recalling)         ? Channel::recall
                : state.contains(cambc::champion_state::submitting_gems) ? Channel::tribute
                : state.contains(cambc::champion_state::teleporting)     ? Channel::teleport
                                                                         : Channel::none;
    if (b.channel != Channel::none) {
        const auto left = engine::channel_time(h);
        b.channel_end_round = fire_round(round, left.value_or(0), b.acted);
    }
}

void World::note_sighting(int enemy_index, vec2 pos, int seen_round) {
    if (enemy_index < 0 || enemy_index >= static_cast<int>(enemies.size()) || !in_bounds(pos)) return;
    auto& b = enemies[enemy_index];
    if (!b.alive || b.visible || seen_round <= b.pos_round) return;
    b.pos = pos;
    b.pos_round = seen_round;
    b.pos_source = Source::comms;
}

void World::update_camps() {
    const auto& s = map();
    std::vector<char> group_visible(s.groups.size(), 0);
    for (auto p : (visible & s.camp_tiles).positions()) group_visible[s.group_at(p)] = 1;
    const auto ally_champs = cambc::vision::champion_tiles(team::ally);
    const auto enemy_champs = cambc::vision::champion_tiles(team::enemy);
    const auto champs = ally_champs | enemy_champs;
    const auto hidden = ~visible;

    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        guard("camp", [&] {
            const auto& G = s.groups[g];
            auto& c = camps[g];

            if (!group_visible[g]) {
                // Project through fog with the capture and respawn rules.
                if (c.state == CampState::cleared && c.holder && round >= c.held_since + cambc::constants::capture_time + 1) {
                    c.state = CampState::respawning;
                    c.respawn_round = c.held_since + cambc::constants::capture_time + 1 + G.respawn;
                    c.holder.reset();
                }
                if (c.state == CampState::respawning && round >= c.respawn_round) {
                    c.state = CampState::alive;
                    for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health;
                    c.awake = Awake::asleep;
                }
                if (c.awake == Awake::awake && round - c.state_round > 2) c.awake = Awake::unknown;
                return; // next group
            }

            const auto [code, timer] = engine::group_state(G.handle);
            const auto previous = c.state;
            if (code == 1) c.state = CampState::alive;
            else if (code == 2) c.state = CampState::cleared;
            else if (code == 3) {
                c.state = CampState::respawning;
                c.respawn_round = round + timer;
            }
            c.state_round = round;
            if (debug_log && c.state != previous)
                std::cout << "world r" << round << " g" << g << str(G.centre) << ' ' << name(previous) << " -> " << name(c.state)
                          << (c.state == CampState::respawning ? " until r" + std::to_string(c.respawn_round) : "") << '\n';
            if (c.state == CampState::alive && previous != CampState::alive) {
                for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health;
                c.awake = Awake::asleep;
            }

            // Member health; a visible camp tile with no live camp on it is a dead member. Any drop,
            // a kill included, is damage, which wakes the group.
            for (std::size_t i = 0; i < G.members.size(); ++i) {
                const auto& m = G.members[i];
                if (!visible.is_set(m.pos)) continue;
                const float hp = engine::camp_health(m.handle).value_or(0.0f);
                if (hp < c.health[i] - 1e-3f) {
                    c.last_damaged_round = round;
                    c.awake = Awake::awake;
                    c.quiet_rounds = 0;
                }
                c.health[i] = hp;
            }
            c.health_round = round;

            if (c.state != CampState::alive) {
                c.awake = Awake::asleep;
            } else if (c.awake != Awake::asleep) {
                // Asleep after 2 camp phases with no champion within 3: count rounds where the whole
                // threat area is visible and empty. Anything unseen there could be a champion.
                const bool fully_seen = (G.threat() & hidden).is_empty();
                if (fully_seen && (G.threat() & champs).is_empty()) {
                    if (++c.quiet_rounds >= 2) c.awake = Awake::asleep;
                } else {
                    c.quiet_rounds = 0;
                }
            }

            // Capture progress on a cleared group: whoever stands on its tiles unopposed.
            if (c.state == CampState::cleared) {
                if ((G.tiles() & hidden).is_empty()) {
                    const bool a = !(G.tiles() & ally_champs).is_empty();
                    const bool e = !(G.tiles() & enemy_champs).is_empty();
                    const std::optional<team> holder = a && !e ? std::optional{team::ally}
                                                       : e && !a ? std::optional{team::enemy}
                                                                 : std::nullopt;
                    if (holder != c.holder) {
                        if (debug_log)
                            std::cout << "world r" << round << " g" << g << str(G.centre) << " held by "
                                      << (holder ? cambc::to_string(*holder) : std::string("nobody")) << '\n';
                        c.holder = holder;
                        c.held_since = holder ? round : -1;
                    }
                }
            } else {
                c.holder.reset();
                c.held_since = -1;
            }
        });
    }
}

void World::update_altars() {
    const auto& s = map();
    for (auto p : (visible & s.altar_tiles).positions()) {
        const int a = s.altar_at(p);
        altars[a] = AltarBelief{};
        altars[a].seen_round = round;
    }
    for (const auto& lock : cambc::vision::altar_locks()) {
        const int a = s.altar_at(lock.position());
        if (a < 0) continue;
        auto& belief = altars[a];
        belief.seen_round = round;
        if (lock.is_ally()) {
            belief.ally_lock = true;
            belief.ally_lock_hits = static_cast<int>(lock.hits_remaining());
        } else {
            belief.enemy_lock = true;
            belief.enemy_lock_hits = static_cast<int>(lock.hits_remaining());
        }
    }
}

void World::update_wards() {
    for (const auto& w : cambc::vision::wards(team::enemy)) {
        auto it = std::find_if(enemy_wards.begin(), enemy_wards.end(), [&](const auto& s) { return s.pos == w.position(); });
        if (it != enemy_wards.end()) it->round = round;
        else enemy_wards.push_back({w.position(), round});
    }
    // Gone if its tile is in view without it; each enemy keeps at most one ward.
    std::erase_if(enemy_wards, [&](const auto& s) { return s.round != round && visible.is_set(s.pos); });
    std::sort(enemy_wards.begin(), enemy_wards.end(), [](const auto& a, const auto& b) { return a.round > b.round; });
    if (enemy_wards.size() > enemies.size()) enemy_wards.resize(enemies.size());
}

std::uint32_t World::tributing_enemies() const {
    std::uint32_t mask = 0;
    for (std::size_t i = 0; i < enemies.size(); ++i)
        if (enemies[i].alive && enemies[i].channel == Channel::tribute) mask |= 1u << i;
    return mask;
}

void World::update_scores(std::uint32_t tributing) {
    const int ally = static_cast<int>(cambc::global_submitted_gems(team::ally));
    const int enemy = static_cast<int>(cambc::global_submitted_gems(team::enemy));
    const bool first = round == first_round;
    score.ally_delta = first ? 0 : ally - score.ally;
    score.enemy_delta = first ? 0 : enemy - score.enemy;
    score.ally = ally;
    score.enemy = enemy;
    if (score.enemy_delta <= 0) return;

    // An enemy tribute just landed: empty the bag of whoever most plausibly made it. First choice:
    // an enemy that was tributing before this update and no longer is. A visible enemy's bag was
    // just read, so only an unseen one's needs emptying.
    score.enemy_tribute_round = round;
    score.enemy_tribute_amount = score.enemy_delta;
    ChampionBelief* tributer = nullptr;
    int candidates = 0;
    for (std::size_t i = 0; i < enemies.size(); ++i) {
        auto& b = enemies[i];
        if ((tributing >> i & 1) && b.alive && b.channel != Channel::tribute) tributer = &b, ++candidates;
    }
    if (candidates != 1) {
        tributer = nullptr;
        candidates = 0;
        for (auto& b : enemies)
            if (b.alive && b.gems == score.enemy_delta) tributer = &b, ++candidates;
    }
    if (candidates == 1) {
        if (!tributer->visible) tributer->gems = 0;
        tributer->channel = Channel::none;
    }
}

// ---------------------------------------------------------------------------------------------
// Debug output
// ---------------------------------------------------------------------------------------------

void World::debug_output() const {
    const auto& s = map();
    if (debug_log && (round == first_round || round % debug_log_period == 0)) {
        const auto& m = me();
        std::cout << "W r" << round << ' ' << m.facts().name << str(m.pos) << " hp " << static_cast<int>(m.health) << '/'
                  << static_cast<int>(m.max_health) << " score " << score.ally << '-' << score.enemy << " (+"
                  << score.ally_delta << ",+" << score.enemy_delta << ")";
        if (score.enemy_tribute_round >= 0)
            std::cout << " last_enemy_tribute r" << score.enemy_tribute_round << " +" << score.enemy_tribute_amount;
        std::cout << '\n';
        for (const auto& b : enemies) {
            std::cout << "  E" << b.index << ' ' << b.facts().name;
            if (!b.alive) {
                std::cout << " dead since r" << b.died_round << " respawn r" << b.respawn_earliest << '-' << b.respawn_latest << '\n';
                continue;
            }
            std::cout << (b.visible ? " SEEN " : " last ") << str(b.pos) << " r" << b.pos_round
                      << (b.pos_source == Source::comms ? " (comms)" : b.pos_source == Source::inferred ? " (inferred)" : "")
                      << " hp " << static_cast<int>(b.health) << '/' << static_cast<int>(b.max_health) << " gems " << b.gems
                      << " items " << b.items << " ready r" << b.ready_round[0] << ",r" << b.ready_round[1]
                      << (b.cooldowns_uncertain() ? "?" : "") << name(b.channel);
            if (b.channel != Channel::none) std::cout << " until r" << b.channel_end_round;
            std::cout << '\n';
        }
        int counts[3] = {};
        std::cout << "  camps:";
        for (std::size_t g = 0; g < camps.size(); ++g) {
            const auto& c = camps[g];
            ++counts[static_cast<int>(c.state)];
            if (c.state == CampState::alive && c.awake == Awake::asleep) continue;
            std::cout << " g" << g << str(s.groups[g].centre) << '=' << name(c.state);
            if (c.state == CampState::respawning) std::cout << "->r" << c.respawn_round;
            if (c.awake == Awake::awake) std::cout << "(awake, hit r" << c.last_damaged_round << ')';
            if (c.awake == Awake::unknown) std::cout << "(awake?)";
            if (c.holder) std::cout << "(held by " << cambc::to_string(*c.holder) << " since r" << c.held_since << ')';
        }
        std::cout << " | " << counts[0] << " alive " << counts[1] << " cleared " << counts[2] << " respawning\n";
        std::cout << "  altars:";
        for (std::size_t a = 0; a < altars.size(); ++a) {
            const auto& b = altars[a];
            std::cout << ' ' << str(s.altars[a].pos) << (b.seen_round < 0 ? "?" : "");
            if (b.ally_lock) std::cout << " ourlock" << b.ally_lock_hits;
            if (b.enemy_lock) std::cout << " THEIRlock" << b.enemy_lock_hits;
        }
        std::cout << " | enemy wards:";
        for (const auto& w : enemy_wards) std::cout << ' ' << str(w.pos) << " r" << w.round;
        std::cout << '\n';
    }

    if constexpr (debug_draw) {
        for (const auto& b : enemies) {
            if (!b.alive || b.pos_round < 0) continue;
            draw_dot(b.pos, b.visible ? 0xFF0000 : b.pos_source == Source::comms ? 0xFF00FF : 0x800000);
            if (b.visible) draw_line(me().pos, b.pos, 0xFF4040);
        }
        for (std::size_t g = 0; g < camps.size(); ++g) {
            const auto& c = camps[g];
            const std::uint32_t colour = c.state == CampState::respawning ? 0x808080
                                         : c.state == CampState::cleared  ? 0xFFFF00
                                         : c.awake == Awake::awake        ? 0xFF8000
                                         : c.awake == Awake::unknown      ? 0xC0A000
                                                                          : 0x00C000;
            draw_dot(s.groups[g].centre, colour);
        }
        for (const auto& w : enemy_wards) draw_dot(w.pos, 0x8000FF);
        for (std::size_t a = 0; a < altars.size(); ++a)
            if (altars[a].enemy_lock) draw_dot(s.altars[a].pos, 0xFF00FF);
    }
}

} // namespace aph
