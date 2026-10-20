#include "world.h"
#include <algorithm>
#include <cstdio>
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

// Summing every item count costs ~350 fuel; only a Home emblem matters.
bool home_emblem(std::uint32_t h) {
    cambc::enum_map<cambc::item_type> counts;
    check(sdk_champion_items(h, counts.ptr()));
    return counts[cambc::item_type::home_emblem_of_strength] + counts[cambc::item_type::home_emblem_of_focus]
               + counts[cambc::item_type::home_emblem_of_health]
           > 0;
}

// Static camp data in one batched raw call: map::camp_groups() builds an SDK object graph that
// costs more fuel than the data itself. Per group: id, gold, gems, max respawn, member count, then
// per member: id, type, x, y.
std::vector<std::uint32_t> camp_layout() {
    std::vector<std::uint32_t> words(256);
    std::uint32_t count{};
    check(sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    if (count > words.size()) {
        words.resize(count);
        check(sdk_map_camp_layout(words.data(), count, &count));
    }
    words.resize(count);
    return words;
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
std::pair<int, int> priorities(std::uint32_t h) {
    std::int32_t now{}, next{};
    check(sdk_bc_champion_priority(h, 0, &now));
    check(sdk_bc_champion_priority(h, 1, &next));
    return {now, next};
}

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

// Whether a visible live camp is awake or asleep; nullopt if hidden or dead.
std::optional<Awake> camp_awake(std::uint32_t h) {
    std::uint32_t value{};
    const auto code = sdk_camp_state(h, &value);
    if (code == not_in_vision || code == not_found) return std::nullopt;
    check(code);
    if (value == 1) return Awake::awake;
    if (value == 2) return Awake::asleep;
    return std::nullopt;
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

vec2 central_tile(const std::vector<vec2>& tiles) {
    long sx = 0, sy = 0;
    for (auto p : tiles) sx += p.x, sy += p.y;
    const vec2 mean{static_cast<int>(sx / static_cast<long>(tiles.size())), static_cast<int>(sy / static_cast<long>(tiles.size()))};
    return *std::min_element(tiles.begin(), tiles.end(), [&](vec2 a, vec2 b) {
        return (a - mean).length_squared() < (b - mean).length_squared();
    });
}

vec2 central_tile(const std::vector<CampMember>& members) {
    long sx = 0, sy = 0;
    for (const auto& m : members) sx += m.pos.x, sy += m.pos.y;
    const auto n = static_cast<long>(members.size());
    const vec2 mean{static_cast<int>(sx / n), static_cast<int>(sy / n)};
    return std::min_element(members.begin(), members.end(), [&](const CampMember& a, const CampMember& b) {
        return (a.pos - mean).length_squared() < (b.pos - mean).length_squared();
    })->pos;
}

// Grows `tiles` by king steps onto open tiles: what a distance field capped at `steps` reaches,
// for less fuel at one or two steps.
void dilate(bitboard& tiles, const bitboard& open, int steps) {
    static bitboard t1{cambc::uninitialized}, t2{cambc::uninitialized};
    for (; steps > 0; --steps) {
        tiles.shift_right_into(1, t1);
        tiles.shift_right_into(-1, t2);
        tiles |= t1;
        tiles |= t2;
        tiles.shift_up_into(1, t1);
        tiles.shift_up_into(-1, t2);
        tiles |= t1;
        tiles |= t2;
        tiles &= open;
    }
}

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

// Append-only text for the belief dump in a fixed buffer: std::string appends cost several times
// more fuel per character.
class DumpWriter {
public:
    static constexpr std::size_t capacity = 1 << 16;
    std::size_t size() const { return size_; }
    const char* data() const { return buffer_; }
    void clear() { size_ = 0; }
    void text(const char* s) {
        while (*s && size_ < capacity) buffer_[size_++] = *s++;
    }
    // Zigzag, then 5 bits per base64 digit, least significant first; bit 5 marks a following digit.
    void num(long v) {
        auto n = static_cast<std::uint32_t>((v << 1) ^ (v >> 31));
        if (capacity - size_ < 8) return;
        while (n >= 32) {
            buffer_[size_++] = digits[32 | (n & 31)];
            n >>= 5;
        }
        buffer_[size_++] = digits[n];
    }
    // The engine's 8x8 chunks straight from the board's storage: per non-empty chunk, its index
    // gap since the previous one (x2, +1 if full), then unless full its 64 bits as 11 raw digits,
    // least significant first. Bit (y % 8) * 8 + x % 8 of chunk (y / 8) * chunked_width + x / 8.
    void chunks(const bitboard& b) {
        const auto& layout = cambc::detail::layout();
        const std::uint64_t* words = b.ptr();
        long last = 0;
        for (std::uint32_t cy = 0; cy < layout.chunked_height; ++cy)
            for (std::uint32_t cx = 0; cx < layout.chunked_width; ++cx) {
                const std::uint64_t word = words[cy * layout.chunk_stride + cx];
                if (!word) continue;
                if (capacity - size_ < 24) return;
                const long i = static_cast<long>(cy * layout.chunked_width + cx);
                const bool full = word == ~std::uint64_t{0};
                num((i - last) * 2 + full);
                last = i;
                if (!full)
                    for (int k = 0; k < 64; k += 6) buffer_[size_++] = digits[(word >> k) & 63];
            }
    }

private:
    static constexpr char digits[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char buffer_[capacity];
    std::size_t size_ = 0;
};

template <class F> void guard(const char* what, F&& f) {
    try {
        f();
    } catch (const std::exception& e) {
        std::cout << "world " << what << " error: " << e.what() << '\n';
    }
}

} // namespace

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
    for (;;) {
        if (const int i = cluster_of_[tile_index(p)]; i > 0) return bush_clusters_[i - 1];
        grow_cluster(p, 0);
    }
}

const BushCluster* StaticMap::grow_cluster(vec2 p, std::uint64_t fuel_floor) const {
    FuelMeter meter{"bush_cluster"};
    if (!growth_ || !growth_->tiles.is_set(p)) {
        // The host floods 8-connected. That cluster is edge-connected too unless it holds a pair
        // of bushes joined only diagonally; then grow from p by edge steps within it.
        auto tiles = (~bushes).reachable_tiles(p, static_cast<std::uint16_t>(width * height));
        const bool diagonal = !(tiles & diagonal_links()).is_empty();
        growth_ = Growth{std::move(tiles), single(p), diagonal};
    }
    auto& g = *growth_;
    if (!g.diagonal) g.grown = g.tiles;
    static bitboard next{cambc::uninitialized}, shifted{cambc::uninitialized};
    while (g.diagonal) {
        next.clear();
        next |= g.grown;
        for (int d : {1, -1}) {
            g.grown.shift_right_into(d, shifted);
            next |= shifted;
            g.grown.shift_up_into(d, shifted);
            next |= shifted;
        }
        next &= g.tiles;
        if (next == g.grown) break;
        g.grown.swap(next);
        if (!fuel_ok(fuel_floor)) return nullptr;
    }
    // Indexing costs ~20 fuel a tile. bush_cluster() passes no floor and must finish.
    const int size = static_cast<int>(g.grown.count());
    if (fuel_floor > 0 && !fuel_ok(fuel_floor + 20 * static_cast<std::uint64_t>(size))) return nullptr;
    BushCluster c;
    c.size = size;
    c.tiles = std::move(g.grown);
    clustered_ |= c.tiles;
    growth_.reset();
    for (auto t : c.tiles.positions()) cluster_of_[tile_index(t)] = static_cast<std::uint16_t>(bush_clusters_.size() + 1);
    bush_clusters_.push_back(std::move(c));
    return &bush_clusters_.back();
}

bool StaticMap::find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const {
    auto left = bushes & square(p, radius) & ~clustered_;
    while (!left.is_empty()) {
        if (!fuel_ok(fuel_floor + (growth_ ? 0 : 20000))) return false;
        const auto* c = grow_cluster(first_tile(left), fuel_floor);
        if (!c) return false;
        left &= ~c->tiles;
    }
    return true;
}

const bitboard& StaticMap::near_bushes() const {
    if (!near_bushes_) {
        auto rows = bushes;
        for (int d = 1; d <= 2; ++d) rows |= bushes.shift_right(d) | bushes.shift_right(-d);
        auto b = rows;
        for (int d = 1; d <= 2; ++d) b |= rows.shift_up(d) | rows.shift_up(-d);
        near_bushes_ = std::move(b);
    }
    return *near_bushes_;
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
        return (walls_and_bushes & ~cluster).shadow_cast(p, r) & cluster;
    };
    if (bushes.is_set(p)) return cast_from_inside(bush_cluster(p).tiles);
    auto out = walls_and_bushes.shadow_cast(p, r);
    // Cast each cluster in reach once.
    auto left = bushes & square(p, radius);
    while (!left.is_empty()) {
        const auto& cluster = bush_cluster(first_tile(left)).tiles;
        out |= cast_from_inside(cluster);
        left &= ~cluster;
    }
    return out;
}

bool StaticMap::warm_up(std::uint64_t fuel_floor) const {
    const auto afford = [&](std::uint64_t cost) { return fuel_ok(fuel_floor + cost); };
    const auto field = field_cost_estimate();
    if (!ally_field_ && !afford(field)) return false;
    from_ally_spawn();
    for (const auto& g : groups) {
        if (!afford(small_cost_estimate)) return false;
        g.tiles();
    }
    for (const auto& a : altars) {
        if (!afford(small_cost_estimate)) return false;
        a.tribute_tiles();
    }
    if (!enemy_field_ && !afford(field)) return false;
    from_enemy_spawn();
    for (const auto& g : groups) {
        if (!afford(small_cost_estimate)) return false;
        g.adjacent();
        g.threat();
    }
    for (const auto& a : altars) {
        if (!afford(small_cost_estimate)) return false;
        a.lock_tiles();
    }
    return true;
}

const bitboard& Altar::tribute_tiles() const {
    if (!tribute_) {
        tribute_ = square(pos, cambc::constants::submit_gems_range);
        *tribute_ &= map_->open_for_us;
    }
    return *tribute_;
}

const bitboard& Altar::lock_tiles() const {
    if (!lock_) {
        lock_ = square(pos, 2);
        *lock_ &= map_->open_for_us;
    }
    return *lock_;
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
        for (const auto& m : members) b.draw_chebyshev(m.pos, m.reach);
        threat_ = std::move(b);
    }
    return *threat_;
}


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
    s->passable = ~s->impassable;
    s->blocked_for_us = s->impassable | s->enemy_spawn;
    s->blocked_for_them = s->impassable | s->ally_spawn;
    s->open_for_us = ~s->blocked_for_us;
    s->open_for_them = ~s->blocked_for_them;
    for (auto t : s->enemy_spawn_tiles) s->near_enemy_spawn.draw_chebyshev(t, 1);
    s->walls_and_bushes = s->walls | s->bushes;

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
    std::vector<std::optional<cambc::camp_stats>> design;
    const auto layout = engine::camp_layout();
    std::size_t group_count = 0;
    for (std::size_t i = 0; i + 5 <= layout.size(); i += 5 + 4 * layout[i + 4]) ++group_count;
    s->groups.reserve(group_count);
    for (std::size_t i = 0; i + 5 <= layout.size();) {
        const auto gi = s->groups.size();
        auto& g = s->groups.emplace_back();
        g.handle = layout[i];
        g.map_ = s.get();
        g.gold = static_cast<int>(layout[i + 1]);
        g.gems = static_cast<int>(layout[i + 2]);
        g.respawn = static_cast<std::int32_t>(layout[i + 3]);
        const auto size = layout[i + 4];
        i += 5;
        g.members.reserve(size);
        for (std::uint32_t m = 0; m < size && i + 4 <= layout.size(); ++m, i += 4) {
            const auto id = layout[i];
            const auto raw_type = layout[i + 1];
            const auto type = static_cast<cambc::camp_type>(raw_type);
            if (raw_type >= design.size()) design.resize(raw_type + 1);
            auto& stats = design[raw_type];
            if (!stats) {
                raw::camp_design d{};
                raw::check(raw::sdk_camp_design(raw_type, &d));
                stats = d.base_stats;
            }
            const vec2 pos{static_cast<std::int32_t>(layout[i + 2]), static_cast<std::int32_t>(layout[i + 3])};
            g.members.push_back({id, pos, type, stats->base_health, stats->base_strength, stats->base_attack_range});
            g.strength += stats->base_strength;
            g.reach = std::max(g.reach, stats->base_attack_range);
            s->max_camp_reach = std::max(s->max_camp_reach, stats->base_attack_range);
            g.has_monolith |= type == cambc::camp_type::monolith;
            s->camp_tiles.set(pos);
            s->group_lookup_[tile_index(pos)] = static_cast<std::uint16_t>(gi + 1);
        }
        g.centre = central_tile(g.members);
    }
    for (auto& g : s->groups) g.mirror = s->group_at(s->mirror(g.centre));
    s->standable = ~(s->camp_tiles | s->blocked_for_us);

    static_ = std::move(s);
}

void World::init_beliefs() {
    FuelMeter meter{"init_beliefs"};
    const auto& s = map();
    plan = read_draft_plan();
    const auto self_handle = static_cast<cambc::handle_champion_t>(cambc::self());

    for (const auto side : {team::ally, team::enemy}) {
        auto& list = side == team::ally ? allies : enemies;
        auto handles = engine::handles(side);
        const auto types = types_from_draft(side);
        list.reserve(handles.size());
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
            if (side == team::enemy) fix(b, s.enemy_spawn, {1, -1});
            if (b.is_self) self_index = static_cast<int>(i);
            list.push_back(std::move(b));
        }
    }

    rank_turns(); // the first update's moments need our slot
    if (round == 1) {
        // An enemy acting before us in round 1 has had one turn: a step, or with a dash three
        // (walls bound a dash). Shared fields, not one per enemy, keep the heavy first turn cheap.
        std::optional<bitboard> reach[2];
        const auto grown = [&](bool dash) -> const bitboard& {
            if (!reach[dash]) {
                auto tiles = s.enemy_spawn;
                if (dash) {
                    cambc::distance_field field;
                    field.compute(s.walls, s.enemy_spawn, tiles, 3);
                    tiles &= s.open_for_them;
                } else {
                    dilate(tiles, s.open_for_them, 1);
                }
                reach[dash] = std::move(tiles);
            }
            return *reach[dash];
        };
        for (auto& b : enemies) {
            b.at = now();
            b.turns_since_fixed = turns_between(b, b.fixed, b.at);
            if (b.turns_since_fixed > 0) b.possible = grown(b.facts().has_dash());
        }
    }
    camps.assign(s.groups.size(), CampBelief{});
    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        auto& health = camps[g].health;
        health.reserve(s.groups[g].members.size());
        for (const auto& m : s.groups[g].members) health.push_back(m.max_health);
        camps[g].health_round.assign(health.size(), 0);
    }
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
    read_vision();
    const auto tributing = tributing_enemies(); // before update_champions ends their channels
    update_champions(true);
    // A priority read in round r applies from r + 1: ranks change when a round passes one unread.
    for (const auto* team : {&allies, &enemies})
        for (const auto& c : *team)
            ranks_stale_ |= c.next_priority != c.priority && ranked_round_ <= c.priority_round && c.priority_round < round;
    if (ranks_stale_) rank_turns();
    guard("camps", [&] { update_camps(); });
    guard("altars", [&] { update_altars(); });
    guard("wards", [&] { update_wards(); });
    guard("scores", [&] { update_scores(tributing); });
}

void World::observe() {
    FuelMeter meter{"observe"};
    read_vision();
    update_champions(false);
}

void World::update_champions(bool full) {
    // Allies read this round have not changed but for our own move and heals, and nothing reads
    // those before the next update.
    for (auto& b : allies)
        if (full || b.stats_round != round) guard("champion", [&] { update_champion(b, full); });
    for (auto& b : enemies) guard("champion", [&] { update_champion(b, full); });
}

// `full` reads liveness, priorities and bags too; observe() refreshes positions, health and
// channels, and cooldowns only of champions not yet seen this turn.
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
            fix_nowhere(b, now());
            return;
        }
        if (!b.alive) {
            // Respawned on its spawn, at its turn start this round or (after our turn) last round.
            // The respawn turn allows no casting, so abilities are ready this round or next. Only
            // ours, or one whose turn came before ours in both rounds, is surely this round's.
            b.alive = true;
            b.died_round = b.respawn_earliest = b.respawn_latest = -1;
            const bool before_us = slot(b, round) < slot(me(), round) && slot(b, round - 1) < slot(me(), round - 1);
            b.respawned_round = b.is_self || before_us ? round : round - 1;
            b.pos = spawn;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health;
            b.gems = 0;
            b.ready_round = {b.respawned_round + 1, b.respawned_round + 1};
            if (b.side == team::enemy) fix(b, s.enemy_spawn, {round - 1, -1});
        }
    }

    const auto info = engine::champion(h);
    b.visible = info.has_value();
    if (!info) {
        // A channel completes at its owner's turn start.
        const bool ended = round > b.channel_end_round || (round == b.channel_end_round && slot(b, round) < slot(me(), round));
        if (b.channel != Channel::none && ended) {
            if (b.channel == Channel::recall) {
                b.pos = spawn;
                b.pos_round = b.channel_end_round;
                b.pos_source = Source::inferred;
                b.health = b.max_health;
                // Damage or a stun could have cancelled it, so add the spawn, not replace.
                if (b.side == team::enemy) b.possible |= s.enemy_spawn;
            }
            b.channel = Channel::none;
        }
        // An untracked `possible` is unread until a fix overwrites it.
        if (b.side == team::enemy && b.tracked) {
            advance(b);
            if (b.tracked) prune(b);
        }
        return;
    }

    const auto seen_type = static_cast<cambc::champion_type>(info->type);
    if (debug_log && seen_type != b.type)
        std::cout << "world: " << cambc::to_string(b.side) << b.index << " drafted as " << b.facts().name << " but is "
                  << facts(seen_type).name << '\n';
    b.type = seen_type;
    const int last_seen = b.stats_round;
    const auto state = cambc::champion_state::from_bits_retain(static_cast<std::uint32_t>(info->state));
    b.acted = !b.is_self && state.contains(cambc::champion_state::completed_turn);
    if (b.side == team::enemy) {
        const vec2 seen{info->x, info->y};
        if (debug_log && b.tracked) {
            advance(b);
            if (b.tracked && !b.possible.is_set(seen))
                std::cout << "trackcheck r" << round << " E" << b.index << ' ' << b.facts().name << " at " << str(seen)
                          << " outside its " << b.possible.count() << " possible tiles; fixed r" << b.fixed.round << '\n';
        }
        fix(b, seen, now());
    }
    b.pos = {info->x, info->y};
    b.pos_round = round;
    b.pos_source = Source::seen;
    b.health = info->health;
    b.max_health = info->max_health;
    b.strength = info->strength;
    b.focus = info->focus;
    b.stats_round = round;
    if (!full && last_seen == round) return; // nothing else changes during our turn
    // Also in observe() for a champion first seen after our move: a recall then still tells when
    // it lands, and its cooldowns show casts made out of sight.
    b.channel = state.contains(cambc::champion_state::recalling)         ? Channel::recall
                : state.contains(cambc::champion_state::submitting_gems) ? Channel::tribute
                : state.contains(cambc::champion_state::teleporting)     ? Channel::teleport
                                                                         : Channel::none;
    if (b.channel != Channel::none) {
        const auto left = engine::channel_time(h);
        b.channel_end_round = fire_round(round, left.value_or(0), b.acted);
    }
    // The crystal's destination: a free tile within 3, terrain in between ignored.
    if (b.side == team::enemy && b.channel == Channel::teleport)
        b.possible |= square(b.pos, teleport_crystal_range) & ~s.blocked_for_them;
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
        if (cd > 0 && b.ready_round[slot] <= round) b.last_cast_round[slot] = ready - ability_cooldown;
        b.ready_round[slot] = std::max(ready, b.respawned_round + 1);
    }
    // In observe() too, for a champion first seen after our move.
    b.gems = engine::gems(h);
    b.gems_round = round;
    if (b.side == team::enemy || b.is_self) b.fast_recall = engine::home_emblem(h);
    if (!full) return;

    const auto [priority, next_priority] = engine::priorities(h);
    if (b.side == team::enemy
        && (next_priority != priority || (b.priority_round >= 0 && b.priority_round < round && priority != b.next_priority)))
        enemy_priorities_change = true;
    ranks_stale_ |= priority != b.priority || next_priority != b.next_priority;
    b.priority = priority;
    b.next_priority = next_priority;
    b.priority_round = round;
}

void World::note_sighting(int enemy_index, vec2 pos, int seen_round, float health) {
    if (enemy_index < 0 || enemy_index >= static_cast<int>(enemies.size()) || !in_bounds(pos)) return;
    auto& b = enemies[enemy_index];
    if (!b.alive || b.visible || seen_round <= b.pos_round) return;
    b.health = health * b.max_health;
    b.pos = pos;
    b.pos_round = seen_round;
    b.pos_source = Source::comms;
    // The poster's turn in that round is unknown, and so is whether it saw a recall about to land.
    fix(b, map().enemy_spawn, {seen_round, -1});
    b.possible.set(pos);
    advance(b);
    prune(b);
}

void World::note_capture(int group, int respawn_round) {
    if (group < 0 || group >= static_cast<int>(camps.size()) || respawn_round <= round) return;
    auto& c = camps[group];
    c.told_respawn = respawn_round;
    if (c.state_round == round) return; // in view: our own reading stands
    c.state = CampState::respawning;
    c.respawn_round = respawn_round;
    c.awake = Awake::asleep;
    c.holder.reset();
    c.held_since = -1;
}

void World::read_vision() {
    cambc::vision::visible_tiles_into(visible);
    unseen_.fill();
    unseen_ ^= visible;
}

void World::mark_fixed(ChampionBelief& b, Moment when) {
    b.tracked = true;
    b.fixed = b.at = when;
    b.turns_since_fixed = 0;
}

void World::fix(ChampionBelief& b, const bitboard& tiles, Moment when) {
    b.possible.clear();
    b.possible |= tiles;
    mark_fixed(b, when);
}

void World::fix(ChampionBelief& b, vec2 tile, Moment when) {
    b.possible.clear();
    b.possible.set(tile);
    mark_fixed(b, when);
}

void World::fix_nowhere(ChampionBelief& b, Moment when) {
    b.possible.clear();
    mark_fixed(b, when);
}

void World::rank_turns() {
    ranks_stale_ = false;
    ranked_round_ = round;
    for (auto* team : {&allies, &enemies}) {
        const auto priority = [&](const ChampionBelief& x) { return round > x.priority_round ? x.next_priority : x.priority; };
        for (auto& c : *team) {
            c.rank = 0;
            for (const auto& o : *team)
                c.rank += priority(o) > priority(c) || (priority(o) == priority(c) && o.handle < c.handle);
        }
    }
}

int World::slot(const ChampionBelief& c, int r) const {
    // Teams alternate one turn at a time, A first in odd rounds; the larger team's extra
    // champions go last.
    const int others = static_cast<int>((c.side == team::ally ? enemies : allies).size());
    const bool first = (c.side == team::ally) == (map().team_a == (r % 2 == 1));
    return c.rank < others ? 2 * c.rank + (first ? 0 : 1) : others + c.rank;
}

int World::turns_between(const ChampionBelief& c, Moment from, Moment to) const {
    int turns = 0;
    for (int r = std::max(from.round, 1); r <= to.round; ++r) {
        const Moment turn{r, slot(c, r)};
        turns += from < turn && turn < to;
    }
    return turns;
}

void World::advance(ChampionBelief& b) {
    if (!b.tracked) return;
    const auto& s = map();
    if (round - b.fixed.round > params::track_horizon) {
        b.tracked = false;
        b.possible.clear();
        return;
    }
    const auto to = now();
    const int turns = turns_between(b, b.at, to);
    b.at = to;
    if (turns == 0) return;
    b.turns_since_fixed += turns;
    // A recall started on any turn after the fix lands at the start of the turn recall turn ends
    // later, which is a full turn: from turn recall + 1 on, add the spawn before growing.
    if (b.turns_since_fixed > (b.fast_recall ? home_recall_time : cambc::constants::recall_time)) b.possible |= s.enemy_spawn;
    FuelMeter meter{"track"};
    // A dash (2 steps, with a walk) crosses holes, altars and champions, so only walls bound it
    // and landings are filtered after.
    bool dash = false;
    for (int slot = 0; slot < 2; ++slot)
        dash |= b.facts().abilities[slot].kind == AbilityKind::dash && (b.ability_ready(slot, round) || b.cooldowns_uncertain());
    // `possible` never holds a tile closed to them, so a walk dilates it.
    const int steps = turns * (dash ? 3 : 1);
    if (steps <= 2) {
        dilate(b.possible, s.open_for_them, steps);
        return;
    }
    static cambc::distance_field field;
    static bitboard grown{cambc::uninitialized};
    field.compute(dash ? s.walls : s.blocked_for_them, b.possible, grown, static_cast<std::uint16_t>(steps));
    if (dash) grown &= s.open_for_them;
    b.possible.swap(grown);
}

void World::prune(ChampionBelief& b) const {
    b.possible &= unseen_;
    // Emptied by something unmodelled (a teleport crystal, say): it could be anywhere.
    if (b.tracked && b.possible.is_empty()) b.tracked = false;
}

void World::update_camps() {
    const auto& s = map();
    std::vector<char> group_visible(s.groups.size(), 0);
    const auto seen = visible & s.camp_tiles;
    for (auto p : Tiles<17 * 17 + 13 * 13>{seen}) group_visible[s.group_at(p)] = 1;
    // Read only for a visible group that is awake or cleared: most turns none is.
    static bitboard ally_champs_b{cambc::uninitialized}, enemy_champs_b{cambc::uninitialized},
        champs_b{cambc::uninitialized}, hidden_b{cambc::uninitialized};
    bool champs_read = false, hidden_made = false;
    const auto read_champs = [&] {
        if (champs_read) return;
        champs_read = true;
        cambc::vision::champion_tiles_into(team::ally, ally_champs_b);
        cambc::vision::champion_tiles_into(team::enemy, enemy_champs_b);
        cambc::vision::champion_tiles_into(team::ally, champs_b);
        champs_b |= enemy_champs_b;
    };
    const auto ally_champs = [&]() -> const bitboard& { return read_champs(), ally_champs_b; };
    const auto enemy_champs = [&]() -> const bitboard& { return read_champs(), enemy_champs_b; };
    const auto champs = [&]() -> const bitboard& { return read_champs(), champs_b; };
    // Where a champion could stand unseen: ~(visible | impassable).
    const auto hidden = [&]() -> const bitboard& {
        if (!hidden_made) {
            hidden_made = true;
            hidden_b.clear();
            hidden_b |= unseen_;
            hidden_b &= s.passable;
        }
        return hidden_b;
    };

    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        guard("camp", [&] {
            const auto& G = s.groups[g];
            auto& c = camps[g];

            if (!group_visible[g]) {
                if (c.state == CampState::cleared && c.holder && round >= c.held_since + cambc::constants::capture_time + 1) {
                    c.state = CampState::respawning;
                    c.respawn_round = c.held_since + cambc::constants::capture_time + 1 + G.respawn;
                    c.holder.reset();
                }
                if (c.state == CampState::respawning && round >= c.respawn_round) {
                    c.state = CampState::alive;
                    c.health_round.assign(G.members.size(), c.respawn_round - 1);
                    for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health;
                    c.awake = Awake::asleep;
                }
                if (c.awake == Awake::awake && round - c.state_round > 2) c.awake = Awake::unknown;
                return;
            }

            const auto [code, timer] = engine::group_state(G.handle);
            const auto previous = c.state;
            const int previous_round = c.state_round;
            const int previous_respawn = c.respawn_round;
            if (previous_round != round - 1) c.quiet_rounds = 0;
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
            // Not alive when last seen: it returned at full health after that, and after its timer.
            if (c.state == CampState::alive && previous != CampState::alive) {
                c.health_round.assign(G.members.size(), std::max(previous_round, previous_respawn - 1));
                for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health;
                c.awake = Awake::asleep;
            }

            // Member health; a visible camp tile with no live camp on it is a dead member. Any drop,
            // a kill included, is damage, which wakes the group, but if the health is older than a
            // sleep it may have fallen asleep again since. A visible live member shows the group's
            // wakefulness outright.
            std::optional<Awake> seen_awake;
            for (std::size_t i = 0; i < G.members.size(); ++i) {
                const auto& m = G.members[i];
                if (!visible.is_set(m.pos)) continue;
                const float hp = engine::camp_health(m.handle).value_or(0.0f);
                if (hp < c.health[i] - 1e-3f) {
                    c.quiet_rounds = 0;
                    if (round - c.health_round[i] < cambc::constants::camp_sleep_time) {
                        c.last_damaged_round = round;
                        c.awake = Awake::awake;
                    } else if (c.awake == Awake::asleep) {
                        c.awake = Awake::unknown;
                    }
                }
                c.health[i] = hp;
                c.health_round[i] = round;
                if (hp > 0 && !seen_awake && c.state == CampState::alive) seen_awake = engine::camp_awake(m.handle);
            }

            if (c.state != CampState::alive) {
                c.awake = Awake::asleep;
            } else if (seen_awake) {
                c.awake = *seen_awake;
                c.quiet_rounds = 0;
            } else if (c.awake != Awake::asleep) {
                // Asleep after 2 camp phases with no champion within 3: count rounds where the whole
                // threat area is visible and empty. Anything unseen there could be a champion.
                const bool fully_seen = (G.threat() & hidden()).is_empty();
                if (fully_seen && (G.threat() & champs()).is_empty()) {
                    if (++c.quiet_rounds >= 2) c.awake = Awake::asleep;
                } else {
                    c.quiet_rounds = 0;
                }
            }

            if (c.state == CampState::cleared) {
                if ((G.tiles() & hidden()).is_empty()) {
                    const bool a = !(G.tiles() & ally_champs()).is_empty();
                    const bool e = !(G.tiles() & enemy_champs()).is_empty();
                    const std::optional<team> holder = a && !e ? std::optional{team::ally}
                                                       : e && !a ? std::optional{team::enemy}
                                                                 : std::nullopt;
                    if (holder != c.holder) {
                        if (debug_log)
                            std::cout << "world r" << round << " g" << g << str(G.centre) << " held by "
                                      << (holder ? cambc::to_string(*holder) : std::string("nobody")) << '\n';
                        c.holder = holder;
                        // A group not seen cleared was cleared no earlier than when last seen, or than
                        // it returned.
                        const int earliest = previous == CampState::cleared ? -1
                                             : previous == CampState::respawning
                                                 ? std::max(previous_round + 1, previous_respawn)
                                                 : std::max(previous_round, previous_respawn);
                        c.held_since = holder ? hold_start(G, *holder, earliest) : -1;
                    }
                }
            } else {
                c.holder.reset();
                c.held_since = -1;
            }
        });
    }
}

// A hold first seen at our turn began after our previous one: last round if a holder on the tiles
// is us or acts after us this round, so cannot have arrived since; else, taking the later
// possibility, this round.
int World::hold_start(const CampGroup& G, team holder, int earliest) const {
    if (earliest >= round) return round;
    const auto& list = holder == team::ally ? allies : enemies;
    for (const auto& c : list)
        if (c.alive && c.pos_round == round && G.tiles().is_set(c.pos) && (c.is_self || slot(c, round) > slot(me(), round)))
            return round - 1;
    return round;
}

void World::update_altars() {
    const auto& s = map();
    for (std::size_t a = 0; a < s.altars.size(); ++a) {
        if (!visible.is_set(s.altars[a].pos)) continue;
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
            if (b.alive && !b.visible && b.gems == score.enemy_delta) tributer = &b, ++candidates;
    }
    if (candidates == 1) {
        if (!tributer->visible) tributer->gems = 0;
        tributer->channel = Channel::none;
    }
}

void World::debug_output() const {
    if constexpr (debug_beliefs) dump_beliefs();
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
                      << " ready r" << b.ready_round[0] << ",r" << b.ready_round[1]
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

void World::dump_beliefs() const {
    static std::size_t written = 0;
    static std::uint64_t last_cost = 0;
    static bool mapped = false;
    if (!(round <= 3 || round % debug_beliefs_period == 0) || !fuel_ok(params::end_reserve + 15000)) return;
    const std::size_t budget = (1u << 20) * 9 / 10 / std::max<std::size_t>(allies.size(), 1);
    if (written >= budget) return;
    const auto start = fuel();
    const auto& s = map();
    static auto& out = *new DumpWriter; // allocated only when the dump is on
    out.clear();
    if (!mapped) {
        mapped = true;
        out.text("BM ");
        out.num(round);
        out.num(engine::id(me().handle));
        for (const auto& g : s.groups) {
            out.num(g.handle);
            out.num(g.members.front().pos.x);
            out.num(g.members.front().pos.y);
        }
        out.text("\n");
    }
    const auto& m = me();
    const vec2 here = m.alive ? cambc::self().position() : vec2{-1, -1};
    out.text("BD ");
    out.num(round);
    out.num(engine::id(m.handle));
    out.num(now().slot);
    out.num(here.x);
    out.num(here.y);
    out.num(m.alive);
    out.num(static_cast<long>(last_cost));
    out.num(cambc::detail::layout().chunked_width);
    for (const auto& b : enemies) {
        out.text("|E");
        out.num(engine::id(b.handle));
        out.num(b.alive);
        out.num(b.visible);
        out.num(b.tracked);
        out.num(b.pos.x);
        out.num(b.pos.y);
        out.num(b.pos_round);
        out.num(static_cast<int>(b.pos_source));
        out.num(b.fixed.round);
        out.num(b.at.round);
        out.num(b.at.slot);
        out.num(b.turns_since_fixed);
        out.num(b.ready_round[0]);
        out.num(b.ready_round[1]);
        out.num(b.respawn_earliest);
        out.num(b.respawn_latest);
        if (!b.alive || !b.tracked) {
            out.num(-1);
            continue;
        }
        // -2: left out for fuel.
        if (!fuel_ok(params::end_reserve + 10000)) {
            out.num(-2);
            continue;
        }
        out.num(b.possible.count());
        out.chunks(b.possible);
    }
    for (std::size_t g = 0; g < camps.size(); ++g) {
        const auto& c = camps[g];
        if (c.state == CampState::alive && c.awake == Awake::asleep && !c.holder && c.state_round != round) continue;
        out.text("|G");
        out.num(s.groups[g].handle);
        out.num(static_cast<int>(c.state));
        out.num(static_cast<int>(c.awake));
        out.num(c.state_round);
        out.num(c.respawn_round);
        out.num(c.holder ? (*c.holder == team::ally ? 0 : 1) : -1);
        out.num(c.held_since);
        out.num(c.last_damaged_round);
        out.num(c.quiet_rounds);
        out.num(c.state == CampState::cleared ? (s.groups[g].tiles() & ~visible).is_empty() : -1);
    }
    for (std::size_t a = 0; a < altars.size(); ++a) {
        const auto& b = altars[a];
        if (!b.ally_lock && !b.enemy_lock) continue;
        out.text("|A");
        out.num(s.altars[a].pos.x);
        out.num(s.altars[a].pos.y);
        out.num(b.ally_lock);
        out.num(b.enemy_lock);
        out.num(b.seen_round);
    }
    out.text("\n");
    std::fwrite(out.data(), 1, out.size(), stdout);
    written += out.size();
    last_cost = start - fuel();
}

} // namespace aph
