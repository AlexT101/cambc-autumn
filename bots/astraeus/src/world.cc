#include "world.h"
#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <span>
#include <tuple>

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
    ok(code);
    if (info.x < 0 || info.y < 0) return nullptr; // dead
    return &info;
}

// Readable for hidden and dead champions too.
cambc::champion_type type(std::uint32_t h) {
    champion_identity identity{};
    ok(sdk_champion_identity(h, &identity));
    return static_cast<cambc::champion_type>(identity.type);
}

// The active shield's value and turn ends left, {0, 0} if none.
std::pair<float, int> shield(std::uint32_t h) {
    static std::array<buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
    std::uint32_t n = 0;
    ok(sdk_champion_buff_data(h, buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::shield))
            return {buffs[i].data.shield.value, buffs[i].data.shield.duration};
    return {0.0f, 0};
}

bool alive(std::uint32_t h) {
    static std::int32_t value;
    ok(sdk_champion_is_alive(h, &value));
    return value != 0;
}

int cooldown(std::uint32_t h, std::uint32_t slot) {
    static std::int32_t value;
    ok(sdk_champion_cooldown(h, slot, &value));
    return value;
}

int gems(std::uint32_t h) {
    static std::uint32_t value;
    ok(sdk_champion_gems(h, &value));
    return static_cast<int>(value);
}

// A hidden champion's gems are unreadable: cheaper than champion().
bool in_sight(std::uint32_t h) {
    static std::uint32_t value;
    return sdk_champion_gems(h, &value) == 0;
}

// Summing every item count costs ~350 fuel; only the emblems below matter.
struct Emblems {
    bool home, durability, tribute, capture, prospector;
    float dealt, camp_dealt; // ChampionBelief::dealt, ::camp_dealt
};
bool owns(const cambc::enum_map<cambc::item_type>& counts, cambc::item_family family) {
    using S = cambc::item_stat;
    return counts[cambc::get_item_enum(family, S::strength, false)] + counts[cambc::get_item_enum(family, S::focus, false)]
               + counts[cambc::get_item_enum(family, S::health, false)] > 0;
}
// Ours, read live: bot.cc's champion_dealt_with() and camp_dealt_with().
Emblems emblems(std::uint32_t h) {
    using F = cambc::item_family;
    static cambc::enum_map<cambc::item_type> counts; // overwritten whole: not cleared first
    ok(sdk_champion_items(h, counts.ptr()));
    float dealt = owns(counts, F::skirmish) ? skirmish_dealt : 1.0f;
    float camp_dealt = owns(counts, F::monster) ? monster_camp_dealt : 1.0f;
    if (owns(counts, F::collectors)) {
        int families = 0;
        for (int f = 0; f <= static_cast<int>(F::collectors); ++f) families += owns(counts, static_cast<F>(f));
        dealt *= 1.0f + collectors_dealt * static_cast<float>(families);
        camp_dealt *= 1.0f + collectors_dealt * static_cast<float>(families);
    }
    return {owns(counts, F::home), owns(counts, F::durability), owns(counts, F::tribute), owns(counts, F::capture),
            owns(counts, F::prospector), dealt, camp_dealt};
}

// Static camp data in one batched raw call: map::camp_groups() builds an SDK object graph that
// costs more fuel than the data itself. Per group: id, gold, gems, max respawn, member count, then
// per member: id, type, x, y. Static storage starts zeroed for free, where a vector pays to clear.
std::span<const std::uint32_t> camp_layout() {
    static std::array<std::uint32_t, 4096> words;
    static std::vector<std::uint32_t> more;
    std::uint32_t count{};
    ok(sdk_map_camp_layout(words.data(), static_cast<std::uint32_t>(words.size()), &count));
    if (count <= words.size()) return {words.data(), count};
    more.resize(count);
    ok(sdk_map_camp_layout(more.data(), count, &count));
    return {more.data(), std::min<std::size_t>(count, more.size())};
}

using Handles = std::array<cambc::handle_champion_t, 16>;

// Every champion handle of a side, visible or not, in id (= pick) order; returns the count.
int handles(team side, Handles& out) {
    std::array<std::uint32_t, 16> raw;
    std::uint32_t count{};
    ok(side == team::ally ? sdk_num_allies(&count) : sdk_num_enemies(&count));
    count = std::min<std::uint32_t>(count, raw.size());
    ok(side == team::ally ? sdk_allies(raw.data(), count, &count) : sdk_enemies(raw.data(), count, &count));
    const int n = static_cast<int>(std::min<std::uint32_t>(count, raw.size()));
    for (int i = 1; i < n; ++i)
        for (int j = i; j > 0 && raw[j] < raw[j - 1]; --j) std::swap(raw[j], raw[j - 1]);
    for (int i = 0; i < n; ++i) out[i] = static_cast<cambc::handle_champion_t>(raw[i]);
    return n;
}

// Remaining channel turn ends, or nullopt if not channelling.
std::optional<int> channel_time(std::uint32_t h) {
    static std::int32_t value;
    if (sdk_champion_channel_time(h, &value) != 0) return std::nullopt;
    return value;
}

// Visible camp health, or nullopt if the engine has no live camp to show.
std::optional<float> camp_health(std::uint32_t h) {
    static camp_state state;
    const auto code = sdk_camp(h, &state);
    if (code == not_in_vision || code == not_found) return std::nullopt;
    ok(code);
    return state.health;
}

// The raw state codes of sdk_camp_state and sdk_camp_group_state (no SDK enum).
enum : std::uint32_t { camp_awake_code = 1, camp_asleep_code = 2 };
enum : std::uint32_t { group_alive = 1, group_cleared = 2, group_respawning = 3 };

// Whether a visible live camp is awake or asleep; nullopt if hidden or dead.
std::optional<Awake> camp_awake(std::uint32_t h) {
    static std::uint32_t value;
    const auto code = sdk_camp_state(h, &value);
    if (code == not_in_vision || code == not_found) return std::nullopt;
    ok(code);
    if (value == camp_awake_code) return Awake::awake;
    if (value == camp_asleep_code) return Awake::asleep;
    return std::nullopt;
}

// Camp-group state code and the respawn timer.
std::pair<std::uint32_t, int> group_state(std::uint32_t h) {
    static std::uint32_t state;
    static std::int32_t timer;
    ok(sdk_camp_group_state(h, &state));
    if (state != group_respawning) return {state, 0};
    ok(sdk_camp_group_cooldown(h, &timer));
    return {state, timer};
}

// While `side` captures the group, the rounds to its payout (paid at that round's capture phase,
// a Capture emblem's cap included); else -1. Needs the group in vision, not the capturers.
int capture_timer(std::uint32_t h, team side) {
    static cambc::detail::camp_group_capture_state value;
    if (sdk_camp_group_capture_state(h, &value) != 0) return -1;
    using T = cambc::map::camp_group_capture_type;
    const auto capturing = static_cast<std::int32_t>(side == team::ally ? T::ally_capturing : T::enemy_capturing);
    return static_cast<std::int32_t>(value.state) == capturing ? value.timer : -1;
}

// Who is capturing the group, if anyone, and capture_timer's rounds to payout. Readable while any
// one of its camp tiles is in vision.
std::pair<std::optional<team>, int> capturer(std::uint32_t h) {
    static cambc::detail::camp_group_capture_state value;
    if (sdk_camp_group_capture_state(h, &value) != 0) return {std::nullopt, -1};
    using T = cambc::map::camp_group_capture_type;
    if (value.state == static_cast<std::int32_t>(T::ally_capturing)) return {team::ally, value.timer};
    if (value.state == static_cast<std::int32_t>(T::enemy_capturing)) return {team::enemy, value.timer};
    return {std::nullopt, -1};
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
    if (items.size() == 1) return pos(*items.begin());
    long sx = 0, sy = 0;
    for (const auto& x : items) sx += pos(x).x, sy += pos(x).y;
    const auto n = static_cast<long>(items.size());
    const vec2 mean{static_cast<int>(sx / n), static_cast<int>(sy / n)};
    // Squared lengths of tile offsets fit in 32 bits.
    const auto length_squared = [&](vec2 p) {
        const int dx = p.x - mean.x, dy = p.y - mean.y;
        return dx * dx + dy * dy;
    };
    vec2 best = pos(*items.begin());
    int nearest = length_squared(best);
    for (const auto& x : items)
        if (const int d = length_squared(pos(x)); d < nearest) nearest = d, best = pos(x);
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

constexpr std::uint32_t unlisted = ~0u;
constexpr std::uint32_t reach_few = 6;
vec2 growth_tiles[65];

// A few tiles grow for less as a square drawn around each (~22 fuel) than by the 8 shifts and
// unions, at about 1 fuel per 8x8 chunk each.
std::uint32_t dilate_few() {
    static const auto few = static_cast<std::uint32_t>(std::min<std::uint64_t>(64, (7 * (search_chunks() + 13) - 100) / 22));
    return few;
}

// Lists `tiles` into growth_tiles, as far as dilate and reach_each need to tell whether they are
// few; returns how many it listed.
std::uint32_t list_growth(const bitboard& tiles) {
    return positions_into(tiles, growth_tiles, std::max(dilate_few(), reach_few) + 1);
}

// Grows `tiles` by king steps onto open tiles, the last onto `land` within them: what a distance
// field capped at `steps` reaches, for less fuel at one or two steps.
void dilate(bitboard& tiles, const bitboard& open, int steps, const bitboard& land, std::uint32_t listed) {
    static bitboard t1{cambc::uninitialized}, t2{cambc::uninitialized};
    const auto few = dilate_few();
    namespace raw = cambc::detail;
    for (; steps > 0; --steps, listed = unlisted) {
        if (const auto n = listed == unlisted ? list_growth(tiles) : listed; n <= few) {
            clear_board(t1);
            for (std::uint32_t i = 0; i < n; ++i) draw_square(t1, growth_tiles[i], 1.0f);
            and_into(t1, steps == 1 ? land : open, tiles);
            continue;
        }
        ok(raw::sdk_Bitboard_ShiftRight(tiles.ptr(), t1.ptr(), 1));
        ok(raw::sdk_Bitboard_ShiftRight(tiles.ptr(), t2.ptr(), -1));
        or_into(tiles, t1, tiles);
        or_into(tiles, t2, tiles);
        ok(raw::sdk_Bitboard_ShiftUp(tiles.ptr(), t1.ptr(), 1));
        ok(raw::sdk_Bitboard_ShiftUp(tiles.ptr(), t2.ptr(), -1));
        or_into(tiles, t1, tiles);
        or_into(tiles, t2, tiles);
        and_into(tiles, steps == 1 ? land : open, tiles);
    }
}

// `out` (which may be `from`) = the tiles within `steps` king steps of `from` avoiding `walls`, on
// `land`, as one reach per tile when at most `few`: less fuel than a distance field or a dilate of
// 2 or more steps.
bool reach_each(const bitboard& from, bitboard& out, const bitboard& walls, int steps, const bitboard& land, std::uint32_t few,
                std::uint32_t listed) {
    static bitboard one{cambc::uninitialized};
    const auto n = listed == unlisted ? list_growth(from) : listed;
    if (n > few) return false;
    namespace raw = cambc::detail;
    const auto d = static_cast<std::uint16_t>(steps);
    const auto* at = growth_tiles;
    if (!n) clear_board(out);
    else ok(raw::sdk_Bitboard_ReachableMask(walls.ptr(), at[0].x, at[0].y, out.ptr(), d));
    for (std::uint32_t i = 1; i < n; ++i) {
        ok(raw::sdk_Bitboard_ReachableMask(walls.ptr(), at[i].x, at[i].y, one.ptr(), d));
        or_into(out, one, out);
    }
    and_into(out, land, out);
    return true;
}

// out = the tiles within Chebyshev r of `in`, terrain ignored; out must not be `in`. Shifts cost
// less than a square drawn per tile once there are more than a few.
void square_dilate(const bitboard& in, int r, bitboard& out) {
    static bitboard rows{cambc::uninitialized}, shifted{cambc::uninitialized};
    copy_into(in, rows);
    for (int d = 1; d <= r; ++d) {
        in.shift_right_into(d, shifted);
        rows |= shifted;
        in.shift_right_into(-d, shifted);
        rows |= shifted;
    }
    copy_into(rows, out);
    for (int d = 1; d <= r; ++d) {
        rows.shift_up_into(d, shifted);
        out |= shifted;
        rows.shift_up_into(-d, shifted);
        out |= shifted;
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


const std::vector<int>& StaticMap::groups_near(vec2 p, int radius) const {
    static std::vector<int> out;
    // Camp tiles are fixed for the game: each tile keeps its answers for the last two radii asked,
    // as a range of `pool`. An evicted answer's range is reused when the new one fits, so the pool
    // stays bounded however many radii callers alternate between.
    struct Kept {
        std::array<std::uint8_t, 2> radius; // radius + 1; 0: none
        std::array<std::uint8_t, 2> count, capacity;
        std::uint8_t next;
        std::array<std::uint32_t, 2> from;
    };
    static std::array<Kept, 100 * 100> kept;
    static std::vector<std::uint16_t> pool;
    const bool keep = in_bounds(p) && radius >= 0 && radius < 255;
    const auto i = keep ? static_cast<std::size_t>(tile_index(p)) : 0;
    if (keep) {
        const auto& k = kept[i];
        for (int j = 0; j < 2; ++j)
            if (k.radius[j] == radius + 1) {
                out.assign(pool.begin() + k.from[j], pool.begin() + k.from[j] + k.count[j]);
                return out;
            }
    }
    out.clear();
    // Groups listed by this call: a find in `out` per camp tile cost up to ~1.7k a miss on
    // camp-dense maps.
    static std::vector<std::uint32_t> listed;
    static std::uint32_t call = 0;
    if (listed.size() < groups.size()) listed.resize(groups.size());
    ++call;
    for (auto tile : positions_within(camp_tiles, p, radius)) {
        const int g = group_at(tile);
        if (g >= 0 && listed[static_cast<std::size_t>(g)] != call) listed[static_cast<std::size_t>(g)] = call, out.push_back(g);
    }
    if (keep && out.size() < 256) {
        auto& k = kept[i];
        const int j = k.next;
        k.next ^= 1;
        k.radius[j] = static_cast<std::uint8_t>(radius + 1);
        k.count[j] = static_cast<std::uint8_t>(out.size());
        if (out.size() <= k.capacity[j]) {
            std::copy(out.begin(), out.end(), pool.begin() + k.from[j]);
        } else {
            k.capacity[j] = static_cast<std::uint8_t>(out.size());
            k.from[j] = static_cast<std::uint32_t>(pool.size());
            pool.insert(pool.end(), out.begin(), out.end());
        }
    }
    return out;
}

const Field& StaticMap::make_ally_field() const {
    FuelMeter meter{"ally_spawn_field"};
    ally_field_ = make_field(blocked_for_us, ally_spawn);
    return *ally_field_;
}

const bitboard& StaticMap::make_foot() const {
    FuelMeter meter{"foot"};
    bitboard b;
    if (!ally_spawn_tiles.empty()) blocked_for_us.reachable_tiles_into(ally_spawn_tiles[0], unreachable, b);
    return foot_.emplace(std::move(b));
}

const bitboard& StaticMap::make_dash_foot() const {
    FuelMeter meter{"dash_foot"};
    bitboard b;
    if (!ally_spawn_tiles.empty()) dash_walls.reachable_tiles_into(ally_spawn_tiles[0], unreachable, b);
    return dash_foot_.emplace(std::move(b));
}

const bitboard& StaticMap::make_landing_dash_foot() const {
    FuelMeter meter{"dash_foot"};
    bitboard b;
    if (!ally_spawn_tiles.empty()) landing_dash_walls.reachable_tiles_into(ally_spawn_tiles[0], unreachable, b);
    return landing_dash_foot_.emplace(std::move(b));
}

// The region around `from`, if a crystal from foot lands in it.
void StaticMap::add_hop(vec2 from, int altar) const {
    static bitboard near_foot{cambc::uninitialized};
    static bool near_made = false;
    if (!near_made) square_dilate(foot(), teleport_crystal_range, near_foot), near_made = true;
    Hop hop;
    hop.altar = altar;
    blocked_for_us.reachable_tiles_into(from, unreachable, hop.pocket);
    and_into(hop.pocket, near_foot, hop.landings);
    drop(hop.landings, camp_tiles);
    if (hop.landings.is_empty()) return;
    square_dilate(hop.landings, teleport_crystal_range, hop.sources);
    hop.sources &= foot();
    drop(hop.sources, camp_tiles);
    hops_->push_back(std::move(hop));
}

const std::vector<StaticMap::Hop>& StaticMap::make_hops() const {
    FuelMeter meter{"hops"};
    auto& hops = hops_.emplace();
    if (ally_spawn_tiles.empty()) return hops;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        const auto& tributes = altars[a].tribute_tiles();
        if (!tributes.is_empty() && disjoint(tributes, foot())) add_hop(first_tile(tributes), a);
    }
    debug_block({ std::printf("HOPS %d\n", static_cast<int>(hops.size())); });
    return hops;
}

void StaticMap::add_group_hop(int g, bool off_theirs) const {
    const auto& G = groups[g];
    if (ally_spawn_tiles.empty() || G.has_monolith || G.gems + G.gold == 0 || !disjoint(G.tiles(), foot())) return;
    const auto& hops = *hops_;
    const vec2 t = first_tile(G.tiles());
    int h = 0;
    while (h < static_cast<int>(hops.size()) && !test(hops[h].pocket, t)) ++h;
    if (h == static_cast<int>(hops.size())) add_hop(t, -1);
    if (h == static_cast<int>(hops.size())) return;
    // Not into the enemy's walk: they come and go there at will, and no walk takes us out.
    if (off_theirs) {
        group_hops_[g] = h;
        return;
    }
    static bitboard theirs{cambc::uninitialized};
    static bool theirs_made = false;
    if (!theirs_made) {
        clear_board(theirs);
        if (const auto tiles = enemy_spawn.positions(); !tiles.empty()) blocked_for_them.reachable_tiles_into(tiles[0], unreachable, theirs);
        theirs_made = true;
    }
    if (disjoint(hops[h].pocket, theirs)) group_hops_[g] = h;
}

// A group gets a hop only with every camp tile off our walk and its region off the enemy's: with
// the draft's steps, a group whose centre (a camp tile) either spawn walks to has none, so most
// maps try none. The rest are tried in group order, as a loop over every group would. A region is
// walk-connected, so the enemy's steps to the centre say whether their walk enters it.
void StaticMap::list_hop_tried() const {
    if (hop_tried_listed_) return;
    hop_tried_listed_ = true;
    group_hops_.assign(groups.size(), -1), hop_rank_.assign(groups.size(), -1);
    auto& tried = hop_tried_;
    if (drafted()) {
        for (int g = 0; g < static_cast<int>(groups.size()); ++g)
            if (!groups[g].has_monolith && groups[g].gems + groups[g].gold > 0 && ally_steps(g) == unreachable && enemy_steps(g) == unreachable)
                tried.push_back(g);
    } else {
        static bitboard off{cambc::uninitialized};
        not_into(foot(), off);
        off &= camp_tiles;
        while (!board_empty(off)) {
            const int g = group_at(first_tile(off));
            tried.push_back(g);
            drop(off, groups[g].tiles());
        }
        std::sort(tried.begin(), tried.end());
    }
    for (int i = 0; i < static_cast<int>(tried.size()); ++i) hop_rank_[tried[i]] = i;
}

// On a map with islands, a flood of our walk and one of each island's region: up to ~150k on a
// turn when made at once (01islands).
void StaticMap::make_group_hops(int upto) const {
    list_hop_tried();
    upto = std::min(upto, static_cast<int>(hop_tried_.size()));
    if (hop_tried_.empty() || (foot_ && hops_ && hops_made_ >= upto)) return;
    FuelMeter meter{"group_hops"};
    foot();
    hops();
    for (; hops_made_ < upto; ++hops_made_) {
        add_group_hop(hop_tried_[hops_made_], drafted());
        if (group_hops_[hop_tried_[hops_made_]] >= 0) first_hop_rank_ = std::min(first_hop_rank_, hops_made_);
    }
}

int StaticMap::hops_readable() const {
    const int step = static_cast<int>(checked_round()) - static_cast<int>(built_round) - 1;
    if (step < 0) return -1;
    list_hop_tried();
    return std::min(step, static_cast<int>(hop_tried_.size()));
}

int StaticMap::group_hop(int group) const {
    const int n = hops_readable();
    if (n < 0) return -1;
    make_group_hops(n);
    return hop_rank_[group] >= 0 && hop_rank_[group] < n ? group_hops_[group] : -1;
}

bool StaticMap::any_group_hop() const {
    const int n = hops_readable();
    if (n < 0) return false;
    make_group_hops(n);
    return first_hop_rank_ < n;
}

const BushCluster& StaticMap::bush_cluster(vec2 p) const {
    for (;;) {
        if (const int i = cluster_of_[tile_index(p)]; i > 0) return bush_clusters_[i - 1];
        grow_cluster(p, 0);
    }
}

namespace {

// Bush runs, a row's maximal segments of bushes, in tile order. Union-find over runs that share an
// edge labels every cluster in one pass over the bushes; a host flood cost ~1.5k + 52 a chunk per
// cluster. One map per process.
namespace runs {
constexpr int max_runs = 100 * 100 / 2;
std::array<std::uint16_t, max_runs> starts, ends; // tile indices as cluster_of_'s, ends inclusive
std::array<std::uint16_t, max_runs> parent;       // a union-find forest; each root is its set's first run
std::array<std::uint16_t, max_runs> next;         // each set's runs in a ring, joined as sets unite
std::array<std::uint16_t, max_runs> runs_in, tiles_in; // per root, its set's runs and tiles
// The bushes row-major; the extra word is zero, so a run ends before the last word.
std::array<std::uint64_t, (100 * 100 + 63) / 64 + 1> linear;
// Per word, a run that only runs starting before the word precede.
std::array<std::uint16_t, (100 * 100 + 63) / 64 + 1> word_first;
// Where labelling stopped: the words in use (0 until exported), the word in `bits` and its bits
// not yet in runs, the last run's row, and the runs of that row and the one above.
struct State {
    int words = 0, word = 0;
    std::uint64_t bits = 0;
    int count = 0, row = -2, row_begin = 0, prev_begin = 0, prev_end = 0, prev_at = 0;
};
State state;
// The cluster being built, from its run `first`: its tiles until it joins bush_clusters_, then
// its cluster_of_ entries. `at` is the next run; first is -1 between clusters.
struct Build {
    int first = -1, at = 0;
    bool whole = false; // the fuel covers it in one pass, indexed as it goes
    std::optional<bitboard> tiles;
};
Build build;

// Labels the runs that start before word `limit`; true once every run is labelled.
bool label(int limit, int w) {
    State s = state; // locals, as globals would be stored at every change
    bool done = false;
    for (;;) {
        if (!s.bits) {
            if (s.word + 1 >= s.words) {
                done = true;
                break;
            }
            if (s.word + 1 >= limit) break;
            s.bits = linear[++s.word];
            word_first[s.word] = static_cast<std::uint16_t>(s.count);
            continue;
        }
        const int first = s.word * 64 + std::countr_zero(s.bits);
        const std::uint64_t past = s.bits + (s.bits & (~s.bits + 1)); // the run cleared, the bit after it set
        int end;
        if (past) {
            end = s.word * 64 + std::countr_zero(past) - 1;
            s.bits &= past;
        } else { // on into the next words
            do {
                s.bits = linear[++s.word];
                word_first[s.word] = static_cast<std::uint16_t>(s.count);
            } while (!~s.bits);
            end = s.word * 64 + std::countr_one(s.bits) - 1;
            s.bits &= s.bits + 1;
        }
        // A run of the bit stream, split at row ends.
        for (int y = first / w, last = y * w + w - 1, from = first;; from = last + 1, ++y, last += w) {
            const int to = std::min(end, last);
            if (y != s.row) {
                if (y == s.row + 1) s.prev_begin = s.row_begin, s.prev_end = s.count;
                else s.prev_begin = s.prev_end = s.count;
                s.row = y, s.row_begin = s.count, s.prev_at = s.prev_begin;
            }
            const auto n = static_cast<std::uint16_t>(s.count++);
            starts[n] = static_cast<std::uint16_t>(from), ends[n] = static_cast<std::uint16_t>(to);
            parent[n] = n, next[n] = n, runs_in[n] = 1, tiles_in[n] = static_cast<std::uint16_t>(to - from + 1);
            // Runs above share an edge if they overlap one row up.
            while (s.prev_at < s.prev_end && ends[s.prev_at] + w < from) ++s.prev_at;
            std::uint16_t root = n;
            for (int k = s.prev_at; k < s.prev_end && starts[k] + w <= to; ++k) {
                auto r = static_cast<std::uint16_t>(k);
                while (parent[r] != r) r = parent[r] = parent[parent[r]];
                if (r == root) continue;
                if (r < root) parent[root] = r, runs_in[r] += runs_in[root], tiles_in[r] += tiles_in[root], root = r;
                else parent[r] = root, runs_in[root] += runs_in[r], tiles_in[root] += tiles_in[r];
                std::swap(next[n], next[k]); // splices the two rings
            }
            if (to == end) break;
        }
    }
    state = s;
    return done;
}

// The run holding tile `at`, a bush, once every run is labelled.
int run_at(int at) {
    int i = word_first[at >> 6];
    while (i < state.count && starts[i] <= at) ++i;
    return i - 1;
}

// Above the fuel to build run i's cluster in one pass: ~200 a run and ~8 a tile.
std::uint64_t build_cost(int i) {
    while (parent[i] != i) i = parent[i];
    return 200u * runs_in[i] + 8u * tiles_in[i];
}

} // namespace runs

} // namespace

[[gnu::flatten, gnu::noinline]] const BushCluster* StaticMap::grow_cluster(vec2 p, std::uint64_t fuel_floor) const {
    FuelMeter meter{"bush_cluster"};
    const auto afford = [&](std::uint64_t cost) { return fuel_floor == 0 || fuel_ok(fuel_floor + cost); };
    // Steps of `cost` the fuel above the floor covers.
    const auto steps = [&](std::uint64_t cost) { return fuel_floor == 0 ? 1 << 20 : static_cast<int>((fuel() - fuel_floor) / cost); };
    // A word holds at most 32 runs, ~250 fuel each to label; a run is at most a row, under ~1.5k to
    // add to a board or index.
    constexpr std::uint64_t word_cost = 32 * 250, run_cost = 1500;
    const int w = width;
    auto& state = runs::state;
    if (!state.words) {
        if (!afford(small_cost_estimate)) return nullptr;
        const int tiles = w * height;
        ok(cambc::detail::sdk_Bitboard_ExportLinearBuffer(bushes.ptr(), reinterpret_cast<std::uint8_t*>(runs::linear.data()),
                                                          bitboard::linear_buffer_size()));
        if (tiles & 63) runs::linear[tiles >> 6] &= (std::uint64_t{1} << (tiles & 63)) - 1;
        state.words = (tiles >> 6) + 1;
        state.bits = runs::linear[0];
    }
    // A batch labels the current word's rest and fewer than `steps` more words.
    for (bool done = state.word + 1 >= state.words && !state.bits; !done;) {
        if (!afford(2 * word_cost)) return nullptr;
        done = runs::label(state.word + steps(word_cost), w);
    }
    auto& b = runs::build;
    if (b.first < 0) {
        if (!afford(small_cost_estimate)) return nullptr;
        b.first = b.at = runs::run_at(tile_index(p));
        b.tiles.emplace();
        b.whole = afford(runs::build_cost(b.first));
    }
    // Bits set in the boards' storage: a host call per tile costs more. Vectorised loops cost
    // more than these few iterations.
    const auto stride = cambc::detail::layout().chunk_stride;
    // Into both boards, which may be the same.
    const auto add_run = [&](int i, std::uint64_t* board, std::uint64_t* also) {
        const int s = runs::starts[i], e = runs::ends[i], y = s / w, a = s - y * w, z = a + (e - s);
        const auto row = static_cast<std::size_t>(y >> 3) * stride;
        const int shift = (y & 7) * 8;
        const int last = z >> 3;
        std::uint32_t mask = (0xffu << (a & 7)) & 0xffu;
#pragma clang loop vectorize(disable) unroll(disable)
        for (int cx = a >> 3;; ++cx, mask = 0xffu) {
            if (cx == last) mask &= 0xffu >> (7 - (z & 7));
            const auto bits = static_cast<std::uint64_t>(mask) << shift;
            board[row + cx] |= bits;
            also[row + cx] |= bits;
            if (cx == last) break;
        }
    };
    const auto index_run = [&](int i, std::uint16_t index) {
#pragma clang loop vectorize(disable) unroll(disable)
        for (int t = runs::starts[i]; t <= runs::ends[i]; ++t) cluster_of_[t] = index;
    };
    if (b.whole) {
        const auto index = static_cast<std::uint16_t>(bush_clusters_.size() + 1);
        do {
            add_run(b.at, b.tiles->ptr(), clustered_.ptr());
            index_run(b.at, index);
            b.at = runs::next[b.at];
        } while (b.at != b.first);
        bush_clusters_.push_back(BushCluster{std::move(*b.tiles)});
        b.tiles.reset();
        b.first = -1;
        return &bush_clusters_.back();
    }
    // Else its tiles and then their index, a batch the fuel covers at a time. f on the ring's runs
    // from b.at; true once round.
    const auto each_run = [&](auto&& f) {
        for (;;) {
            if (!afford(run_cost)) return false;
            for (int n = steps(run_cost); n > 0; --n) {
                f(b.at);
                b.at = runs::next[b.at];
                if (b.at == b.first) return true;
            }
        }
    };
    if (b.tiles) {
        if (!each_run([&](int i) { add_run(i, b.tiles->ptr(), b.tiles->ptr()); })) return nullptr;
        bush_clusters_.push_back(BushCluster{std::move(*b.tiles)});
        b.tiles.reset();
    }
    // The cluster is complete before any tile points at it; bush_cluster() reads only those.
    const auto index = static_cast<std::uint16_t>(bush_clusters_.size());
    if (!each_run([&](int i) { add_run(i, clustered_.ptr(), clustered_.ptr()), index_run(i, index); })) return nullptr;
    b.first = -1;
    return &bush_clusters_.back();
}

bool StaticMap::find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized}, rest{cambc::uninitialized};
    not_into(clustered_, left);
    left &= within(bushes, p, radius);
    while (!left.is_empty()) {
        const auto* c = grow_cluster(first_tile(left), fuel_floor);
        if (!c) return false;
        not_into(c->tiles, rest);
        left &= rest;
    }
    return true;
}

bool StaticMap::find_bush_clusters(const bitboard& tiles, std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized}, rest{cambc::uninitialized};
    not_into(clustered_, left);
    left &= tiles;
    left &= bushes;
    while (!left.is_empty()) {
        const auto* c = grow_cluster(first_tile(left), fuel_floor);
        if (!c) return false;
        not_into(c->tiles, rest);
        left &= rest;
    }
    return true;
}

bool StaticMap::find_all_bush_clusters(std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized};
    for (;;) {
        not_into(clustered_, left);
        left &= bushes;
        if (left.is_empty()) return true;
        if (!grow_cluster(first_tile(left), fuel_floor)) return false;
    }
}

const bitboard& StaticMap::make_near_bushes() const {
    bitboard b{cambc::uninitialized};
    square_dilate(bushes, ward_range(), b);
    return near_bushes_.emplace(std::move(b));
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
    if (test(bushes, p)) {
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

[[gnu::flatten]] bool StaticMap::warm_up(std::uint64_t fuel_floor) const {
    const auto round = cambc::round_number();
    const auto afford = [&](std::uint64_t cost) { return cambc::round_number() == round && fuel_ok(fuel_floor + cost); };
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
    for (const auto& g : groups) {
        if (!afford(small_cost_estimate)) return false;
        g.adjacent();
        g.threat();
    }
    if (!foot_ && !afford(field)) return false;
    foot();
    if (!hops_ && !afford(field)) return false;
    hops();
    list_hop_tried();
    for (; hops_made_ < static_cast<int>(hop_tried_.size()); make_group_hops(hops_made_ + 1))
        if (!afford(field)) return false;
    return true;
}

std::uint16_t StaticMap::fixed_step(int which, int group) const {
    auto& kept = (which == 0 ? drafted_.ally : which == 1 ? drafted_.enemy : drafted_.altar)[group];
    if (kept != pending_step) return kept;
    const vec2 c = groups[group].centre;
    int mirror_ally = 0;
    if (which == 1 && header_.mirrored) {
        const int m = group_at(mirror(c));
        if (m < 0) return kept = unreachable;
        mirror_ally = fixed_step(0, m);
    } else if (which == 1 && !enemy_box_known_) {
        enemy_box_ = TileBox::of(enemy_spawn.positions()), enemy_box_known_ = true;
    }
    return kept = index_steps(index_code(*plan_, index_, which, group), which, header_.mirrored, drafted_.spawn, enemy_box_, c, mirror_ally);
}

void StaticMap::fixed_steps(int which) const {
    auto& kept = which == 0 ? drafted_.ally : which == 1 ? drafted_.enemy : drafted_.altar;
    if (which == 1 && !header_.mirrored && !enemy_box_known_) enemy_box_ = TileBox::of(enemy_spawn.positions()), enemy_box_known_ = true;
    const int w = index_.width[which];
    PlanReader bits{*plan_, index_.codes_at[which]};
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto code = bits.get(w);
        if (kept[g] != pending_step) continue;
        const vec2 c = groups[g].centre;
        int mirror_ally = 0;
        if (which == 1 && header_.mirrored) {
            const int m = group_at(mirror(c));
            if (m < 0) {
                kept[g] = unreachable;
                continue;
            }
            mirror_ally = fixed_step(0, m);
        }
        kept[g] = index_steps(code, which, header_.mirrored, drafted_.spawn, enemy_box_, c, mirror_ally);
    }
}

void StaticMap::warm_drafted_steps(std::uint64_t fuel_floor) const {
    if (!index_.steps) return;
    // A pass costs up to ~200 a group: one kind a check.
    for (int which = 1; which <= 2; ++which) {
        if (steps_warm_ >> which & 1) continue;
        if (!fuel_ok(fuel_floor + 250 * groups.size() + small_cost_estimate)) return;
        fixed_steps(which);
        steps_warm_ |= static_cast<std::uint8_t>(1u << which);
    }
}

int StaticMap::ally_steps(int group) const {
    return plan_ ? (index_.steps ? fixed_step(0, group) : drafted_.ally[group]) : from_ally_spawn().at(groups[group].centre);
}

int StaticMap::enemy_steps(int group) const {
    if (!plan_) return enemy_spawn_steps(groups[group].centre);
    if (index_.steps) return fixed_step(1, group);
    if (drafted_.enemy.empty()) decode_enemy_steps(*plan_, header_, *this, drafted_);
    return drafted_.enemy[group];
}

int StaticMap::enemy_steps_of(int group) const {
    if (plan_ && drafted_.enemy.empty())
        if (const int steps = mirrored_enemy_steps(*plan_, header_, *this, drafted_, group); steps >= 0) return steps;
    return enemy_steps(group);
}

void StaticMap::warm_enemy_steps(std::uint64_t fuel_floor) const {
    // ~150 fuel a group.
    if (plan_ && drafted_.enemy.empty() && fuel_ok(fuel_floor + 300 * groups.size() + small_cost_estimate))
        decode_enemy_steps(*plan_, header_, *this, drafted_);
}

std::optional<int> StaticMap::drafted_altar_steps(int group) const {
    if (!plan_) return std::nullopt;
    return index_.steps ? fixed_step(2, group) : drafted_.altar[group];
}

std::optional<int> StaticMap::drafted_spawn_steps(vec2 tile, int group) const {
    if (!spawn_steps_drafted()) return std::nullopt;
    // The tile's spawn index, -1 off spawn, kept for the tile last asked: farm asks for every group.
    static vec2 asked{-1, -1};
    static int i = -1;
    if (tile != asked) {
        i = test(ally_spawn, tile) ? static_cast<int>(std::find(ally_spawn_tiles.begin(), ally_spawn_tiles.end(), tile) - ally_spawn_tiles.begin()) : -1;
        asked = tile;
    }
    if (i < 0) return std::nullopt;
    const int base = index_.steps ? fixed_step(0, group) : drafted_.ally[group];
    if (base == unreachable) return base;
    if (drafted_.predicted[group]) return base + spawn_offset(drafted_.spawn, tile, groups[group].centre);
    return base + static_cast<int>(drafted_.offsets[group] >> (2 * i) & 3);
}

void StaticMap::decode_dash_steps(int body, int kind) const {
    dash_for_ = body;
    dash_steps_.clear();
    std::array<DashEntry, DraftPlan::lead_bodies> entries;
    if (kind == 0 || !plan_ || body < 0 || body >= DraftPlan::lead_bodies || !index_dash_steps(*plan_, header_, static_cast<int>(groups.size()), entries))
        return;
    const auto& e = entries[body];
    if (e.kind != kind || e.tile < 0 || e.tile >= static_cast<int>(ally_spawn_tiles.size())) return;
    dash_tile_ = ally_spawn_tiles[e.tile];
    PlanReader bits{*plan_, e.at};
    dash_steps_.resize(groups.size());
    for (std::size_t g = 0; g < groups.size(); ++g) {
        const auto code = static_cast<int>(bits.get_rice(e.rice));
        dash_steps_[g] = code == 0 ? unreachable : code - 1 + dist(dash_tile_, groups[g].centre);
    }
}

bool StaticMap::attack_tiles_drafted(int group, int range) const {
    return plan_ && group < header_.attack_groups
           && std::find(DraftPlan::attack_ranges.begin(), DraftPlan::attack_ranges.end(), range) != DraftPlan::attack_ranges.end();
}

const bitboard& StaticMap::open_bushes() const {
    if (!open_bushes_) and_into(bushes, open_for_us, open_bushes_.emplace(cambc::uninitialized));
    return *open_bushes_;
}

bitboard StaticMap::sight_off_bushes(vec2 p, int radius) const {
    if (!open_off_bushes_) xor_into(open_for_us, open_bushes(), open_off_bushes_.emplace(cambc::uninitialized));
    bitboard out{cambc::uninitialized};
    // From a bush, only its own cluster sees it.
    if (test(bushes, p)) {
        clear_board(out);
        return out;
    }
    walls_and_bushes.shadow_cast_into(p, static_cast<std::uint16_t>(radius), out);
    and_into(out, *open_off_bushes_, out);
    return out;
}

// Counting each flagged member's bush bits is the cost, so groups are indexed only as far as asked:
// with checkpoints, only the asked group's block of PlanIndex::block groups.
void StaticMap::index_attack_tiles(int group) const {
    if (attack_first_.empty()) {
        int members = 0;
        attack_first_.reserve(groups.size() + 1);
        for (const auto& g : groups) attack_first_.push_back(members), members += static_cast<int>(g.members.size());
        attack_first_.push_back(members);
        attack_bit_.assign(attack_first_[header_.attack_groups], -1);
        attack_next_bit_ = drafted_.end + members;
    }
    int from = attack_indexed_, to = group + 1, at = attack_next_bit_;
    if (index_.checkpoints) {
        const int block = group / PlanIndex::block;
        attack_blocks_ |= 1u << block;
        from = block * PlanIndex::block, to = std::min<int>(from + PlanIndex::block, header_.attack_groups);
        at = drafted_.end + attack_first_.back() + index_checkpoint(*plan_, index_, block);
    }
    const int start = attack_first_[from], end = attack_first_[to];
    PlanReader flags{*plan_, drafted_.end + start};
    int g = from;
    for (int i = start; i < end; i += 32)
        for (auto w = flags.get(std::min(32, end - i)); w; w &= w - 1) {
            const int m = i + __builtin_ctz(w);
            while (attack_first_[g + 1] <= m) ++g;
            attack_bit_[m] = at;
            at += count_in_small_square<DraftPlan::bush_range>(open_bushes(), groups[g].members[m - attack_first_[g]].pos);
        }
    if (index_.checkpoints) return;
    attack_next_bit_ = at;
    attack_indexed_ = group + 1;
}

const std::vector<std::uint8_t>* StaticMap::nearest_groups(int group) const {
    const int n = static_cast<int>(groups.size());
    if (n > 256) return nullptr;
    if (nearest_.empty()) nearest_.resize(n);
    auto& order = nearest_[group];
    if (!order.empty()) return &order;
    // By counting: Chebyshev distances on a map are under 100.
    const vec2 from = groups[group].centre;
    std::array<std::uint8_t, 256> d;
    std::array<std::uint16_t, 102> at{};
    int far = 0;
    for (int g = 0; g < n; ++g) {
        if (g == group) continue;
        const int r = dist(from, groups[g].centre);
        d[g] = static_cast<std::uint8_t>(r);
        ++at[r + 2];
        far = std::max(far, r);
    }
    at[1] = 1; // `group` itself first
    for (int i = 2; i <= far + 1; ++i) at[i] += at[i - 1];
    order.resize(n);
    order[0] = static_cast<std::uint8_t>(group);
    for (int g = 0; g < n; ++g)
        if (g != group) order[at[d[g] + 1]++] = static_cast<std::uint8_t>(g);
    return &order;
}

bitboard StaticMap::drafted_attack_tiles(int group, int member, int range) const {
    if (index_.checkpoints ? !(attack_blocks_ >> (group / PlanIndex::block) & 1) : group >= attack_indexed_) index_attack_tiles(group);
    const vec2 p = groups[group].members[member].pos;
    auto tiles = sight_off_bushes(p, range);
    const int at = attack_bit_[attack_first_[group] + member];
    if (at < 0) return tiles;
    PlanReader bits{*plan_, at};
    std::uint64_t* words = tiles.ptr();
    const auto stride = cambc::detail::layout().chunk_stride;
    each_in_square(open_bushes(), p, DraftPlan::bush_range, [&](vec2 t) {
        if (bits.get(1) && dist(t, p) <= range) words[(t.y >> 3) * stride + (t.x >> 3)] |= std::uint64_t{1} << ((t.y & 7) * 8 + (t.x & 7));
    });
    return tiles;
}

vec2 StaticMap::drafted_ward(int site) const {
    if (!plan_ || header_.wards_at == 0) return {-1, -1};
    if (site != ward_site_) ward_tile_ = aph::drafted_ward(*plan_, header_, *this, site), ward_site_ = site;
    return ward_tile_;
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
        lock_ = square(pos, altar_lock_range);
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
        static bitboard excluded{cambc::uninitialized};
        bitboard b;
        for (const auto& m : members) b.draw_chebyshev(m.pos, 1);
        or_into(tiles(), map_->blocked_for_us, excluded);
        drop(b, excluded);
        adjacent_ = std::move(b);
    }
    return *adjacent_;
}

int CampGroup::threat_radius() const {
    if (threat_radius_ < 0) {
        threat_radius_ = 0;
        for (const auto& m : members) threat_radius_ = std::max(threat_radius_, dist(m.pos, centre) + m.reach);
    }
    return threat_radius_;
}

const bitboard& CampGroup::threat() const {
    if (!threat_) {
        bitboard b;
        for (const auto& m : members) b.draw_chebyshev(m.pos, m.reach);
        threat_ = std::move(b);
    }
    return *threat_;
}


namespace {

void find_crossings(StaticMap& s) {
    bitboard t{cambc::uninitialized}, ahead{cambc::uninitialized}, behind{cambc::uninitialized};
    const auto opposite = [&](int dx, int dy) {
        s.standable.shift_right_into(-dx, t);
        t.shift_up_into(-dy, ahead);
        s.standable.shift_right_into(dx, t);
        t.shift_up_into(dy, behind);
        ahead &= behind;
        s.crossable |= ahead;
    };
    opposite(1, 0);
    opposite(0, 1);
    opposite(1, 1);
    opposite(1, -1);
    or_into(s.holes, s.altar_tiles, t);
    s.crossable &= t;
    // No two may touch, or a field would walk along the line, which no dash does: keep every other
    // tile ((x + y) even), and of diagonal neighbours, which share that parity, the one on an even
    // row. Ties broken by height would chain: a diagonal run would keep only its lowest tile.
    // Both masks are written straight into the boards' 8x8 chunks, which start on even rows and
    // columns: (x + y) even is 0x55 on even rows and 0xAA on odd ones; odd rows are 0xFF.
    const auto words = bitboard::raw_buffer_size() / sizeof(std::uint64_t);
    bitboard even{cambc::uninitialized}, beside{cambc::uninitialized};
    std::fill_n(even.ptr(), words, 0xAA55AA55AA55AA55ull);
    clear_board(beside);
    for (const int d : {1, -1}) {
        s.crossable.shift_right_into(d, t);
        beside |= t;
        s.crossable.shift_up_into(d, t);
        beside |= t;
    }
    beside &= s.crossable;
    drop(beside, even);
    drop(s.crossable, beside);
    bitboard odd_rows{cambc::uninitialized};
    std::fill_n(odd_rows.ptr(), words, 0xFF00FF00FF00FF00ull);
    clear_board(beside);
    for (const int dx : {1, -1})
        for (const int dy : {1, -1}) {
            s.crossable.shift_right_into(dx, t);
            t.shift_up_into(dy, ahead);
            beside |= ahead;
        }
    beside &= odd_rows;
    drop(s.crossable, beside);
    copy_into(s.blocked_for_us, s.dash_walls);
    drop(s.dash_walls, s.crossable);
    square_dilate(s.crossable, 1, s.near_crossable);
    clear_board(t);
    for (const auto& g : s.groups)
        if (g.strength > 0)
            for (const auto& m : g.members) set_tile(t, m.pos);
    square_dilate(t, 2, ahead);
    and_into(s.crossable, ahead, behind);
    or_into(s.dash_walls, behind, s.landing_dash_walls);
}

} // namespace

[[gnu::flatten]] std::unique_ptr<StaticMap> StaticMap::build() {
    FuelMeter meter{"build_static"};
    std::optional<FuelMeter> part{std::in_place, "static_new"};
    auto s = std::make_unique<StaticMap>();
    part.reset(), part.emplace("static_boards");
    s->built_round = checked_round();
    s->width = cambc::map::width();
    s->height = cambc::map::height();
    s->symmetry = cambc::map::symmetry();
    s->team_a = cambc::detail::sdk_my_team() == 0;

    s->ally_spawn_tiles = s->ally_spawn.positions();
    const auto enemy_spawn_tiles = s->enemy_spawn.positions();
    const auto tile = [](vec2 p) { return p; };
    s->ally_spawn_centre = central_tile(s->ally_spawn_tiles, tile);
    // A's order by rows from (minX, minY); B's is its mirror image, so sorted by the mirror tile.
    s->landing_tiles = s->ally_spawn_tiles;
    std::sort(s->landing_tiles.begin(), s->landing_tiles.end(), [&](vec2 a, vec2 b) {
        if (!s->team_a) a = s->mirror(a), b = s->mirror(b);
        return a.y != b.y ? a.y < b.y : a.x < b.x;
    });
    s->enemy_spawn_centre = central_tile(enemy_spawn_tiles, tile);

    or_into(s->walls, s->holes, s->impassable);
    s->impassable |= s->altar_tiles;
    not_into(s->impassable, s->passable);
    or_into(s->impassable, s->enemy_spawn, s->blocked_for_us);
    or_into(s->impassable, s->ally_spawn, s->blocked_for_them);
    not_into(s->blocked_for_us, s->open_for_us);
    not_into(s->blocked_for_them, s->open_for_them);
    for (auto t : enemy_spawn_tiles) draw_square(s->near_enemy_spawn, t, 1);
    or_into(s->walls, s->bushes, s->walls_and_bushes);

    part.reset(), part.emplace("static_camps");
    const auto altar_positions = s->altar_tiles.positions();
    s->altars.resize(altar_positions.size());
    for (std::size_t i = 0; i < altar_positions.size(); ++i) {
        s->altars[i].pos = altar_positions[i];
        s->altars[i].map_ = s.get();
        s->altar_lookup_[tile_index(altar_positions[i])] = static_cast<std::uint16_t>(i + 1);
    }

    // Camp groups, through the raw imports. Member stats come from the camp designs, read once
    // per camp type.
    // A group's sums are kept in locals and its centre found here: written through the group and
    // the map pointer, with central_tile's vectorised loops, the loop cost ~200 fuel a member.
    namespace raw = cambc::detail;
    using Stats = decltype(raw::camp_design::base_stats);
    Unwritten<Stats, 32> design;
    std::uint32_t designed = 0; // bit t: design.a[t] read
    const auto layout = engine::camp_layout();
    const std::uint32_t* const words = layout.data();
    const std::size_t word_count = layout.size();
    StaticMap& map = *s;
    std::size_t group_count = 0;
    std::size_t member_count = 0;
    for (std::size_t i = 0; i + 5 <= word_count; i += 5 + 4 * words[i + 4]) ++group_count, member_count += words[i + 4];
    StaticArray<CampMember> member_pool(member_count);
    std::size_t members_used = 0;
    map.groups.reserve(group_count);
    int max_reach = 0;
    for (std::size_t i = 0; i + 5 <= word_count;) {
        const auto lookup = static_cast<std::uint16_t>(map.groups.size() + 1);
        auto& g = map.groups.emplace_back();
        g.handle = words[i];
        g.map_ = &map;
        g.gold = static_cast<int>(words[i + 1]);
        g.gems = static_cast<int>(words[i + 2]);
        g.respawn = static_cast<std::int32_t>(words[i + 3]);
        const auto size = words[i + 4];
        i += 5;
        g.members = StaticArray<CampMember>(member_pool, members_used, std::min<std::size_t>(size, (word_count - i) / 4));
        CampMember* const out = g.members.data();
        float strength = 0, health = 0;
        int reach = 0, cluster_gems = 0, cluster_gold = 0;
        bool monolith = false;
        long sx = 0, sy = 0;
        for (std::uint32_t m = 0; m < size && i + 4 <= word_count; ++m, i += 4) {
            const auto raw_type = words[i + 1];
            Stats read;
            Stats* const stats = raw_type < 32 ? &design.a[raw_type] : &read;
            if (raw_type >= 32 || !(designed >> raw_type & 1)) {
                raw::camp_design d{};
                raw::check(raw::sdk_camp_design(raw_type, &d));
                *stats = d.base_stats;
                if (raw_type < 32) designed |= 1u << raw_type;
            }
            const auto type = static_cast<cambc::camp_type>(raw_type);
            const vec2 pos{static_cast<std::int32_t>(words[i + 2]), static_cast<std::int32_t>(words[i + 3])};
            out[m] = {words[i], pos, type, stats->base_health, stats->base_strength, stats->base_attack_range};
            strength += stats->base_strength;
            health += stats->base_health;
            reach = std::max(reach, stats->base_attack_range);
            monolith |= type == cambc::camp_type::monolith;
            if (type == cambc::camp_type::gem_cluster) cluster_gems += gem_cluster_gems;
            if (type == cambc::camp_type::gold_cluster) cluster_gold += gold_cluster_gold;
            sx += pos.x, sy += pos.y;
            set_tile(map.camp_tiles, pos);
            map.group_lookup_[pos.x + pos.y * map.width] = lookup;
        }
        g.strength = strength;
        g.health = health;
        g.reach = reach;
        g.has_monolith = monolith;
        g.cluster_gems = cluster_gems;
        g.cluster_gold = cluster_gold;
        max_reach = std::max(max_reach, reach);
        // central_tile: the first member nearest the members' mean.
        const auto* const member = g.members.data();
        const auto n = static_cast<long>(g.members.size());
        if (n > 0) g.centre = member[0].pos;
        if (n > 1) {
            const vec2 mean{static_cast<int>(sx / n), static_cast<int>(sy / n)};
            int nearest = 1 << 30;
#pragma clang loop vectorize(disable)
            for (long k = 0; k < n; ++k) {
                const int dx = member[k].pos.x - mean.x, dy = member[k].pos.y - mean.y;
                if (const int d = dx * dx + dy * dy; d < nearest) nearest = d, g.centre = member[k].pos;
            }
        }
    }
    map.max_camp_reach = max_reach;
    debug_block({
        if (max_reach > max_camp_range) std::printf("CAMP-REACH %d above max_camp_range\n", max_reach);
    });
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
    part.reset(), part.emplace("crossings");
    // Only a dash reads the crossings (~13k of board ops): a champion without one leaves them unbuilt.
    if (cambc::is_draft() || facts(engine::type(static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(cambc::self())))).has_dash())
        find_crossings(*s);
    part.reset();

    if (const auto* plan = read_draft_plan(); plan && !s->ally_spawn_tiles.empty()) {
        const auto header = PlanHeader::read(*plan);
        const int n = static_cast<int>(s->groups.size()), spawn = static_cast<int>(s->ally_spawn_tiles.size());
        PlanIndex index;
        const bool indexed = header.check == plan_check(*s) && read_index(*plan, header, n, spawn, index);
        // Fixed steps are read on first ask: only the spawn offsets now.
        const auto fixed = [&] {
            auto& d = s->drafted_;
            d.spawn = TileBox::of(s->ally_spawn_tiles);
            d.ally.assign(n, pending_step), d.enemy.assign(n, pending_step), d.altar.assign(n, pending_step);
            if (header.spawn_offsets) index_offsets(*plan, index, n, spawn, d);
            else d.offsets.assign(n, 0), d.predicted.assign(n, 0);
            d.end = index.steps_end;
            return true;
        };
        if (header.check == plan_check(*s) && header.steps
            && (!header.spawn_offsets || s->ally_spawn_tiles.size() <= DraftPlan::max_spawn_tiles)
            && (indexed && index.steps ? fixed() : decode_steps(*plan, header, *s, s->drafted_, false))) {
            if (indexed) s->index_ = index;
            s->plan_ = plan;
            s->header_ = header;
            if (indexed && index.steps) s->fixed_steps(0);
            max_field_layers() = std::max<int>(max_field_layers(), header.field_layers);
        }
    }
    return s;
}

[[gnu::flatten]] void World::init_beliefs() {
    FuelMeter meter{"init_beliefs"};
    const auto& s = map();
    const auto self_handle = static_cast<cambc::handle_champion_t>(cambc::self());

    for (const auto side : {team::ally, team::enemy}) {
        auto& list = side == team::ally ? allies : enemies;
        engine::Handles handles;
        const int n = engine::handles(side, handles);
        list.reserve(n);
        for (int i = 0; i < n; ++i) {
            auto& b = side == team::ally ? list.emplace_back(ChampionBelief::Ally{}) : list.emplace_back();
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
            if (side == team::enemy || b.is_self) b.shield_slot = static_cast<std::int8_t>(b.facts().slot_of(AbilityKind::shield));
            if (side == team::enemy) fix_at_spawn(b, s.enemy_spawn, {1, -1});
            if (b.is_self) self_index = i;
            if (i < 16) b.rank = b.next_rank = i; // rank_turns' answer while every priority is 0
        }
    }
    me_ = allies.data() + self_index;
    ally_count_ = static_cast<int>(allies.size());
    enemy_count_ = static_cast<int>(enemies.size());
    team_a_ = s.team_a;

    for (auto& order : turn_order_)
        for (int i = 0; i < 16; ++i) order[i] = static_cast<std::uint8_t>(i);
    // The first update keeps these as last round's ranks: with every priority 0 and the orders by
    // index, rank_turns would leave each rank its index (set above).
    ranks_stale_ = false;
    ranked_round_ = round;
    camps.clear();
    camps.resize(s.groups.size());
    std::size_t member_count = 0, health_used = 0, rounds_used = 0;
    for (const auto& G : s.groups) member_count += G.members.size();
    StaticArray<float> health_pool(member_count);
    StaticArray<int> rounds_pool(member_count);
    for (std::size_t g = 0; g < s.groups.size(); ++g) {
        const auto& members = s.groups[g].members;
        auto& c = camps[g];
        c.health = StaticArray<float>(health_pool, health_used, members.size());
        c.health_round = StaticArray<int>(rounds_pool, rounds_used, members.size());
        for (std::size_t i = 0; i < members.size(); ++i) c.health[i] = members[i].max_health, c.health_round[i] = 0;
    }
    altars.assign(s.altars.size(), AltarBelief{});
    stirring_.assign((s.groups.size() + 63) / 64, 0);
    cleared_.assign((s.groups.size() + 63) / 64, 0);
    respawning_.assign((s.groups.size() + 63) / 64, 0);
}

void World::update() {
    priority_start_enemies.count = 0;
    round = static_cast<int>(checked_round());
    turn_round() = static_cast<std::uint32_t>(round);
    // First turn; a failure part-way is retried next turn from scratch.
    if (!ready()) {
        first_round = round;
        if (!static_) static_ = StaticMap::build();
        allies.clear();
        enemies.clear();
        try {
            init_beliefs();
        } catch (...) {
            // ready() reads the ally list, filled first: empty it so the next turn starts over.
            allies.clear();
            enemies.clear();
            throw;
        }
    }
    FuelMeter meter{"update"};
    ++observations;
    read_vision();
    const auto tributing = tributing_enemies(); // before update_champions ends their channels
    guard("priorities", [&] { read_priorities(updated_round_ != round); });
    updated_round_ = round;
    if (ranks_stale_) rank_turns();
    update_champions(true);
    sight_pos_ = clear_pos_ = me().pos;
    // Visible champions that have acted come before us and those that have not after us, which
    // bounds our slot; a visible enemy's modelled order against ours should match its flag.
    debug_block({
        int lo = 0, hi = ally_count_ + enemy_count_ - 1, wrong = 0, seen = 0;
        for (const auto* team : {&allies, &enemies})
            for (const auto& c : *team)
                if (!c.is_self && c.alive && c.visible) c.acted ? ++lo : --hi;
        for (const auto& e : enemies)
            if (e.alive && e.visible) ++seen, wrong += (slot(e, round) < slot(me(), round)) != e.acted;
        std::printf("SLOT %d %u %d %d %d %d %d\n", round, static_cast<std::uint32_t>(me().handle), slot(me(), round), lo, hi,
                    seen, wrong);
    });
    guard("camps", [&] { update_camps(); });
    guard("altars", [&] { update_altars(); });
    guard("scores", [&] { update_scores(tributing); });
}

[[gnu::flatten]] void World::observe() {
    FuelMeter meter{"observe"};
    ++observations;
    read_vision();
    update_champions(false);
    sight_pos_ = clear_pos_ = my_position();
}

bool World::read_stuns() {
    const auto& f = me().facts();
    // Ren's reflection may have killed us this turn.
    if (stuns_read_ == round || !me().alive || (f.stun_reach(0) < 0 && f.stun_reach(1) < 0) || !is_alive(me().handle)) return false;
    int reach = -1;
    for (int s = 0; s < 2; ++s)
        // Marcella's stun is the attack after her reset.
        if (const int r = f.stun_reach(s); r >= 0 && my_cooldown(s) >= ability_cooldown
                                           && (f.abilities[s].kind != AbilityKind::attack_reset || !my_can_attack()))
            reach = std::max(reach, r);
    if (reach < 0) return false;
    stuns_read_ = round;
    // A walk may follow a cast that does not exclude it.
    const vec2 here = my_position();
    bool changed = false;
    for (auto& e : enemies) {
        if (!e.alive || !e.visible || e.stun_pending || e.facts().passive == Passive::stun_immune || dist(here, e.pos) > reach + 1) continue;
        // Not stun_pending(): one we killed has no buffs to read, and a thrown error costs ~3.9k.
        static std::array<cambc::detail::buff_data, static_cast<std::size_t>(cambc::buff_types::count)> buffs;
        std::uint32_t n = 0;
        if (cambc::detail::sdk_champion_buff_data(static_cast<std::uint32_t>(e.handle), buffs.data(), static_cast<std::uint32_t>(buffs.size()), &n) != 0) continue;
        for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
            if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::stun) && buffs[i].data.stun.duration > 0) e.stun_pending = changed = true;
    }
    return changed;
}

namespace {

// An enemy shielder's or our own active shield, read only while the cast is recent enough. Shield
// and cooldown tick together, so it has cd - (8 - duration) turn ends left, and at 0 it still
// absorbs until its owner's next turn start.
[[gnu::noinline]] void read_shield(ChampionBelief& b, const std::array<int, 2>& cds) {
    b.shield = 0, b.shield_turns = 0;
    if (cds[b.shield_slot] >= ability_cooldown - b.facts().abilities[b.shield_slot].duration)
        std::tie(b.shield, b.shield_turns) = engine::shield(engine::id(b.handle));
}

} // namespace

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
    enemy_seen_known_ = false;
    const auto& s = map();
    const auto h = engine::id(b.handle);
    const int round = this->round;
    const bool enemy = b.side == team::enemy;
    const auto spawn = [&] { return enemy ? s.enemy_spawn_centre : s.ally_spawn_centre; };

    // A champion in view is alive: liveness is read only for one out of view.
    const auto* info = engine::champion(h);
    const auto state = cambc::champion_state::from_bits_retain(info ? static_cast<std::uint32_t>(info->state) : 0u);
    const bool acted = info && !b.is_self && state.contains(cambc::champion_state::completed_turn);
    // Mid-turn, an enemy seen this turn and now out of sight may be one we killed.
    if (full || (enemy && !info && b.alive && b.visible)) {
        const bool alive_now = info || engine::alive(h);
        if (!alive_now) {
            if (b.alive) {
                // Died since our last turn: in round-1 after our turn, or this round before it.
                // Death in round D respawns in D+61, or D+60 if it died before its own turn.
                b.respawn_earliest = (full ? round - 1 : round) + cambc::constants::respawn_time;
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
            // ours, or one whose turn came before ours in both rounds, is surely this round's; one in
            // view yet to act this round respawned at an earlier turn start.
            b.alive = true;
            b.respawn_earliest = b.respawn_latest = -1;
            const bool before_us = info ? acted && slot(b, round - 1) < slot(me(), round - 1)
                                        : slot(b, round) < slot(me(), round) && slot(b, round - 1) < slot(me(), round - 1);
            b.respawned_round = b.is_self || before_us ? round : round - 1;
            b.pos = spawn();
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health;
            b.scale = 1;
            b.gems = 0;
            b.ready_round = {b.respawned_round + 1, b.respawned_round + 1};
            if (enemy) fix_at_spawn(b, s.enemy_spawn, {round - 1, -1});
        }
    }

    b.visible = info != nullptr;
    if (!info) {
        // A channel completes at its owner's turn start.
        // A stun, lock or damage may have cancelled it: a tribute's bag is emptied by update_scores
        // only when the score shows it landed, and a recall leaves `pos` to the last sighting.
        if (b.channel != Channel::none
            && (round > b.channel_end_round || (round == b.channel_end_round && slot(b, round) < slot(me(), round)))) {
            if (b.channel == Channel::recall) {
                b.health = b.max_health;
                b.scale = 1;
                if (enemy) {
                    or_into(b.possible, s.enemy_spawn, b.possible);
                    also_undashed(b, s.enemy_spawn);
                    b.lineage = 0;
                }
            }
            b.channel = Channel::none;
        }
        // An untracked `possible` is unread until a fix overwrites it, as is one note_sighting is
        // about to fix.
        const auto expected = [&](const Sighting& x) { return x.enemy == b.index && in_bounds(x.pos) && x.round > b.pos_round; };
        if (enemy && b.tracked && !(full && (expected(expected_sighting) || expected(expected_second)))) track(b);
        return;
    }

    const int last_seen = b.stats_round;
    b.acted = acted;
    if (enemy) {
        const vec2 seen{info->x, info->y};
        // Fixed there at this turn's update already, and nothing moves during our turn. Dated by
        // its own flag, not our slot: stale ranks can misplace its turn against ours.
        if (full || last_seen != round || b.pos != seen) fix(b, seen, {round, acted ? Moment::end : -1});
    }
    b.pos = {info->x, info->y};
    b.pos_round = round;
    b.pos_source = Source::seen;
    b.health = info->health;
    b.max_health = info->max_health;
    b.strength = info->strength;
    b.focus = info->focus;
    b.scale = damage_scale(b.facts().passive, b.health, b.max_health) * b.dealt;
    b.stats_round = round;
    if (!full && last_seen == round) return; // nothing else changes during our turn
    if (!b.is_self) b.stun_pending = b.facts().passive != Passive::stun_immune && stun_pending(b.handle);
    // Also in observe() for a champion first seen after our move: a recall then still tells when
    // it lands, and its cooldowns show casts made out of sight.
    b.channel = state.contains(cambc::champion_state::recalling)         ? Channel::recall
                : state.contains(cambc::champion_state::submitting_gems) ? Channel::tribute
                : state.contains(cambc::champion_state::teleporting)     ? Channel::teleport
                                                                         : Channel::none;
    b.seen_channel = b.channel;
    if (b.channel != Channel::none) {
        const auto left = engine::channel_time(h);
        b.channel_end_round = fire_round(round, left.value_or(0), acted);
    }
    // The crystal's destination: a free tile within 3, terrain in between ignored.
    b.tp_dest = {-1, -1};
    if (enemy && b.channel == Channel::teleport) {
        // Its reservation is listed only while we see the destination tile.
        std::array<cambc::detail::teleport_info, 8> tps;
        std::uint32_t n = 0;
        if (cambc::detail::sdk_teleports(tps.data(), static_cast<std::uint32_t>(tps.size()), &n) == 0)
            for (std::uint32_t i = 0; i < std::min<std::uint32_t>(n, static_cast<std::uint32_t>(tps.size())); ++i)
                if (tps[i].champion == h) b.tp_dest = {tps[i].destination.x, tps[i].destination.y};
        debug_block({
            static std::array<int, 8> last{};
            if (last[b.index & 7] != b.channel_end_round) {
                last[b.index & 7] = b.channel_end_round;
                std::printf("ETP %d enemy %d d_me %d end %d dest %d,%d d_dest %d\n", round, b.index, dist(b.pos, me().pos),
                            b.channel_end_round, b.tp_dest.x, b.tp_dest.y, b.tp_dest.x < 0 ? -1 : dist(b.tp_dest, me().pos));
            }
        });
        // It lands there unless a stun or death cancels it, which leaves it here.
        if (in_bounds(b.tp_dest)) set_tile(b.possible, b.tp_dest);
        else or_into(b.possible, within(s.open_for_them, b.pos, teleport_crystal_range), b.possible);
        also_undashed(b, b.possible);
        b.lineage = 0;
    }
    const int earliest = b.respawned_round + 1;
    std::array<int, 2> cds;
    for (int slot = 0; slot < 2; ++slot) {
        cds[slot] = engine::cooldown(h, static_cast<std::uint32_t>(slot));
        b.ready_round[slot] = std::max(fire_round(round, cds[slot], acted), earliest);
    }
    if (b.shield_slot >= 0) read_shield(b, cds);
    if (full && enemy && priority_start_enemies.count < static_cast<int>(priority_start_enemies.units.size())) {
        auto& saved = priority_start_enemies.units[static_cast<std::size_t>(priority_start_enemies.count)];
        saved.type = static_cast<int>(b.type);
        saved.x = b.pos.x;
        saved.y = b.pos.y;
        saved.health = b.health;
        saved.shield = b.shield;
        saved.max_health = b.max_health;
        saved.strength = b.strength;
        saved.focus = b.focus;
        saved.cooldowns = cds;
        saved.alive = true;
        saved.stunned = b.stun_pending;
        priority_start_handles[static_cast<std::size_t>(priority_start_enemies.count)] = b.handle;
        ++priority_start_enemies.count;
    }
    // In observe() too, for a champion first seen after our move.
    b.gems = engine::gems(h);
    const auto e = engine::emblems(h);
    b.fast_recall = e.home;
    b.taken = e.durability ? durability_taken : 1.0f;
    b.fast_tribute = e.tribute;
    b.fast_capture = e.capture;
    b.prospector = e.prospector;
    b.dealt = e.dealt;
    b.camp_dealt = e.camp_dealt;
    b.scale = damage_scale(b.facts().passive, b.health, b.max_health) * b.dealt;
}

void World::read_priorities(bool new_round) {
    static std::int32_t priority, next_priority;
    const int now = round, ranked = ranked_round_;
    bool stale = ranks_stale_, enemy_change = enemy_priorities_change;
    for (auto* team : {&allies, &enemies})
        for (auto& b : *team) {
            // This round's order before anything dates a turn in it.
            if (new_round) b.prev_rank = b.rank;
            const auto h = engine::id(b.handle);
            // Fails for champions out of sight. A priority read in round r applies from r + 1:
            // ranks change when a round passes one unread.
            if (cambc::detail::sdk_bc_champion_priority(h, 0, &priority) != 0
                || cambc::detail::sdk_bc_champion_priority(h, 1, &next_priority) != 0) {
                stale |= b.next_priority != b.priority && ranked <= b.priority_round && b.priority_round < now;
                continue;
            }
            if (b.side == team::enemy
                && (next_priority != priority || (b.priority_round >= 0 && b.priority_round < now && priority != b.next_priority)))
                enemy_change = true;
            stale |= priority != b.priority || next_priority != b.next_priority;
            b.priority = priority;
            b.next_priority = next_priority;
            b.priority_round = now;
        }
    ranks_stale_ = stale;
    enemy_priorities_change = enemy_change;
}

[[gnu::flatten]] void World::note_turn_end() {
    if (!me().alive || !engine::alive(my_handle())) return;
    const vec2 p = my_position();
    const int g = in_bounds(p) ? map().group_at(p) : -1;
    if (g < 0 || camps[g].state != CampState::alive) return;
    guard("turn end", [&] {
        if (engine::group_state(map().groups[g].handle).first == engine::group_cleared) camps[g].cleared_by_us = round;
    });
}

void World::note_sighting(int enemy_index, vec2 pos, int seen_round, float health) {
    if (enemy_index < 0 || enemy_index >= static_cast<int>(enemies.size()) || !in_bounds(pos)) return;
    auto& b = enemies[enemy_index];
    if (!b.alive || b.visible || seen_round <= b.pos_round) return;
    b.health = health * b.max_health;
    b.scale = damage_scale(b.facts().passive, b.health, b.max_health) * b.dealt;
    b.pos = pos;
    b.pos_round = seen_round;
    b.pos_source = Source::comms;
    // The poster's turn in that round is unknown: from the round's start, its turns that round count.
    fix(b, pos, {seen_round, -1});
    track(b);
}

void World::note_capture(int group, int respawn_round) {
    if (group < 0 || group >= static_cast<int>(camps.size()) || respawn_round <= round) return;
    auto& c = camps[group];
    c.told_respawn = respawn_round;
    if (c.state_round == round) return; // in view: our own reading stands
    if (static_cast<std::size_t>(group) < 64 * camps_pending_.size()) camps_pending_[group >> 6] |= std::uint64_t{1} << (group & 63);
    c.version += c.state != CampState::respawning;
    camps_version += c.state != CampState::respawning;
    c.state = CampState::respawning;
    c.respawn_round = respawn_round;
    c.awake = Awake::asleep;
    c.asleep = 0;
    c.holder.reset();
    c.held_since = -1;
    note_stirring(group);
}

void World::note_stirring(int g) {
    const auto& c = camps[g];
    const std::uint64_t bit = std::uint64_t{1} << (g % 64);
    auto& word = stirring_[g / 64];
    word = c.state == CampState::alive && c.awake != Awake::asleep ? word | bit : word & ~bit;
    auto& cleared = cleared_[g / 64];
    cleared = c.state == CampState::cleared ? cleared | bit : cleared & ~bit;
    auto& respawning = respawning_[g / 64];
    respawning = c.state == CampState::respawning ? respawning | bit : respawning & ~bit;
}

void World::read_vision() {
    vision_into(visible);
    not_into(visible, unseen_);
    landing_ready_ = false;
}

bool World::revealed(vec2 p, int r, bool bumped) const {
    // Nothing moves during our turn: a tile looked from once shows the same.
    if (!bumped && (p == sight_pos_ || p == clear_pos_)) return false;
    for (const auto& b : enemies)
        if (b.alive && b.stats_round != round && engine::in_sight(engine::id(b.handle)))
            if (const auto* info = engine::champion(engine::id(b.handle)); info && dist(p, {info->x, info->y}) <= r) return true;
    clear_pos_ = p;
    return false;
}

// `undashed` is read only while turns_since_fixed <= ability_cooldown, in advance(), which first
// adds the turns; the next fix resets it. Once no later advance can read it, it is left stale.
void World::also_undashed(ChampionBelief& b, const bitboard& tiles) {
    if (b.facts().has_dash() && b.turns_since_fixed < ability_cooldown) or_into(b.undashed, tiles, b.undashed);
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

[[gnu::always_inline]] void World::fix(ChampionBelief& b, vec2 tile, Moment when) {
    clear_board(b.possible);
    set_tile(b.possible, tile);
    mark_fixed(b, when);
    b.lineage = 0;
}

void World::rank_turns() {
    ranks_stale_ = false;
    ranked_round_ = round;
    const int now = round;
    // Passes 2 and 3 rank next round, when every next_priority applies.
    for (int t = 0; t < 4; ++t) {
        auto& team = t % 2 == 0 ? allies : enemies;
        ChampionBelief* const members = team.data();
        // Handles ascend with the index: a tie goes to the lower index.
        const int n = std::min(static_cast<int>(team.size()), 16);
        std::array<int, 16> priority;
        for (int i = 0; i < n; ++i) {
            const auto& x = members[i];
            priority[i] = t >= 2 || now > x.priority_round ? x.next_priority : x.priority;
        }
        // Insertion sort from the last order, which mostly still holds; in a local copy, which no
        // store to a belief can alias.
        auto order = turn_order_[t];
        for (int k = 1; k < n; ++k) {
            const int i = order[k], p = priority[i];
            int j = k;
            for (; j > 0; --j) {
                const int o = order[j - 1];
                if (priority[o] > p || (priority[o] == p && o < i)) break;
                order[j] = order[j - 1];
            }
            order[j] = static_cast<std::uint8_t>(i);
        }
        turn_order_[t] = order;
        if (t < 2)
            for (int k = 0; k < n; ++k) members[order[k]].rank = k;
        else
            for (int k = 0; k < n; ++k) members[order[k]].next_rank = k;
    }
}

int World::turns_between(const ChampionBelief& c, Moment from, Moment to) const {
    if (!(from < to)) return 0;
    int turns = 0;
    for (int r = std::max(from.round, 1); r <= to.round; ++r) {
        const Moment turn{r, slot(c, r)};
        turns += from < turn && turn <= to;
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

bool World::grow(ChampionBelief& b, int turns) {
    const auto& s = map();
    const auto& land = landing();
    b.turns_since_fixed += turns;
    const bool dasher = b.facts().has_dash();
    const bool undashed_read = dasher && b.turns_since_fixed <= ability_cooldown;
    const bool undashed_kept = dasher && b.turns_since_fixed < ability_cooldown;
    // A recall started on any turn after the fix lands at the start of the turn after its last
    // turn end, which is a full turn: from turn recall_time + 1 on, add the spawn before growing.
    if (b.turns_since_fixed > b.recall_turns()) {
        or_into(b.possible, s.enemy_spawn, b.possible);
        if (undashed_read) or_into(b.undashed, s.enemy_spawn, b.undashed);
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
        const auto listed = list_growth(b.undashed);
        widen_by_dash(b.undashed, dashed, s, turns, land, listed);
        if (undashed_kept) walk(b.undashed, s, turns, land, listed);
        walk(b.possible, s, turns, land);
        or_into(b.possible, dashed, b.possible);
    } else if (dash) {
        // undashed lies within possible (equal to it, or read no more): dashing from possible
        // covers dashing from it.
        const auto listed = list_growth(b.possible);
        widen_by_dash(b.possible, b.possible, s, turns, land, listed);
        if (undashed_kept) walk(b.undashed, s, turns, land, b.undashed_all ? listed : unlisted);
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

[[gnu::flatten]] void World::track(ChampionBelief& b) {
    if (round - b.fixed.round > params::track_horizon) {
        b.tracked = false;
        return;
    }
    // Out of sight, its turn this round may come before ours whatever its rank says (ranks rest on
    // priorities read only in sight): count it now, so `possible` grows too much rather than
    // missing a tile, and date `possible` after that turn so the next update does not count it again.
    const auto to = std::max(now(), Moment{round, slot(b, round)});
    // A teleport seen under way pins it until it lands, at its turn start in channel_end_round:
    // that turn is counted.
    if (b.seen_channel == Channel::teleport) {
        const Moment lands{b.channel_end_round, slot(b, b.channel_end_round) - 1};
        if (b.at < lands) b.at = std::min(to, lands);
    }
    const int turns = turns_between(b, b.at, to);
    // With no turns to add, every enemy of a lineage gets the same prune this pass.
    if (!turns) {
        b.at = to;
        prune(b);
        return;
    }
    const bool dasher = b.facts().has_dash();
    for (int i = 0; i < tracked_count_ && b.lineage; ++i) {
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
    Tracked t{b.lineage, 0, b.index, turns, b.turns_since_fixed, b.fixed, b.at, dasher, false, b.fast_recall};
    b.at = to;
    t.dash = grow(b, turns);
    note_emptied(b);
    if (!t.before) return;
    b.lineage = t.after = ++lineages_;
    if (tracked_count_ < static_cast<int>(tracked_.size())) tracked_[tracked_count_++] = t;
}

// `possible` never holds a tile closed to them, so a walk dilates it.
void World::walk(bitboard& tiles, const StaticMap& s, int steps, const bitboard& land, std::uint32_t listed) {
    if (steps >= 2) {
        if (listed == unlisted) listed = list_growth(tiles);
        if (reach_each(tiles, tiles, s.blocked_for_them, steps, land, steps > 2 ? reach_few : 4, listed)) return;
    }
    if (steps <= 2) {
        dilate(tiles, s.open_for_them, steps, land, listed);
        return;
    }
    static cambc::distance_field field;
    static bitboard grown{cambc::uninitialized};
    field.compute(s.blocked_for_them, tiles, grown, static_cast<std::uint16_t>(steps));
    tiles.swap(grown);
    and_into(tiles, land, tiles);
}

// `steps` turns with one dash (dash_range king steps, with that turn's walk): it crosses holes, altars and
// champions, so only walls bound it and landings are filtered after.
void World::widen_by_dash(const bitboard& from, bitboard& out, const StaticMap& s, int steps, const bitboard& land,
                          std::uint32_t listed) {
    if (reach_each(from, out, s.walls, steps + dash_range, land, reach_few, listed)) return;
    static cambc::distance_field field;
    static bitboard grown{cambc::uninitialized};
    field.compute(s.walls, from, grown, static_cast<std::uint16_t>(steps + dash_range));
    and_into(grown, land, grown);
    out.swap(grown);
}

void World::prune(ChampionBelief& b) const {
    and_into(b.possible, unseen_, b.possible);
    if (b.facts().has_dash() && b.turns_since_fixed < ability_cooldown) and_into(b.undashed, unseen_, b.undashed);
    note_emptied(b);
}

// Emptied by something unmodelled (a teleport crystal, say): it could be anywhere.
void World::note_emptied(ChampionBelief& b) {
    if (b.tracked && board_empty(b.possible)) b.tracked = false;
}

namespace {
// Back at full health and asleep, each member's health known from `since`.
void restore(CampBelief& c, const CampGroup& G, int since) {
    for (std::size_t i = 0; i < G.members.size(); ++i) c.health[i] = G.members[i].max_health, c.health_round[i] = since;
    c.awake = Awake::asleep;
    c.asleep = 0;
    ++c.version;
}
} // namespace

// update_camps' board, read on first use: most turns no visible group is cleared.
struct World::CampViews {
    bool champs_read = false;
    const bitboard& champs() {
        static bitboard ally{cambc::uninitialized}, enemy{cambc::uninitialized}, both{cambc::uninitialized};
        if (!champs_read) {
            champs_read = true;
            occupancy_into(team::ally, ally);
            occupancy_into(team::enemy, enemy);
            or_into(ally, enemy, both);
        }
        return both;
    }
};

[[gnu::flatten]] void World::update_camps() {
    const auto& s = map();
    const std::size_t words = (s.groups.size() + 63) / 64;
    // The camp tiles in view as last turn: the same groups are.
    static bitboard seen{cambc::uninitialized}, before{cambc::uninitialized};
    and_into(visible, s.camp_tiles, seen);
    if (group_visible_.size() != words || !boards_equal(seen, before)) {
        group_visible_.assign(words, 0);
        auto* const visible_bits = group_visible_.data();
        for (auto p : Tiles<17 * 17 + 13 * 13>{seen}) {
            const int g = s.group_at(p);
            visible_bits[g >> 6] |= std::uint64_t{1} << (g & 63);
        }
    }
    seen.swap(before);
    const auto* group_visible = group_visible_.data();
    CampViews views;

    camps_pending_.resize(words);
    for (std::size_t w = 0; w < words; ++w) {
        for (std::uint64_t bits = group_visible[w] | camps_pending_[w]; bits; bits &= bits - 1) {
            const std::size_t g = 64 * w + static_cast<std::size_t>(__builtin_ctzll(bits));
            const std::uint64_t bit = std::uint64_t{1} << (g & 63);
            const bool in_view = (group_visible[w] & bit) != 0;
            if (!in_view) {
                // Out of view, it changes only when a timer runs out.
                const auto& c = camps[g];
                if (!(c.state == CampState::cleared && c.holder && round >= c.payout_round())
                    && !(c.state == CampState::respawning && round >= c.respawn_round)
                    && !(c.awake == Awake::awake && round - c.state_round > cambc::constants::camp_sleep_time))
                    continue;
            }
            const auto version = camps[g].version;
            guard("camp", [&] { update_camp(g, in_view, views); });
            const auto& c = camps[g];
            const bool pending = (c.state == CampState::cleared && c.holder) || c.state == CampState::respawning || c.awake == Awake::awake;
            camps_pending_[w] = pending ? camps_pending_[w] | bit : camps_pending_[w] & ~bit;
            camps_version += c.version != version;
            note_stirring(static_cast<int>(g));
        }
    }
}

[[gnu::flatten]] void World::update_camp(std::size_t g, bool in_view, CampViews& views) {
    const auto& G = map().groups[g];
    auto& c = camps[g];

    if (!in_view) {
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
        if (c.awake == Awake::awake && round - c.state_round > cambc::constants::camp_sleep_time) c.awake = Awake::unknown;
        return;
    }

    const auto [code, timer] = engine::group_state(G.handle);
    const auto previous = c.state;
    const int previous_round = c.state_round;
    const int previous_respawn = c.respawn_round;
    if (code == engine::group_alive) c.state = CampState::alive;
    else if (code == engine::group_cleared) c.state = CampState::cleared;
    else if (code == engine::group_respawning) {
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
    // sleep it may have fallen asleep again since. Waking is group-wide but each monster sleeps
    // on its own range, so the group is awake while any striking member is: settled outright by
    // one seen awake, or by every live striker seen asleep. Without strikers left, any member
    // shows it.
    std::optional<Awake> seen_awake;
    bool hidden_tile = false; // a camp tile out of view where a champion could stand
    {
        const int now = round;
        const bool alive = c.state == CampState::alive;
        float* health = c.health.data();
        int* health_round = c.health_round.data();
        const CampMember* members = G.members.data();
        const std::size_t n = G.members.size();
        Awake awake = c.awake;
        std::uint32_t version = c.version;
        bool striker_awake = false, striker_asleep = false, striker_unread = false, woke = false;
        std::uint64_t read_asleep = 0, read_awake = 0, unseen = 0;
        int harmless = -1;
        const bool cleared = c.state == CampState::cleared;
        // One loop per liveness: a group cleared or respawning has no live member to read.
        const auto read_members = [&](auto live_group) {
            constexpr bool live = decltype(live_group)::value;
            for (std::size_t i = 0; i < n; ++i) {
                const auto& m = members[i];
                const std::uint64_t bit = i < 64 ? std::uint64_t{1} << i : 0;
                if (!test(visible, m.pos)) {
                    if constexpr (!live) {
                        if (cleared && !hidden_tile) hidden_tile = test(map().passable, m.pos);
                    }
                    if (m.strength > 0 && health[i] > 0) {
                        unseen |= bit;
                        striker_unread |= bit == 0;
                    }
                    continue;
                }
                const float hp = live ? engine::camp_health(m.handle).value_or(0.0f) : 0.0f;
                if (hp < health[i] - 1e-3f) {
                    if (now - health_round[i] < cambc::constants::camp_sleep_time) {
                        c.last_damaged_round = now;
                        awake = Awake::awake;
                        woke = true;
                    } else if (awake == Awake::asleep) {
                        awake = Awake::unknown;
                        woke = true;
                    }
                }
                version += hp != health[i];
                health[i] = hp;
                health_round[i] = now;
                if (hp <= 0 || !live) continue;
                if (m.strength <= 0) {
                    if (harmless < 0) harmless = static_cast<int>(i);
                    continue;
                }
                const auto read = engine::camp_awake(m.handle);
                striker_awake |= read == Awake::awake;
                striker_asleep |= read == Awake::asleep;
                striker_unread |= !read;
                if (read == Awake::asleep) read_asleep |= bit;
                else if (read == Awake::awake) read_awake |= bit;
            }
        };
        if (alive) read_members(std::true_type{});
        else read_members(std::false_type{});
        debug_block({
            // The vision boards of awake and asleep camps (unused: a host read per member costs less
            // than a board read in place) and the not-alive shortcut, against the per-camp reads.
            namespace raw = cambc::detail;
            static bitboard awake_tiles{cambc::uninitialized}, asleep_tiles{cambc::uninitialized};
            static std::uint32_t state;
            static std::int32_t on_awake, on_asleep, seen;
            static raw::camp_state record;
            if (raw::sdk_awake_camp_occupancy(awake_tiles.ptr()) == 0 && raw::sdk_asleep_camp_occupancy(asleep_tiles.ptr()) == 0)
                for (std::size_t i = 0; i < n; ++i) {
                    const vec2 p = members[i].pos;
                    if (raw::sdk_Bitboard_Test(visible.ptr(), p.x, p.y, &seen) != 0 || !seen
                        || raw::sdk_Bitboard_Test(awake_tiles.ptr(), p.x, p.y, &on_awake) != 0
                        || raw::sdk_Bitboard_Test(asleep_tiles.ptr(), p.x, p.y, &on_asleep) != 0)
                        continue;
                    const int read = raw::sdk_camp_state(members[i].handle, &state) == 0 && (state == 1 || state == 2) ? static_cast<int>(state) : 0;
                    const int board = on_awake ? 1 : on_asleep ? 2 : 0;
                    const float hp = raw::sdk_camp(members[i].handle, &record) == 0 ? record.health : 0.0f;
                    if (read != board || (on_awake && on_asleep) || (!alive && hp != 0.0f))
                        std::printf("CAMP-AWAKE-MISMATCH %d %d %d state %d board %d alive %d hp %g\n", now, static_cast<int>(g),
                                    static_cast<int>(i), read, on_awake + 2 * on_asleep, alive, static_cast<double>(hp));
                }
        });
        // A member known asleep that reads awake was woken by damage, which woke the rest too.
        woke |= (c.awake == Awake::asleep ? read_awake : c.asleep & read_awake) != 0;
        c.asleep = woke ? read_asleep : (c.asleep & ~read_awake) | read_asleep;
        striker_unread |= (unseen & ~c.asleep) != 0;
        striker_asleep |= (unseen & c.asleep) != 0;
        if (striker_awake) seen_awake = Awake::awake;
        else if (striker_asleep && !striker_unread) seen_awake = Awake::asleep;
        else if (!striker_asleep && !striker_unread && harmless >= 0) seen_awake = engine::camp_awake(members[harmless].handle);
        c.awake = awake;
        c.version = version;
    }

    if (c.state != CampState::alive) {
        c.awake = Awake::asleep;
    } else if (seen_awake) {
        c.awake = *seen_awake;
    }
    if (c.awake == Awake::asleep) c.asleep = 0;

    if (c.state == CampState::cleared) {
        if (!hidden_tile) {
            std::uint32_t occupants = 0;
            if (!disjoint(G.tiles(), views.champs())) {
                for (const auto& b : allies)
                    if (b.alive && (b.visible || b.is_self) && test(G.tiles(), b.pos)) occupants |= 1u << b.index;
                for (const auto& b : enemies)
                    if (b.alive && b.visible && test(G.tiles(), b.pos)) occupants |= 1u << (16 + b.index);
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
                // Unseen last round, a contest may have ended this round before our turn: our hold
                // dates from then; an enemy's stays early, as dating it late could lose us the contest.
                if (!holder) c.held_since = -1;
                else if (*holder == team::ally && previous_round < round - 1) c.held_since = round;
                else c.held_since = hold_start(G, *holder, earliest, c.cleared_by_us >= previous_round);
            }
            // The engine's countdown dates the hold exactly, as it counts a Capture emblem.
            if (c.holder)
                if (const int timer = engine::capture_timer(G.handle, *c.holder); timer >= 0)
                    c.held_since = round + timer - cambc::constants::capture_time - 1;
        } else {
            // An unseen camp tile may hold champions, so the occupants can't say who holds it; the
            // engine's capture state can. `occupants` stays as last fully seen.
            const auto [holder, timer] = engine::capturer(G.handle);
            c.holder = holder;
            c.held_since = holder ? round + timer - cambc::constants::capture_time - 1 : -1;
        }
    } else {
        c.holder.reset();
        c.held_since = -1;
        c.occupants = 0;
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
        if (c.alive && c.pos_round == round && test(G.tiles(), c.pos)
            && (c.is_self || (c.visible ? !c.acted : slot(c, round) > slot(me(), round))))
            return round - 1;
    return round;
}

[[gnu::flatten]] void World::update_altars() {
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
            if (test(visible, s.altars[a].pos)) seen(static_cast<int>(a));
    }
    std::uint32_t count{};
    ok(raw::sdk_altar_locks(nullptr, 0, &count));
    if (count == 0) return;
    static std::vector<raw::altar_lock_info> locks; // kept across turns: allocating costs more than the read
    if (locks.size() < count) locks.resize(count);
    ok(raw::sdk_altar_locks(locks.data(), count, &count));
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

[[gnu::flatten]] void World::update_scores(std::uint32_t tributing) {
    // cambc::global_submitted_gems, with our absolute team read once.
    static std::uint32_t submitted;
    const std::int32_t own = cambc::detail::sdk_my_team();
    ok(cambc::detail::sdk_bc_submitted_gems(own, &submitted));
    const int ally = static_cast<int>(submitted);
    ok(cambc::detail::sdk_bc_submitted_gems(1 - own, &submitted));
    const int enemy = static_cast<int>(submitted);
    const int enemy_delta = round == first_round ? 0 : enemy - score.enemy;
    score.ally = ally;
    score.enemy = enemy;
    if (ally_scores_.empty()) ally_scores_.reserve(cambc::constants::max_rounds + 1);
    // Rounds we did not read keep the score before them, not this one.
    if (static_cast<int>(ally_scores_.size()) <= round) {
        ally_scores_.resize(round + 1, ally_scores_.empty() ? ally : ally_scores_.back());
        ally_scores_[round] = ally;
    }
    // No tribute landed: an ended channel was cancelled, and its bag kept.
    if (enemy_delta <= 0) return;

    // An enemy tribute just landed: empty the bag of whoever most plausibly made it. One enemy that
    // was tributing before this update and no longer is made it (a visible one's bag was just
    // read); failing that, an unseen one whose bag matches.
    ChampionBelief* tributer = nullptr;
    int candidates = 0;
    for (std::size_t i = 0; i < enemies.size(); ++i) {
        auto& b = enemies[i];
        if ((tributing >> i & 1) && b.alive && b.channel != Channel::tribute) tributer = &b, ++candidates;
    }
    if (candidates == 1) {
        if (!tributer->visible) tributer->gems = 0;
        return;
    }
    tributer = nullptr;
    candidates = 0;
    for (auto& b : enemies)
        if (b.alive && !b.visible && b.gems == enemy_delta) tributer = &b, ++candidates;
    if (candidates == 1) {
        tributer->gems = 0;
        tributer->channel = Channel::none;
    }
}

float World::ally_rate() const {
    const int from = std::max(first_round, round / 2);
    if (round <= from || from >= static_cast<int>(ally_scores_.size())) return 0;
    return static_cast<float>(score.ally - ally_scores_[from]) / static_cast<float>(round - from);
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
