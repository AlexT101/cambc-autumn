#pragma once
// Backward Dijkstra in the 7x7 window around us, in ONE u64: bit (r * 8 + c), r, c in 0..6 (column 7
// and row 7 stay empty, so shifts never wrap). Seeds: the goals inside the window at 0, and the window's
// rim at 2 x its host steps (the rest of the way, unweighted). Costs in half turns: entering a tile 2,
// plus its weight class's extra; a dash (a jump of up to 2 king steps whose middle tile a dash may
// cross) costs `dash_cost` plus its landing's extra, with no cooldown: `dash_cost` prices the dash.
// Stops when our tile settles; costs to go are kept for the 5x5 around us.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>

namespace localroute {

using cambc::bitboard;
using cambc::vec2;

inline constexpr int R = 3, side = 7;
inline constexpr std::uint16_t unreachable = cambc::distance_field::unreachable;
inline constexpr std::uint64_t col0 = 0x0101010101010101ull, col7 = 0x8080808080808080ull;
inline constexpr std::uint64_t valid7 = 0x007F7F7F7F7F7F7Full; // rows 0..6, columns 0..6

inline std::uint64_t dil(std::uint64_t m) {
    const std::uint64_t t = m | ((m << 1) & ~col0) | ((m >> 1) & ~col7);
    return (t | (t << 8) | (t >> 8)) & valid7;
}

// The 7x7 window at (x0, y0) .. (x0 + 6, y0 + 6) of a board, 0 off the map: rows straight from the
// engine's 8x8 chunk words.
inline std::uint64_t window_of(const std::uint64_t* b, int stride, int x0, int y0, int W, int H) {
    std::uint64_t out = 0;
    const int k0 = x0 >> 3, sh = x0 - 8 * k0, chunks = (W + 7) >> 3;
    for (int r = 0; r < side; ++r) {
        const int y = y0 + r;
        if (y < 0 || y >= H) continue;
        const std::uint64_t* row = b + (y >> 3) * stride;
        const int s = (y & 7) * 8;
        std::uint32_t v = 0;
        if (k0 >= 0 && k0 < chunks) v = static_cast<std::uint32_t>((row[k0] >> s) & 0xFF);
        if (k0 + 1 >= 0 && k0 + 1 < chunks) v |= static_cast<std::uint32_t>((row[k0 + 1] >> s) & 0xFF) << 8;
        out |= static_cast<std::uint64_t>((v >> sh) & 0x7F) << (r * 8);
    }
    return out;
}

struct Weight {
    const bitboard* tiles;
    int extra;
};

struct Query {
    vec2 start;
    const bitboard* walls = nullptr;
    const bitboard* solid = nullptr; // no dash path through; null: no dashes
    const bitboard* goals = nullptr;
    const cambc::distance_field* steps = nullptr; // host walking steps to the goals
    std::array<Weight, 4> weights{};  // most expensive first: a tile takes its first class
    int n_weights = 0;
    int dash_cost = 0;
};

struct Result {
    bool found = false;
    int cost = -1;
    std::array<std::int16_t, 25> near{}; // the 5x5 around us: cost to go, -1 unknown
    int at(int dx, int dy) const { return near[(dy + 2) * 5 + dx + 2]; }
};

inline Result route(const Query& q) {
    Result res;
    res.near.fill(-1);
    const int W = cambc::map::width(), H = cambc::map::height();
    const auto& layout = cambc::detail::layout();
    const int stride = static_cast<int>(layout.chunk_stride), chunks = static_cast<int>(layout.chunked_width);
    const int x0 = q.start.x - R, y0 = q.start.y - R;
    // In-map part of the window.
    std::uint64_t valid = 0;
    for (int r = 0; r < side; ++r) {
        const int y = y0 + r;
        if (y < 0 || y >= H) continue;
        const int lo = std::max(0, -x0), hi = std::min(side - 1, W - 1 - x0);
        if (lo <= hi) valid |= (((std::uint64_t{1} << (hi - lo + 1)) - 1) << lo) << (r * 8);
    }
    constexpr std::uint64_t me = std::uint64_t{1} << (R * 8 + R);
    const std::uint64_t goal = window_of(q.goals->ptr(), stride, x0, y0, W, H) & valid;
    const std::uint64_t open = ((~window_of(q.walls->ptr(), stride, x0, y0, W, H) & valid) | goal | me);
    const bool dashes = q.solid && q.dash_cost > 0;
    const std::uint64_t cross = dashes ? ~window_of(q.solid->ptr(), stride, x0, y0, W, H) & valid : 0;
    std::uint64_t classes[5];
    int extras[5], n_classes = 0;
    {
        std::uint64_t taken = 0;
        for (int i = 0; i < q.n_weights; ++i) {
            const std::uint64_t m = window_of(q.weights[i].tiles->ptr(), stride, x0, y0, W, H) & open & ~taken;
            if (!m) continue;
            classes[n_classes] = m, extras[n_classes++] = q.weights[i].extra;
            taken |= m;
        }
        classes[n_classes] = open & ~taken, extras[n_classes++] = 0;
    }
    constexpr std::uint64_t rim = 0x007F41414141417Full; // rows 0 and 6, columns 0 and 6
    const std::uint64_t seeds = rim & open & ~goal;
    // Pending levels: a 64-slot ring of masks (every move costs < 64).
    static std::uint64_t pending[64];
    std::uint64_t dirty = 0;
    const auto add = [&](int level, std::uint64_t m) {
        const int s = level & 63;
        const std::uint64_t bit = std::uint64_t{1} << s;
        if (dirty & bit) pending[s] |= m;
        else pending[s] = m, dirty |= bit;
    };
    // Rim seeds at 2 x host steps, relative to the lowest; up to 24 of them.
    const std::uint16_t* field = q.steps->ptr();
    int levels[24], base = goal ? 0 : 1 << 30, n = 0;
    std::uint64_t bits_of[24];
    for (std::uint64_t left = seeds; left; left &= left - 1) {
        const int b = __builtin_ctzll(left), x = x0 + (b & 7), y = y0 + (b >> 3);
        const int d = field[((y >> 3) * chunks + (x >> 3)) * 64 + (y & 7) * 8 + (x & 7)];
        if (d == unreachable) continue;
        levels[n] = 2 * d, bits_of[n++] = std::uint64_t{1} << b;
        base = std::min(base, 2 * d);
    }
    if (base == (1 << 30)) return res;
    if (goal) add(0, goal);
    // Seeds farther than the ring buffer reaches are added when their level comes near.
    std::uint64_t later = 0; // bit i: seed i still to add
    for (int i = 0; i < n; ++i) {
        if (levels[i] - base < 48) add(levels[i] - base, bits_of[i]);
        else later |= std::uint64_t{1} << i;
    }
    constexpr std::uint64_t box5 = 0x00003E3E3E3E3E00ull; // rows 1..5, columns 1..5
    std::uint64_t visited = 0;
    for (int lv = 0; lv < 4096; ++lv) {
        if (later)
            for (std::uint64_t l = later; l; l &= l - 1) {
                const int i = __builtin_ctzll(l);
                if (levels[i] - base < lv + 48) add(levels[i] - base, bits_of[i]), later &= ~(std::uint64_t{1} << i);
            }
        const int sl = lv & 63;
        const std::uint64_t bit = std::uint64_t{1} << sl;
        if (!(dirty & bit)) {
            if (!dirty && !later) break;
            continue;
        }
        dirty &= ~bit;
        const std::uint64_t S = pending[sl] & ~visited;
        if (!S) continue;
        visited |= S;
        if (S & box5)
            for (std::uint64_t l = S & box5; l; l &= l - 1) {
                const int b = __builtin_ctzll(l);
                res.near[((b >> 3) - 1) * 5 + (b & 7) - 1] = static_cast<std::int16_t>(lv + base);
            }
        if (S & me) {
            res.found = true;
            res.cost = lv + base;
            return res;
        }
        for (int i = 0; i < n_classes; ++i) {
            const std::uint64_t part = S & classes[i];
            if (!part) continue;
            const std::uint64_t d1 = dil(part);
            const std::uint64_t pred = d1 & open & ~visited;
            if (pred) add(lv + 2 + extras[i], pred);
            if (dashes) {
                const std::uint64_t jump = dil(d1 & cross) & open & ~visited;
                if (jump) add(lv + q.dash_cost + extras[i], jump);
            }
        }
    }
    return res;
}

} // namespace localroute
