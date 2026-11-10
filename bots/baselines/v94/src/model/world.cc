#include "world.h"
#include "../emblems.h"
#include "turn_order.h"
#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdio>
#include <cstring>
#include <span>
#include <stdexcept>
#include <tuple>
#include <wasm_simd128.h>

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
    return read_visible_record(h, info);
}

// Readable for hidden and dead champions too.
cambc::champion_type type(std::uint32_t h) {
    champion_identity identity{};
    ok(sdk_champion_identity(h, &identity));
    return static_cast<cambc::champion_type>(identity.type);
}

// The champion's buffs, valid until the next call; empty when `code` is an error.
std::span<const buff_data> buffs(std::uint32_t h, std::int32_t& code) {
    static ChampionBuffs data;
    std::uint32_t n;
    code = read_buffs(h, data, n);
    return {data.data(), code ? 0 : std::min<std::size_t>(n, data.size())};
}

// The active shield's value and turn ends left, {0, 0} if none.
std::pair<float, int> shield(std::uint32_t h) {
    static ChampionBuffs buffs;
    std::uint32_t n;
    ok(read_buffs(h, buffs, n));
    for (std::uint32_t i = 0; i < n && i < buffs.size(); ++i)
        if (buffs[i].type == static_cast<std::uint32_t>(cambc::buff_types::shield))
            return {buffs[i].data.shield.value, buffs[i].data.shield.duration};
    return {0.0f, 0};
}

bool alive(std::uint32_t h) {
    static std::int32_t value;
    return read_alive(h, value);
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
    bool home, durability, tribute, capture, prospector, jungle;
    float dealt, camp_dealt; // ChampionBelief::dealt, ::camp_dealt
};
Emblems emblems(std::uint32_t h) {
    using F = cambc::item_family;
    static cambc::enum_map<cambc::item_type> counts; // overwritten whole: not cleared first
    ok(sdk_champion_items(h, counts.ptr()));
    // Straight from the storage: has_family()'s checked lookups cost ~15 fuel each.
    const std::uint32_t* c = counts.ptr();
    const auto has = [c](F f) {
        const std::uint32_t* e = c + static_cast<int>(f) * 6 + 1;
        return (e[0] | e[2] | e[4]) != 0;
    };
    const auto dealt = has(F::collectors) ? dealt_with(counts)
                                          : Dealt{has(F::skirmish) ? skirmish_dealt : 1.0f, has(F::monster) ? monster_camp_dealt : 1.0f};
    return {has(F::home), has(F::durability), has(F::tribute), has(F::capture), has(F::prospector), has(F::jungle), dealt.champion, dealt.camp};
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

// Who is capturing the group, if anyone, and the rounds to its payout (paid at that round's capture
// phase, a Capture emblem's cap included), else -1. Needs any one of its camp tiles in vision, not
// the capturers.
std::pair<std::optional<team>, int> capturer(std::uint32_t h) {
    static cambc::detail::camp_group_capture_state value;
    if (sdk_camp_group_capture_state(h, &value) != 0) return {std::nullopt, -1};
    using T = cambc::map::camp_group_capture_type;
    if (value.state == static_cast<std::int32_t>(T::ally_capturing)) return {team::ally, value.timer};
    if (value.state == static_cast<std::int32_t>(T::enemy_capturing)) return {team::enemy, value.timer};
    return {std::nullopt, -1};
}

// capturer's rounds to payout while `side` captures the group, else -1.
int capture_timer(std::uint32_t h, team side) {
    const auto [who, timer] = capturer(h);
    return who == side ? timer : -1;
}
} // namespace engine

// An emptied bag takes Prism's Focus from its gems with it: its Focus was last read with that bag.
void drop_bag(ChampionBelief& b) {
    if (b.facts().passive == Passive::gem_focus) b.focus -= cambc::constants::passive_abilities::prism_focus_per_gem * static_cast<float>(b.gems);
    b.gems = 0;
}

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
    if (foot_ || ally_spawn_tiles.empty()) {
        ally_field_ = make_field(blocked_for_us, ally_spawn);
    } else {
        // Its flood is foot(): the spawn is a rectangle of open tiles, so reached from any one.
        bitboard reached{cambc::uninitialized};
        ally_field_ = make_field(blocked_for_us, ally_spawn, reached);
        foot_.emplace(std::move(reached));
    }
    return *ally_field_;
}

const bitboard& StaticMap::make_foot() const {
    // The spawn field is always made by the warm-up, and its flood is this one.
    if (!ally_field_ && !ally_spawn_tiles.empty()) {
        make_ally_field();
        return *foot_;
    }
    FuelMeter meter{"foot"};
    bitboard b;
    if (!ally_spawn_tiles.empty()) blocked_for_us.reachable_tiles_into(ally_spawn_tiles[0], unreachable, b);
    return foot_.emplace(std::move(b));
}

// A dash's walls are a subset of blocked_for_us, so its flood from the spawn holds foot(): grown
// from foot, the flood costs only the layers past it (a flood from one tile costs the map's depth).
void StaticMap::dash_flood(const bitboard& walls, bitboard& out) const {
    if (ally_spawn_tiles.empty()) return;
    if (!foot_) {
        flood_into(walls, ally_spawn_tiles[0], out);
        return;
    }
    static cambc::distance_field steps;
    steps.compute(walls, *foot_, out);
}

const bitboard& StaticMap::make_dash_foot() const {
    FuelMeter meter{"dash_foot"};
    bitboard b;
    dash_flood(dash_walls, b);
    return dash_foot_.emplace(std::move(b));
}

const bitboard& StaticMap::make_landing_dash_foot() const {
    FuelMeter meter{"landing_dash_foot"};
    bitboard b;
    dash_flood(landing_dash_walls, b);
    return landing_dash_foot_.emplace(std::move(b));
}

// The region around `from`, if a crystal from foot lands in it.
void StaticMap::add_hop(vec2 from, int altar) const {
    static bitboard near_foot{cambc::uninitialized};
    static bool near_made = false;
    // Every tile of a barren pocket floods to it again.
    if (barren_ && test(*barren_, from)) return;
    if (!near_made) square_dilate(foot(), teleport_crystal_range, near_foot), near_made = true;
    Hop hop;
    hop.altar = altar;
    flood_into(blocked_for_us, from, hop.pocket);
    and_into(hop.pocket, near_foot, hop.landings);
    and_into(hop.landings, camp_tiles, hop.camp_landings);
    drop(hop.landings, camp_tiles);
    if (hop.landings.is_empty()) {
        if (barren_) *barren_ |= hop.pocket;
        else barren_.emplace(std::move(hop.pocket));
        return;
    }
    square_dilate(hop.landings, teleport_crystal_range, hop.sources);
    hop.sources &= foot();
    drop(hop.sources, camp_tiles);
    hops_->push_back(std::move(hop));
}

const std::vector<StaticMap::Hop>& StaticMap::make_hops() const {
    FuelMeter meter{"hops"};
    auto& hops = hops_.emplace();
    if (ally_spawn_tiles.empty()) return hops;
    // A hop whose pocket holds the next altar's tile is that altar's too: the region's flood under
    // the same walls (up to 40k each on winding maps).
    const auto same_pocket = [&](vec2 t, bool camps) {
        for (int h = 0; h < static_cast<int>(hops.size()); ++h)
            if (hops[h].camps == camps && test(hops[h].pocket, t)) return h;
        return -1;
    };
    const auto share = [&](int h, int a) {
        Hop hop = hops[h];
        hop.altar = a;
        hops.push_back(std::move(hop));
    };
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        const auto& tributes = altars[a].tribute_tiles();
        if (tributes.is_empty() || !disjoint(tributes, foot())) continue;
        const vec2 from = first_tile(tributes);
        if (const int h = same_pocket(from, false); h >= 0) share(h, a);
        else add_hop(from, a);
    }
    // Altars on foot that the walk with every camp standing misses: sealed by camps.
    if (may_camp_seal()) {
        static bitboard walls{cambc::uninitialized}, walk{cambc::uninitialized}, near_walk{cambc::uninitialized},
            tile{cambc::uninitialized}, rim{cambc::uninitialized}, barren{cambc::uninitialized};
        or_into(blocked_for_us, camp_tiles, walls);
        flood_into(walls, ally_spawn_tiles[0], walk);
        clear_board(barren); // pockets with no landing
        bool near_made = false;
        for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
            copy_into(altars[a].tribute_tiles(), tile);
            drop(tile, camp_tiles);
            if (board_empty(tile) || disjoint(tile, foot()) || !disjoint(tile, walk)) continue;
            const vec2 from = first_tile(tile);
            if (const int h = same_pocket(from, true); h >= 0) {
                share(h, a);
                continue;
            }
            if (test(barren, from)) continue;
            if (!near_made) square_dilate(walk, teleport_crystal_range, near_walk), near_made = true;
            Hop hop;
            hop.altar = a;
            hop.camps = true;
            flood_into(walls, from, hop.pocket);
            and_into(hop.pocket, near_walk, hop.landings);
            if (hop.landings.is_empty()) {
                barren |= hop.pocket;
                continue;
            }
            square_dilate(hop.landings, teleport_crystal_range, hop.sources);
            hop.sources &= walk;
            square_dilate(hop.pocket, 1, rim);
            rim &= camp_tiles;
            // Groups listed by this hop: a find in the ring per rim tile cost ~120k on a big pocket.
            static std::vector<std::uint32_t> ringed;
            static std::uint32_t ring_stamp = 0;
            if (ringed.size() < groups.size()) ringed.resize(groups.size());
            ++ring_stamp;
            for (const vec2 p : rim.positions())
                if (const int g = group_at(p); g < 0 ? std::find(hop.ring.begin(), hop.ring.end(), g) == hop.ring.end()
                                                     : ringed[static_cast<std::size_t>(g)] != ring_stamp) {
                    if (g >= 0) ringed[static_cast<std::size_t>(g)] = ring_stamp;
                    hop.ring.push_back(g);
                }
            hops.push_back(std::move(hop));
            camp_hops_ = true;
        }
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
    if (h == static_cast<int>(hops.size())) {
        add_hop(t, -1);
        if (h == static_cast<int>(hops.size())) return; // no crystal reaches the region
    }
    // Not into the enemy's walk: they come and go there at will, and no walk takes us out.
    if (off_theirs) {
        group_hops_[g] = h;
        return;
    }
    static bitboard theirs{cambc::uninitialized};
    static bool theirs_made = false;
    if (!theirs_made) {
        clear_board(theirs);
        if (const auto tiles = enemy_spawn.positions(); !tiles.empty()) flood_into(blocked_for_them, tiles[0], theirs);
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
    // None readable (the second turn) needs neither our walk nor the hops yet.
    if (hop_tried_.empty() || upto <= 0 || (foot_ && hops_ && hops_made_ >= upto)) return;
    FuelMeter meter{"group_hops"};
    foot();
    hops();
    for (; hops_made_ < upto; ++hops_made_) {
        add_group_hop(hop_tried_[hops_made_], drafted());
        if (group_hops_[hop_tried_[hops_made_]] >= 0) first_hop_rank_ = std::min(first_hop_rank_, hops_made_);
    }
}

int StaticMap::hops_readable() const {
    const int step = static_cast<int>(round_now()) - static_cast<int>(built_round) - 1;
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

[[gnu::always_inline]] inline bool StaticMap::grow_clusters(bitboard& left, std::uint64_t fuel_floor) const {
    static bitboard rest{cambc::uninitialized};
    while (!left.is_empty()) {
        const auto* c = grow_cluster(first_tile(left), fuel_floor);
        if (!c) return false;
        not_into(c->tiles, rest);
        left &= rest;
    }
    return true;
}

bool StaticMap::find_bush_clusters(vec2 p, int radius, std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized};
    not_into(clustered_, left);
    left &= within(bushes, p, radius);
    return grow_clusters(left, fuel_floor);
}

bool StaticMap::find_bush_clusters(const bitboard& tiles, std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized};
    not_into(clustered_, left);
    left &= tiles;
    left &= bushes;
    return grow_clusters(left, fuel_floor);
}

bool StaticMap::find_all_bush_clusters(std::uint64_t fuel_floor) const {
    static bitboard left{cambc::uninitialized};
    not_into(clustered_, left);
    left &= bushes;
    return grow_clusters(left, fuel_floor);
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

bool StaticMap::warm_drafted_steps(std::uint64_t fuel_floor) const {
    if (!index_.steps) return true;
    // A pass costs up to ~200 a group: one kind a check.
    for (int which = 1; which <= 2; ++which) {
        if (steps_warm_ >> which & 1) continue;
        if (!fuel_ok(fuel_floor + 250 * groups.size() + small_cost_estimate)) return false;
        fixed_steps(which);
        steps_warm_ |= static_cast<std::uint8_t>(1u << which);
    }
    return true;
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

bool StaticMap::warm_enemy_steps(std::uint64_t fuel_floor) const {
    if (!plan_ || index_.steps || !drafted_.enemy.empty()) return true;
    // ~150 fuel a group.
    if (!fuel_ok(fuel_floor + 300 * groups.size() + small_cost_estimate)) return false;
    decode_enemy_steps(*plan_, header_, *this, drafted_);
    return true;
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
    // By counting: Chebyshev distances on a map are under 100. The centres as bytes, sixteen a
    // vector (coordinates below 100 and their differences fit a signed byte), made once: a group's
    // distance read one by one cost ~90 fuel (16.8k a call on 126 groups in all, now ~11k).
    alignas(16) static std::array<std::int8_t, 256> xs, ys;
    // lanes[16 - k..]: the first k lanes set, to mask a last chunk of k groups.
    alignas(16) static constexpr std::array<std::uint8_t, 32> lanes{255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255};
    static int listed = -1;
    if (listed != n) {
        for (int g = 0; g < n; ++g) xs[g] = static_cast<std::int8_t>(groups[g].centre.x), ys[g] = static_cast<std::int8_t>(groups[g].centre.y);
        listed = n;
    }
    const vec2 from = groups[group].centre;
    alignas(16) std::array<std::uint8_t, 256> d;
    int far = 0; // past the farthest distance the sums are never read
#if defined(__wasm_simd128__)
    const v128_t fx = wasm_i8x16_splat(static_cast<std::int8_t>(from.x)), fy = wasm_i8x16_splat(static_cast<std::int8_t>(from.y));
    v128_t most = wasm_i8x16_splat(0);
    for (int c = 0; c < n; c += 16) {
        const v128_t r = wasm_i8x16_max(wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&xs[c]), fx)),
                                        wasm_i8x16_abs(wasm_i8x16_sub(wasm_v128_load(&ys[c]), fy)));
        wasm_v128_store(&d[c], r);
        most = wasm_u8x16_max(most, n - c >= 16 ? r : wasm_v128_and(r, wasm_v128_load(&lanes[16 - (n - c)])));
    }
    most = wasm_u8x16_max(most, wasm_i8x16_shuffle(most, most, 8, 9, 10, 11, 12, 13, 14, 15, 0, 1, 2, 3, 4, 5, 6, 7));
    most = wasm_u8x16_max(most, wasm_i8x16_shuffle(most, most, 4, 5, 6, 7, 0, 1, 2, 3, 4, 5, 6, 7, 0, 1, 2, 3));
    most = wasm_u8x16_max(most, wasm_i8x16_shuffle(most, most, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1));
    most = wasm_u8x16_max(most, wasm_i8x16_shuffle(most, most, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0));
    far = wasm_u8x16_extract_lane(most, 0);
#else
    for (int g = 0; g < n; ++g)
        d[g] = static_cast<std::uint8_t>(std::max(std::abs(xs[g] - from.x), std::abs(ys[g] - from.y))), far = std::max<int>(far, d[g]);
#endif
    std::array<std::uint16_t, 102> at{};
    for (int g = 0; g < n; ++g) ++at[d[g] + 2];
    --at[d[group] + 2]; // `group` itself is counted first instead
    at[1] = 1;
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
    const auto& layout = cambc::detail::layout();
    // A word's bush tiles take the stream's next bits in ascending order (each_in_square's): a tile at a
    // time cost ~30 fuel. Within the bush square, dist(t, p) <= range is the square of radius range.
    const int x0 = p.x - range, x1 = p.x + range, y0 = p.y - range, y1 = p.y + range;
    each_word_in_square(open_bushes(), p, DraftPlan::bush_range, [&](int cx, int cy, std::uint64_t w) {
        if (!w) return;
        const int n = __builtin_popcountll(w);
        std::uint64_t s = bits.get(std::min(n, 32));
        if (n > 32) s |= static_cast<std::uint64_t>(bits.get(n - 32)) << 32;
        std::uint64_t out = 0;
        for (; w; w &= w - 1, s >>= 1) out |= (w & (0 - w)) & (0 - (s & 1));
        if (range < DraftPlan::bush_range) {
            const int l = std::clamp(x0 - 8 * cx, 0, 8), h = std::clamp(x1 - 8 * cx, -1, 7);
            const int lo = std::clamp(y0 - 8 * cy, 0, 8), hi = std::clamp(y1 - 8 * cy, -1, 7);
            if (l > h || lo > hi) return;
            const std::uint64_t cols = 0x0101010101010101ull * (0xffu >> (7 - h) & 0xffu << l & 0xffu);
            const std::uint64_t rows = ~std::uint64_t{0} >> (8 * (7 - hi)) & ~std::uint64_t{0} << (8 * lo);
            out &= rows & cols;
        }
        words[cy * layout.chunk_stride + cx] |= out;
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

void crossing_tiles(const StaticMap& s, const bitboard& standable, bitboard& crossable, bool thin) {
    // Shifts are linear, so a shift of a union is the union of the shifts: each step below shares
    // its shifts where the obvious form makes one pair per direction (~180 fuel an op on 100x100).
    bitboard t{cambc::uninitialized}, ahead{cambc::uninitialized}, behind{cambc::uninitialized};
    bitboard left{cambc::uninitialized}, right{cambc::uninitialized};
    // Standable on two opposite sides: across, up and down, and both diagonals.
    standable.shift_right_into(-1, left);
    standable.shift_right_into(1, right);
    and_into(left, right, crossable);
    standable.shift_up_into(-1, ahead);
    standable.shift_up_into(1, behind);
    ahead &= behind;
    crossable |= ahead;
    left.shift_up_into(-1, ahead);
    right.shift_up_into(1, behind);
    ahead &= behind;
    crossable |= ahead;
    left.shift_up_into(1, ahead);
    right.shift_up_into(-1, behind);
    ahead &= behind;
    crossable |= ahead;
    or_into(s.holes, s.altar_tiles, t);
    crossable &= t;
    if (!thin) return;
    // No two may touch, or a field would walk along the line, which no dash does: keep every other
    // tile ((x + y) even), and of diagonal neighbours, which share that parity, the one on an even
    // row. Ties broken by height would chain: a diagonal run would keep only its lowest tile.
    // Both masks are written straight into the boards' 8x8 chunks, which start on even rows and
    // columns: (x + y) odd is 0xAA on even rows and 0x55 on odd ones; odd rows are 0xFF.
    const auto words = bitboard::raw_buffer_size() / sizeof(std::uint64_t);
    bitboard odd{cambc::uninitialized}, beside{cambc::uninitialized};
    std::fill_n(odd.ptr(), words, 0x55AA55AA55AA55AAull);
    crossable.shift_right_into(1, t);
    crossable.shift_right_into(-1, ahead);
    or_into(t, ahead, beside);
    crossable.shift_up_into(1, t);
    beside |= t;
    crossable.shift_up_into(-1, t);
    beside |= t;
    beside &= crossable;
    beside &= odd;
    drop(crossable, beside);
    bitboard odd_rows{cambc::uninitialized};
    std::fill_n(odd_rows.ptr(), words, 0xFF00FF00FF00FF00ull);
    crossable.shift_right_into(1, t);
    crossable.shift_right_into(-1, ahead);
    t |= ahead;
    t.shift_up_into(1, beside);
    t.shift_up_into(-1, ahead);
    beside |= ahead;
    beside &= odd_rows;
    drop(crossable, beside);
}

const bitboard& StaticMap::make_their_dash_walls() const {
    FuelMeter meter{"their_dash_walls"};
    bitboard standable{cambc::uninitialized}, crossable{cambc::uninitialized};
    or_into(camp_tiles, blocked_for_them, standable);
    not_into(standable, standable);
    // Unthinned: a thinned line drops crossings a dash makes (a diagonal one), and S must not exceed its walk.
    crossing_tiles(*this, standable, crossable, false);
    their_dash_walls_.emplace(blocked_for_them);
    drop(*their_dash_walls_, crossable);
    return *their_dash_walls_;
}

namespace {

void find_crossings(StaticMap& s) {
    crossing_tiles(s, s.standable, s.crossable);
    bitboard t{cambc::uninitialized}, ahead{cambc::uninitialized}, behind{cambc::uninitialized};
    copy_into(s.blocked_for_us, s.dash_walls);
    drop(s.dash_walls, s.crossable);
    square_dilate(s.crossable, 1, s.near_crossable);
    // The striking members' tiles: every camp tile but those of groups that never strike. Only
    // those within 2 of a crossable tile reach landing_dash_walls: with many groups, a pass over
    // them (~60 a group, ~14k on 200-group maps) costs more than finding the camp tiles near a
    // crossable tile first and testing those. Few tiles are drawn as squares (~40 each) rather
    // than dilated (8 board ops a tile of radius).
    const auto strikers = [&] {
        copy_into(s.camp_tiles, t);
        for (const auto& g : s.groups)
            if (!(g.strength > 0))
                for (const auto& m : g.members) set_tile(t, m.pos, false);
        square_dilate(t, 2, ahead);
    };
    constexpr std::uint32_t most = 128, square = 40;
    const std::uint64_t op = search_chunks() + 13;
    union Near {
        vec2 at[most]; // left unwritten: vec2's initialisers would cost ~8 a tile
        Near() {}
    } near_tiles;
    vec2* const near = near_tiles.at;
    std::uint32_t n = 0;
    if (s.groups.size() < 24) {
        strikers();
    } else if (n = board_count(s.crossable); n * square < 16 * op && n <= most) {
        (void)positions_into(s.crossable, near, most);
        behind.clear();
        for (std::uint32_t i = 0; i < n; ++i) draw_square(behind, near[i], 2);
    } else {
        square_dilate(s.near_crossable, 1, behind);
    }
    if (s.groups.size() >= 24) {
        and_into(s.camp_tiles, behind, t);
        if (n = board_count(t); n <= most) {
            (void)positions_into(t, near, most);
            std::uint32_t k = 0;
            for (std::uint32_t i = 0; i < n; ++i)
                if (s.groups[s.group_at(near[i])].strength > 0) near[k++] = near[i];
                else set_tile(t, near[i], false);
            if (k * square < 16 * op) {
                ahead.clear();
                for (std::uint32_t i = 0; i < k; ++i) draw_square(ahead, near[i], 2);
            } else {
                square_dilate(t, 2, ahead);
            }
        } else {
            strikers();
        }
    }
    and_into(s.crossable, ahead, behind);
    or_into(s.dash_walls, behind, s.landing_dash_walls);
}

// Out of line, so build()'s code is the same but for the call.
[[gnu::noinline, gnu::cold, noreturn]] void plan_check_failed(unsigned plan, unsigned ours) {
    char what[160];
    if (plan == 0)
        std::snprintf(what, sizeof what, "PLAN-CHECK no plan: check 0, map's %04x (the draft crashed, failed or ran "
                      "out of fuel before setting it)", ours);
    else
        std::snprintf(what, sizeof what, "PLAN-CHECK mismatch: plan's %04x, map's %04x (version, map size, group "
                      "count or first spawn tile)", plan, ours);
    // Resigning loses the game at once, so a broken handoff can't hide in an A/B; the throw only backs a failed resign.
    std::printf("%s\n", what);
    cambc::resign();
    throw std::runtime_error(what);
}
} // namespace

[[gnu::flatten]] std::unique_ptr<StaticMap> StaticMap::build() {
    FuelMeter meter{"build_static"};
    std::optional<FuelMeter> part{std::in_place, "static_new"};
    // Default-initialised, as World is in main.cc: the arena's fresh memory is already zero.
    auto s = std::unique_ptr<StaticMap>(new StaticMap);
    part.reset(), part.emplace("static_boards");
    s->built_round = round_now();
    s->width = cambc::map::width();
    s->height = cambc::map::height();
    s->symmetry = cambc::map::symmetry();
    s->team_a = cambc::detail::sdk_my_team() == 0;

    s->ally_spawn_tiles = s->ally_spawn.positions();
    // Read-once tile lists into a fixed buffer while they fit: positions() costs a count call, a
    // heap allocation, its zeroing and its free (~450).
    const auto tiles_of = [](const bitboard& b, vec2* buffer, std::vector<vec2>& spill) -> std::span<const vec2> {
        if (board_count(b) <= 64) return {buffer, positions_into(b, buffer, 64)};
        spill = b.positions();
        return spill;
    };
    static vec2 enemy_buffer[64], altar_buffer[64];
    std::vector<vec2> enemy_spill, altar_spill;
    const auto enemy_spawn_tiles = tiles_of(s->enemy_spawn, enemy_buffer, enemy_spill);
    const auto tile = [](vec2 p) { return p; };
    s->ally_spawn_centre = central_tile(s->ally_spawn_tiles, tile);
    // A's order by rows from (minX, minY); B's is its mirror image, so sorted by the mirror tile.
    s->landing_tiles = s->ally_spawn_tiles;
    // A spawn filling its box (every competition map's): its tiles sorted are the box's rows, and by
    // the mirror tile the mirrored box's rows mirrored back (mirror is an involution), without a sort.
    const auto& spawn_tiles = s->ally_spawn_tiles;
    vec2 lo = spawn_tiles.empty() ? vec2{0, 0} : spawn_tiles[0], hi = lo;
    for (const vec2 t : spawn_tiles) lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
    if (!spawn_tiles.empty() && static_cast<std::size_t>((hi.x - lo.x + 1) * (hi.y - lo.y + 1)) == spawn_tiles.size()) {
        vec2 mlo = lo, mhi = hi;
        if (!s->team_a) {
            const vec2 a = s->mirror(lo), b = s->mirror(hi);
            mlo = {std::min(a.x, b.x), std::min(a.y, b.y)}, mhi = {std::max(a.x, b.x), std::max(a.y, b.y)};
        }
        vec2* out = s->landing_tiles.data();
        for (int y = mlo.y; y <= mhi.y; ++y)
            for (int x = mlo.x; x <= mhi.x; ++x) *out++ = s->team_a ? vec2{x, y} : s->mirror({x, y});
    } else if (const std::size_t n = s->landing_tiles.size(); !s->team_a && n <= 64) {
        // Sorted as packed keys (mirrored tile's y, x, then the index): the comparator mirrored both
        // tiles at every comparison (~1.2k more). Distinct tiles have distinct keys: the same order.
        std::uint32_t keys[64];
        for (std::size_t i = 0; i < n; ++i) {
            const vec2 t = s->mirror(s->landing_tiles[i]);
            keys[i] = static_cast<std::uint32_t>(t.y) << 20 | static_cast<std::uint32_t>(t.x) << 8 | static_cast<std::uint32_t>(i);
        }
        std::sort(keys, keys + n);
        for (std::size_t i = 0; i < n; ++i) s->landing_tiles[i] = s->ally_spawn_tiles[keys[i] & 0xff];
    } else {
        std::sort(s->landing_tiles.begin(), s->landing_tiles.end(), [&](vec2 a, vec2 b) {
            if (!s->team_a) a = s->mirror(a), b = s->mirror(b);
            return a.y != b.y ? a.y < b.y : a.x < b.x;
        });
    }
    s->enemy_spawn_centre = central_tile(enemy_spawn_tiles, tile);
    for (const vec2 t : enemy_spawn_tiles) s->enemy_spawn_box.add(t);

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
    const auto altar_positions = tiles_of(s->altar_tiles, altar_buffer, altar_spill);
    s->altars.resize(altar_positions.size());
    for (std::size_t i = 0; i < altar_positions.size(); ++i) {
        s->altars[i].pos = altar_positions[i];
        s->altars[i].map_ = s.get();
        s->altar_lookup_[tile_index(altar_positions[i])] = static_cast<std::uint16_t>(i + 1);
    }

    // Camp groups, through the raw imports. Member stats come from the camp designs, read once
    // per camp type, with what a member of that type adds to its group's sums.
    // A group's sums are kept in SIMD lanes and its centre found here: a member costs ~40 fuel, where
    // scalar sums in locals cost ~150 (~100k on a 450-member map, every champion's first turn).
    // A member's first 16 bytes are its 4 layout words, copied whole.
    namespace raw = cambc::detail;
    static_assert(offsetof(CampMember, type) == 4 && offsetof(CampMember, pos) == 8 && offsetof(CampMember, max_health) == 16
                  && offsetof(CampMember, strength) == 20 && offsetof(CampMember, reach) == 24 && sizeof(CampMember) == 28);
    // A type's lanes: {health, strength, reach, 0} (CampMember's last 12 bytes, and the float sums
    // and the reach's max) and {cluster gems, cluster gold, monolith, 0} (integer sums).
    struct alignas(16) Kind {
        float health, strength;
        int reach, zero;
        int cluster_gems, cluster_gold, monolith, zero2;
    };
    const auto kind_of = [](std::uint32_t raw_type) __attribute__((noinline)) {
        raw::camp_design d{};
        raw::check(raw::sdk_camp_design(raw_type, &d));
        const auto type = static_cast<cambc::camp_type>(raw_type);
        return Kind{d.base_stats.base_health, d.base_stats.base_strength, d.base_stats.base_attack_range, 0,
                    type == cambc::camp_type::gem_cluster ? gem_cluster_gems : 0,
                    type == cambc::camp_type::gold_cluster ? gold_cluster_gold : 0, type == cambc::camp_type::monolith, 0};
    };
    Unwritten<Kind, 32> kinds;
    std::uint32_t designed = 0; // bit t: kinds.a[t] read
    const auto layout = engine::camp_layout();
    const std::uint32_t* const words = layout.data();
    const std::size_t word_count = layout.size();
    StaticMap& map = *s;
    // The counts from the engine's group count: a walk over the layout cost ~30 fuel a group.
    std::uint32_t engine_groups = 0;
    ok(raw::sdk_map_num_camp_groups(&engine_groups));
    std::size_t group_count = engine_groups;
    std::size_t member_count = (word_count - 5 * group_count) / 4;
    if (5 * group_count > word_count || (word_count - 5 * group_count) % 4 != 0) {
        group_count = member_count = 0;
        for (std::size_t i = 0; i + 5 <= word_count; i += 5 + 4 * words[i + 4]) ++group_count, member_count += words[i + 4];
    }
    // One spare: a member's 12 stat bytes are written as 16, over the next member's first 4.
    StaticArray<CampMember> member_pool(member_count + 1);
    std::size_t members_used = 0;
    map.camp_members = StaticArray<CampMember>(member_pool, members_used, member_count);
    members_used = 0;
    // Made in one resize, which writes nothing (UnwrittenAllocator); each constructed as it is read.
    map.groups.resize(group_count);
    CampGroup* next_group = map.groups.data();
    int max_reach = 0;
    bool monolith_only = true, big = false, other = false;
    std::uint16_t* const group_lookup = map.group_lookup_.data();
    const int width = map.width;
    std::uint16_t lookup = 0; // group index + 1
    for (std::size_t i = 0; i + 5 <= word_count;) {
        ++lookup;
        auto& g = *::new (static_cast<void*>(next_group++)) CampGroup();
        g.handle = words[i];
        g.map_ = &map;
        g.gold = static_cast<int>(words[i + 1]);
        g.gems = static_cast<int>(words[i + 2]);
        g.respawn = static_cast<std::int32_t>(words[i + 3]);
        const auto size = words[i + 4];
        i += 5;
        const auto count = std::min<std::size_t>(size, (word_count - i) / 4);
        g.members = StaticArray<CampMember>(member_pool, members_used, count);
        CampMember* const out = g.members.data();
        v128_t sums = wasm_f32x4_splat(0.0f), most = wasm_i32x4_splat(0), extra = wasm_i32x4_splat(0), at = wasm_i32x4_splat(0);
        const std::uint32_t* w = words + i;
        i += 4 * count;
        for (CampMember* o = out; o != out + count; ++o, w += 4) {
            const auto raw_type = w[1];
            Kind other;
            Kind* k = &other;
            if (raw_type < 32 && (designed >> raw_type & 1)) [[likely]] {
                k = &kinds.a[raw_type];
            } else {
                if (raw_type < 32) k = &kinds.a[raw_type], designed |= 1u << raw_type;
                *k = kind_of(raw_type);
            }
            const v128_t record = wasm_v128_load(w);
            const v128_t stats = wasm_v128_load(k);
            wasm_v128_store(o, record);
            wasm_v128_store(&o->max_health, stats);
            sums = wasm_f32x4_add(sums, stats);
            most = wasm_i32x4_max(most, stats);
            extra = wasm_i32x4_add(extra, wasm_v128_load(&k->cluster_gems));
            at = wasm_i32x4_add(at, record);
            const vec2 pos{static_cast<std::int32_t>(w[2]), static_cast<std::int32_t>(w[3])};
            set_tile(map.camp_tiles, pos);
            group_lookup[pos.x + pos.y * width] = lookup;
        }
        g.health = wasm_f32x4_extract_lane(sums, 0);
        g.strength = wasm_f32x4_extract_lane(sums, 1);
        const int reach = wasm_i32x4_extract_lane(most, 2);
        g.reach = reach;
        const int cluster_gems = wasm_i32x4_extract_lane(extra, 0), cluster_gold = wasm_i32x4_extract_lane(extra, 1);
        const int monolith = wasm_i32x4_extract_lane(extra, 2);
        g.has_monolith = monolith != 0;
        g.cluster_gems = cluster_gems;
        g.cluster_gold = cluster_gold;
        max_reach = std::max(max_reach, reach);
        const int gems = g.gems;
        monolith_only &= monolith != 0 || gems == 0;
        if (!monolith && gems >= params::big_gems) big = true;
        else if (!monolith && gems > 0) other = true;
        // central_tile: the first member nearest the members' mean.
        const auto n = static_cast<int>(count);
        if (n == 1) g.centre = out[0].pos;
        if (n > 1) {
            const vec2 mean{wasm_i32x4_extract_lane(at, 2) / n, wasm_i32x4_extract_lane(at, 3) / n};
            int nearest = 1 << 30;
            vec2 centre = out[0].pos;
#pragma clang loop vectorize(disable)
            for (int k = 0; k < n; ++k) {
                const int dx = out[k].pos.x - mean.x, dy = out[k].pos.y - mean.y;
                if (const int d = dx * dx + dy * dy; d < nearest) nearest = d, centre = out[k].pos;
            }
            g.centre = centre;
        }
    }
    for (auto* const end = map.groups.data() + map.groups.size(); next_group != end;) ::new (static_cast<void*>(next_group++)) CampGroup();
    map.groups.resize(lookup); // the same count, but for a layout cut short
    map.max_camp_reach = max_reach;
    debug_block({
        if (max_reach > max_camp_range) std::printf("CAMP-REACH %d above max_camp_range\n", max_reach);
    });
    s->monolith_only = monolith_only;
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
        const bool matches = header.check == plan_check(*s);
        // Local builds only: a plan we cannot use is a broken draft handoff that the fallback below would
        // hide. Thrown on every first-turn retry, so the bot never plays. The draft writes no check past
        // 255 groups.
        if constexpr (local_build) {
            if (!matches && !cambc::is_draft() && (header.check != 0 || n <= 255)) plan_check_failed(header.check, plan_check(*s));
        }
        PlanIndex index;
        const bool indexed = matches && read_index(*plan, header, n, spawn, index);
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
        if (matches && header.steps
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
            const auto type = engine::type(engine::id(handles[i]));
            auto& b = side == team::ally ? list.emplace_back(ChampionBelief::Ally{})
                      : facts(type).has_dash() ? list.emplace_back()
                                               : list.emplace_back(ChampionBelief::Walker{});
            b.handle = handles[i];
            b.side = side;
            b.index = i;
            b.is_self = handles[i] == self_handle;
            b.type = type;
            b.pos = side == team::ally ? s.ally_spawn_centre : s.enemy_spawn_centre;
            b.pos_round = round;
            b.pos_source = Source::inferred;
            b.health = b.max_health = b.facts().health.base;
            b.strength = b.facts().strength.base;
            b.focus = b.facts().focus.base;
            if (side == team::enemy || b.is_self) b.shield_slot = static_cast<std::int8_t>(b.facts().slot_of(AbilityKind::shield));
            if (side == team::enemy) fix_at_spawn(b, s.enemy_spawn, s.enemy_spawn_box, {1, -1});
            if (b.is_self) self_index = i;
            if (i < 16) b.rank = b.next_rank = i; // rank_turns' answer while every priority is 0
        }
    }
    me_ = allies.data() + self_index;
    ally_count_ = static_cast<int>(allies.size());
    enemy_count_ = static_cast<int>(enemies.size());
    team_a_ = s.team_a;

    // The first update keeps these as last round's ranks: with every priority 0, rank_turns would
    // leave each rank its index (set above).
    ranks_stale_ = {false, false};
    ranked_round_ = {round, round};
    camps.clear();
    // Through raw pointers: indexing the vectors reloaded their bounds after every store (~70 fuel a group).
    const CampGroup* const group = s.groups.data();
    const std::size_t groups = s.groups.size();
    std::size_t member_count = 0, health_used = 0, rounds_used = 0;
    for (std::size_t g = 0; g < groups; ++g) member_count += group[g].members.size();
    StaticArray<float> health_pool(member_count);
    StaticArray<int> rounds_pool(member_count);
    // Each a copy of one start belief, held in SIMD locals, and its slices: constructing each wrote
    // every field (~110 fuel a group), and a memcpy is a memory.copy at a fuel a byte.
    camps.resize(groups);
    static_assert(sizeof(CampBelief) == 104 && std::is_trivially_copyable_v<CampBelief>);
    const CampBelief start;
    const auto* from = reinterpret_cast<const unsigned char*>(&start);
    const v128_t s0 = wasm_v128_load(from), s1 = wasm_v128_load(from + 16), s2 = wasm_v128_load(from + 32);
    const v128_t s3 = wasm_v128_load(from + 48), s4 = wasm_v128_load(from + 64), s5 = wasm_v128_load(from + 80);
    const v128_t s6 = wasm_v128_load64_zero(from + 96);
    auto* to = reinterpret_cast<unsigned char*>(camps.data());
    for (std::size_t g = 0; g < groups; ++g, to += sizeof(CampBelief)) {
        wasm_v128_store(to, s0), wasm_v128_store(to + 16, s1), wasm_v128_store(to + 32, s2);
        wasm_v128_store(to + 48, s3), wasm_v128_store(to + 64, s4), wasm_v128_store(to + 80, s5);
        wasm_v128_store64_lane(to + 96, s6, 0);
        auto& c = *reinterpret_cast<CampBelief*>(to);
        const auto size = group[g].members.size();
        c.health = StaticArray<float>(health_pool, health_used, size);
        c.health_round = StaticArray<int>(rounds_pool, rounds_used, size);
    }
    // The groups' members are consecutive slices of s.camp_members, as the healths are of the pool:
    // one pass over all of them, where a loop a group cost ~100 fuel to set up.
    const CampMember* const member = s.camp_members.data();
    float* const health = health_pool.data();
    for (std::size_t i = 0; i < member_count; ++i) health[i] = member[i].max_health;
    if (member_count) std::memset(rounds_pool.data(), 0, member_count * sizeof(int));
    clear_health.assign(groups + 4, 0.0f);
    for (std::size_t g = 0; g < groups; ++g) clear_health[g] = group[g].health;
    altars.assign(s.altars.size(), AltarBelief{});
    stirring_.assign((s.groups.size() + 63) / 64, 0);
    cleared_.assign((s.groups.size() + 63) / 64, 0);
    respawning_.assign((s.groups.size() + 63) / 64, 0);
}

void World::update() {
    round = static_cast<int>(round_now());
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
    previous_update_ = updated_round_;
    updated_round_ = round;
    if (ranks_stale_[0] || ranks_stale_[1]) rank_turns();
    my_slot_now_ = slot(me(), round), my_slot_next_ = slot(me(), round + 1);
    update_champions(true);
    sight_pos_ = clear_pos_ = turn_start = me().pos;
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
        // Not stun_pending(), which throws (~3.9k) for one we killed: it has no buffs to read.
        std::int32_t code;
        for (const auto& buff : engine::buffs(engine::id(e.handle), code))
            if (buff.type == static_cast<std::uint32_t>(cambc::buff_types::stun) && buff.data.stun.duration > 0) e.stun_pending = changed = true;
        // The stun cancelled its recall, tribute or teleport: it stays where it is, its bag kept.
        if (e.stun_pending) e.channel = e.seen_channel = Channel::none, e.tp_dest = {-1, -1};
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
                // Died since our last update (in its round after it, or a later one) or, mid-turn, this
                // round. Death in round D respawns in D+61, or D+60 if it died before its own turn.
                const int earliest_death = !full ? round : previous_update_ >= 0 ? previous_update_ : round - 1;
                b.respawn_earliest = earliest_death + cambc::constants::respawn_time;
                b.respawn_latest = round + cambc::constants::respawn_time + 1;
                // Nothing reads where a dead champion could be.
                b.tracked = false;
            }
            b.alive = false;
            b.visible = false;
            drop_bag(b);
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
            b.scale = b.dealt; // full health; emblems are kept
            b.shield = 0, b.shield_turns = 0;
            drop_bag(b);
            b.ready_round = {b.respawned_round + 1, b.respawned_round + 1};
            // At its respawn turn, which allows no walk: growth starts with the turn after.
            if (enemy) fix_at_spawn(b, s.enemy_spawn, s.enemy_spawn_box, {b.respawned_round, slot(b, b.respawned_round)});
        }
    }

    b.visible = info != nullptr;
    if (!info) {
        // A shield expires at its owner's turn start, as a channel completes. Damage out of sight
        // may have drained it sooner.
        if (b.shield > 0
            && (round > b.shield_end_round || (round == b.shield_end_round && slot(b, round) < my_slot_now_)))
            b.shield = 0, b.shield_turns = 0;
        // A channel completes at its owner's turn start.
        // A stun, lock or damage may have cancelled it: a tribute's bag is emptied by update_scores
        // only when the score shows it landed, and a recall leaves `pos` to the last sighting.
        if (b.channel != Channel::none
            && (round > b.channel_end_round || (round == b.channel_end_round && slot(b, round) < my_slot_now_))) {
            // An unkept recall from a feinting team (ours, enemy_feints_) is cancelled at its next turn
            // start: it does not heal. It may still have been kept out of sight, so it may be home.
            if (b.channel == Channel::recall) {
                if (b.recall_kept || (enemy && !enemy_feints_)) b.health = b.max_health, b.scale = b.dealt;
                if (enemy) {
                    or_into(b.possible, s.enemy_spawn, b.possible);
                    b.possible_box.add(s.enemy_spawn_box);
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
    if (last_seen >= round - 2 && info->health < b.health - 0.01f) b.hurt_round = round;
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
    std::optional<int> left;
    if (b.channel != Channel::none) {
        left = engine::channel_time(h);
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
        if (in_bounds(b.tp_dest)) set_tile(b.possible, b.tp_dest), b.possible_box.add(b.tp_dest);
        else or_into(b.possible, within(s.open_for_them, b.pos, teleport_crystal_range), b.possible), b.possible_box.add(b.pos, teleport_crystal_range);
        also_undashed(b, b.possible);
        b.lineage = 0;
    }
    const int earliest = b.respawned_round + 1;
    std::array<int, 2> cds;
    for (int slot = 0; slot < 2; ++slot) {
        cds[slot] = engine::cooldown(h, static_cast<std::uint32_t>(slot));
        b.ready_round[slot] = std::max(fire_round(round, cds[slot], acted), earliest);
    }
    if (b.shield_slot >= 0) {
        read_shield(b, cds);
        b.shield_end_round = fire_round(round, b.shield_turns, acted);
    }
    // In observe() too, for a champion first seen after our move.
    b.gems = engine::gems(h);
    // Emblems change only with a shard bought, which adds to a stat, or with Tavi's sales. Prism's
    // Focus also moves with its gems.
    const auto passive = b.facts().passive;
    const std::array<float, 4> key{b.max_health, b.strength, b.focus, passive == Passive::gem_focus ? static_cast<float>(b.gems) : 0.0f};
    // Compared as bits: the stats are never NaN, and none reads as -0.
    if (!wasm_i32x4_all_true(wasm_i32x4_eq(wasm_v128_load(key.data()), wasm_v128_load(b.items_key.data()))) || passive == Passive::remote_shop) {
        b.items_key = key;
        const auto e = engine::emblems(h);
        b.fast_recall = e.home;
        b.taken = e.durability ? durability_taken : 1.0f;
        b.camp_taken = b.taken * (e.jungle ? jungle_camp_taken : 1.0f);
        b.fast_tribute = e.tribute;
        b.fast_capture = e.capture;
        b.prospector = e.prospector;
        b.dealt = e.dealt;
        b.camp_dealt = e.camp_dealt;
        b.scale = damage_scale(passive, b.health, b.max_health) * b.dealt; // as above, with this `dealt`
    }
    // kept_recall, from the state and channel time read above.
    b.recall_kept = b.channel == Channel::recall && left && *left < b.recall_turns() - 1;
    // A real recall shows a fresh start once; two turns in a row is a cancel and restart.
    if (enemy && acted && b.channel == Channel::recall && left && *left == b.recall_turns() - 1) {
        if (b.fresh_recall_round == round - 1 && b.hurt_round != round) enemy_feints_ = true;
        b.fresh_recall_round = round;
    }
}

void World::read_priorities(bool new_round) {
    static std::int32_t priority, next_priority;
    const int now = round;
    bool enemy_change = enemy_priorities_change;
    for (const int side : {0, 1}) {
        const int ranked = ranked_round_[side];
        bool stale = ranks_stale_[side];
        // Our team packs a rank above the payload that differs for each ally, or leaves its priority 0
        // (unset): a change in the payload alone never changes the allies' order.
        const int shift = side == 0 ? priority_payload_bits : 0;
        for (auto& b : side == 0 ? allies : enemies) {
            // This round's order before anything dates a turn in it.
            if (new_round) b.prev_rank = b.rank;
            const auto h = engine::id(b.handle);
            // Fails for champions out of sight. A priority read in round r applies from r + 1:
            // ranks change when a round passes one unread.
            if (cambc::detail::sdk_bc_champion_priority(h, 0, &priority) != 0
                || cambc::detail::sdk_bc_champion_priority(h, 1, &next_priority) != 0) {
                stale |= (b.next_priority >> shift) != (b.priority >> shift) && ranked <= b.priority_round && b.priority_round < now;
                continue;
            }
            if (b.side == team::enemy
                && (next_priority != priority || (b.priority_round >= 0 && b.priority_round < now && priority != b.next_priority)))
                enemy_change = true;
            stale |= (priority >> shift) != (b.priority >> shift) || (next_priority >> shift) != (b.next_priority >> shift);
            b.priority = priority;
            b.next_priority = next_priority;
            b.priority_round = now;
        }
        ranks_stale_[side] = stale;
    }
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

void World::camp_moved(std::size_t g) {
    ++camps_version;
    if (camps_dirty.size() <= g / 64) camps_dirty.resize(g / 64 + 1);
    camps_dirty[g / 64] |= std::uint64_t{1} << (g & 63);
    const auto& c = camps[g];
    const auto& members = map().groups[g].members;
    float sum = 0;
    bool sound = true; // an unread (negative) member's sum could cancel
    if (c.state != CampState::cleared)
        for (std::size_t i = 0; i < members.size(); ++i) {
            const float hp = c.state == CampState::respawning ? members[i].max_health : c.health[i];
            sound &= hp >= 0;
            sum += hp;
        }
    clear_health[g] = sound ? sum : 0.0f;
}

void World::note_capture(int group, int respawn_round) {
    if (group < 0 || group >= static_cast<int>(camps.size()) || respawn_round <= round) return;
    auto& c = camps[group];
    c.told_respawn = respawn_round;
    if (c.state_round == round) return; // in view: our own reading stands
    if (static_cast<std::size_t>(group) < 64 * camps_pending_.size()) camps_pending_[group >> 6] |= std::uint64_t{1} << (group & 63);
    const bool moved = c.state != CampState::respawning;
    c.version += moved;
    c.state = CampState::respawning;
    c.respawn_round = respawn_round;
    c.awake = Awake::asleep;
    c.asleep = 0;
    c.holder.reset();
    c.held_since = -1;
    if (moved) camp_moved(static_cast<std::size_t>(group));
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
    b.fixed_tile = {-1, -1}; // it follows a change to `possible`
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
void World::fix_at_spawn(ChampionBelief& b, const bitboard& spawn, const GrowBox& spawn_box, Moment when) {
    b.fixed_tile = {-1, -1};
    copy_into(spawn, b.possible);
    b.possible_box = spawn_box;
    mark_fixed(b, when);
    b.lineage = 0x80000000u | static_cast<std::uint32_t>(when.round) << 6 | static_cast<std::uint32_t>(when.slot + 1);
}

// A visible enemy is fixed at every update: its boards are rewritten only when it has moved or they changed.
[[gnu::always_inline]] void World::fix(ChampionBelief& b, vec2 tile, Moment when) {
    if (b.fixed_tile == tile) {
        if (b.facts().has_dash()) b.undashed_all = true;
        b.tracked = true;
        b.fixed = b.at = when;
        b.turns_since_fixed = 0;
    } else {
        clear_board(b.possible);
        set_tile(b.possible, tile);
        b.possible_box.set(tile);
        mark_fixed(b, when);
        b.fixed_tile = tile;
    }
    b.lineage = 0;
}

namespace {

// Each of the n <= 16 priorities' rank, the count of those ahead of it: higher, or equal at a lower
// index (handles ascend with the index). Up to 8 compare 4 lanes at once; an insertion sort, or the
// same loops vectorised by the compiler, cost two to three times more.
template <class Write> [[gnu::always_inline]] inline void rank_by(const std::int32_t* p, int n, Write&& write) {
    const unsigned valid = (1u << n) - 1;
    if (n <= 8) {
        const v128_t a = wasm_v128_load(p), b = wasm_v128_load(p + 4); // lanes from n on are masked out
#pragma clang loop vectorize(disable) unroll(disable)
        for (int i = 0; i < n; ++i) {
            const v128_t x = wasm_i32x4_splat(p[i]);
            const unsigned ahead = static_cast<unsigned>(wasm_i32x4_bitmask(wasm_i32x4_gt(a, x)) | wasm_i32x4_bitmask(wasm_i32x4_gt(b, x)) << 4);
            const unsigned tied = static_cast<unsigned>(wasm_i32x4_bitmask(wasm_i32x4_eq(a, x)) | wasm_i32x4_bitmask(wasm_i32x4_eq(b, x)) << 4);
            write(i, std::popcount((ahead | (tied & ((1u << i) - 1))) & valid));
        }
        return;
    }
    for (int i = 0; i < n; ++i) {
        unsigned ahead = 0, tied = 0;
        for (int j = 0; j < n; ++j) {
            ahead |= static_cast<unsigned>(p[j] > p[i]) << j;
            tied |= static_cast<unsigned>(p[j] == p[i]) << j;
        }
        write(i, std::popcount((ahead | (tied & ((1u << i) - 1))) & valid));
    }
}

} // namespace

void World::rank_turns() {
    const auto stale = ranks_stale_;
    const int now = round;
    for (int side = 0; side < 2; ++side) {
        if (!stale[side]) continue;
        ranks_stale_[side] = false;
        ranked_round_[side] = now;
        auto& team = side == 0 ? allies : enemies;
        ChampionBelief* const members = team.data();
        const int n = std::min(static_cast<int>(team.size()), 16);
        // Whether this round's priorities order the team as its next ones do (allies compared above
        // the payload bits, as in read_priorities): next round's ranks are then this round's.
        const int shift = side == 0 ? priority_payload_bits : 0;
        bool same = true;
        Unwritten<std::int32_t, 16> priority;
        for (int i = 0; i < n; ++i) {
            const auto& x = members[i];
            const std::int32_t p = now > x.priority_round ? x.next_priority : x.priority;
            same &= (p >> shift) == (x.next_priority >> shift);
            priority.a[static_cast<std::size_t>(i)] = p;
        }
        rank_by(priority.a.data(), n, [&](int i, int rank) { members[i].rank = rank; });
        if (same) {
            for (int i = 0; i < n; ++i) members[i].next_rank = members[i].rank;
            continue;
        }
        for (int i = 0; i < n; ++i) priority.a[static_cast<std::size_t>(i)] = members[i].next_priority;
        rank_by(priority.a.data(), n, [&](int i, int rank) { members[i].next_rank = rank; });
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
    b.fixed_tile = {-1, -1};
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
        b.possible_box.add(s.enemy_spawn_box);
        if (undashed_read) or_into(b.undashed, s.enemy_spawn, b.undashed);
    }
    FuelMeter meter{"track"};
    if (!dasher) {
        b.possible_box.grow(turns);
        walk(b.possible, s, turns, land);
        return false;
    }
    // A dash readies once per cooldown: from the undashed tiles it adds 2 steps once in these
    // turns; tiles already reached with a dash grow only by walking until the next is ready.
    const bool dash = dash_ready(b, round);
    // A dash (from undashed, within possible) adds dash_range king steps to the walk's.
    b.possible_box.grow(turns + (dash ? dash_range : 0));
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
        // `at` only dates the turns counted: a lineage's tiles grown by as many turns are the same tiles.
        if (t.before != b.lineage || t.turns != turns || t.tsf != b.turns_since_fixed || t.fixed != b.fixed
            || t.dasher != dasher || t.fast_recall != b.fast_recall || t.dash != (dasher && dash_ready(b, round)))
            continue;
        const auto& leader = enemies[t.leader];
        b.fixed_tile = {-1, -1};
        copy_into(leader.possible, b.possible);
        b.possible_box = leader.possible_box;
        if (dasher && leader.turns_since_fixed < ability_cooldown) copy_into(leader.undashed, b.undashed);
        b.undashed_all = leader.undashed_all;
        b.tracked = leader.tracked;
        b.at = to;
        b.turns_since_fixed = leader.turns_since_fixed;
        b.lineage = t.after;
        return;
    }
    Tracked t{b.lineage, 0, b.index, turns, b.turns_since_fixed, b.fixed, dasher, false, b.fast_recall};
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
    b.fixed_tile = {-1, -1};
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

// By tile: a camp tile in update_camps' view.
std::array<std::uint8_t, 100 * 100> camp_tile_seen{};
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
    // The camp tiles in view, by tile, follow those that came into or left view since the last
    // update: members are then looked up rather than tested on the board.
    static bitboard seen{cambc::uninitialized}, before{cambc::uninitialized}, changed{cambc::uninitialized};
    and_into(visible, s.camp_tiles, seen);
    const bool first = group_visible_.size() != words;
    if (first) group_visible_.assign(words, 0);
    if (first || !boards_equal(seen, before)) {
        ++camp_view_;
        if (!first) xor_into(seen, before, changed);
        auto* const visible_bits = group_visible_.data();
        const int width = s.width;
        constexpr int most = 2 * (17 * 17 + 13 * 13); // both views
        // Groups a tile left, each looked over once its tiles are all toggled.
        union Left {
            std::array<std::uint16_t, most> at;
            Left() {}
        } left;
        int lefts = 0;
        for (auto p : Tiles<most>{first ? seen : changed}) {
            const int g = s.group_at(p);
            const std::uint64_t bit = std::uint64_t{1} << (g & 63);
            auto& word = visible_bits[g >> 6];
            if ((camp_tile_seen[p.x + p.y * width] ^= 1) != 0) word |= bit;
            else if (word & bit) word &= ~bit, left.at[lefts++] = static_cast<std::uint16_t>(g);
        }
        for (int k = 0; k < lefts; ++k) {
            const int g = left.at[k];
            for (const auto& m : s.groups[g].members)
                if (camp_tile_seen[m.pos.x + m.pos.y * width]) {
                    visible_bits[g >> 6] |= std::uint64_t{1} << (g & 63);
                    break;
                }
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
            // Settled: its pending and stirring bits stand as last round's reading set them.
            bool settled = false;
            guard("camp", [&] { settled = in_view && camp_settled(s.groups[g], camps[g]); });
            if (settled) continue;
            guard("camp", [&] { update_camp(g, in_view, views); });
            const auto& c = camps[g];
            const bool pending = (c.state == CampState::cleared && c.holder) || c.state == CampState::respawning || c.awake == Awake::awake;
            camps_pending_[w] = pending ? camps_pending_[w] | bit : camps_pending_[w] & ~bit;
            if (c.version != version) camp_moved(g);
            note_stirring(static_cast<int>(g));
        }
    }
}

// A group in view that reads as it did last round, settled without reading its members: every member
// in view now was then, and it is respawning before the round it returns, or alive and asleep with a
// member read asleep then that still is. Damage or a stun wakes every asleep member, which sleeps again
// no sooner than 3 camp phases on, so no member's health has changed. Most visible groups, most turns.
bool World::camp_settled(const CampGroup& G, CampBelief& c) {
    if (c.state_round != round - 1) return false;
    const bool respawning = c.state == CampState::respawning && c.respawn_round == c.read_respawn && round < c.respawn_round;
    if (!respawning && !(c.state == CampState::alive && c.awake == Awake::asleep && c.witness >= 0)) return false;
    const auto& members = G.members;
    const std::size_t n = members.size();
    if (n > 64) return false;
    std::uint64_t seen = 0;
    // Settled last round with the same camp tiles in view and no version since: the same members
    // are in view, each with health_round set to last round then.
    if (c.settled_round == round - 1 && c.settled_view == camp_view_ && c.settled_version == c.version) {
        seen = c.settled_seen;
    } else {
        const int width = map().width;
        for (std::size_t i = 0; i < n; ++i)
            if (camp_tile_seen[members[i].pos.x + members[i].pos.y * width]) {
                if (c.health_round[i] != round - 1) return false;
                seen |= std::uint64_t{1} << i;
            }
    }
    if (!respawning && engine::camp_awake(members[static_cast<std::size_t>(c.witness)].handle) != Awake::asleep) return false;
    c.settled_round = round, c.settled_version = c.version, c.settled_view = camp_view_, c.settled_seen = seen;
    for (; seen; seen &= seen - 1) c.health_round[static_cast<std::size_t>(__builtin_ctzll(seen))] = round;
    c.state_round = round;
    return true;
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
            c.held_since = -1;
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
        c.respawn_round = c.read_respawn = round + timer;
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
        int harmless = -1, witness = -1;
        const bool cleared = c.state == CampState::cleared;
        const int width = map().width;
        // One loop per liveness: a group cleared or respawning has no live member to read.
        const auto read_members = [&](auto live_group) {
            constexpr bool live = decltype(live_group)::value;
            for (std::size_t i = 0; i < n; ++i) {
                const auto& m = members[i];
                const std::uint64_t bit = i < 64 ? std::uint64_t{1} << i : 0;
                if (!camp_tile_seen[m.pos.x + m.pos.y * width]) {
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
                if (read == Awake::asleep) read_asleep |= bit, witness = witness < 0 ? static_cast<int>(i) : witness;
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
        else if (!striker_asleep && !striker_unread && harmless >= 0) {
            seen_awake = engine::camp_awake(members[harmless].handle);
            if (seen_awake == Awake::asleep) witness = harmless;
        }
        c.awake = awake;
        c.version = version;
        c.witness = witness;
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
            && (c.is_self || (c.visible ? !c.acted : slot(c, round) > my_slot_now_)))
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
    // Nobody shares lock sightings, and either side's can be broken out of our sight: one unseen this
    // long is as likely broken as not, and forgetting it sooner would turn bags back and forth between altars.
    constexpr int lock_memory = 20;
    // Only the read below sets a lock belief: with none held, forgetting and the tributes' proof clear nothing.
    if (lock_beliefs_) {
        bool held = false;
        for (auto& b : altars) {
            if (round - b.seen_round >= lock_memory) {
                if (b.enemy_lock) b.enemy_lock = false, b.enemy_lock_hits = 0;
                b.ally_lock = false;
            }
            held |= b.enemy_lock || b.ally_lock;
        }
        lock_beliefs_ = held;
        // An ally's tribute under way proves no enemy lock at its altar: placing one cancels every tribute
        // there, and one blocks our tributes (rules altar_locks). Only where one altar is in its range.
        for (const auto& a : allies) {
            if (!held || !a.alive || (!a.is_self && !a.visible) || a.channel != Channel::tribute) continue;
            int at = -1, n = 0;
            for (std::size_t k = 0; k < s.altars.size(); ++k)
                if (dist(a.pos, s.altars[k].pos) <= static_cast<int>(cambc::constants::submit_gems_range)) at = static_cast<int>(k), ++n;
            if (n == 1 && altars[at].enemy_lock) altars[at].enemy_lock = false, altars[at].enemy_lock_hits = 0;
        }
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
        lock_beliefs_ = true;
        if (lock.team == own) {
            belief.ally_lock = true;
        } else {
            belief.enemy_lock = true;
            belief.enemy_lock_hits = static_cast<int>(lock.hits_remaining);
        }
    }
}

World::Tributing World::tributing_enemies() const {
    Tributing t;
    for (std::size_t i = 0; i < enemies.size() && i < t.gems.size(); ++i)
        if (enemies[i].alive && enemies[i].channel == Channel::tribute) t.mask |= 1u << i, t.gems[i] = enemies[i].gems;
    return t;
}

[[gnu::flatten]] void World::update_scores(const Tributing& tributing) {
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

    // Enemy tributes just landed: empty the bags of whoever most plausibly made them (a visible
    // one's was just read). Those tributing before this update and no longer: one alone made it
    // (capture shares paid during its channel may have grown its bag); several, the only set of
    // them whose bags (as before this update) sum to the delta. Failing that, the one unseen
    // enemy whose bag matches.
    std::uint32_t ended = 0;
    for (std::size_t i = 0; i < enemies.size() && i < tributing.gems.size(); ++i)
        if ((tributing.mask >> i & 1) && enemies[i].alive && enemies[i].channel != Channel::tribute) ended |= 1u << i;
    std::uint32_t landed = 0;
    if (std::popcount(ended) == 1) {
        landed = ended;
    } else {
        int matches = 0;
        // Each nonempty subset of `ended`.
        for (std::uint32_t sub = ended; sub; sub = (sub - 1) & ended) {
            int sum = 0;
            for (std::uint32_t m = sub; m; m &= m - 1) sum += tributing.gems[std::countr_zero(m)];
            if (sum == enemy_delta) landed = sub, ++matches;
        }
        if (matches != 1) landed = 0;
    }
    if (landed) {
        for (std::uint32_t m = landed; m; m &= m - 1)
            if (auto& b = enemies[std::countr_zero(m)]; !b.visible) drop_bag(b);
        return;
    }
    ChampionBelief* tributer = nullptr;
    int candidates = 0;
    for (auto& b : enemies)
        if (b.alive && !b.visible && b.gems == enemy_delta) tributer = &b, ++candidates;
    if (candidates == 1) {
        drop_bag(*tributer);
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
