#pragma once
// Backward Dijkstra in a 15x15 window around us, bit-parallel: every cost level's settled tiles are a
// 256-bit mask (rows of 16 bits), and relaxing them is a king dilation by word shifts. Seeds are the
// goals inside the window (cost 0) and the window's ring at 2 x its host steps (what lies beyond it,
// unweighted). Costs, in half turns: entering a tile 2, plus its weight class's extra; a dash, a jump
// of up to 2 king steps whose middle tile a dash may cross, costs `dash_cost` plus its landing's extra
// (no cooldown: dash_cost prices what the spent dash is worth). Stops once our tile settles.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>

namespace winroute {

inline long long prof[4];

using cambc::bitboard;
using cambc::vec2;

inline constexpr int R = 7, side = 2 * R + 1;
inline constexpr int ring_slots = 64; // > the largest single move cost
inline constexpr std::uint16_t unreachable = cambc::distance_field::unreachable;

struct M {
    std::uint64_t w[4];
};
inline M operator|(const M& a, const M& b) { return {{a.w[0] | b.w[0], a.w[1] | b.w[1], a.w[2] | b.w[2], a.w[3] | b.w[3]}}; }
inline M operator&(const M& a, const M& b) { return {{a.w[0] & b.w[0], a.w[1] & b.w[1], a.w[2] & b.w[2], a.w[3] & b.w[3]}}; }
inline M andnot(const M& a, const M& b) { return {{a.w[0] & ~b.w[0], a.w[1] & ~b.w[1], a.w[2] & ~b.w[2], a.w[3] & ~b.w[3]}}; }
inline bool any(const M& a) { return (a.w[0] | a.w[1] | a.w[2] | a.w[3]) != 0; }
inline M shl(const M& a, int s) {
    return {{a.w[0] << s, a.w[1] << s | a.w[0] >> (64 - s), a.w[2] << s | a.w[1] >> (64 - s), a.w[3] << s | a.w[2] >> (64 - s)}};
}
inline M shr(const M& a, int s) {
    return {{a.w[0] >> s | a.w[1] << (64 - s), a.w[1] >> s | a.w[2] << (64 - s), a.w[2] >> s | a.w[3] << (64 - s), a.w[3] >> s}};
}
inline bool get(const M& a, int r, int c) { const int b = r * 16 + c; return a.w[b >> 6] >> (b & 63) & 1; }
inline void set(M& a, int r, int c) { const int b = r * 16 + c; a.w[b >> 6] |= std::uint64_t{1} << (b & 63); }
// King neighbours and the tiles themselves, inside `valid` (column 15 is never valid: no row wraps).
inline M dilate(const M& a, const M& valid) {
    const M h = a | shl(a, 1) | shr(a, 1);
    return (h | shl(h, 16) | shr(h, 16)) & valid;
}

// Bits x0..x0+14 of row y of a board, 0 off the map.
inline std::uint32_t row_bits(const std::uint64_t* b, int stride, int y, int x0, int W, int H) {
    if (y < 0 || y >= H) return 0;
    const int k0 = x0 >> 3;
    const std::uint64_t* row = b + (y >> 3) * stride;
    const int shift = (y & 7) * 8, chunks = (W + 7) >> 3;
    std::uint32_t v = 0;
    for (int k = 0; k < 3; ++k) {
        const int kk = k0 + k;
        if (kk >= 0 && kk < chunks) v |= static_cast<std::uint32_t>((row[kk] >> shift) & 0xFF) << (8 * k);
    }
    return (v >> (x0 - 8 * k0)) & 0x7FFF;
}
inline M window_of(const bitboard& b, vec2 c, int W, int H, int stride) {
    M m{};
    const std::uint64_t* words = b.ptr();
    for (int r = 0; r < side; ++r) {
        const std::uint32_t bits = row_bits(words, stride, c.y - R + r, c.x - R, W, H);
        m.w[(r * 16) >> 6] |= static_cast<std::uint64_t>(bits) << ((r * 16) & 63);
    }
    return m;
}

// A weight class: tiles whose entry costs `extra` more (exclusive classes; the rest cost nothing more).
struct Weight {
    const bitboard* tiles;
    int extra;
};

struct Query {
    vec2 start;
    const bitboard* walls = nullptr;  // no walk or landing, but onto goals
    const bitboard* solid = nullptr;  // no dash path through; null: no dashes
    const bitboard* goals = nullptr;
    const cambc::distance_field* steps = nullptr; // host walking steps to the goals
    std::array<Weight, 4> weights{};  // most expensive first: a tile takes its first class
    int n_weights = 0;
    int dash_cost = 0;                // 0: no dash edges
};

struct Result {
    bool found = false;
    int cost = -1;                    // ours, in half turns
    std::array<std::int16_t, 25> near{}; // the 5x5 around us: cost to go, -1 unknown (more than ours, or blocked)
    int levels = 0;
    int at(int dx, int dy) const { return near[(dy + 2) * 5 + dx + 2]; }
};

inline Result route(const Query& q) {
    Result res;
    res.near.fill(-1);
    const int W = cambc::map::width(), H = cambc::map::height();
    const auto& layout = cambc::detail::layout();
    const int stride = static_cast<int>(layout.chunk_stride), chunks = static_cast<int>(layout.chunked_width);
    const vec2 s0 = q.start;
    M valid{};
    for (int r = 0; r < side; ++r) {
        const int y = s0.y - R + r;
        if (y < 0 || y >= H) continue;
        const int lo = std::max(0, R - s0.x), hi = std::min(side - 1, W - 1 - s0.x + R);
        if (lo > hi) continue;
        valid.w[(r * 16) >> 6] |= (((std::uint64_t{1} << (hi - lo + 1)) - 1) << lo) << ((r * 16) & 63);
    }
    const auto p0 = cambc::fuel_remaining();
    const M goal = window_of(*q.goals, s0, W, H, stride) & valid;
    M open = andnot(valid, window_of(*q.walls, s0, W, H, stride)) | goal;
    set(open, R, R);
    const bool dashes = q.solid && q.dash_cost > 0;
    const M cross = dashes ? andnot(valid, window_of(*q.solid, s0, W, H, stride)) : M{};
    M classes[5];
    int extras[5];
    int n_classes = 0;
    {
        M taken{};
        for (int i = 0; i < q.n_weights; ++i) {
            const M m = andnot(window_of(*q.weights[i].tiles, s0, W, H, stride) & open, taken);
            if (!any(m)) continue;
            classes[n_classes] = m, extras[n_classes++] = q.weights[i].extra;
            taken = taken | m;
        }
        classes[n_classes] = andnot(open, taken), extras[n_classes++] = 0;
    }
    M ring{};
    for (int r = 0; r < side; ++r) {
        const std::uint64_t row = (r == 0 || r == side - 1) ? 0x7FFFu : ((1u << (side - 1)) | 1u);
        ring.w[(r * 16) >> 6] |= row << ((r * 16) & 63);
    }
    ring = andnot(ring & open, goal);

    const auto p1 = cambc::fuel_remaining();
    prof[0] += static_cast<long long>(p0 - p1);
    // Pending levels, a ring buffer indexed by level; `dirty` marks the slots written since last read.
    static M pending[ring_slots];
    static std::uint64_t dirty;
    dirty = 0;
    const auto add = [&](int level, const M& m) {
        M& slot = pending[level & (ring_slots - 1)];
        const std::uint64_t bit = std::uint64_t{1} << (level & (ring_slots - 1));
        if (dirty & bit) slot = slot | m;
        else slot = m, dirty |= bit;
    };
    // Seeds: goals at 0; ring tiles at their host steps (doubled), sorted into levels relative to the lowest.
    const std::uint16_t* field = q.steps->ptr();
    const auto steps_at = [&](int x, int y) -> int { return field[((y >> 3) * chunks + (x >> 3)) * 64 + (y & 7) * 8 + (x & 7)]; };
    int base = 1 << 30;
    struct Seed {
        std::int16_t r, c;
        int level;
    };
    static Seed seeds[64];
    int n_seeds = 0;
    for (int r = 0; r < side; ++r) {
        std::uint32_t bits = static_cast<std::uint32_t>(ring.w[(r * 16) >> 6] >> ((r * 16) & 63)) & 0x7FFF;
        for (; bits; bits &= bits - 1) {
            const int c = __builtin_ctz(bits);
            const int d = steps_at(s0.x - R + c, s0.y - R + r);
            if (d == unreachable) continue;
            seeds[n_seeds++] = {static_cast<std::int16_t>(r), static_cast<std::int16_t>(c), 2 * d};
            base = std::min(base, 2 * d);
        }
    }
    if (any(goal)) base = 0;
    if (base == (1 << 30)) return res;
    // Levels are relative to `base`; ring seeds beyond the buffer's reach are added as their level comes up.
    if (any(goal)) add(0, goal);
    int seed_next = 0;
    std::sort(seeds, seeds + n_seeds, [](const Seed& a, const Seed& b) { return a.level < b.level; });
    const auto p2 = cambc::fuel_remaining();
    prof[1] += static_cast<long long>(p1 - p2);
    // Our 5x5 neighbourhood, to read costs to go off as they settle.
    M box5{};
    for (int r = R - 2; r <= R + 2; ++r)
        for (int c = R - 2; c <= R + 2; ++c) set(box5, r, c);
    M visited{};
    const int max_level = 4 * (side + 8) * 2 + 512; // a safety bound
    for (int lv = 0; lv < max_level; ++lv) {
        while (seed_next < n_seeds && seeds[seed_next].level - base <= lv + ring_slots - 1) {
            M m{};
            set(m, seeds[seed_next].r, seeds[seed_next].c);
            add(seeds[seed_next].level - base, m);
            ++seed_next;
        }
        const std::uint64_t bit = std::uint64_t{1} << (lv & (ring_slots - 1));
        if (!(dirty & bit)) {
            if (!dirty && seed_next >= n_seeds) break;
            continue;
        }
        dirty &= ~bit;
        const M S = andnot(pending[lv & (ring_slots - 1)], visited);
        if (!any(S)) continue;
        visited = visited | S;
        ++res.levels;
        const M near = S & box5;
        if (any(near))
            for (int r = R - 2; r <= R + 2; ++r)
                for (int c = R - 2; c <= R + 2; ++c)
                    if (get(near, r, c)) res.near[(r - R + 2) * 5 + c - R + 2] = static_cast<std::int16_t>(lv);
        if (get(S, R, R)) {
            prof[2] += static_cast<long long>(p2 - cambc::fuel_remaining());
            res.found = true;
            res.cost = lv + base;
            for (auto& v : res.near)
                if (v >= 0) v = static_cast<std::int16_t>(v + base);
            return res;
        }
        // Walking predecessors: a step onto a tile of S costs 2 plus its class's extra.
        for (int i = 0; i < n_classes; ++i) {
            const M part = S & classes[i];
            if (!any(part)) continue;
            const M pred = andnot(dilate(part, valid) & open, visited);
            if (any(pred)) add(lv + 2 + extras[i], pred);
            if (dashes) {
                const M jump = andnot((dilate(dilate(part, valid) & cross, valid) & open), visited);
                if (any(jump)) add(lv + q.dash_cost + extras[i], jump);
            }
        }
    }
    return res;
}

} // namespace winroute
