#pragma once
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <type_traits>
#include <vector>

namespace aph {

struct StaticMap;

struct DraftPlan {
    // Bump when the layout changes; a champion ignores a plan with another version.
    static constexpr std::uint16_t current_version = 3;

    std::uint16_t version = current_version; // 0 means the draft bot never wrote a plan
    std::array<std::uint8_t, 2> reserved{};

    // Static map analysis, so that champions skip it. A champion whose map differs (size, group
    // count, first ally spawn tile) ignores it.
    std::uint8_t width = 0, height = 0, groups = 0, spawn_x = 0, spawn_y = 0;
    std::uint8_t spawn_tiles = 0;   // ally spawn tiles with steps in the group entries; 0: none
    std::uint8_t steps = 0;         // 1 once the group entries are in
    std::uint8_t attack_groups = 0; // leading groups whose members' attack tiles are in
    std::uint16_t field_layers = 0; // the deepest field computed
    std::uint8_t mirrored = 0;      // 1: every group has a mirror group, and enemy steps are coded from its ally steps
    std::array<std::uint8_t, 3> rice{}; // Rice parameter of the ally, enemy and altar steps
    std::uint16_t attack_start = 0; // the bit in data where the attack tiles begin
    // A bit stream, least significant bit of each byte first. Walking steps to each group's centre
    // from our spawn, from theirs and from the tribute tiles of every altar: per group, Rice-coded,
    // 0 for unreachable, else steps + 1 less a Chebyshev lower bound (steps_bound). Mirrored, a
    // group's enemy steps are instead the zigzag of their difference from its mirror group's ally
    // steps: the same but for the centres' tie-break. Then, with spawn_tiles, per group reachable
    // from our spawn: 1 if every spawn tile's steps beyond the whole spawn's are spawn_offset's,
    // else 2 bits a tile. Then a bit per member of every group, by group: 1 if a bush tile within
    // bush_range sees it. Then for each member with a 1 in the first attack_groups groups, a bit
    // per open bush tile in its bush_range square, in each_in_square's order. A range's attack tiles
    // are StaticMap::sight_off_bushes plus those bush tiles within it, which the draft checked.
    std::array<std::uint8_t, 1004> data{};

    static constexpr int max_spawn_tiles = 16;
    static constexpr std::array<int, 2> attack_ranges{3, 1};
    static constexpr int bush_range = attack_ranges[0]; // the largest
};
static_assert(std::is_trivially_copyable_v<DraftPlan>);
static_assert(sizeof(DraftPlan) == 1024, "draft memory is 1024 bytes");

class PlanWriter {
public:
    explicit PlanWriter(DraftPlan& plan, int at = 0) : data_{plan.data.data()}, at_{at} {}
    int at() const { return at_; }
    static constexpr int capacity = static_cast<int>(sizeof(DraftPlan::data)) * 8;
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
    explicit PlanReader(const DraftPlan& plan, int at = 0) : data_{plan.data.data()}, at_{at} {}
    int at() const { return at_; }
    bool ok() const { return at_ <= PlanWriter::capacity; }
    // At most 32 bits.
    std::uint32_t get(int bits) {
        const auto value = static_cast<std::uint32_t>(window() & ((std::uint64_t{1} << bits) - 1));
        at_ += bits;
        return value;
    }
    void skip(int bits) { at_ += bits; }
    // k at most 15.
    std::uint32_t get_rice(int k) {
        // A window holds at least 57 bits of the stream.
        constexpr int valid = 57;
        std::uint32_t q = 0;
        auto w = window();
        while (!(~w & ((std::uint64_t{1} << valid) - 1))) q += valid, at_ += valid, w = window();
        const int ones = __builtin_ctzll(~w);
        q += static_cast<std::uint32_t>(ones);
        if (ones + 1 + k > valid) {
            at_ += ones + 1;
            return q << k | get(k);
        }
        at_ += ones + 1 + k;
        return q << k | static_cast<std::uint32_t>(w >> (ones + 1) & ((std::uint64_t{1} << k) - 1));
    }

private:
    std::uint64_t window() const {
        constexpr int size = static_cast<int>(sizeof(DraftPlan::data));
        const int byte = at_ >> 3;
        std::uint64_t w = 0;
        if (byte + 8 <= size) std::memcpy(&w, data_ + byte, sizeof w);
        else
            for (int i = 0; byte + i < size; ++i) w |= std::uint64_t{data_[byte + i]} << (8 * i);
        return w >> (at_ & 7);
    }

    const std::uint8_t* data_;
    int at_;
};

// The Chebyshev box around a set of tiles: no tile of the set is nearer p than dist(p).
struct TileBox {
    int x0 = 0, y0 = 0, x1 = -1, y1 = -1;
    static TileBox of(const std::vector<cambc::vec2>& tiles) {
        TileBox b{1 << 20, 1 << 20, -(1 << 20), -(1 << 20)};
        for (const auto t : tiles) b.x0 = std::min(b.x0, t.x), b.y0 = std::min(b.y0, t.y), b.x1 = std::max(b.x1, t.x), b.y1 = std::max(b.y1, t.y);
        return b;
    }
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
    std::vector<std::uint16_t> ally, enemy, altar; // per group
    std::vector<std::uint32_t> offsets;            // per group: 2 bits per ally spawn tile, unless predicted
    std::vector<std::uint8_t> predicted;           // per group: offsets are spawn_offset's
    TileBox spawn;                                 // our spawn's box
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
bool decode_steps(const DraftPlan& plan, const StaticMap& map, DraftSteps& out);

// In the draft memory snapshot, which lasts the match; null if none or another version. Copying
// it costs ~1 fuel a byte.
const DraftPlan* read_draft_plan();

struct DraftState {
    DraftPlan plan;
    int picked_round = -1;
};

void play_draft(DraftState& state);

// A draft turn that ends without a pick makes every remaining pick random, and the draft bot
// never runs again.
void ensure_picked(DraftState& state);

} // namespace aph
