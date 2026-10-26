#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <bit>
#include <cstdint>
#include <cstring>
#include <type_traits>
#include <vector>

namespace aph {

struct StaticMap;

// The draft memory as one bit stream, least significant bit of each byte first: the header
// (PlanHeader), then the sections in this order. A section champions decode as they build the
// static map just follows the one before. One read lazily, or after a section whose length takes
// work to find, starts at an offset in the header (0: absent). Each takes what is left of the
// stream when the draft writes it, in this order, and never assumes a size.
//  1. Steps, decoded at build. Walking steps to each group's centre from our spawn, from theirs
//     and from the tribute tiles of every altar: per group, Rice-coded, 0 for unreachable, else
//     steps + 1 less a Chebyshev lower bound (steps_bound). Mirrored, a group's enemy steps are
//     instead the zigzag of their difference from its mirror group's ally steps: the same but for
//     the centres' tie-break. Then, with spawn_offsets, per group reachable from our spawn: 1 if
//     every spawn tile's steps beyond the whole spawn's are spawn_offset's, else 2 bits a tile.
//  2. Attack tiles, indexed on first use, from where the steps end. A bit per member of every
//     group, by group: 1 if a bush tile within bush_range sees it. Then for each member with a 1
//     in the first attack_groups groups, a bit per open bush tile in its bush_range square, in
//     each_in_square's order. A range's attack tiles are StaticMap::sight_off_bushes plus those
//     bush tiles within it, which the draft checked.
//  3. Leads at leads_at, from where the attack tiles end, read in round 1: for each of
//     lead_bodies bodies (our champions in id order) `leads` codes of lead_width bits, 0 for none,
//     else 1 + a group the draft guesses the body's first farm choice to be, likeliest first.
//     With dash_steps, a dash's steps then follow: per lead body, 2 bits of dash kind
//     (ChampionFacts::dash_kind, 0 for no entry), and for a kind, 4 bits of a spawn tile's index,
//     3 of a Rice parameter, 13 of the codes' length in bits and a code per group of that dash's
//     steps from the tile to its centre: 0 for unreachable, else 1 + steps less their Chebyshev
//     distance.
//  4. Ward tiles at wards_at, from where those end (else the attack tiles), read on first use:
//     4 bits of code width w, then w bits per ward site (each group, then each altar), 0 for none,
//     else 1 + the tile's index in the site's ward_box, row-major. Sites past the end of the
//     stream read 0.
// A new section decoded at build goes after the steps, with no offset; a lazy one gets an offset.
struct DraftPlan {
    // Bump when the layout changes: the header's check covers it.
    static constexpr std::uint32_t current_version = 7;

    std::array<std::uint8_t, 1024> bytes{};

    static constexpr int max_spawn_tiles = 16;
    static constexpr std::array<int, 2> attack_ranges{3, 1};
    static constexpr int bush_range = attack_ranges[0]; // the largest
    static constexpr int leads = 2, lead_bodies = 6; // five picks, one of them Cassi and Issac
};
static_assert(std::is_trivially_copyable_v<DraftPlan>);
static_assert(sizeof(DraftPlan) == 1024, "draft memory is 1024 bytes");

// The stream's first `bits` bits: these fields in this order, with these widths.
struct PlanHeader {
    // plan_check(): a hash of current_version and the map (size, group count, first ally spawn
    // tile), never 0. Unwritten memory reads 0, no plan; another version or map mismatches but
    // for a 1 in 65535 chance.
    std::uint16_t check = 0;            // 16
    std::uint16_t field_layers = 0;     // 14: the deepest field computed, clamped
    bool steps = false;                 // 1: the steps section is in
    bool mirrored = false;              // 1: every group has a mirror group, and enemy steps are coded from its ally steps
    bool spawn_offsets = false;         // 1: the steps hold each ally spawn tile's offsets
    // 1: every tribute tile is off the camp tiles and walkable from our first spawn tile with every
    // camp standing, so on our walk however many have died.
    bool tributes_walked = false;
    // 1 each: a dash's static walls (StaticMap::dash_walls) give every group the same steps from each
    // ally spawn tile as the plan's spawn steps, and from the altars as its altar steps; so do
    // landing_dash_walls, which lie between them and walking's.
    bool dash_spawn_steps = false, dash_altar_steps = false;
    bool dash_steps = false;            // 1: the dash steps follow the leads
    std::array<std::uint8_t, 3> rice{}; // 3 each: Rice parameter of the ally, enemy and altar steps
    std::uint8_t attack_groups = 0;     // 8: leading groups whose members' attack tiles are in
    std::uint16_t wards_at = 0;         // 13
    std::uint16_t leads_at = 0;         // 13
    static constexpr int check_bits = 16, layer_bits = 14, rice_bits = 3, group_bits = 8, at_bits = 13;
    static constexpr int bits = check_bits + layer_bits + 7 + 3 * rice_bits + group_bits + 2 * at_bits;
    static constexpr int max_rice = (1 << rice_bits) - 1;

    void write(DraftPlan& plan) const;
    static PlanHeader read(const DraftPlan& plan);
};

class PlanWriter {
public:
    explicit PlanWriter(DraftPlan& plan, int at = 0) : data_{plan.bytes.data()}, at_{at} {}
    int at() const { return at_; }
    static constexpr int capacity = static_cast<int>(sizeof(DraftPlan::bytes)) * 8;
    bool fits(int bits) const { return at_ + bits <= capacity; }
    // False, writing nothing, if it does not fit.
    bool put(std::uint32_t value, int bits) {
        if (!fits(bits)) return false;
        for (int i = 0; i < bits; ++i, ++at_) {
            auto& byte = data_[at_ >> 3];
            const auto mask = static_cast<std::uint8_t>(1u << (at_ & 7));
            byte = static_cast<std::uint8_t>((value >> i & 1) ? byte | mask : byte & ~mask);
        }
        return true;
    }
    bool put_rice(std::uint32_t value, int k) {
        if (!fits(rice_bits(value, k))) return false;
        for (auto q = value >> k; q > 0; --q) put(1, 1);
        return put(0, 1) && put(value & ((1u << k) - 1), k);
    }
    static int rice_bits(std::uint32_t value, int k) { return static_cast<int>(value >> k) + 1 + k; }

private:
    std::uint8_t* data_;
    int at_;
};

// Reads past the end as zero bits, and is then no longer ok.
class PlanReader {
public:
    explicit PlanReader(const DraftPlan& plan, int at = 0) : data_{plan.bytes.data()}, end_{at} {}
    int at() const { return end_ - have_; }
    bool ok() const { return at() <= PlanWriter::capacity; }
    // At most 32 bits.
    [[gnu::always_inline]] std::uint32_t get(int bits) {
        if (have_ < bits) fill();
        const auto value = static_cast<std::uint32_t>(w_ & ((std::uint64_t{1} << bits) - 1));
        consume(bits);
        return value;
    }
    void skip(int bits) { end_ = at() + bits, w_ = 0, have_ = 0; }
    // Past n Rice codes of parameter k. With k 0 each ends at a zero bit, found ~5 fuel a code where
    // get_rice costs ~50.
    void skip_rice(int n, int k) {
        if (k > 0) {
            while (n-- > 0) get_rice(k);
            return;
        }
        for (int from = at(); n > 0; from += valid) {
            auto zeros = ~window(from) & valid_mask;
            if (const int count = __builtin_popcountll(zeros); count < n) {
                n -= count;
                continue;
            }
            for (; n > 1; --n) zeros &= zeros - 1;
            skip(from + __builtin_ctzll(zeros) + 1 - at());
            return;
        }
    }
    // k at most 15. Inlined, the reader stays in locals through a decode loop.
    [[gnu::always_inline]] std::uint32_t get_rice(int k) {
        // w_'s bits from have_ up are zero, so ~w_ has a one at have_ at the latest.
        if (const int ones = __builtin_ctzll(~w_); ones + 1 + k <= have_) [[likely]]
            return take_rice(ones, k);
        fill();
        if (const int ones = __builtin_ctzll(~w_); ones + 1 + k <= have_) return take_rice(ones, k);
        std::uint32_t q = 0;
        while (w_ == valid_mask) q += valid, consume(valid), fill();
        const int ones = __builtin_ctzll(~w_);
        consume(ones + 1);
        return (q + static_cast<std::uint32_t>(ones)) << k | get(k);
    }

private:
    // A window holds at least 57 bits of the stream; w_ keeps the have_ of them before end_.
    static constexpr int valid = 57;
    static constexpr std::uint64_t valid_mask = (std::uint64_t{1} << valid) - 1;
    [[gnu::always_inline]] void fill() {
        const int at = end_ - have_;
        w_ = window(at) & valid_mask, have_ = valid, end_ = at + valid;
    }
    void consume(int bits) { w_ >>= bits, have_ -= bits; }
    std::uint32_t take_rice(int ones, int k) {
        const auto value = static_cast<std::uint32_t>(ones) << k | static_cast<std::uint32_t>(w_ >> (ones + 1) & ((std::uint64_t{1} << k) - 1));
        consume(ones + 1 + k);
        return value;
    }

    [[gnu::always_inline]] std::uint64_t window(int at) const {
        constexpr int size = static_cast<int>(sizeof(DraftPlan::bytes));
        const int byte = at >> 3;
        std::uint64_t w = 0;
        if (byte + 8 <= size) std::memcpy(&w, data_ + byte, sizeof w);
        else
            for (int i = 0; byte + i < size; ++i) w |= std::uint64_t{data_[byte + i]} << (8 * i);
        return w >> (at & 7);
    }

    const std::uint8_t* data_;
    int end_;
    std::uint64_t w_ = 0;
    int have_ = 0;
};

// The Chebyshev box around a set of tiles: no tile of the set is nearer p than dist(p).
struct TileBox {
    int x0 = 0, y0 = 0, x1 = -1, y1 = -1;
    static TileBox of(const std::vector<cambc::vec2>& tiles) {
        TileBox b{1 << 20, 1 << 20, -(1 << 20), -(1 << 20)};
        for (const auto t : tiles) b.x0 = std::min(b.x0, t.x), b.y0 = std::min(b.y0, t.y), b.x1 = std::max(b.x1, t.x), b.y1 = std::max(b.y1, t.y);
        return b;
    }
    int area() const { return (x1 - x0 + 1) * (y1 - y0 + 1); }
    int dist(cambc::vec2 p) const { return std::max(std::max(x0 - p.x, p.x - x1), std::max(std::max(y0 - p.y, p.y - y1), 0)); }
};

// Calls f(chunk x, chunk y, word) for each 8x8 chunk overlapping the square of Chebyshev radius r
// around p, with `tiles`' word masked to the square.
template <class F> void each_word_in_square(const cambc::bitboard& tiles, cambc::vec2 p, int r, F&& f) {
    const auto& layout = cambc::detail::layout();
    const std::uint64_t* words = tiles.ptr();
    const int x0 = std::max(0, p.x - r), x1 = std::min(layout.width - 1, p.x + r);
    const int y0 = std::max(0, p.y - r), y1 = std::min(layout.height - 1, p.y + r);
    for (int cy = y0 >> 3; cy <= y1 >> 3; ++cy) {
        const int lo = std::max(y0, 8 * cy) & 7, hi = std::min(y1, 8 * cy + 7) & 7;
        const std::uint64_t rows = ~std::uint64_t{0} >> (8 * (7 - hi)) & ~std::uint64_t{0} << (8 * lo);
        for (int cx = x0 >> 3; cx <= x1 >> 3; ++cx) {
            const int l = std::max(x0, 8 * cx) & 7, h = std::min(x1, 8 * cx + 7) & 7;
            const std::uint64_t cols = 0x0101010101010101ull * (0xffu >> (7 - h) & 0xffu << l & 0xffu);
            f(cx, cy, words[cy * layout.chunk_stride + cx] & rows & cols);
        }
    }
}

// Calls f(tile) for each tile of `tiles` within Chebyshev r of p: by chunks, from the bottom
// left, then by rows from the bottom left within a chunk.
template <class F> void each_in_square(const cambc::bitboard& tiles, cambc::vec2 p, int r, F&& f) {
    each_word_in_square(tiles, p, r, [&](int cx, int cy, std::uint64_t w) {
        for (; w; w &= w - 1) {
            const int b = __builtin_ctzll(w);
            f(cambc::vec2{8 * cx + (b & 7), 8 * cy + (b >> 3)});
        }
    });
}

inline int count_in_square(const cambc::bitboard& tiles, cambc::vec2 p, int r) {
    int n = 0;
    each_word_in_square(tiles, p, r, [&](int, int, std::uint64_t w) { n += __builtin_popcountll(w); });
    return n;
}

// The plan's walking steps, decoded.
struct DraftSteps {
    std::vector<std::uint16_t> ally, enemy, altar; // per group; enemy empty until decode_enemy_steps
    std::vector<std::uint32_t> offsets;            // per group: 2 bits per ally spawn tile, unless predicted
    std::vector<std::uint8_t> predicted;           // per group: offsets are spawn_offset's
    TileBox spawn;                                 // our spawn's box
    int enemy_at = 0;                              // the enemy steps' first bit
    int end = 0;                                   // the bit after the section
};

// The lower bound the plan's steps to a group centred on c are coded against: 0 from our spawn,
// 1 from theirs, 2 from the altars. The altars' is 0: the nearest altar's distance costs champions
// a pass over every altar per group, ~30 fuel an altar, to save a few bytes.
inline int steps_bound(const TileBox& ally, const TileBox& enemy, cambc::vec2 c, int which) {
    return which == 0 ? ally.dist(c) : which == 1 ? enemy.dist(c) : 0;
}
// A spawn tile's steps beyond the whole spawn's, as the walk would be with no walls.
int spawn_offset(const TileBox& spawn, cambc::vec2 tile, cambc::vec2 centre);
// False if the stream is cut short.
bool decode_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out, bool with_enemy = true);
// The enemy steps decode_steps skipped: champions read them only after their first decision. A
// mirror group is always there in a plan written for this map; unreachable if not.
void decode_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, DraftSteps& out);
// One group's enemy steps as decode_enemy_steps would give them, when the plan mirrors them with
// Rice parameter 0 (each code a few bits): read on from the last group asked when past it. -1 otherwise.
int mirrored_enemy_steps(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, const DraftSteps& steps, int group);

// Where a champion working a site (a group, then an altar, by index) can place a ward while it
// captures or tributes: within ward placement range of a camp tile, or of a tribute tile.
TileBox ward_box(const StaticMap& map, int site);
inline constexpr int ward_width_bits = 4;
// A site's ward tile from its code, {-1, -1} for none.
cambc::vec2 ward_tile(const StaticMap& map, int site, std::uint32_t code);
// The plan's ward tile for a site, {-1, -1} for none.
cambc::vec2 drafted_ward(const DraftPlan& plan, const PlanHeader& header, const StaticMap& map, int site);

// A lead code's width for `groups` groups.
inline int lead_width(int groups) { return std::bit_width(static_cast<unsigned>(groups)); }
// The plan's leads for a body into `out`, likeliest first; how many.
int drafted_leads(const DraftPlan& plan, const PlanHeader& header, int groups, int body, std::array<int, DraftPlan::leads>& out);

// A dash-steps entry: the kind of dash (0 for none), the spawn tile's index, the Rice parameter
// and the first code's bit.
struct DashEntry {
    int kind = 0, tile = -1, rice = 0, at = 0;
};
// The entries; false if there are none or the stream is cut short.
bool index_dash_steps(const DraftPlan& plan, const PlanHeader& header, int groups, std::array<DashEntry, DraftPlan::lead_bodies>& out);
inline constexpr int dash_kind_bits = 2, dash_tile_bits = 4;

// PlanHeader::check for this map.
std::uint16_t plan_check(const StaticMap& map);

// In the draft memory snapshot, which lasts the match; null if it is too short. Copying it costs
// ~1 fuel a byte.
const DraftPlan* read_draft_plan();

struct DraftState {
    DraftPlan plan;
    PlanHeader header; // written into plan's first bits with it
    int picked_round = -1;
};

void play_draft(DraftState& state);

// A draft turn that ends without a pick makes every remaining pick random, and the draft bot
// never runs again.
void ensure_picked(DraftState& state);

} // namespace aph
