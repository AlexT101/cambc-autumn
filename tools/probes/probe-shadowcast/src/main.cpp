// probe-shadowcast: bitboard::shadow_cast near its origin, on synthetic opaque boards (uniform densities
// 5-60% over the whole map, plus single walls, diagonal pairs, lines, checkerboards, gappy rings and clutter
// near the origin; origins biased to edges and corners). Each trial casts radii 1,2,3,4,6,8 from one clear origin.
//   Q1 radius independence: cast(p,r) == cast(p,R) restricted to Chebyshev <= r, for every r < R.
//   Q2 adjacency: every in-bounds tile within Chebyshev 1 of p is in cast(p,R) (opaque and clear counted apart).
// Also counts output tiles that are opaque, outside Chebyshev R, casts that include the origin, and clear
// tiles within R the cast leaves out (shadowed_clear, the control: it must be nonzero).
// Each champion runs kTrials trials over its play turns (a turn that runs out resumes next round) with its own
// seed, then prints a "PROBE ... summary" block; counterexamples print as they are found (at most kMaxPrinted).
//   cambc run tools/probes/probe-shadowcast tools/probes/probe-shadowcast --map 00corners --rounds 20 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <vector>

namespace {

constexpr int kTrials = 4000;
constexpr int kRadii[] = {1, 2, 3, 4, 6, 8};
constexpr int kNR = sizeof(kRadii) / sizeof(kRadii[0]);
constexpr int kWin = 10; // structured boards and all per-tile checks stay within this of p
constexpr int kMaxPrinted = 6;

std::uint64_t rng_state;
std::uint32_t rnd() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17;
    return static_cast<std::uint32_t>(rng_state >> 11);
}
int rnd_in(int lo, int hi) { return lo + static_cast<int>(rnd() % static_cast<std::uint32_t>(hi - lo + 1)); }

int W, H;
int cheb(int x0, int y0, int x1, int y1) {
    int dx = x0 > x1 ? x0 - x1 : x1 - x0;
    int dy = y0 > y1 ? y0 - y1 : y1 - y0;
    return dx > dy ? dx : dy;
}
bool inb(int x, int y) { return x >= 0 && y >= 0 && x < W && y < H; }

// Linear buffers are bit-packed (bit y*W+x, LSB first), despite the SDK comment's "one byte per tile".
using Bits = std::vector<std::uint8_t>;
bool get(const Bits& b, int x, int y) {
    const int i = y * W + x;
    return (b[i >> 3] >> (i & 7)) & 1;
}
void put(Bits& b, int x, int y) {
    if (!inb(x, y)) return;
    const int i = y * W + x;
    b[i >> 3] |= static_cast<std::uint8_t>(1u << (i & 7));
}
void unset(Bits& b, int x, int y) {
    const int i = y * W + x;
    b[i >> 3] &= static_cast<std::uint8_t>(~(1u << (i & 7)));
}

// Neighbourhood of p within `rad`: '#' opaque, '.' clear, 'P' origin, 'x' out of bounds; rows from high y down.
// With both casts: 'A' clear and only in the small cast, 'B' clear and only in the big one; 'a'/'b' if opaque.
// Without: 'v' clear and in the cast, 'o' opaque and in the cast.
void dump(const Bits& opq, int px, int py, int rad, const Bits* small, const Bits* big) {
    for (int y = py + rad; y >= py - rad; --y) {
        char line[64];
        int n = 0;
        for (int x = px - rad; x <= px + rad; ++x) {
            char c;
            if (!inb(x, y)) c = 'x';
            else if (x == px && y == py) c = 'P';
            else {
                const bool o = get(opq, x, y);
                c = o ? '#' : '.';
                if (small && big) {
                    const bool s = get(*small, x, y), b = get(*big, x, y);
                    if (s != b) c = s ? (o ? 'a' : 'A') : (o ? 'b' : 'B');
                } else if (small && get(*small, x, y)) c = o ? 'o' : 'v';
            }
            line[n++] = c;
        }
        line[n] = 0;
        debug_block({ std::printf("PROBE   y=%3d %s\n", y, line); });
    }
}

int edge_coord(int n) {
    int k = static_cast<int>(rnd() % 4);
    return (rnd() & 1) ? k : n - 1 - k;
}

void build(Bits& opq, int& px, int& py, int& kind) {
    std::fill(opq.begin(), opq.end(), 0);
    // Origin: half near an edge or corner.
    const int m = static_cast<int>(rnd() % 4);
    if (m == 0) { px = edge_coord(W); py = edge_coord(H); }
    else if (m == 1) { px = edge_coord(W); py = rnd_in(0, H - 1); }
    else { px = rnd_in(0, W - 1); py = rnd_in(0, H - 1); }
    if (rnd() & 1) std::swap(px, py), px = std::min(px, W - 1), py = std::min(py, H - 1);
    kind = static_cast<int>(rnd() % 8);
    switch (kind) {
    case 0: { // uniform density 5-60% over the whole map
        const int d = rnd_in(5, 60);
        for (int y = 0; y < H; ++y)
            for (int x = 0; x < W; ++x)
                if (static_cast<int>(rnd() % 100) < d) put(opq, x, y);
        break;
    }
    case 1: { // uniform density 5-60% within kWin
        const int d = rnd_in(5, 60);
        for (int y = py - kWin; y <= py + kWin; ++y)
            for (int x = px - kWin; x <= px + kWin; ++x)
                if (static_cast<int>(rnd() % 100) < d) put(opq, x, y);
        break;
    }
    case 2: { // clutter within 4 only, density 10-70%
        const int d = rnd_in(10, 70);
        for (int y = py - 4; y <= py + 4; ++y)
            for (int x = px - 4; x <= px + 4; ++x)
                if (static_cast<int>(rnd() % 100) < d) put(opq, x, y);
        break;
    }
    case 3: { // 1-3 single walls within 3
        const int n = rnd_in(1, 3);
        for (int i = 0; i < n; ++i) put(opq, px + rnd_in(-3, 3), py + rnd_in(-3, 3));
        break;
    }
    case 4: { // 1-2 diagonal pairs (two walls touching at a corner) within 3
        const int n = rnd_in(1, 2);
        for (int i = 0; i < n; ++i) {
            const int x = px + rnd_in(-3, 3), y = py + rnd_in(-3, 3), s = (rnd() & 1) ? 1 : -1;
            put(opq, x, y);
            put(opq, x + 1, y + s);
        }
        break;
    }
    case 5: { // straight or diagonal line segment near p
        const int x = px + rnd_in(-3, 3), y = py + rnd_in(-3, 3);
        int dx = rnd_in(-1, 1);
        const int dy = rnd_in(-1, 1);
        if (!dx && !dy) dx = 1;
        const int len = rnd_in(2, 9);
        for (int i = 0; i < len; ++i) put(opq, x + i * dx, y + i * dy);
        break;
    }
    case 6: { // checkerboard within 2-5 of p, either parity
        const int rad = rnd_in(2, 5), par = static_cast<int>(rnd() & 1);
        for (int y = py - rad; y <= py + rad; ++y)
            for (int x = px - rad; x <= px + rad; ++x)
                if (((x + y) & 1) == par) put(opq, x, y);
        break;
    }
    default: { // density 5-30% within kWin plus a gappy ring of walls at distance 1 or 2
        const int d = rnd_in(5, 30);
        for (int y = py - kWin; y <= py + kWin; ++y)
            for (int x = px - kWin; x <= px + kWin; ++x)
                if (static_cast<int>(rnd() % 100) < d) put(opq, x, y);
        const int r = rnd_in(1, 2);
        for (int y = py - r; y <= py + r; ++y)
            for (int x = px - r; x <= px + r; ++x)
                if (cheb(x, y, px, py) == r && rnd() % 3) put(opq, x, y);
        break;
    }
    }
    unset(opq, px, py);
}

struct Stats {
    long long pair_cmp[kNR][kNR] = {}, pair_bad[kNR][kNR] = {};
    long long adj_clear = 0, adj_clear_missing = 0, adj_opaque = 0, adj_opaque_seen = 0;
    long long out_opaque = 0, out_beyond = 0, shadowed = 0, origin_in = 0, casts = 0, opaque_within = 0;
    int printed = 0, layout_bad = 0;
};

Stats st;
int trial = 0;

void layout_check(cambc::bitboard& board, cambc::bitboard& out, Bits& bits) {
    for (int k = 0; k < 50; ++k) {
        const int x = rnd_in(0, W - 1), y = rnd_in(0, H - 1);
        board.clear();
        board.set(cambc::vec2{x, y});
        board.export_linear_buffer(bits);
        int ones = 0;
        for (auto b : bits) ones += __builtin_popcount(b);
        st.layout_bad += ones != 1 || !get(bits, x, y);
        out.import_linear_buffer(bits);
        st.layout_bad += !out.is_set(cambc::vec2{x, y}) || out.count() != 1;
    }
}

void one_trial(cambc::bitboard& board, cambc::bitboard& out, Bits& opq, std::vector<Bits>& cast) {
    const int t = trial;
    int px, py, kind;
    build(opq, px, py, kind);
    board.import_linear_buffer(opq);
    for (int k = 0; k < kNR; ++k) {
        const int R = kRadii[k];
        board.shadow_cast_into(cambc::vec2{px, py}, static_cast<std::uint16_t>(R), out);
        out.export_linear_buffer(cast[k]);
        const Bits& c = cast[k];
        ++st.casts;
        if (get(c, px, py)) ++st.origin_in;
        long long within = 0;
        for (int y = std::max(0, py - R); y <= std::min(H - 1, py + R); ++y)
            for (int x = std::max(0, px - R); x <= std::min(W - 1, px + R); ++x) {
                const bool o = get(opq, x, y), v = get(c, x, y);
                st.opaque_within += o;
                within += v;
                st.out_opaque += o && v;
                st.shadowed += !o && !v;
            }
        st.out_beyond += static_cast<long long>(out.count()) - within;
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int tx = px + dx, ty = py + dy;
                if ((!dx && !dy) || !inb(tx, ty)) continue;
                const bool v = get(c, tx, ty);
                if (get(opq, tx, ty)) {
                    ++st.adj_opaque;
                    st.adj_opaque_seen += v;
                    continue;
                }
                ++st.adj_clear;
                if (v) continue;
                ++st.adj_clear_missing;
                if (st.printed < kMaxPrinted) {
                    ++st.printed;
                    debug_block({ std::printf("PROBE adjacent miss trial=%d kind=%d p=(%d,%d) R=%d tile=(%d,%d)\n", t, kind, px, py, R, tx, ty); });
                    dump(opq, px, py, R + 1, &c, nullptr);
                }
            }
    }
    for (int a = 0; a < kNR; ++a)
        for (int b = a + 1; b < kNR; ++b) {
            const int r = kRadii[a];
            ++st.pair_cmp[a][b];
            // The small cast's tiles outside r are counted by out_beyond (all zero means none exist).
            bool bad = false;
            for (int y = std::max(0, py - r); y <= std::min(H - 1, py + r); ++y)
                for (int x = std::max(0, px - r); x <= std::min(W - 1, px + r); ++x)
                    bad |= get(cast[a], x, y) != get(cast[b], x, y);
            if (!bad) continue;
            ++st.pair_bad[a][b];
            if (st.printed < kMaxPrinted) {
                ++st.printed;
                const int R = kRadii[b];
                debug_block({ std::printf("PROBE radius mismatch trial=%d kind=%d p=(%d,%d) r=%d R=%d\n", t, kind, px, py, r, R); });
                dump(opq, px, py, R + 1, &cast[a], &cast[b]);
            }
        }
}

void summary(std::uint64_t seed) {
    const unsigned long long s = seed;
    debug_block({ std::printf("PROBE summary map=%dx%d seed=%llu trials=%d layout_bad=%d\n", W, H, s, kTrials, st.layout_bad); });
    for (int a = 0; a < kNR; ++a)
        for (int b = a + 1; b < kNR; ++b) {
            const int r = kRadii[a], R = kRadii[b];
            const long long n = st.pair_cmp[a][b], bad = st.pair_bad[a][b];
            debug_block({ std::printf("PROBE radius r=%d R=%d comparisons=%lld mismatches=%lld\n", r, R, n, bad); });
        }
    debug_block({ std::printf("PROBE adjacent clear: checks=%lld missing=%lld\n", st.adj_clear, st.adj_clear_missing); });
    debug_block({ std::printf("PROBE adjacent opaque: checks=%lld in_output=%lld\n", st.adj_opaque, st.adj_opaque_seen); });
    debug_block({ std::printf("PROBE casts=%lld origin_in_output=%lld opaque_in_output=%lld (opaque tiles within R: %lld) outside_R=%lld shadowed_clear=%lld\n", st.casts, st.origin_in, st.out_opaque, st.opaque_within, st.out_beyond, st.shadowed); });
}

} // namespace

int main() {
    if (cambc::is_draft()) {
        while (true) cambc::end_turn();
    }
    const std::uint64_t id = static_cast<std::uint64_t>(cambc::detail::cached_my_team) * 4 +
                             static_cast<std::uint64_t>(cambc::detail::cached_my_champion);
    const std::uint64_t seed = 0x9E3779B97F4A7C15ull ^ (id * 0x2545F4914F6CDD1Dull + 1);
    rng_state = seed;
    W = cambc::map::width();
    H = cambc::map::height();
    cambc::bitboard board, out;
    Bits opq(cambc::bitboard::linear_buffer_size());
    std::vector<Bits> cast(kNR, Bits(opq.size()));
    layout_check(board, out, opq);
    for (; trial < kTrials; ++trial) one_trial(board, out, opq, cast);
    summary(seed);
    while (true) cambc::end_turn();
}
