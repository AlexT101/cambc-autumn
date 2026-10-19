#include "world.h"
#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <span>

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

// Null if hidden or dead; valid until the next call.
const champion_info* champion(std::uint32_t h) {
    static champion_info info;
    const auto code = sdk_champion(h, &info);
    if (code == not_in_vision) return nullptr;
    check(code);
    if (info.x < 0 || info.y < 0) return nullptr; // dead
    return &info;
}

// Readable for hidden and dead champions too.
cambc::champion_type type(std::uint32_t h) {
    champion_identity identity{};
    check(sdk_champion_identity(h, &identity));
    return static_cast<cambc::champion_type>(identity.type);
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
    static cambc::enum_map<cambc::item_type> counts; // overwritten whole: not cleared first
    check(sdk_champion_items(h, counts.ptr()));
    return counts[cambc::item_type::home_emblem_of_strength] + counts[cambc::item_type::home_emblem_of_focus]
               + counts[cambc::item_type::home_emblem_of_health]
           > 0;
}

// Static camp data in one batched raw call: map::camp_groups() builds an SDK object graph that
// costs more fuel than the data itself. Per group: id, gold, gems, max respawn, member count, then
// per member: id, type, x, y. Static storage starts zeroed for free, where a vector pays to clear.
std::span<const std::uint32_t> camp_layout() {
    static std::array<std::uint32_t, 4096> words;
    static std::vector<std::uint32_t> more;
    std::uint32_t count{};
    check(sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    if (count <= words.size()) return {words.data(), count};
    more.resize(count);
    check(sdk_map_camp_layout(more.data(), count, &count));
    return {more.data(), std::min<std::size_t>(count, more.size())};
}

using Handles = std::array<cambc::handle_champion_t, 16>;

// Every champion handle of a side, visible or not, in id (= pick) order; returns the count.
int handles(team side, Handles& out) {
    std::array<std::uint32_t, 16> raw;
    std::uint32_t count{};
    check(side == team::ally ? sdk_num_allies(&count) : sdk_num_enemies(&count));
    count = std::min<std::uint32_t>(count, raw.size());
    check(side == team::ally ? sdk_allies(raw.data(), count, &count) : sdk_enemies(raw.data(), count, &count));
    const int n = static_cast<int>(std::min<std::uint32_t>(count, raw.size()));
    for (int i = 1; i < n; ++i)
        for (int j = i; j > 0 && raw[j] < raw[j - 1]; --j) std::swap(raw[j], raw[j - 1]);
    for (int i = 0; i < n; ++i) out[i] = static_cast<cambc::handle_champion_t>(raw[i]);
    return n;
}

// Remaining channel turn ends, or nullopt if not channelling.
std::optional<int> channel_time(std::uint32_t h) {
    std::int32_t value{};
    if (sdk_champion_channel_time(h, &value) != 0) return std::nullopt;
    return value;
}

// Visible camp health, or nullopt if the engine has no live camp to show.
std::optional<float> camp_health(std::uint32_t h) {
    static camp_state state;
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

// The first of the items' tiles (`pos` of each) nearest their mean.
template <class Items, class Pos> vec2 central_tile(const Items& items, Pos pos) {
    long sx = 0, sy = 0;
    for (const auto& x : items) sx += pos(x).x, sy += pos(x).y;
    const auto n = static_cast<long>(items.size());
    const vec2 mean{static_cast<int>(sx / n), static_cast<int>(sy / n)};
    vec2 best = pos(*items.begin());
    auto nearest = (best - mean).length_squared();
    for (const auto& x : items)
        if (const auto d = (pos(x) - mean).length_squared(); d < nearest) nearest = d, best = pos(x);
    return best;
}

bool dash_ready(const ChampionBelief& b, int round) {
    bool dash = false;
    for (int slot = 0; slot < 2; ++slot)
        dash |= b.facts().abilities[slot].kind == AbilityKind::dash && (b.ability_ready(slot, round) || b.cooldowns_uncertain());
    return dash;
}

bool disjoint(const bitboard& a, const bitboard& b) {
    static bitboard both{cambc::uninitialized};
    and_into(a, b, both);
    return both.is_empty();
}

// Grows `tiles` by king steps onto open tiles, the last onto `land` within them: what a distance
// field capped at `steps` reaches, for less fuel at one or two steps.
void dilate(bitboard& tiles, const bitboard& open, int steps, const bitboard& land) {
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
        tiles &= steps == 1 ? land : open;
    }
}

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
        std::printf("world %s error: %s\n", what, e.what());
    }
}

} // namespace

void* static_alloc(std::size_t bytes, std::size_t align) {
    alignas(16) static std::byte pool[1 << 16];
    static std::size_t used = 0;
    const std::size_t start = (used + align - 1) / align * align;
    if (align > 16 || start + bytes > sizeof(pool)) return ::operator new(bytes);
    used = start + bytes;
    return pool + start;
}

int StaticMap::group_at(vec2 p) const { return static_cast<int>(group_lookup_[tile_index(p)]) - 1; }

int StaticMap::altar_at(vec2 p) const { return in_bounds(p) ? static_cast<int>(altar_lookup_[tile_index(p)]) - 1 : -1; }

const std::vector<int>& StaticMap::groups_near(vec2 p, int radius) const {
    static std::vector<int> out;
    out.clear();
    for (auto tile : positions_within(camp_tiles, p, radius)) {
        const int g = group_at(tile);
        if (g >= 0 && std::find(out.begin(), out.end(), g) == out.end()) out.push_back(g);
    }
    return out;
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
        growth_ = Growth{std::move(tiles), diagonal};
    }
    auto& g = *growth_;
    static std::array<vec2, max_tiles> flood, reached;
    const auto n = static_cast<int>(g.tiles.positions_into(flood));
    // Indexing costs ~20 fuel a tile, an edge-step flood in WASM ~150 (a host step over the whole
    // board ~2k). bush_cluster() passes no floor and must finish.
    if (fuel_floor > 0 && !fuel_ok(fuel_floor + (g.diagonal ? 170 : 20) * static_cast<std::uint64_t>(n))) return nullptr;
    const auto index = static_cast<std::uint16_t>(bush_clusters_.size() + 1);
    BushCluster c;
    if (!g.diagonal) {
        for (int i = 0; i < n; ++i) cluster_of_[tile_index(flood[i])] = index;
        c.tiles = std::move(g.tiles);
    } else {
        // Tiles of the flood in no cluster yet are marked pending; those of other clusters are
        // not edge-connected to p.
        constexpr std::uint16_t pending = 0xFFFF;
        for (int i = 0; i < n; ++i)
            if (auto& k = cluster_of_[tile_index(flood[i])]; k == 0) k = pending;
        int size = 0;
        reached[size++] = p;
        cluster_of_[tile_index(p)] = index;
        c.tiles.set(p);
        for (int head = 0; head < size; ++head)
            for (const vec2 d : {vec2::north, vec2::east, vec2::south, vec2::west}) {
                const vec2 q = reached[head] + d;
                if (!in_bounds(q)) continue;
                auto& k = cluster_of_[tile_index(q)];
                if (k != pending) continue;
                k = index;
                reached[size++] = q;
                c.tiles.set(q);
            }
        for (int i = 0; i < n; ++i)
            if (auto& k = cluster_of_[tile_index(flood[i])]; k == pending) k = 0;
    }
    clustered_ |= c.tiles;
    growth_.reset();
    bush_clusters_.push_back(std::move(c));
    return &bush_clusters_.back();
}

bool StaticMap::find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized}, rest{cambc::uninitialized};
    not_into(clustered_, left);
    left &= within(bushes, p, radius);
    while (!left.is_empty()) {
        if (!fuel_ok(fuel_floor + (growth_ ? 0 : 20000))) return false;
        const auto* c = grow_cluster(first_tile(left), fuel_floor);
        if (!c) return false;
        not_into(c->tiles, rest);
        left &= rest;
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
    static bitboard opaque{cambc::uninitialized}, seen{cambc::uninitialized}, left{cambc::uninitialized},
        rest{cambc::uninitialized};
    const auto cast_from_inside = [&](const bitboard& cluster, bitboard& out) {
        xor_into(walls_and_bushes, cluster, opaque); // walls_and_bushes & ~cluster
        opaque.shadow_cast_into(p, r, out);
        out &= cluster;
    };
    if (bushes.is_set(p)) {
        bitboard out{cambc::uninitialized};
        cast_from_inside(bush_cluster(p).tiles, out);
        return out;
    }
    auto out = walls_and_bushes.shadow_cast(p, r);
    // Cast each cluster in reach once.
    left.clear();
    left.draw_chebyshev(p, static_cast<float>(radius));
    left &= bushes;
    while (!left.is_empty()) {
        const auto& cluster = bush_cluster(first_tile(left)).tiles;
        cast_from_inside(cluster, seen);
        out |= seen;
        not_into(cluster, rest);
        left &= rest;
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
    return true;
}

int StaticMap::drafted_steps(int group, int which) const {
    std::uint16_t steps;
    std::memcpy(&steps, plan_->data.data() + group * DraftPlan::group_bytes + 2 * which, sizeof steps);
    return steps;
}

int StaticMap::ally_steps(int group) const {
    return plan_ ? drafted_steps(group, 0) : from_ally_spawn().at(groups[group].centre);
}

int StaticMap::enemy_steps(int group) const {
    return plan_ ? drafted_steps(group, 1) : from_enemy_spawn().at(groups[group].centre);
}

std::optional<int> StaticMap::drafted_altar_steps(int group) const {
    if (!plan_) return std::nullopt;
    return drafted_steps(group, 2);
}

std::optional<int> StaticMap::drafted_spawn_steps(vec2 tile, int group) const {
    if (!spawn_steps_drafted() || !ally_spawn.is_set(tile)) return std::nullopt;
    const int base = drafted_steps(group, 0);
    if (base == unreachable) return base;
    const int i = static_cast<int>(std::find(ally_spawn_tiles.begin(), ally_spawn_tiles.end(), tile) - ally_spawn_tiles.begin());
    return base + (plan_->data[group * DraftPlan::group_bytes + 6 + i / 4] >> (2 * (i % 4)) & 3);
}

bool StaticMap::attack_tiles_drafted(int group, int range) const {
    return plan_ && group < plan_->attack_groups
           && std::find(DraftPlan::attack_ranges.begin(), DraftPlan::attack_ranges.end(), range) != DraftPlan::attack_ranges.end();
}

bitboard StaticMap::drafted_attack_tiles(int group, int member, int range) const {
    if (attack_bit_.empty()) {
        int bit = plan_->groups * DraftPlan::group_bytes * 8;
        attack_bit_.reserve(plan_->attack_groups);
        for (int g = 0; g < plan_->attack_groups; ++g) {
            attack_bit_.push_back(bit);
            bit += static_cast<int>(groups[g].members.size()) * DraftPlan::member_bits;
        }
    }
    int bit = attack_bit_[group] + member * DraftPlan::member_bits;
    for (const int r : DraftPlan::attack_ranges) {
        if (r == range) break;
        bit += (2 * r + 1) * (2 * r + 1);
    }
    // A row at a time into the engine's 8x8 chunks; tiles off the map are never set.
    const int side = 2 * range + 1;
    const auto at = static_cast<std::size_t>(bit >> 3);
    std::uint64_t rows = 0;
    std::memcpy(&rows, plan_->data.data() + at, std::min<std::size_t>(sizeof rows, plan_->data.size() - at));
    rows >>= bit & 7;
    bitboard tiles;
    std::uint64_t* words = tiles.ptr();
    const auto stride = cambc::detail::layout().chunk_stride;
    const vec2 p = groups[group].members[member].pos;
    for (int y = p.y - range; y <= p.y + range; ++y, rows >>= side) {
        std::uint64_t row = rows & ((std::uint64_t{1} << side) - 1);
        if (!row) continue;
        int x = p.x - range;
        if (x < 0) row >>= -x, x = 0;
        std::uint64_t* line = words + (y >> 3) * stride + (x >> 3);
        const int shift = (y & 7) * 8;
        line[0] |= (row << (x & 7) & 0xff) << shift;
        if (const auto rest = row >> (8 - (x & 7))) line[1] |= rest << shift;
    }
    return tiles;
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
        for (const auto& m : members) b.draw_chebyshev(m.pos, 3);
        threat_ = std::move(b);
    }
    return *threat_;
}


std::unique_ptr<StaticMap> StaticMap::build() {
    FuelMeter meter{"build_static"};
    auto s = std::make_unique<StaticMap>();
    s->width = cambc::map::width();
    s->height = cambc::map::height();
    s->symmetry = cambc::map::symmetry();
    s->team_a = cambc::detail::sdk_my_team() == 0;

    s->ally_spawn_tiles = s->ally_spawn.positions();
    s->enemy_spawn_tiles = s->enemy_spawn.positions();
    const auto tile = [](vec2 p) { return p; };
    s->ally_spawn_centre = central_tile(s->ally_spawn_tiles, tile);
    s->enemy_spawn_centre = central_tile(s->enemy_spawn_tiles, tile);

    or_into(s->walls, s->holes, s->impassable);
    s->impassable |= s->altar_tiles;
    not_into(s->impassable, s->passable);
    or_into(s->impassable, s->enemy_spawn, s->blocked_for_us);
    or_into(s->impassable, s->ally_spawn, s->blocked_for_them);
    not_into(s->blocked_for_us, s->open_for_us);
    not_into(s->blocked_for_them, s->open_for_them);
    for (auto t : s->enemy_spawn_tiles) s->near_enemy_spawn.draw_chebyshev(t, 1);
    or_into(s->walls, s->bushes, s->walls_and_bushes);

    const auto altar_positions = s->altar_tiles.positions();
    s->altars.resize(altar_positions.size());
    for (std::size_t i = 0; i < altar_positions.size(); ++i) {
        s->altars[i].pos = altar_positions[i];
        s->altars[i].map_ = s.get();
        s->altar_lookup_[tile_index(altar_positions[i])] = static_cast<std::uint16_t>(i + 1);
    }

    // Camp groups, through the raw imports. Member stats come from the camp designs, read once
    // per camp type.
    namespace raw = cambc::detail;
    std::array<std::optional<cambc::camp_stats>, 5> design{};
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
            auto& stats = design[static_cast<std::size_t>(raw_type)];
            if (!stats) {
                raw::camp_design d{};
                raw::check(raw::sdk_camp_design(raw_type, &d));
                stats = d.base_stats;
            }
            const vec2 pos{static_cast<std::int32_t>(layout[i + 2]), static_cast<std::int32_t>(layout[i + 3])};
            g.members.push_back({id, pos, type, stats->base_health, stats->base_strength});
            g.strength += stats->base_strength;
            g.has_monolith |= type == cambc::camp_type::monolith;
            s->camp_tiles.set(pos);
            s->group_lookup_[tile_index(pos)] = static_cast<std::uint16_t>(gi + 1);
        }
        g.centre = central_tile(g.members, [](const CampMember& m) { return m.pos; });
    }
    bool big = false, other = false;
    s->monolith_only = true;
    for (const auto& g : s->groups) {
        s->monolith_only &= g.has_monolith || g.gems == 0;
        if (!g.has_monolith && g.gems >= params::big_gems) big = true;
        else if (!g.has_monolith && g.gems > 0) other = true;
    }
    s->shared_gems = big && !other;
    or_into(s->camp_tiles, s->blocked_for_us, s->standable);
    not_into(s->standable, s->standable);

    const auto* plan = read_draft_plan();
    if (plan && plan->steps && plan->width == s->width && plan->height == s->height && plan->groups == s->groups.size()
        && !s->ally_spawn_tiles.empty() && plan->spawn_x == s->ally_spawn_tiles[0].x && plan->spawn_y == s->ally_spawn_tiles[0].y
        && (plan->spawn_tiles == 0 || plan->spawn_tiles == s->ally_spawn_tiles.size())) {
        max_field_layers() = std::max<int>(max_field_layers(), plan->field_layers);
        s->plan_ = plan;
    }
    return s;
}

void World::init_beliefs() {
    FuelMeter meter{"init_beliefs"};
    const auto& s = map();
    const auto self_handle = static_cast<cambc::handle_champion_t>(cambc::self());

    for (const auto side : {team::ally, team::enemy}) {
        auto& list = side == team::ally ? allies : enemies;
        engine::Handles handles;
        const int n = engine::handles(side, handles);
        list.reserve(n);
        for (int i = 0; i < n; ++i) {
            auto& b = list.emplace_back();
            b.handle = handles[i];
            b.side = side;
            b.index = i;
            b.is_self = handles[i] == self_handle;
            b.type = engine::type(engine::id(handles[i]));
            b.pos = side == team::ally ? s.ally_spawn_centre : s.enemy_spawn_centre;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health = b.facts().health.base;
            b.strength = b.facts().strength.base;
            b.focus = b.facts().focus.base;
            if (side == team::enemy) fix_at_spawn(b, s.enemy_spawn, {1, -1});
            if (b.is_self) self_index = i;
        }
    }

    rank_turns(); // the first update keeps these as last round's ranks
    camps.assign(s.groups.size(), CampBelief{});
    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        auto& health = camps[g].health;
        health.reserve(s.groups[g].members.size());
        for (const auto& m : s.groups[g].members) health.push_back(m.max_health);
        camps[g].health_round.assign(health.size(), 0);
    }
    altars.assign(s.altars.size(), AltarBelief{});
    stirring_.assign((s.groups.size() + 63) / 64, 0);
}

void World::update() {
    round = static_cast<int>(cambc::round_number());
    // First turn; a failure part-way is retried next turn from scratch.
    if (!ready()) {
        first_round = round;
        if (!static_) static_ = StaticMap::build();
        allies.clear();
        enemies.clear();
        init_beliefs();
    }
    FuelMeter meter{"update"};
    read_vision();
    const auto tributing = tributing_enemies(); // before update_champions ends their channels
    guard("priorities", [&] { read_priorities(updated_round_ != round); });
    updated_round_ = round;
    if (ranks_stale_) rank_turns();
    update_champions(true);
    guard("camps", [&] { update_camps(); });
    guard("altars", [&] { update_altars(); });
    guard("scores", [&] { update_scores(tributing); });
}

void World::observe() {
    FuelMeter meter{"observe"};
    read_vision();
    update_champions(false);
}

void World::update_champions(bool full) {
    tracked_count_ = 0;
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
                b.respawn_earliest = round - 1 + cambc::constants::respawn_time;
                b.respawn_latest = round + cambc::constants::respawn_time + 1;
                // Nothing reads where a dead champion could be.
                b.tracked = false;
            }
            b.alive = false;
            b.visible = false;
            b.gems = 0;
            b.channel = Channel::none;
            return;
        }
        if (!b.alive) {
            // Respawned on its spawn, at its turn start this round or (after our turn) last round.
            // The respawn turn allows no casting, so abilities are ready this round or next. Only
            // ours, or one whose turn came before ours in both rounds, is surely this round's.
            b.alive = true;
            b.respawn_earliest = b.respawn_latest = -1;
            const bool before_us = slot(b, round) < slot(me(), round) && slot(b, round - 1) < slot(me(), round - 1);
            b.respawned_round = b.is_self || before_us ? round : round - 1;
            b.pos = spawn;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health;
            b.gems = 0;
            b.ready_round = {b.respawned_round + 1, b.respawned_round + 1};
            if (b.side == team::enemy) fix_at_spawn(b, s.enemy_spawn, {round - 1, -1});
        }
    }

    const auto* info = engine::champion(h);
    b.visible = info != nullptr;
    if (!info) {
        // A channel completes at its owner's turn start.
        const bool ended = round > b.channel_end_round || (round == b.channel_end_round && slot(b, round) < slot(me(), round));
        if (b.channel != Channel::none && ended) {
            if (b.channel == Channel::tribute) b.gems = 0;
            if (b.channel == Channel::recall) {
                b.pos = spawn;
                b.pos_round = b.channel_end_round;
                b.pos_source = Source::inferred;
                b.health = b.max_health;
                // Damage or a stun could have cancelled it, so add the spawn, not replace.
                if (b.side == team::enemy) {
                    b.possible |= s.enemy_spawn;
                    also_undashed(b, s.enemy_spawn);
                    b.lineage = 0;
                }
            }
            b.channel = Channel::none;
        }
        // An untracked `possible` is unread until a fix overwrites it.
        if (b.side == team::enemy && b.tracked) track(b);
        return;
    }

    const int last_seen = b.stats_round;
    const auto state = cambc::champion_state::from_bits_retain(static_cast<std::uint32_t>(info->state));
    b.acted = !b.is_self && state.contains(cambc::champion_state::completed_turn);
    if (b.side == team::enemy) {
        const vec2 seen{info->x, info->y};
        // Fixed there at this turn's update already, and nothing moves during our turn.
        if (full || last_seen != round || b.pos != seen) fix(b, seen, now());
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
    if (b.side == team::enemy && b.channel == Channel::teleport) {
        b.possible |= square(b.pos, teleport_crystal_range) & ~s.blocked_for_them;
        also_undashed(b, b.possible);
        b.lineage = 0;
    }
    for (int slot = 0; slot < 2; ++slot) {
        const int cd = engine::cooldown(h, static_cast<std::uint32_t>(slot));
        const int ready = fire_round(round, cd, b.acted);
        b.ready_round[slot] = std::max(ready, b.respawned_round + 1);
    }
    // In observe() too, for a champion first seen after our move.
    b.gems = engine::gems(h);
    if (b.side == team::enemy) b.fast_recall = engine::home_emblem(h);
}

void World::read_priorities(bool new_round) {
    for (auto* team : {&allies, &enemies})
        for (auto& b : *team) {
            // This round's order before anything dates a turn in it.
            if (new_round) b.prev_rank = b.rank;
            const auto h = engine::id(b.handle);
            std::int32_t priority{}, next_priority{};
            // Fails for champions out of sight. A priority read in round r applies from r + 1:
            // ranks change when a round passes one unread.
            if (cambc::detail::sdk_bc_champion_priority(h, 0, &priority) != 0
                || cambc::detail::sdk_bc_champion_priority(h, 1, &next_priority) != 0) {
                ranks_stale_ |= b.next_priority != b.priority && ranked_round_ <= b.priority_round && b.priority_round < round;
                continue;
            }
            if (b.side == team::enemy
                && (next_priority != priority || (b.priority_round >= 0 && b.priority_round < round && priority != b.next_priority)))
                enemy_priorities_change = true;
            ranks_stale_ |= priority != b.priority || next_priority != b.next_priority;
            b.priority = priority;
            b.next_priority = next_priority;
            b.priority_round = round;
        }
}

void World::note_turn_end() {
    auto& self = cambc::self();
    if (!me().alive || !self.is_alive()) return;
    const vec2 p = self.position();
    const int g = in_bounds(p) ? map().group_at(p) : -1;
    if (g < 0 || camps[g].state != CampState::alive) return;
    guard("turn end", [&] {
        if (engine::group_state(map().groups[g].handle).first == 2) camps[g].cleared_by_us = round;
    });
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
    fix_at_spawn(b, map().enemy_spawn, {seen_round, -1});
    b.possible.set(pos);
    if (b.facts().has_dash()) b.undashed.set(pos);
    b.lineage = 0;
    track(b);
}

void World::note_capture(int group, int respawn_round) {
    if (group < 0 || group >= static_cast<int>(camps.size()) || respawn_round <= round) return;
    auto& c = camps[group];
    c.told_respawn = respawn_round;
    if (c.state_round == round) return; // in view: our own reading stands
    if (static_cast<std::size_t>(group) < camps_pending_.size()) camps_pending_[group] = 1;
    c.version += c.state != CampState::respawning;
    camps_version += c.state != CampState::respawning;
    c.state = CampState::respawning;
    c.respawn_round = respawn_round;
    c.awake = Awake::asleep;
    c.holder.reset();
    c.held_since = -1;
    note_stirring(group);
}

void World::note_stirring(int g) {
    const auto& c = camps[g];
    const std::uint64_t bit = std::uint64_t{1} << (g % 64);
    auto& word = stirring_[g / 64];
    word = c.state == CampState::alive && c.awake != Awake::asleep ? word | bit : word & ~bit;
}

void World::read_vision() {
    cambc::vision::visible_tiles_into(visible);
    not_into(visible, unseen_);
    landing_ready_ = false;
}

// `undashed` is read only while turns_since_fixed <= ability_cooldown, in advance(), which first
// adds the turns; the next fix resets it. Once no later advance can read it, it is left stale.
void World::also_undashed(ChampionBelief& b, const bitboard& tiles) {
    if (b.facts().has_dash() && b.turns_since_fixed < ability_cooldown) b.undashed |= tiles;
}

void World::mark_fixed(ChampionBelief& b, Moment when) {
    if (b.facts().has_dash()) {
        copy_into(b.possible, b.undashed);
        b.undashed_all = true;
    }
    b.tracked = true;
    b.fixed = b.at = when;
    b.turns_since_fixed = 0;
}

// Enemies fixed to their spawn at the same moment share a lineage.
void World::fix_at_spawn(ChampionBelief& b, const bitboard& spawn, Moment when) {
    copy_into(spawn, b.possible);
    mark_fixed(b, when);
    b.lineage = 0x80000000u | static_cast<std::uint32_t>(when.round) << 6 | static_cast<std::uint32_t>(when.slot + 1);
}

void World::fix(ChampionBelief& b, vec2 tile, Moment when) {
    b.possible.clear();
    b.possible.set(tile);
    mark_fixed(b, when);
    b.lineage = 0;
}

void World::rank_turns() {
    ranks_stale_ = false;
    ranked_round_ = round;
    for (auto* team : {&allies, &enemies}) {
        // Handles ascend with the index: a tie goes to the lower index.
        const int n = std::min(static_cast<int>(team->size()), 16);
        std::array<int, 16> priority;
        for (int i = 0; i < n; ++i) {
            const auto& x = (*team)[i];
            priority[i] = round > x.priority_round ? x.next_priority : x.priority;
        }
        std::array<int, 16> rank{};
        for (int i = 0; i < n; ++i)
            for (int j = i + 1; j < n; ++j) ++rank[priority[j] > priority[i] ? i : j];
        for (int i = 0; i < n; ++i) (*team)[i].rank = rank[i];
    }
}

int World::slot(const ChampionBelief& c, int r) const {
    // Teams alternate one turn at a time, A first in odd rounds; the larger team's extra
    // champions go last.
    const int others = static_cast<int>((c.side == team::ally ? enemies : allies).size());
    const bool first = (c.side == team::ally) == (map().team_a == (r % 2 == 1));
    const int rank = r < round ? c.prev_rank : c.rank;
    return rank < others ? 2 * rank + (first ? 0 : 1) : others + rank;
}

int World::turns_between(const ChampionBelief& c, Moment from, Moment to) const {
    if (!(from < to)) return 0;
    int turns = 0;
    for (int r = std::max(from.round, 1); r <= to.round; ++r) {
        const Moment turn{r, slot(c, r)};
        turns += from < turn && turn < to;
    }
    return turns;
}

const bitboard& World::landing() {
    if (!landing_ready_) {
        and_into(map().open_for_them, unseen_, landing_);
        landing_ready_ = true;
    }
    return landing_;
}

bool World::grow(ChampionBelief& b, int turns, const bitboard& land) {
    const auto& s = map();
    b.turns_since_fixed += turns;
    const bool dasher = b.facts().has_dash();
    const bool undashed_read = dasher && b.turns_since_fixed <= ability_cooldown;
    const bool undashed_kept = dasher && b.turns_since_fixed < ability_cooldown;
    // A recall started on any turn after the fix lands at the start of the turn after its last
    // turn end, which is a full turn: from turn recall_time + 1 on, add the spawn before growing.
    if (b.turns_since_fixed > (b.fast_recall ? home_recall_time : cambc::constants::recall_time)) {
        b.possible |= s.enemy_spawn;
        if (undashed_read) b.undashed |= s.enemy_spawn;
    }
    FuelMeter meter{"track"};
    if (!dasher) {
        walk(b.possible, s, turns, land);
        return false;
    }
    // A dash readies once per cooldown: from the undashed tiles it adds 2 steps once in these
    // turns; tiles already reached with a dash grow only by walking until the next is ready.
    const bool dash = dash_ready(b, round);
    if (dash && undashed_read && !b.undashed_all) {
        static bitboard dashed{cambc::uninitialized};
        widen_by_dash(b.undashed, dashed, s, turns, land);
        walk(b.possible, s, turns, land);
        b.possible |= dashed;
        if (undashed_kept) walk(b.undashed, s, turns, land);
    } else if (dash) {
        // undashed lies within possible (equal to it, or read no more): dashing from possible
        // covers dashing from it.
        if (undashed_kept) walk(b.undashed, s, turns, land);
        widen_by_dash(b.possible, b.possible, s, turns, land);
    } else {
        walk(b.possible, s, turns, land);
        if (undashed_kept) {
            if (b.undashed_all) copy_into(b.possible, b.undashed);
            else walk(b.undashed, s, turns, land);
        }
    }
    b.undashed_all = b.undashed_all && !dash && undashed_kept;
    return dash;
}

void World::track(ChampionBelief& b) {
    if (round - b.fixed.round > params::track_horizon) {
        b.tracked = false;
        b.possible.clear();
        return;
    }
    const auto to = now();
    const int turns = turns_between(b, b.at, to);
    // With no turns to add, every enemy of a lineage gets the same prune this pass.
    if (!turns) {
        b.at = to;
        prune(b);
        return;
    }
    if (!b.lineage) {
        b.at = to;
        (void)grow(b, turns, landing());
        note_emptied(b);
        return;
    }
    const bool dasher = b.facts().has_dash();
    for (int i = 0; i < tracked_count_; ++i) {
        const auto& t = tracked_[i];
        if (t.before != b.lineage || t.turns != turns || t.tsf != b.turns_since_fixed || t.fixed != b.fixed || t.at != b.at
            || t.dasher != dasher || t.fast_recall != b.fast_recall || t.dash != (dasher && dash_ready(b, round)))
            continue;
        const auto& leader = enemies[t.leader];
        copy_into(leader.possible, b.possible);
        if (dasher && leader.turns_since_fixed < ability_cooldown) copy_into(leader.undashed, b.undashed);
        b.undashed_all = leader.undashed_all;
        b.tracked = leader.tracked;
        b.at = to;
        b.turns_since_fixed = leader.turns_since_fixed;
        b.lineage = t.after;
        return;
    }
    Tracked t{b.lineage, ++lineages_, b.index, turns, b.turns_since_fixed, b.fixed, b.at, dasher, false, b.fast_recall};
    b.at = to;
    t.dash = grow(b, turns, landing());
    note_emptied(b);
    b.lineage = t.after;
    if (tracked_count_ < static_cast<int>(tracked_.size())) tracked_[tracked_count_++] = t;
}

// `possible` never holds a tile closed to them, so a walk dilates it.
void World::walk(bitboard& tiles, const StaticMap& s, int steps, const bitboard& land) {
    if (steps <= 2) {
        dilate(tiles, s.open_for_them, steps, land);
        return;
    }
    static cambc::distance_field field;
    static bitboard grown{cambc::uninitialized};
    field.compute(s.blocked_for_them, tiles, grown, static_cast<std::uint16_t>(steps));
    tiles.swap(grown);
    if (&land != &s.open_for_them) tiles &= land;
}

// `steps` turns with one dash (2 king steps, with that turn's walk): it crosses holes, altars and
// champions, so only walls bound it and landings are filtered after.
void World::widen_by_dash(const bitboard& from, bitboard& out, const StaticMap& s, int steps, const bitboard& land) {
    static cambc::distance_field field;
    static bitboard grown{cambc::uninitialized};
    field.compute(s.walls, from, grown, static_cast<std::uint16_t>(steps + 2));
    grown &= land;
    out.swap(grown);
}

void World::prune(ChampionBelief& b) const {
    b.possible &= unseen_;
    if (b.facts().has_dash() && b.turns_since_fixed < ability_cooldown) b.undashed &= unseen_;
    note_emptied(b);
}

// Emptied by something unmodelled (a teleport crystal, say): it could be anywhere.
void World::note_emptied(ChampionBelief& b) {
    if (b.tracked && b.possible.is_empty()) b.tracked = false;
}

namespace {
// Back at full health and asleep, each member's health known from `since`.
void restore(CampBelief& c, const CampGroup& G, int since) {
    c.health_round.assign(G.members.size(), since);
    for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health;
    c.awake = Awake::asleep;
    ++c.version;
}
} // namespace

void World::update_camps() {
    const auto& s = map();
    group_visible_.assign(s.groups.size(), 0);
    static bitboard seen{cambc::uninitialized};
    and_into(visible, s.camp_tiles, seen);
    for (auto p : Tiles<17 * 17 + 13 * 13>{seen}) group_visible_[s.group_at(p)] = 1;
    const auto& group_visible = group_visible_;
    // Read only for a visible group that is awake or cleared: most turns none is.
    static bitboard ally_champs_b{cambc::uninitialized}, enemy_champs_b{cambc::uninitialized},
        champs_b{cambc::uninitialized}, hidden_b{cambc::uninitialized};
    bool champs_read = false, hidden_made = false;
    const auto read_champs = [&] {
        if (champs_read) return;
        champs_read = true;
        cambc::vision::champion_tiles_into(team::ally, ally_champs_b);
        cambc::vision::champion_tiles_into(team::enemy, enemy_champs_b);
        or_into(ally_champs_b, enemy_champs_b, champs_b);
    };
    const auto champs = [&]() -> const bitboard& { return read_champs(), champs_b; };
    // Where a champion could stand unseen: ~(visible | impassable).
    const auto hidden = [&]() -> const bitboard& {
        if (!hidden_made) {
            hidden_made = true;
            and_into(unseen_, s.passable, hidden_b);
        }
        return hidden_b;
    };

    camps_pending_.resize(s.groups.size());
    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        if (!group_visible[g] && !camps_pending_[g]) continue;
        const auto version = camps[g].version;
        guard("camp", [&] {
            const auto& G = s.groups[g];
            auto& c = camps[g];

            if (!group_visible[g]) {
                if (c.state == CampState::cleared && c.holder && round >= c.payout_round()) {
                    c.state = CampState::respawning;
                    ++c.version;
                    c.respawn_round = c.payout_round() + G.respawn;
                    c.holder.reset();
                }
                if (c.state == CampState::respawning && round >= c.respawn_round) {
                    c.state = CampState::alive;
                    restore(c, G, c.respawn_round - 1); // a new version
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
            c.version += c.state != previous;
            c.state_round = round;
            // Not alive when last seen: it returned at full health after that, and after its timer.
            if (c.state == CampState::alive && previous != CampState::alive)
                restore(c, G, std::max(previous_round, previous_respawn - 1));

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
                c.version += hp != c.health[i];
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
                const bool fully_seen = disjoint(G.threat(), hidden());
                if (fully_seen && disjoint(G.threat(), champs())) {
                    if (++c.quiet_rounds >= 2) c.awake = Awake::asleep;
                } else {
                    c.quiet_rounds = 0;
                }
            }

            if (c.state == CampState::cleared) {
                if (disjoint(G.tiles(), hidden())) {
                    std::uint32_t occupants = 0;
                    if (!disjoint(G.tiles(), champs())) {
                        for (const auto& b : allies)
                            if (b.alive && (b.visible || b.is_self) && G.tiles().is_set(b.pos)) occupants |= 1u << b.index;
                        for (const auto& b : enemies)
                            if (b.alive && b.visible && G.tiles().is_set(b.pos)) occupants |= 1u << (16 + b.index);
                    }
                    const bool a = (occupants & 0xFFFF) != 0, e = (occupants >> 16) != 0;
                    const std::optional<team> holder = a && !e ? std::optional{team::ally}
                                                       : e && !a ? std::optional{team::enemy}
                                                                 : std::nullopt;
                    // Progress resets the moment the tiles empty or are contested, mid-turn included.
                    // A hold seen last round by other occupants than now may have lapsed between
                    // them; one that follows a contest or the other side's hold began once that
                    // ended, which can be this round before our turn. Late costs a round, early
                    // the capture.
                    const std::uint32_t before = c.occupants;
                    c.occupants = occupants;
                    const std::uint32_t side_mask = holder == team::ally ? 0xFFFFu : 0xFFFF0000u;
                    const bool watched = previous_round == round - 1 && previous == CampState::cleared;
                    const bool handed_over = holder && holder == c.holder && watched && !(before & occupants & side_mask);
                    if (handed_over) {
                        c.held_since = std::max(c.held_since, hold_start(G, *holder, -1, false));
                    } else if (holder && holder != c.holder && watched && (before & ~side_mask)) {
                        c.holder = holder;
                        c.held_since = round;
                    } else if (holder != c.holder) {
                        c.holder = holder;
                        // A group not seen cleared was cleared no earlier than when last seen, or than
                        // it returned.
                        const int earliest = previous == CampState::cleared ? -1
                                             : previous == CampState::respawning
                                                 ? std::max(previous_round + 1, previous_respawn)
                                                 : std::max(previous_round, previous_respawn);
                        c.held_since = holder ? hold_start(G, *holder, earliest, c.cleared_by_us >= previous_round) : -1;
                    }
                }
            } else {
                c.holder.reset();
                c.held_since = -1;
                c.occupants = 0;
            }
        });
        const auto& c = camps[g];
        camps_pending_[g] = (c.state == CampState::cleared && c.holder) || c.state == CampState::respawning || c.awake == Awake::awake;
        camps_version += c.version != version;
        note_stirring(static_cast<int>(g));
    }
}

// A hold first seen at our turn began after our previous one: last round if a holder on the tiles
// is us or acts after us this round, so cannot have arrived since; else, taking the later
// possibility, this round. A group cleared since our previous turn, other than by us in it, may
// have been cleared this round before our turn, and no hold began before that.
int World::hold_start(const CampGroup& G, team holder, int earliest, bool cleared_by_us) const {
    if (earliest >= round || (earliest >= 0 && !cleared_by_us)) return round;
    const auto& list = holder == team::ally ? allies : enemies;
    for (const auto& c : list)
        if (c.alive && c.pos_round == round && G.tiles().is_set(c.pos) && (c.is_self || slot(c, round) > slot(me(), round)))
            return round - 1;
    return round;
}

void World::update_altars() {
    namespace raw = cambc::detail;
    const auto& s = map();
    const auto seen = [&](int a) {
        altars[a] = AltarBelief{};
        altars[a].seen_round = round;
    };
    // A tile test costs ~75 fuel an altar, a board operation about 1 per 8x8 chunk.
    if (s.altars.size() * 40 > search_chunks()) {
        static bitboard in_view{cambc::uninitialized};
        and_into(visible, s.altar_tiles, in_view);
        for (auto p : Tiles<128>{in_view}) seen(s.altar_at(p));
    } else {
        for (std::size_t a = 0; a < s.altars.size(); ++a)
            if (visible.is_set(s.altars[a].pos)) seen(static_cast<int>(a));
    }
    std::uint32_t count{};
    raw::check(raw::sdk_altar_locks(nullptr, 0, &count));
    if (count == 0) return;
    static std::vector<raw::altar_lock_info> locks; // kept across turns: allocating costs more than the read
    if (locks.size() < count) locks.resize(count);
    raw::check(raw::sdk_altar_locks(locks.data(), count, &count));
    const auto own = static_cast<std::uint32_t>(raw::sdk_my_team());
    for (std::uint32_t i = 0; i < count && i < locks.size(); ++i) {
        const auto& lock = locks[i];
        const int a = s.altar_at({lock.x, lock.y});
        if (a < 0) continue;
        auto& belief = altars[a];
        belief.seen_round = round;
        if (lock.team == own) {
            belief.ally_lock = true;
        } else {
            belief.enemy_lock = true;
            belief.enemy_lock_hits = static_cast<int>(lock.hits_remaining);
        }
    }
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
    const int enemy_delta = round == first_round ? 0 : enemy - score.enemy;
    score.ally = ally;
    score.enemy = enemy;
    if (enemy_delta <= 0) return;

    // An enemy tribute just landed: empty the bag of whoever most plausibly made it. First choice:
    // an enemy that was tributing before this update and no longer is. A visible enemy's bag was
    // just read, so only an unseen one's needs emptying.
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
            if (b.alive && !b.visible && b.gems == enemy_delta) tributer = &b, ++candidates;
    }
    if (candidates == 1 && !tributer->visible) {
        tributer->gems = 0;
        tributer->channel = Channel::none;
    }
}

void World::debug_output() const {
    if constexpr (debug_beliefs) dump_beliefs();
    if constexpr (debug_draw) {
        const auto& s = map();
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
        for (std::size_t a = 0; a < altars.size(); ++a)
            if (altars[a].enemy_lock) draw_dot(s.altars[a].pos, 0xFF00FF);
    }
}

void World::dump_beliefs() const {
    static std::size_t written = 0;
    static std::uint64_t last_cost = 0;
    static bool mapped = false;
    if (!(round <= 3 || round % debug_beliefs_period == 0) || !fuel_ok(end_reserve + 15000)) return;
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
    const vec2 here = m.alive ? my_position() : vec2{-1, -1};
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
        if (!fuel_ok(end_reserve + 10000)) {
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
