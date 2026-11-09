// Mirrors tools/mapgen/grid.mjs, generate.mjs metrics() and draftlab/features.mjs extras() step for
// step, rounding included (the model was fit on the rounded values): change them together.
#include "map_features.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <iterator>
#include <limits>
#include <memory>
#include <stdexcept>
#include <utility>
#include "draft_model.h"
#if defined(__wasm_simd128__)
#include <wasm_simd128.h>
#endif

namespace aph::mapfeat {

namespace {

constexpr int camp_gems[6] = {4, 15, 7, 0, 200, 36};  // wolf, elk, gem_cluster, gold_cluster, monolith, golem
constexpr int camp_gold[6] = {40, 90, 0, 20, 300, 160};
constexpr int dash_cost = 4, tele_cost = 8;
// grid.mjs N8, in its order: the clearance below depends on it.
constexpr int n8[8][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}, {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
constexpr double inf = std::numeric_limits<double>::infinity();
constexpr double nan = std::numeric_limits<double>::quiet_NaN();

constexpr bool same(const char* a, const char* b) { return *a == *b && (*a == 0 || same(a + 1, b + 1)); }
constexpr int slot_of(const char* name) {
    for (int k = 0; k < count; ++k)
        if (same(names[k], name)) return k;
    return -1;
}
// draft_model.h's features as indices into compute()'s values.
constexpr auto slots = [] {
    std::array<int, draft_model::features> s{};
    for (int k = 0; k < draft_model::features; ++k) s[k] = slot_of(draft_model::feature_names[k]);
    return s;
}();
static_assert(std::find(slots.begin(), slots.end(), -1) == slots.end(), "draft_model.h has a feature compute() does not measure");
enum Extra : int { dash_gain = 19, narrow, spawn_ring, max_group, camp_altar, sight_gap };
static_assert(same(names[dash_gain], "dash_gain") && same(names[sight_gap], "sight_gap") && sight_gap == base_count - 1);
enum Raw : int { monoliths = base_count, golems, camps_side, walls, shared_groups, first_derived };
static_assert(same(names[monoliths], "monoliths") && same(names[shared_groups], "shared_groups"));

// Derived features (tools/draftlab/derived.mjs), parsed from their names: one_altar, sq_<a> = T(a)^2 and
// pr_<a>__<b> = T(a) T(b), T the base feature's model.mjs transform.
enum Kind : int { k_none, k_one_altar, k_square, k_product };
struct Derived {
    int kind = k_none, a = -1, b = -1;
};
constexpr int length(const char* s) { return *s ? 1 + length(s + 1) : 0; }
constexpr int base_slot(const char* s, int len) {
    for (int k = 0; k < base_count; ++k) {
        if (length(names[k]) != len) continue;
        bool eq = true;
        for (int i = 0; i < len; ++i) eq = eq && names[k][i] == s[i];
        if (eq) return k;
    }
    return -1;
}
constexpr Derived derived_of(const char* name) {
    const int len = length(name);
    if (same(name, "one_altar")) return {k_one_altar};
    const bool sq = len > 3 && name[0] == 's' && name[1] == 'q' && name[2] == '_', pr = len > 3 && name[0] == 'p' && name[1] == 'r' && name[2] == '_';
    if (sq) return {k_square, base_slot(name + 3, len - 3), base_slot(name + 3, len - 3)};
    if (pr)
        for (int i = 3; i + 1 < len; ++i)
            if (name[i] == '_' && name[i + 1] == '_') return {k_product, base_slot(name + 3, i - 3), base_slot(name + i + 2, len - i - 2)};
    return {};
}
constexpr auto derived = [] {
    std::array<Derived, count> d{};
    for (int k = first_derived; k < count; ++k) d[k] = derived_of(names[k]);
    return d;
}();
static_assert([] {
    for (int k = first_derived; k < count; ++k)
        if (derived[k].kind == k_none || (derived[k].kind != k_one_altar && (derived[k].a < 0 || derived[k].b < 0))) return false;
    return true;
}(), "map_features.h names a derived feature this file cannot parse");
enum BaseTf : int { bt_none, bt_log, bt_log1p };
// model.mjs FEATURES' transforms of the 25 base features (derived.mjs BASE_TRANSFORMS).
constexpr BaseTf base_tf[base_count] = {bt_log, bt_none, bt_log, bt_none, bt_none, bt_none, bt_none, bt_none, bt_log1p, bt_none,
                                        bt_none, bt_log1p, bt_log1p, bt_none, bt_none, bt_none, bt_none, bt_none, bt_log1p, bt_log,
                                        bt_none, bt_none, bt_log1p, bt_log, bt_none};

// JS Math.round (halves toward +infinity), then mapgen's r2 / r3 and frac.
double js_round(double v) {
    const double r = std::floor(v);
    return v - r >= 0.5 ? r + 1 : r;
}
double r2(double v) { return js_round(100 * v) / 100; }
double r3(double v) { return js_round(1000 * v) / 1000; }

// Dash ends at Chebyshev 2, their middle tiles (king-adjacent to both ends, as n8 indices) and, per
// mask of unwalkable n8 neighbours, the ends whose middle tiles are all among them.
struct Dashes {
    int dx[16], dy[16], mids[16], mid[16][3];
    std::uint16_t over[256];
};
// Built at compile time: at run time it cost ~300k fuel, paid on the first draft turn.
constexpr int iabs(int v) { return v < 0 ? -v : v; }
constexpr Dashes make_dashes() {
    Dashes t{};
    int e = 0;
    for (int dy = -2; dy <= 2; ++dy)
        for (int dx = -2; dx <= 2; ++dx) {
            if (std::max(iabs(dx), iabs(dy)) < 2) continue;
            t.dx[e] = dx, t.dy[e] = dy;
            for (int k = 0; k < 8; ++k) {
                const int a = n8[k][0], b = n8[k][1];
                const bool ax = iabs(dx) == 2 ? a == dx / 2 : dx ? a == 0 || a == dx : true;
                const bool by = iabs(dy) == 2 ? b == dy / 2 : dy ? b == 0 || b == dy : true;
                if (ax && by && std::max(iabs(dx - a), iabs(dy - b)) <= 1) t.mid[e][t.mids[e]++] = k;
            }
            ++e;
        }
    for (unsigned m = 0; m < 256; ++m)
        for (e = 0; e < 16; ++e) {
            bool all = true;
            for (int k = 0; k < t.mids[e]; ++k) all = all && (m >> t.mid[e][k] & 1);
            if (all) t.over[m] |= static_cast<std::uint16_t>(1u << e);
        }
    return t;
}
constexpr Dashes dash_table = make_dashes();
const Dashes& dashes() { return dash_table; }

// out[i] = 1 where a[i] >= 0, else 0. In the bot 16 tiles a few SIMD instructions (the plain loop
// vectorised poorly, ~6 fuel a tile).
void nonneg_mask(const int* a, std::uint8_t* out, int n) {
    int i = 0;
#if defined(__wasm_simd128__)
    const v128_t zero = wasm_i32x4_splat(0), one = wasm_i32x4_splat(1);
    const auto lanes = [&](const int* p) { return wasm_v128_and(wasm_i32x4_ge(wasm_v128_load(p), zero), one); };
    for (; i + 16 <= n; i += 16) {
        const v128_t lo = wasm_u16x8_narrow_i32x4(lanes(a + i), lanes(a + i + 4));
        const v128_t up = wasm_u16x8_narrow_i32x4(lanes(a + i + 8), lanes(a + i + 12));
        wasm_v128_store(out + i, wasm_u8x16_narrow_i16x8(lo, up));
    }
#endif
    for (; i < n; ++i) out[i] = a[i] >= 0;
}

struct Grid {
    const Input& in;
    int W, H, n;
    explicit Grid(const Input& i) : in{i}, W{i.W}, H{i.H}, n{i.W * i.H} {}

    bool inside(int x, int y) const { return x >= 0 && y >= 0 && x < W && y < H; }
    int mirror(int i) const {
        const int x = i % W, y = i / W;
        if (in.sym == horizontal) return y * W + (W - 1 - x);
        if (in.sym == vertical) return (H - 1 - y) * W + x;
        return (H - 1 - y) * W + (W - 1 - x);
    }
    // out[i] = a[mirror(i)], a row at a time.
    void mirrored(const std::vector<int>& a, std::vector<int>& out) const {
        out.clear();
        out.reserve(static_cast<std::size_t>(n));
        const bool flip_rows = in.sym != horizontal, reverse = in.sym != vertical;
        for (int y = 0; y < H; ++y) {
            const int* const row = a.data() + (flip_rows ? H - 1 - y : y) * W;
            if (reverse) out.insert(out.end(), std::make_reverse_iterator(row + W), std::make_reverse_iterator(row));
            else out.insert(out.end(), row, row + W);
        }
    }
    std::vector<int> spawn_tiles(int team) const {
        std::vector<int> out;
        for (int y = in.sy; y < in.sy + in.sh; ++y)
            for (int x = in.sx; x < in.sx + in.sw; ++x) out.push_back(team ? mirror(y * W + x) : y * W + x);
        return out;
    }
    bool walk_tile(int i) const { return in.t[i] == ground || in.t[i] == bush; }

    std::vector<std::uint8_t> camp_mask() const {
        std::vector<std::uint8_t> m(n, 0);
        for (const auto& c : in.camps) m[c.y * W + c.x] = 1;
        return m;
    }

    // spawnFields' pass for one side: walkable, the other spawn blocked (and the camps).
    std::vector<std::uint8_t> pass_for(int side, const std::uint8_t* blockers) const {
        std::vector<std::uint8_t> pass(n);
        for (int i = 0; i < n; ++i) pass[i] = walk_tile(i) && !(blockers && blockers[i]) ? 1 : 0;
        for (const int i : spawn_tiles(1 - side)) pass[i] = 0;
        return pass;
    }

    void bfs(const std::vector<int>& starts, const std::vector<std::uint8_t>& pass, std::vector<int>& dist) const {
        dist.assign(n, -1);
        std::vector<int> q(n);
        int head = 0, tail = 0;
        for (const int s : starts)
            if (pass[s] && dist[s] < 0) dist[s] = 0, q[tail++] = s;
        while (head < tail) {
            const int i = q[head++], x = i % W, y = i / W;
            for (const auto& d : n8) {
                const int nx = x + d[0], ny = y + d[1];
                if (!inside(nx, ny)) continue;
                const int j = ny * W + nx;
                if (pass[j] && dist[j] < 0) dist[j] = dist[i] + 1, q[tail++] = j;
            }
        }
    }

    // grid.mjs travel from team `side`'s spawn over spawnFields' tiles with no blockers: walking 1,
    // from level 1 a dash (2 king steps over a middle tile that is not a wall or the other spawn)
    // DASH_COST, from level 2 a crystal (range 3) TELE_COST, only from tiles near something
    // unwalkable. Rather than search from the spawn, it starts from `base`, the walking field over
    // the same tiles: the tiles that could leap try their dashes and crystals in `base`
    // order, and Dial's algorithm runs only from the tiles they improve (any exact order gives the
    // same distances). Fills `dist` if given; returns the tiles brought 6 or more nearer (dash_short).
    // For fuel (~1 a WASM instruction, so per-tile work is what costs): a grid padded by 3 blocked tiles, so no
    // bounds checks, `d` holding distance + 1 (0 where blocked, -1 on holes and altars, which a dash crosses),
    // byte masks read 8 tiles a word, and one instantiation per level.
    // `work`, if given, gets the leaping tiles walked to and the tiles brought nearer than walking (Work).
    int travel(int side, const std::vector<int>& base, int level, std::vector<int>* dist, int* work = nullptr) const {
        return level > 1 ? travel_at<2>(side, base, dist, work) : travel_at<1>(side, base, dist, work);
    }

    template <int level>
    int travel_at(int side, const std::vector<int>& base, std::vector<int>* dist, int* work) const {
        constexpr int pad = 3, far = std::numeric_limits<int>::max(), R = level > 1 ? 2 : 1;
        const int w = W, h = H, S = w + 2 * pad, N = S * (h + 2 * pad);
        int step[8], end[16], mid[16][3];
        for (int k = 0; k < 8; ++k) step[k] = n8[k][1] * S + n8[k][0];
        const auto& t = dashes();
        for (int e = 0; e < 16; ++e) {
            end[e] = t.dy[e] * S + t.dx[e];
            for (int m = 0; m < t.mids[e]; ++m) mid[e][m] = step[t.mid[e][m]];
        }
        const auto load8 = [](const std::uint8_t* p) {
            std::uint64_t x;
            std::memcpy(&x, p, 8);
            return x;
        };
        const auto store8 = [](std::uint8_t* p, std::uint64_t x) { std::memcpy(p, &x, 8); };
        // The byte masks are read and written a word at a time (16 tiles in the bot), up to 16 bytes past a row.
        const auto bytes = [&] { return std::make_unique<std::uint8_t[]>(static_cast<std::size_t>(N + 32)); };
#if defined(__wasm_simd128__)
        using Word = v128_t;
        constexpr int wb = 16;
        const auto ld = [](const std::uint8_t* p) { return wasm_v128_load(p); };
        const auto st = [](std::uint8_t* p, Word x) { wasm_v128_store(p, x); };
        const auto shl = [](Word x, int k) { return wasm_i8x16_shl(x, static_cast<std::uint32_t>(k)); };
#else
        using Word = std::uint64_t;
        constexpr int wb = 8;
        const auto ld = load8;
        const auto st = store8;
        const auto shl = [](Word x, int k) { return x << k; }; // bytes 0 or 1: no carry between them
#endif
        const auto d_v = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(N));
        int* const d = d_v.get();
        // The padding 0 (a row's right padding runs into the next row's left), the map tiles written below.
        std::memset(d, 0, sizeof(int) * static_cast<std::size_t>(pad * S + pad));
        for (int y = 0; y < h; ++y) std::memset(d + (y + pad) * S + pad + w, 0, sizeof(int) * 2 * pad);
        std::memset(d + (h + pad) * S + pad, 0, sizeof(int) * static_cast<std::size_t>(N - (h + pad) * S - pad));
        // Byte masks, written with d: `low`, the tiles no move lands on (d <= 0: JS's !pass and the padding; they
        // never change); the tiles walked to (base 0 or more: base is -1 exactly on the tiles that are
        // unwalkable, the other spawn or not walked to); and with crystals the landable tiles no crystal has
        // reached yet (`open`): tiles pop in distance order, so the first crystal to reach a tile is its best,
        // and each tile is relaxed by a crystal at most once; a tile's 7x7 box is 7 eight-byte words, not 40.
        const auto low_v = bytes(), walked_v = bytes();
        const auto open_v = level > 1 ? bytes() : nullptr;
        // A dash beats walking only over a hole or altar (a walkable middle tile is walked through for 2, walls
        // block), so only tiles next to one (`cross`) try dashes; without crystals only they leap.
        const auto cross_v = bytes();
        std::uint8_t* const cross = cross_v.get();
        std::uint8_t* const low = low_v.get();
        std::uint8_t* const walked = walked_v.get();
        std::uint8_t* const open = open_v.get();
        std::memset(low, 1, static_cast<std::size_t>(N));
        const int* const bd = base.data();
        int top = -1;
        {
            const std::uint8_t* const tile = in.t.data();
            for (int y = 0; y < h; ++y) {
                const int* const b = bd + y * w;
                const std::uint8_t* const k = tile + y * w;
                const int q0 = (y + pad) * S + pad;
                int* const row = d + q0;
                int x = 0;
#if defined(__wasm_simd128__)
                // 16 tiles: the kinds compared as bytes, the masks widened to the 4 groups of 4.
                const v128_t zero = wasm_i32x4_splat(0), one = wasm_i32x4_splat(1), farv = wasm_i32x4_splat(far);
                const v128_t minus1 = wasm_i32x4_splat(-1), one8 = wasm_i8x16_splat(1);
                v128_t most = minus1;
                for (; x + 16 <= w; x += 16) {
                    const v128_t v0 = wasm_v128_load(b + x), v1 = wasm_v128_load(b + x + 4), v2 = wasm_v128_load(b + x + 8), v3 = wasm_v128_load(b + x + 12);
                    if (wasm_i32x4_all_true(wasm_v128_and(wasm_v128_and(wasm_i32x4_ge(v0, zero), wasm_i32x4_ge(v1, zero)),
                                                          wasm_v128_and(wasm_i32x4_ge(v2, zero), wasm_i32x4_ge(v3, zero))))) {
                        // All 16 walked to (so walkable): the common case on open maps.
                        most = wasm_i32x4_max(wasm_i32x4_max(most, wasm_i32x4_max(v0, v1)), wasm_i32x4_max(v2, v3));
                        wasm_v128_store(row + x, wasm_i32x4_add(v0, one)), wasm_v128_store(row + x + 4, wasm_i32x4_add(v1, one));
                        wasm_v128_store(row + x + 8, wasm_i32x4_add(v2, one)), wasm_v128_store(row + x + 12, wasm_i32x4_add(v3, one));
                        wasm_v128_store(walked + q0 + x, one8), wasm_v128_store(low + q0 + x, wasm_i8x16_splat(0));
                        if constexpr (level > 1) wasm_v128_store(open + q0 + x, one8);
                        continue;
                    }
                    const v128_t kind = wasm_v128_load(k + x);
                    const v128_t walk = wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(ground)), wasm_i8x16_eq(kind, wasm_i8x16_splat(bush)));
                    const v128_t wall8 = wasm_i8x16_eq(kind, wasm_i8x16_splat(wall));
                    const v128_t walk16[2] = {wasm_i16x8_extend_low_i8x16(walk), wasm_i16x8_extend_high_i8x16(walk)};
                    const v128_t wall16[2] = {wasm_i16x8_extend_low_i8x16(wall8), wasm_i16x8_extend_high_i8x16(wall8)};
                    v128_t reached[4];
                    for (int g4 = 0; g4 < 4; ++g4) {
                        const v128_t wk = g4 & 1 ? wasm_i32x4_extend_high_i16x8(walk16[g4 >> 1]) : wasm_i32x4_extend_low_i16x8(walk16[g4 >> 1]);
                        const v128_t wl = g4 & 1 ? wasm_i32x4_extend_high_i16x8(wall16[g4 >> 1]) : wasm_i32x4_extend_low_i16x8(wall16[g4 >> 1]);
                        const v128_t v = wasm_v128_load(b + x + 4 * g4);
                        most = wasm_i32x4_max(most, v);
                        reached[g4] = wasm_i32x4_ge(v, zero);
                        const v128_t alt = wasm_v128_bitselect(farv, wasm_v128_bitselect(zero, minus1, wl), wk);
                        wasm_v128_store(row + x + 4 * g4, wasm_v128_bitselect(wasm_i32x4_add(v, one), alt, reached[g4]));
                    }
                    const v128_t walked8 = wasm_i8x16_narrow_i16x8(wasm_i16x8_narrow_i32x4(reached[0], reached[1]), wasm_i16x8_narrow_i32x4(reached[2], reached[3]));
                    wasm_v128_store(walked + q0 + x, wasm_v128_and(walked8, one8));
                    wasm_v128_store(low + q0 + x, wasm_v128_andnot(one8, walk));
                    if constexpr (level > 1) wasm_v128_store(open + q0 + x, wasm_v128_and(walk, one8));
                    wasm_v128_store(cross + q0 + x, wasm_v128_and(wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(hole)), wasm_i8x16_eq(kind, wasm_i8x16_splat(altar))), one8));
                }
                for (int l = 0; l < 4; ++l) top = std::max(top, wasm_i32x4_extract_lane(most, 0)), most = wasm_i32x4_shuffle(most, most, 1, 2, 3, 0);
#endif
                for (; x < w; ++x) {
                    const bool walk = k[x] == ground || k[x] == bush;
                    top = std::max(top, b[x]);
                    row[x] = b[x] >= 0 ? b[x] + 1 : walk ? far : k[x] == wall ? 0 : -1;
                    walked[q0 + x] = b[x] >= 0, low[q0 + x] = !walk;
                    if constexpr (level > 1) open[q0 + x] = walk;
                    cross[q0 + x] = k[x] == hole || k[x] == altar;
                }
            }
        }
        for (const int i : spawn_tiles(1 - side)) {
            const int q = (i / w + pad) * S + i % w + pad;
            d[q] = 0, low[q] = 1;
            if constexpr (level > 1) open[q] = 0;
        }
        // The tiles that may leap: within R of something unwalkable or the padding (R 2 with crystals, which can
        // beat walking from a tile whose neighbours are all walkable; JS leaves the padding out, but leaping from
        // more tiles changes no distance), or without crystals next to a hole or altar. Dilated along the rows,
        // then across them. nb is left 0 outside the leaping words, where no dash can beat walking.
        const std::uint8_t* const src = level > 1 ? low : cross;
        const auto across_v = bytes(), leaps_v = bytes();
        std::uint8_t* const across = across_v.get();
        std::uint8_t* const leaps = leaps_v.get();
        for (int r = pad - R; r < h + pad + R; ++r)
            for (int q = r * S + pad, e = q + w; q < e; q += wb) {
                Word x = ld(src + q - 1) | ld(src + q) | ld(src + q + 1);
                if constexpr (R > 1) x |= ld(src + q - 2) | ld(src + q + 2);
                st(across + q, x);
            }
        for (int y = 0; y < h; ++y)
            for (int q = (y + pad) * S + pad, e = q + w; q < e; q += wb) {
                Word x = ld(across + q - S) | ld(across + q) | ld(across + q + S);
                if constexpr (R > 1) x |= ld(across + q - 2 * S) | ld(across + q + 2 * S);
                st(leaps + q, x);
            }
        // Each map tile's mask of low n8 neighbours (a byte's bit k from the low byte at step k).
        const auto nb_v = bytes();
        std::uint8_t* const nb = nb_v.get();
        // Only words with a tile next to a hole or altar are filled (the rest stay 0, trying no dash): with crystals,
        // cross dilated once more into `across`, which the leaps no longer need.
        const std::uint8_t* dashers = leaps;
        if constexpr (level > 1) {
            for (int r = pad - 1; r < h + pad + 1; ++r)
                for (int q = r * S + pad, e = q + w; q < e; q += wb) st(nb_v.get() + q, ld(cross + q - 1) | ld(cross + q) | ld(cross + q + 1));
            for (int y = 0; y < h; ++y)
                for (int q = (y + pad) * S + pad, e = q + w; q < e; q += wb)
                    st(across + q, ld(nb_v.get() + q - S) | ld(nb_v.get() + q) | ld(nb_v.get() + q + S));
            std::memset(nb_v.get(), 0, static_cast<std::size_t>(N + 32));
            dashers = across;
        }
        for (int y = 0; y < h; ++y)
            for (int q = (y + pad) * S + pad, e = q + w; q < e; q += wb) {
#if defined(__wasm_simd128__)
                if (!wasm_v128_any_true(ld(dashers + q))) continue;
#else
                if (!ld(dashers + q)) continue;
#endif
                Word x = ld(low + q + step[0]);
                for (int k = 1; k < 8; ++k) x |= shl(ld(low + q + step[k]), k);
                st(nb + q, x);
            }
        int heads = 0;
        std::vector<int> head(static_cast<std::size_t>(top + 1), -1);
        const auto next = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(N));
        for (int y = 0; y < h; ++y)
            for (int c = (y + pad) * S + pad, e = c + w; c < e; c += 8)
                for (std::uint64_t m = load8(leaps + c) & load8(walked + c); m; m &= m - 1) {
                    const int q = c + (std::countr_zero(m) >> 3);
                    if (q >= e) break;
                    next[q] = head[static_cast<std::size_t>(d[q] - 1)], head[static_cast<std::size_t>(d[q] - 1)] = q;
                    ++heads;
                }
        // Dial's buckets: a bucket holds one distance at a time, and a tile at most once a distance. From distance v
        // a tile is pushed only at v + 1, v + 4 and v + 8, three buckets other than v's (B is 9).
        constexpr int B = tele_cost + 1;
        static_assert(dash_cost == 4 && tele_cost == 8);
        const auto pool = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(B * n));
        int size[B] = {}, pending = 0, gained = 0, popped = 0;
        for (int v = 0; v <= top || pending; ++v) {
            int* const walk_to = &pool[(v + 1) % B * n];
            int* const dash_to = &pool[(v + 4) % B * n];
            int* const tele_to = &pool[(v + 8) % B * n];
            int walks = size[(v + 1) % B], dashes_n = size[(v + 4) % B], teles = size[(v + 8) % B];
            // Dashes and crystals from i. A dash over a walkable middle tile never beats walking
            // through it (2 < DASH_COST), so only ends whose middle tiles are all unwalkable are tried.
            const auto leap = [&](int i, unsigned blocked) __attribute__((always_inline)) {
                for (unsigned c = t.over[blocked]; c; c &= c - 1) {
                    const int e = std::countr_zero(c), j = i + end[e];
                    if (d[j] <= v + 1 + dash_cost) continue;
                    for (int m = 0; m < t.mids[e]; ++m)
                        if (d[i + mid[e][m]]) {
                            d[j] = v + 1 + dash_cost, dash_to[dashes_n++] = j;
                            break;
                        }
                }
                if constexpr (level > 1) {
                    if (!leaps[i]) return;
                    constexpr std::uint64_t box = 0x00ffffffffffffffull;
                    const std::uint8_t* const o = open + i - 3 - 3 * S;
                    std::uint64_t x[7];
                    for (int r = 0; r < 7; ++r) x[r] = load8(o + r * S) & box;
                    if (!(x[0] | x[1] | x[2] | x[3] | x[4] | x[5] | x[6])) return;
                    for (int r = 0; r < 7; ++r)
                        for (; x[r]; x[r] &= x[r] - 1) {
                            const int j = i - 3 + (r - 3) * S + (std::countr_zero(x[r]) >> 3);
                            open[j] = 0;
                            if (v + 1 + tele_cost < d[j]) d[j] = v + 1 + tele_cost, tele_to[teles++] = j;
                        }
                }
            };
            // A tile improved since is popped at its new distance instead.
            if (v <= top)
                for (int i = head[static_cast<std::size_t>(v)]; i >= 0; i = next[i])
                    if (d[i] == v + 1) leap(i, nb[i]);
            int* const bucket = &pool[v % B * n];
            for (int left = size[v % B]; left;) {
                const int i = bucket[--left];
                if (d[i] != v + 1) continue;
                ++popped;
                if constexpr (level == 1)
                    if (const int was = bd[(i / S - pad) * w + i % S - pad]; was >= 0 && was - v >= 6) ++gained;
                // Low tiles hold d <= 0, so never pass the test.
                for (int k = 0; k < 8; ++k)
                    if (const int j = i + step[k]; v + 2 < d[j]) d[j] = v + 2, walk_to[walks++] = j;
                leap(i, nb[i]);
            }
            size[v % B] = 0, size[(v + 1) % B] = walks, size[(v + 4) % B] = dashes_n, size[(v + 8) % B] = teles;
            pending = 0;
            for (const int k : size) pending |= k;
        }
        if (dist) {
            dist->resize(static_cast<std::size_t>(n));
            int* const out = dist->data();
            for (int y = 0, i = 0; y < h; ++y)
                for (int x = 0, q = (y + pad) * S + pad; x < w; ++x, ++i, ++q) out[i] = d[q] > 0 && d[q] != far ? d[q] - 1 : -1;
        }
        if (work) work[0] = heads, work[1] = popped;
        return gained;
    }

    int reach_near(const std::vector<int>& dist, int x, int y) const {
        int best = -1;
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int nx = x + dx, ny = y + dy;
                if ((dx || dy) && inside(nx, ny)) {
                    const int d = dist[ny * W + nx];
                    if (d >= 0 && (best < 0 || d < best)) best = d;
                }
            }
        return best;
    }

    // grid.mjs clearance (metrics' openness: each capped at 6), summed over the tiles `reach` reaches:
    // walls, holes, altars 0, walkable edge tiles 1, then a BFS whose queue mixes the two in index
    // order, so a tile can read one more than its true distance. Tiles at 6 or more are not expanded:
    // everything below 6 is unchanged, as later queue entries are at most one below earlier ones.
    // Padded by a tile that reads as set; raw pointers as in travel.
    int clearance_sum(const std::uint8_t* reach) const {
        constexpr std::uint8_t unset = 0xff;
        const int w = W, h = H, S = w + 2;
        // 8 bytes of slack: the queue's first entries are found 8 tiles a word.
        std::vector<std::uint8_t> d_v(static_cast<std::size_t>(S * (h + 2) + 8), 0);
        const auto q = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(n));
        std::uint8_t* const d = d_v.data();
        const std::uint8_t* const t = in.t.data();
        // Unwalkable 0, walkable edge tiles 1, the rest unset (a loop that vectorises), then the set ones queued
        // in index order.
        for (int y = 0; y < h; ++y) {
            std::uint8_t* const row = d + (y + 1) * S + 1;
            const std::uint8_t* const k = t + y * w;
            for (int x = 0; x < w; ++x) row[x] = k[x] == ground || k[x] == bush ? unset : 0;
            const auto edge = [](std::uint8_t& v) { v = v ? 1 : 0; };
            edge(row[0]), edge(row[w - 1]);
            if (y == 0 || y == h - 1)
                for (int x = 0; x < w; ++x) edge(row[x]);
        }
        int tail = 0;
        for (int y = 0; y < h; ++y)
            for (int c = (y + 1) * S + 1, e = c + w; c < e; c += 8) {
                std::uint64_t word;
                std::memcpy(&word, d + c, 8);
                // A byte of ~word is nonzero where the tile is set (0 or 1), up to 7 bytes past the row.
                for (std::uint64_t m = ~word; m; m &= ~(0xffull << (std::countr_zero(m) & ~7))) {
                    const int p = c + (std::countr_zero(m) >> 3);
                    if (p >= e) break;
                    q[tail++] = p;
                }
            }
        int step[8];
        for (int k = 0; k < 8; ++k) step[k] = n8[k][1] * S + n8[k][0];
        // Tiles reaching 6 are set but not queued: they would only be skipped.
        for (int k = 0; k < tail; ++k) {
            const int p = q[k];
            const std::uint8_t v = d[p];
            if (v >= 6) continue;
            if (v == 5) {
                for (const int o : step)
                    if (d[p + o] == unset) d[p + o] = 6;
            } else
                for (const int o : step)
                    if (d[p + o] == unset) d[p + o] = static_cast<std::uint8_t>(v + 1), q[tail++] = p + o;
        }
        // Set tiles read at most 6, unset ones (255) 6: (v & 7) - (v >> 7) a byte, 8 tiles a word.
        int sum = 0;
        for (int y = 0; y < h; ++y)
            for (int x = 0; x < w; x += 8) {
                std::uint64_t v, r;
                std::memcpy(&v, d + (y + 1) * S + 1 + x, 8);
                std::memcpy(&r, reach + y * w + x, 8);
                if (w - x < 8) r &= (1ull << (8 * (w - x))) - 1;
                const std::uint64_t capped = ((v & 0x0707070707070707ull) - (v >> 7 & 0x0101010101010101ull)) & r * 0xff;
                sum += static_cast<int>(capped * 0x0101010101010101ull >> 56);
            }
        return sum;
    }
};

struct Group {
    std::vector<int> members; // indices into Input::camps
    int lo, mlo;              // lowest tile index, and of the mirror's: sideGroups' tie-break
    bool shared;
    int gems, gold;
};

// grid.mjs groups(): cardinally connected camps; shared when the symmetry maps the group onto itself.
std::vector<Group> groups_of(const Grid& g) {
    const auto& all = g.in.camps;
    // Camp tiles: a byte a tile, and an unset int a tile written only on camps (filling one cost 4 fuel a tile).
    std::vector<std::uint8_t> is_camp(static_cast<std::size_t>(g.n), 0);
    const auto camp_at = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(g.n));
    for (std::size_t k = 0; k < all.size(); ++k) {
        const int i = all[k].y * g.W + all[k].x;
        is_camp[static_cast<std::size_t>(i)] = 1, camp_at[i] = static_cast<int>(k);
    }
    const auto at = [&](int i) { return is_camp[static_cast<std::size_t>(i)] ? camp_at[i] : -1; };
    std::vector<std::uint8_t> seen(all.size(), 0);
    std::vector<Group> out;
    constexpr int n4[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    for (std::size_t k = 0; k < all.size(); ++k) {
        if (seen[k]) continue;
        Group q{{}, g.n, g.n, false, 0, 0};
        std::vector<int> stack{static_cast<int>(k)};
        seen[k] = 1;
        while (!stack.empty()) {
            const int m = stack.back();
            stack.pop_back();
            q.members.push_back(m);
            const auto& c = all[m];
            for (const auto& s : n4) {
                const int nx = c.x + s[0], ny = c.y + s[1];
                if (!g.inside(nx, ny)) continue;
                const int j = at(ny * g.W + nx);
                if (j >= 0 && !seen[j]) seen[j] = 1, stack.push_back(j);
            }
        }
        const int first = all[k].y * g.W + all[k].x, mirror = g.mirror(first);
        for (const int m : q.members) {
            const int i = all[m].y * g.W + all[m].x;
            q.lo = std::min(q.lo, i), q.mlo = std::min(q.mlo, g.mirror(i));
            q.shared = q.shared || i == mirror;
            q.gems += camp_gems[all[m].type], q.gold += camp_gold[all[m].type];
        }
        out.push_back(std::move(q));
    }
    return out;
}

// shapeMetrics' sight_gap: from every floor(n / 300)-th of the n playable tiles (index order; 300-599 of them from 300
// up), of the tiles 2-3 away that are walkable and on a clear line (no wall or bush between, mapgen's rounded line),
// the share 5 or more steps further on foot than the Chebyshev distance r, or unreached. The JS walks a BFS 8 steps in a 17x17 window; only whether a target is
// within r + 4 steps matters, and a walk of at most 7 steps to a tile within 3 never strays more than 5 from its
// start, so a bit-parallel BFS over 11x11 decides the same, stopped once every counted target is reached or the reach
// stops growing (open ground: two or three steps). Rows are bit sets padded so windows need no bounds checks; the 7x7
// around the source is a 49-bit mask, bit (dy + 3) * 7 + dx + 3.
double sight_gap_of(const Grid& g, const std::vector<std::uint8_t>& play, int play_n, int* steps) {
    constexpr int R = 5, side = 2 * R + 1, pad = 8, words = 3;
    struct Target {
        std::uint64_t bit, line; // the target, and the tiles between
    };
    struct Targets {
        std::array<std::uint64_t, 49> blocks; // by tile bit: the targets it lies between the source and
        std::uint64_t ring2, ring3;
    };
    static const auto targets = [] {
        Targets out{};
        for (int dy = -3; dy <= 3; ++dy)
            for (int dx = -3; dx <= 3; ++dx) {
                const int r = std::max(std::abs(dx), std::abs(dy));
                if (r < 2) continue;
                Target t{1ull << ((dy + 3) * 7 + dx + 3), 0};
                (r == 2 ? out.ring2 : out.ring3) |= t.bit;
                // x0 + dx t / 2r rounds as dx t / 2r does: its fraction is a sixth or a quarter, never near a half
                // unless exactly one.
                for (int s = 1; s < 2 * r; ++s) {
                    const int ox = static_cast<int>(js_round(dx * s / (2.0 * r))), oy = static_cast<int>(js_round(dy * s / (2.0 * r)));
                    if ((ox || oy) && (ox != dx || oy != dy)) t.line |= 1ull << ((oy + 3) * 7 + ox + 3);
                }
                for (int b = 0; b < 49; ++b)
                    if (t.line >> b & 1) out.blocks[static_cast<std::size_t>(b)] |= t.bit;
            }
        return out;
    }();
    // Rows 2-8 of an 11x11 window (row r at r + off), columns 2-8.
    const auto core = [](const std::uint32_t* rows, int off) {
        std::uint64_t c = 0;
        for (int r = 0; r < 7; ++r) c |= static_cast<std::uint64_t>(rows[r + 2 + off] >> 2 & 0x7f) << (r * 7);
        return c;
    };
    const int W = g.W, H = g.H, rows = H + 2 * R;
    // Bit x + pad of row y + R: walkable (ground or bush), and opaque (wall or bush).
    std::vector<std::uint64_t> pass(static_cast<std::size_t>(rows * words), 0), opaque(pass.size(), 0);
    // 8 tiles at a time: their kinds as 0/1 bytes, packed to 8 bits by a multiply, then shifted into place.
    {
        std::vector<std::uint8_t> pb(static_cast<std::size_t>(W + 8), 0), ob(pb.size(), 0);
        for (int y = 0; y < H; ++y) {
            const std::uint8_t* const k = g.in.t.data() + static_cast<std::size_t>(y) * W;
            std::uint64_t* const prow = &pass[static_cast<std::size_t>((y + R) * words)];
            std::uint64_t* const orow = &opaque[static_cast<std::size_t>((y + R) * words)];
            int x0 = 0;
#if defined(__wasm_simd128__)
            // 16 tiles at a time, straight to bits.
            for (; x0 + 16 <= W; x0 += 16) {
                const v128_t kind = wasm_v128_load(k + x0), b = wasm_i8x16_eq(kind, wasm_i8x16_splat(bush));
                const std::uint64_t pa = wasm_i8x16_bitmask(wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(ground)), b));
                const std::uint64_t oa = wasm_i8x16_bitmask(wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(wall)), b));
                const int at = x0 + pad, q = at >> 6, sh = at & 63;
                prow[q] |= pa << sh, orow[q] |= oa << sh;
                if (sh > 48) prow[q + 1] |= pa >> (64 - sh), orow[q + 1] |= oa >> (64 - sh);
            }
#endif
            for (int x = x0; x < W; ++x)
                pb[x] = static_cast<std::uint8_t>((k[x] == ground) | (k[x] == bush)), ob[x] = static_cast<std::uint8_t>((k[x] == wall) | (k[x] == bush));
            for (int x = x0; x < W; x += 8) {
                std::uint64_t a, b;
                std::memcpy(&a, &pb[x], 8), std::memcpy(&b, &ob[x], 8);
                if (W - x < 8) a &= (1ull << (8 * (W - x))) - 1, b &= (1ull << (8 * (W - x))) - 1;
                const std::uint64_t pa = a * 0x0102040810204080ull >> 56, oa = b * 0x0102040810204080ull >> 56;
                const int at = x + pad, q = at >> 6, sh = at & 63;
                prow[q] |= pa << sh, orow[q] |= oa << sh;
                if (sh > 56) prow[q + 1] |= pa >> (64 - sh), orow[q + 1] |= oa >> (64 - sh);
            }
        }
    }
    const auto take = [](const std::uint64_t* row, int s) {
        const int q = s >> 6, b = s & 63;
        return static_cast<std::uint32_t>((b ? row[q] >> b | row[q + 1] << (64 - b) : row[q]) & ((1u << side) - 1));
    };
    const int step = std::max(1, play_n / 300);
    int seen = 0, far = 0;
#if defined(__wasm_simd128__)
    const auto ring = [&](int j) { return static_cast<std::uint16_t>((targets.ring2 >> (7 * j) & 0x7f) << 2); };
    const v128_t r2a = wasm_u16x8_make(0, 0, ring(0), ring(1), ring(2), ring(3), ring(4), ring(5)), r2b = wasm_u16x8_make(ring(6), 0, 0, 0, 0, 0, 0, 0);
#endif
#if defined(__wasm_simd128__)
    // Every step-th playable tile. From step 4, found 16 tiles a bitmask (play has 16 bytes of 0 slack), as a test a
    // tile cost ~10 fuel; below, finding a tile among the bits costs more than the tests it saves.
    const std::uint8_t* const pl = play.data();
    std::uint32_t at = 0; // the block's playable tiles from ordinal ord on
    for (int b = -16, k = 0, c = 0, ord = 0, next = 0, i = -1;; next += step) {
        if (step < 4) {
            while (++i < g.n && (!pl[i] || k++ % step)) {}
            if (i >= g.n) break;
        } else {
            while (next >= k + c && (b += 16) < g.n) {
                k += c, ord = k;
                at = wasm_i8x16_bitmask(wasm_i8x16_ne(wasm_v128_load(pl + b), wasm_i8x16_splat(0)));
                c = std::popcount(at);
            }
            if (b >= g.n) break;
            for (; ord < next; ++ord) at &= at - 1;
            i = b + std::countr_zero(at);
        }
#else
    for (int i = 0, k = 0; i < g.n; ++i) {
        if (!play[static_cast<std::size_t>(i)] || k++ % step) continue;
#endif
        const int x0 = i % W, y0 = i / W, s = x0 - R + pad;
        std::uint32_t p[side], o[side];
        for (int r = 0; r < side; ++r) p[r] = take(&pass[static_cast<std::size_t>((y0 + r) * words)], s);
        for (int r = 2; r < 9; ++r) o[r] = take(&opaque[static_cast<std::size_t>((y0 + r) * words)], s);
        // The counted targets: walkable, with a clear line.
        const std::uint64_t lines = core(o, 0);
        std::uint64_t clear = targets.ring2 | targets.ring3;
        for (std::uint64_t m = lines; m; m &= m - 1) clear &= ~targets.blocks[static_cast<std::size_t>(std::countr_zero(m))];
        const std::uint64_t need = core(p, 0) & clear;
        if (!need) continue;
        seen += std::popcount(need);
#if defined(__wasm_simd128__)
        // The window as two u16x8, lane r row r (rows 8-10 in the second's lanes 0-2): a step is a few vector
        // instructions instead of ~30 a row. Every row steps (those beyond d of the source stay 0).
        const auto row = [&](int j) { return static_cast<std::uint16_t>((need >> (7 * j) & 0x7f) << 2); };
        const v128_t z = wasm_i16x8_splat(0);
        const v128_t pa = wasm_u16x8_make(p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]), pb = wasm_u16x8_make(p[8], p[9], p[10], 0, 0, 0, 0, 0);
        const v128_t na = wasm_u16x8_make(0, 0, row(0), row(1), row(2), row(3), row(4), row(5)), nb = wasm_u16x8_make(row(6), 0, 0, 0, 0, 0, 0, 0);
        v128_t ra = wasm_u16x8_make(0, 0, 0, 0, 0, 1u << R, 0, 0), rb = z, w6a = z, w6b = z;
        static_assert(R == 5);
        for (int d = 1; d <= 7; ++d) {
            if (steps) ++*steps;
            const v128_t ha = wasm_v128_or(ra, wasm_v128_or(wasm_i16x8_shl(ra, 1), wasm_u16x8_shr(ra, 1)));
            const v128_t hb = wasm_v128_or(rb, wasm_v128_or(wasm_i16x8_shl(rb, 1), wasm_u16x8_shr(rb, 1)));
            const v128_t ua = wasm_i16x8_shuffle(z, ha, 0, 8, 9, 10, 11, 12, 13, 14), da = wasm_i16x8_shuffle(ha, hb, 1, 2, 3, 4, 5, 6, 7, 8);
            const v128_t ub = wasm_i16x8_shuffle(ha, hb, 7, 8, 9, 10, 11, 12, 13, 14), db = wasm_i16x8_shuffle(hb, z, 1, 2, 3, 4, 5, 6, 7, 8);
            const v128_t xa = wasm_v128_and(wasm_v128_or(ha, wasm_v128_or(ua, da)), pa), xb = wasm_v128_and(wasm_v128_or(hb, wasm_v128_or(ub, db)), pb);
            const bool grew = wasm_v128_any_true(wasm_v128_or(wasm_v128_andnot(xa, ra), wasm_v128_andnot(xb, rb)));
            ra = wasm_v128_or(ra, xa), rb = wasm_v128_or(rb, xb);
            if (d == 6) w6a = ra, w6b = rb;
            if (!grew || !wasm_v128_any_true(wasm_v128_or(wasm_v128_andnot(na, ra), wasm_v128_andnot(nb, rb)))) {
                if (d < 6) w6a = ra, w6b = rb;
                break;
            }
        }
        const v128_t missed = wasm_i8x16_add(
            wasm_i8x16_popcnt(wasm_v128_and(na, wasm_v128_bitselect(wasm_v128_not(w6a), wasm_v128_not(ra), r2a))),
            wasm_i8x16_popcnt(wasm_v128_and(nb, wasm_v128_bitselect(wasm_v128_not(w6b), wasm_v128_not(rb), r2b))));
        const v128_t sum = wasm_u32x4_extadd_pairwise_u16x8(wasm_u16x8_extadd_pairwise_u8x16(missed));
        far += wasm_i32x4_extract_lane(sum, 0) + wasm_i32x4_extract_lane(sum, 1) + wasm_i32x4_extract_lane(sum, 2) + wasm_i32x4_extract_lane(sum, 3);
#else
        // reach: row r at r + 1, between zero rows; after step d only rows R - d to R + d can be set.
        std::uint32_t reach[side + 2] = {}, grown[side + 2] = {};
        reach[R + 1] = 1u << R;
        std::uint64_t within6 = 0, within7 = 0;
        for (int d = 1; d <= 7; ++d) {
            if (steps) ++*steps;
            const int lo = std::max(0, R - d), hi = std::min(side - 1, R + d);
            for (int r = lo; r <= hi; ++r) grown[r + 1] = reach[r + 1] | reach[r + 1] << 1 | reach[r + 1] >> 1;
            bool grew = false;
            for (int r = lo; r <= hi; ++r) {
                const std::uint32_t next = reach[r + 1] | ((grown[r] | grown[r + 1] | grown[r + 2]) & p[r]);
                grew = grew || next != reach[r + 1];
                reach[r + 1] = next;
            }
            within7 = core(reach, 1);
            if (d == 6) within6 = within7;
            if (!grew || !(need & ~within7)) {
                if (d < 6) within6 = within7;
                break;
            }
        }
        far += std::popcount(need & targets.ring2 & ~within6) + std::popcount(need & targets.ring3 & ~within7);
#endif
    }
    return r3(static_cast<double>(far) / std::max(1, seen));
}

} // namespace

std::array<double, count> compute(const Input& in, WalkField walk, bool crystals, std::uint32_t want, ClearanceSum clear, Work* work) {
    if (in.W <= 0 || in.H <= 0 || static_cast<int>(in.t.size()) != in.W * in.H || in.sw <= 0 || in.sh <= 0
        || in.sx < 0 || in.sy < 0 || in.sx + in.sw > in.W || in.sy + in.sh > in.H)
        throw std::invalid_argument("map features: bad input");
    for (const auto& c : in.camps)
        if (c.type < 0 || c.type > 5 || c.x < 0 || c.y < 0 || c.x >= in.W || c.y >= in.H)
            throw std::invalid_argument("map features: bad camp");
    const Grid g{in};
    const int n = g.n;
    const auto a = g.spawn_tiles(0), b = g.spawn_tiles(1);
    const auto camps = g.camp_mask();
    const auto field = [&](int side, bool camps_block, std::vector<int>& out) {
        if (walk) return walk(in, side, camps_block, out);
        g.bfs(side ? b : a, g.pass_for(side, camps_block ? camps.data() : nullptr), out);
    };
    std::vector<int> openA, openB, fA, fB;
    // Team B's fields are team A's mirrored: the symmetry maps the terrain, camps and spawns onto team B's
    // (cambc-rules.yaml map.symmetry_rule; every pool and holdout map), and distances are exact. Half the fields.
    field(0, false, openA), g.mirrored(openA, openB);
    const auto spawn_dist = [&](const std::vector<int>& dA) {
        double best = inf;
        for (const int i : b) {
            const int d = g.reach_near(dA, i % g.W, i / g.W);
            if (d >= 0) best = std::min(best, static_cast<double>(d));
        }
        return best;
    };
    // metrics(): through the camps when they wall the spawns apart, then by dash and crystal.
    field(0, true, fA);
    double S = spawn_dist(fA);
    if (std::isfinite(S)) g.mirrored(fA, fB);
    else {
        fA = openA, fB = openB;
        S = spawn_dist(fA);
        if (!std::isfinite(S)) {
            if (!crystals) throw std::runtime_error("map features: spawns joined only by dash or crystal");
            // Team B's mirrored, as above (every move is symmetric too). One field instead of metrics' two.
            g.travel(0, openA, 2, &fA, work ? work->crystal : nullptr);
            g.mirrored(fA, fB);
            S = spawn_dist(fA);
            if (!std::isfinite(S)) throw std::runtime_error("map features: spawns not connected");
        }
    }
    const int Si = static_cast<int>(S);

    const double area = static_cast<double>(n);
    // Reach, the walking front, bushes, holes and the altars (the nearest reachable one by own distance, then
    // ratio, gives the contest ratio; centrality, summed in index order). Separate loops, so the counts
    // vectorise and the altars are found 8 tiles a word.
    int reach = 0, bushes = 0, holes = 0, altars = 0, wall_n = 0;
    std::vector<int> front(Si + 2, 0);
    bool any_ratio = false;
    double best_d = 0, best_ratio = 0, centre_sum = 0;
    const double cx = (g.W - 1) / 2.0, cy = (g.H - 1) / 2.0, half = std::max(g.W, g.H) / 2.0;
    const std::uint8_t* const tiles = in.t.data();
    // A byte a tile, 1 where team A walks to, with 8 bytes of slack for word reads.
    std::vector<std::uint8_t> walked_v(static_cast<std::size_t>(n + 8), 0);
    std::uint8_t* const walked = walked_v.data();
    nonneg_mask(openA.data(), walked, n);
    // Reach, bushes and holes counted 16 tiles at a time in byte lanes (at most 255 rounds before a flush).
    int c = 0;
#if defined(__wasm_simd128__)
    const auto lanes_sum = [](v128_t v) {
        const v128_t s32 = wasm_u32x4_extadd_pairwise_u16x8(wasm_u16x8_extadd_pairwise_u8x16(v));
        return wasm_i32x4_extract_lane(s32, 0) + wasm_i32x4_extract_lane(s32, 1) + wasm_i32x4_extract_lane(s32, 2) + wasm_i32x4_extract_lane(s32, 3);
    };
    while (c + 16 <= n) {
        v128_t r = wasm_i8x16_splat(0), bu = r, ho = r, wa = r;
        for (int round = 0; round < 255 && c + 16 <= n; ++round, c += 16) {
            const v128_t kind = wasm_v128_load(tiles + c);
            r = wasm_i8x16_add(r, wasm_v128_load(walked + c));
            bu = wasm_i8x16_sub(bu, wasm_i8x16_eq(kind, wasm_i8x16_splat(bush)));
            ho = wasm_i8x16_sub(ho, wasm_i8x16_eq(kind, wasm_i8x16_splat(hole)));
            wa = wasm_i8x16_sub(wa, wasm_i8x16_eq(kind, wasm_i8x16_splat(wall)));
        }
        reach += lanes_sum(r), bushes += lanes_sum(bu), holes += lanes_sum(ho), wall_n += lanes_sum(wa);
    }
#endif
    for (; c < n; ++c) reach += walked[c], bushes += tiles[c] == bush, holes += tiles[c] == hole, wall_n += tiles[c] == wall;
    {
        int* const f = front.data();
        const int* const dA = fA.data();
        int i = 0;
#if defined(__wasm_simd128__)
        // Tiles past Si (or unreached, -1 unsigned) land in front[Si + 1], which choke never reads.
        const v128_t dump = wasm_i32x4_splat(Si + 1);
        for (; i + 16 <= n; i += 16)
            for (int g4 = 0; g4 < 16; g4 += 4) {
                const v128_t v = wasm_u32x4_min(wasm_v128_load(dA + i + g4), dump);
                ++f[wasm_i32x4_extract_lane(v, 0)], ++f[wasm_i32x4_extract_lane(v, 1)];
                ++f[wasm_i32x4_extract_lane(v, 2)], ++f[wasm_i32x4_extract_lane(v, 3)];
            }
#endif
        for (; i < n; ++i)
            if (static_cast<unsigned>(dA[i]) <= static_cast<unsigned>(Si)) ++f[dA[i]];
    }
    for (int c = 0; c < n; c += 8) {
        if (c + 8 <= n) {
            // Whether a byte of the word is an altar (exact as a test, not as to which).
            std::uint64_t word;
            std::memcpy(&word, tiles + c, 8);
            const std::uint64_t z = word ^ 0x0101010101010101ull * altar;
            if (!((z - 0x0101010101010101ull) & ~z & 0x8080808080808080ull)) continue;
        }
        for (int i = c; i < std::min(n, c + 8); ++i) {
            if (tiles[i] != altar) continue;
            ++altars;
            const int x = i % g.W, y = i / g.W, dA = g.reach_near(fA, x, y), dB = g.reach_near(fB, x, y);
            centre_sum += std::max(std::abs(x - cx), std::abs(y - cy)) / half;
            if (dA >= 0 && dB >= 0) {
                const double r = dA / std::max(1.0, static_cast<double>(dA + dB));
                if (!any_ratio || dA < best_d || (dA == best_d && r < best_ratio)) best_d = dA, best_ratio = r;
                any_ratio = true;
            }
        }
    }
    // The narrowest walking front in the middle half; the range is never empty, so never null.
    int choke = front[Si / 4];
    for (int d = Si / 4; d <= (3 * Si + 3) / 4; ++d) choke = std::min(choke, front[d]);
    const double clear_sum = clear ? clear(in, walked) : g.clearance_sum(walked);

    // sideGroups(g, open): our side's groups (a non-shared group's mirror is the enemy's), and shared ones.
    const auto groups = groups_of(g);
    const auto group_dist = [&](const std::vector<int>& d, const Group& q) {
        double best = inf;
        for (const int m : q.members) {
            const int v = g.reach_near(d, in.camps[m].x, in.camps[m].y);
            if (v >= 0) best = std::min(best, static_cast<double>(v));
        }
        return best;
    };
    double gems = 0, gold = 0, types[6] = {};
    double camp_near = inf;
    int ratios = 0, contested = 0, big_members = 0, shared_n = 0;
    for (const auto& q : groups) {
        if (q.members.size() >= 3) big_members += static_cast<int>(q.members.size());
        shared_n += q.shared;
        double share = 0.5;
        if (!q.shared) {
            const double dA = group_dist(openA, q), dB = group_dist(openB, q);
            if (!(dA < dB || (dA == dB && q.lo < q.mlo))) continue;
            share = 1;
            if (std::isfinite(dA)) camp_near = std::min(camp_near, dA);
            if (std::isfinite(dA + dB)) ++ratios, contested += dA / std::max(1.0, dA + dB) >= 0.38;
        }
        gems += q.gems * share, gold += q.gold * share;
        for (const int m : q.members) types[in.camps[m].type] += share;
    }
    const double gem_div = std::max(1.0, gems);

    // extras(): tiles a dash brings 6+ travel nearer team A's spawn.
    const bool wants_dash = want >> dash_gain & 1;
    std::vector<int> dashA;
    const int dash_short = g.travel(0, openA, 1, wants_dash ? &dashA : nullptr, work ? work->dash : nullptr);

    // metrics' detour: from team A's spawn corner to its mirror, less the spawn's width (even where
    // its height is the gap's axis).
    const int bx = in.sym == vertical ? in.sx : g.W - 1 - in.sx, by = in.sym == horizontal ? in.sy : g.H - 1 - in.sy;
    const int cheby = std::max(std::abs(bx - in.sx), std::abs(by - in.sy)) - in.sw + 1;
    const double camps_all = static_cast<double>(in.camps.size());
    std::array<double, count> out{
        area,
        r3(reach / area),
        S,
        r2(S / std::max(1, cheby)),
        r2(choke / std::sqrt(std::max(1.0, static_cast<double>(reach)))),
        r2(clear_sum / std::max(1, reach)),
        js_round(1000.0 * bushes / area) / 1000,
        js_round(1000.0 * holes / area) / 1000,
        static_cast<double>(altars),
        any_ratio ? r2(best_ratio) : nan,
        altars ? centre_sum / altars : nan,
        gems,
        gold,
        r2((types[4] * camp_gems[4] + types[5] * camp_gems[5]) / gem_div),
        r2(types[2] * camp_gems[2] / gem_div),
        ratios ? r2(static_cast<double>(contested) / ratios) : 0.0,
        camps_all > 0 ? big_members / camps_all : 0.0,
        reach ? static_cast<double>(dash_short) / reach : 0.0,
        std::isfinite(camp_near) ? camp_near : nan,
    };
    for (int k = dash_gain; k < count; ++k) out[static_cast<std::size_t>(k)] = nan;
    // metrics' camp type counts per side (shared halved), wall share and shared groups.
    out[monoliths] = types[4], out[golems] = types[5];
    out[camps_side] = types[0] + types[1] + types[2] + types[3] + types[4] + types[5];
    out[walls] = js_round(1000.0 * wall_n / area) / 1000, out[shared_groups] = shared_n;

    // shapeMetrics(): the quirks, over the open fields' playable tiles (either spawn reaches them on foot).
    if (wants_dash) {
        // Walk over dash travel between the spawns, capped at 10 (10 when the spawns are apart on foot).
        const double walked = spawn_dist(openA), dashed = spawn_dist(dashA);
        if (std::isfinite(dashed) && dashed > 0) out[dash_gain] = r2(std::min(10.0, (std::isfinite(walked) ? walked : 10 * dashed) / dashed));
    }
    std::vector<std::uint8_t> play;
    int play_n = 0;
    if (want & (1u << narrow | 1u << sight_gap)) {
        // walked is openA >= 0 already; byte loops, so they vectorise.
        play.resize(static_cast<std::size_t>(n + 16));
        std::uint8_t* const pl = play.data();
        nonneg_mask(openB.data(), pl, n);
        int i = 0;
#if defined(__wasm_simd128__)
        while (i + 16 <= n) {
            v128_t sum = wasm_i8x16_splat(0);
            for (int round = 0; round < 255 && i + 16 <= n; ++round, i += 16) {
                const v128_t v = wasm_v128_or(wasm_v128_load(pl + i), wasm_v128_load(walked + i));
                wasm_v128_store(pl + i, v);
                sum = wasm_i8x16_add(sum, v);
            }
            play_n += lanes_sum(sum);
        }
#endif
        for (; i < n; ++i) pl[i] |= walked[i], play_n += pl[i];
    }
    if (want >> narrow & 1) {
        // Walkable bytes with a blocked border, so a corridor test is four loads and byte logic (it vectorises).
        const int PW = g.W + 2;
        std::vector<std::uint8_t> wk_v(static_cast<std::size_t>(PW * (g.H + 2)), 0);
        std::uint8_t* const wk = wk_v.data();
        for (int y = 0; y < g.H; ++y) {
            const std::uint8_t* const k = tiles + y * g.W;
            std::uint8_t* const row = wk + (y + 1) * PW + 1;
            int x = 0;
#if defined(__wasm_simd128__)
            for (; x + 16 <= g.W; x += 16) {
                const v128_t kind = wasm_v128_load(k + x);
                const v128_t walk = wasm_v128_or(wasm_i8x16_eq(kind, wasm_i8x16_splat(ground)), wasm_i8x16_eq(kind, wasm_i8x16_splat(bush)));
                wasm_v128_store(row + x, wasm_v128_and(walk, wasm_i8x16_splat(1)));
            }
#endif
            for (; x < g.W; ++x) row[x] = static_cast<std::uint8_t>((k[x] == ground) | (k[x] == bush));
        }
        int corridor = 0;
        const std::uint8_t* const pl = play.data();
#if defined(__wasm_simd128__)
        const v128_t one8 = wasm_i8x16_splat(1);
#endif
        for (int y = 0; y < g.H; ++y) {
            const std::uint8_t* const c = wk + (y + 1) * PW + 1;
            const std::uint8_t* const p = pl + y * g.W;
            int x = 0;
#if defined(__wasm_simd128__)
            v128_t sum = wasm_i8x16_splat(0);
            for (; x + 16 <= g.W; x += 16) {
                const v128_t open = wasm_v128_and(wasm_v128_or(wasm_v128_load(c + x - 1), wasm_v128_load(c + x + 1)),
                                                  wasm_v128_or(wasm_v128_load(c + x - PW), wasm_v128_load(c + x + PW)));
                sum = wasm_i8x16_add(sum, wasm_v128_and(wasm_v128_load(p + x), wasm_v128_andnot(one8, open)));
            }
            corridor += lanes_sum(sum);
#endif
            for (; x < g.W; ++x)
                corridor += p[x] & (((c[x - 1] | c[x + 1]) & (c[x - PW] | c[x + PW])) ^ 1);
        }
        out[narrow] = r3(static_cast<double>(corridor) / std::max(1, play_n));
    }
    if (want >> spawn_ring & 1) {
        int ring = 0, ring_n = 0;
        for (int y = in.sy - 1; y <= in.sy + in.sh; ++y)
            for (int x = in.sx - 1; x <= in.sx + in.sw; ++x)
                if (g.inside(x, y) && (x < in.sx || y < in.sy || x >= in.sx + in.sw || y >= in.sy + in.sh)) ++ring_n, ring += !g.walk_tile(y * g.W + x);
        out[spawn_ring] = r2(static_cast<double>(ring) / std::max(1, ring_n));
    }
    if (want >> max_group & 1) {
        std::size_t most = 0;
        for (const auto& q : groups) most = std::max(most, q.members.size());
        out[max_group] = static_cast<double>(most);
    }
    if (want >> camp_altar & 1 && altars && !in.camps.empty()) {
        int nearest = std::numeric_limits<int>::max();
        for (int i = 0; i < n; ++i)
            if (in.t[i] == altar)
                for (const auto& c : in.camps) nearest = std::min(nearest, std::max(std::abs(i % g.W - c.x), std::abs(i / g.W - c.y)));
        out[camp_altar] = nearest;
    }
    if (want >> sight_gap & 1) {
        out[sight_gap] = sight_gap_of(g, play, play_n, work ? &work->sight_steps : nullptr);
        if (work) work->sight_sources = (play_n + std::max(1, play_n / 300) - 1) / std::max(1, play_n / 300);
    }
    const auto tf = [&](int k) {
        const double v = out[static_cast<std::size_t>(k)];
        if (!std::isfinite(v)) return nan;
        return base_tf[k] == bt_log ? std::log(std::max(v, 1.0)) : base_tf[k] == bt_log1p ? std::log1p(std::max(v, 0.0)) : v;
    };
    for (int k = first_derived; k < count; ++k) {
        const auto& d = derived[static_cast<std::size_t>(k)];
        out[static_cast<std::size_t>(k)] = d.kind == k_one_altar ? (altars == 1 ? 1.0 : 0.0) : tf(d.a) * tf(d.b);
    }
    return out;
}

std::uint32_t model_features() {
    // A derived feature wants its components; the raw extras are always measured.
    constexpr std::uint32_t bits = [] {
        std::uint32_t b = 0;
        for (const int s : slots)
            if (s < base_count) b |= 1u << s;
            else if (s >= first_derived && derived[static_cast<std::size_t>(s)].kind != k_one_altar)
                b |= 1u << derived[static_cast<std::size_t>(s)].a | 1u << derived[static_cast<std::size_t>(s)].b;
        return b;
    }();
    return bits;
}

std::uint64_t map_key(const Input& in) {
    const auto mix = [](std::uint64_t z) {
        z += 0x9E3779B97F4A7C15ull;
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
        return z ^ (z >> 31);
    };
    const auto tiles = [&](Tile k) { return static_cast<std::uint64_t>(std::count(in.t.begin(), in.t.end(), k)); };
    std::uint64_t h = mix(static_cast<std::uint64_t>(in.W));
    for (const std::uint64_t v : {static_cast<std::uint64_t>(in.H), tiles(wall), tiles(bush), tiles(hole), tiles(altar)}) h = mix(h ^ v);
    std::uint64_t sum = 0;
    for (const auto& c : in.camps)
        sum += mix(static_cast<std::uint64_t>(c.type) | static_cast<std::uint64_t>(c.x) << 8 | static_cast<std::uint64_t>(c.y) << 16);
    return mix(mix(h ^ sum) ^ in.camps.size());
}

std::vector<int> model_team(const std::array<double, count>& raw, int picks, const std::vector<int>& ours, const std::vector<int>& theirs) {
    namespace m = draft_model;
    const m::PickModel* model = nullptr;
    for (const auto& p : m::models)
        if (p.picks == picks) model = &p;
    if (!model) return {};
    constexpr int NC = m::champions;
    std::array<double, m::features> z{};
    for (int k = 0; k < m::features; ++k) {
        double v = raw[static_cast<std::size_t>(slots[static_cast<std::size_t>(k)])];
        if (std::isfinite(v)) v = m::transforms[k] == m::tf_log ? std::log(std::max(v, 1.0)) : m::transforms[k] == m::tf_log1p ? std::log1p(std::max(v, 0.0)) : v;
        v = (v - m::mean[k]) / m::sd[k];
        z[k] = std::isfinite(v) ? std::max(-4.0, std::min(4.0, v)) : 0.0;
    }
    // The chance each champion is in the opponent's team: 1 for a revealed pick, else the prior q spread over the
    // picks still hidden (q itself before any is revealed, so round 0 is model.mjs deployedTeam exactly).
    double opp[NC];
    if (theirs.empty()) std::copy(model->q, model->q + NC, opp);
    else {
        bool seen[NC] = {};
        for (const int d : theirs) seen[d] = true;
        double rest = 0;
        for (int d = 0; d < NC; ++d) rest += seen[d] ? 0 : model->q[d];
        const int hidden = std::max(0, picks - static_cast<int>(theirs.size()));
        for (int d = 0; d < NC; ++d) opp[d] = seen[d] ? 1.0 : rest > 0 ? std::min(1.0, model->q[d] * hidden / rest) : 0.0;
    }
    double syn[NC][NC];
    for (int i = 0; i < NC; ++i)
        for (int j = i + 1; j < NC; ++j) syn[i][j] = model->syn[m::pair(i, j)];
    bool must[NC] = {};
    for (const int c : ours) must[c] = true;
    int best[5], found = 0;
    // Every team's score without the counter terms, best first, for the re-ranks on later draft turns (100k fuel a
    // turn): scoring every team there ran turns out before the pick, which turns every later pick random. Made on
    // the first call (round 0, with the first turn's fuel); one map per draft instance.
    struct Scored {
        double s;
        std::uint16_t mask;
        std::int8_t ids[5];
    };
    static std::vector<Scored> teams;
    static double reach = 0; // no team's counter terms exceed this: picks x the largest sum of |ctr| over a row
    if (!ours.empty()) {
        if (teams.empty()) return {};
        double cv[NC];
        for (int c = 0; c < NC; ++c) {
            cv[c] = 0;
            for (int d = 0; d < NC; ++d)
                if (d != c) cv[c] += opp[d] * (c < d ? 1 : -1) * model->ctr[m::pair(c, d)];
        }
        std::uint16_t held = 0;
        for (const int c : ours) held |= static_cast<std::uint16_t>(1u << c);
        double best_s = -inf;
        for (const auto& team : teams) {
            if (team.s + reach < best_s) break;
            if ((team.mask & held) != held) continue;
            if ((team.mask & m::required) != m::required || (team.mask & m::banned)) continue; // the team lock, as on the first pick
            double s = team.s;
            for (int i = 0; i < picks; ++i) s += cv[team.ids[i]];
            if (s > best_s) {
                best_s = s, found = 1;
                for (int i = 0; i < picks; ++i) best[i] = team.ids[i];
            }
        }
    } else {
        // model.mjs champValues: b + w.z + the expected counter terms.
        double value[NC], base[NC];
        for (int c = 0; c < NC; ++c) {
            double s = model->b[c];
            for (int k = 0; k < m::features; ++k) s += model->w[c][k] * z[k];
            base[c] = s;
            for (int d = 0; d < NC; ++d)
                if (d != c) s += opp[d] * (c < d ? 1 : -1) * model->ctr[m::pair(c, d)];
            value[c] = s;
        }
        // rankTeams: the first best team in lexicographic order (the JS sort is stable), its terms added in
        // teamValue's order; the pick count a constant, so the scoring unrolls.
        const auto rank = [&]<int P>() {
            int cur[P];
            for (int i = 0; i < P; ++i) cur[i] = i;
            double best_s = -inf;
            for (bool more = true; more;) {
                double s = 0, without = 0;
                unsigned mask = 0;
                for (int i = 0; i < P; ++i) {
                    s += value[cur[i]], without += base[cur[i]];
                    mask |= 1u << cur[i];
                    for (int j = i + 1; j < P; ++j) s += syn[cur[i]][cur[j]], without += syn[cur[i]][cur[j]];
                }
                // The team lock (draft_model.h required, banned; model.mjs TEAM_LOCK): Cassi & Issac, two bodies
                // for one pick (Intercontinental Fish drafts them in 99% of its games), and no Stellar.
                if ((mask & m::required) == m::required && !(mask & m::banned) && s > best_s) best_s = s, std::copy(cur, cur + P, best);
                if constexpr (m::counters) {
                    Scored team{without, 0, {}};
                    for (int i = 0; i < P; ++i) team.mask |= static_cast<std::uint16_t>(1u << cur[i]), team.ids[i] = static_cast<std::int8_t>(cur[i]);
                    teams.push_back(team);
                }
                int i = P - 1;
                while (i >= 0 && cur[i] == NC - P + i) --i;
                if ((more = i >= 0)) {
                    ++cur[i];
                    for (int j = i + 1; j < P; ++j) cur[j] = cur[j - 1] + 1;
                }
            }
            found = 1;
        };
        teams.clear();
        if (picks == 3) rank.template operator()<3>();
        else if (picks == 4) rank.template operator()<4>();
        else rank.template operator()<5>();
        if constexpr (m::counters) {
            std::stable_sort(teams.begin(), teams.end(), [](const Scored& a, const Scored& b) { return a.s > b.s; });
            double row = 0;
            for (int c = 0; c < NC; ++c) {
                double r = 0;
                for (int d = 0; d < NC; ++d)
                    if (d != c) r += std::abs(model->ctr[m::pair(c, d)]);
                row = std::max(row, r);
            }
            reach = picks * row;
        }
    }
    if (!found) return {};
    // model.mjs pickOrder: our picks so far as made, then the least opponent-dependent first, so the most
    // counter-sensitive pick comes last (when most is known); with no counter terms, champion id order.
    std::vector<int> order(ours), rest;
    for (int i = 0; i < picks; ++i)
        if (!must[best[i]]) rest.push_back(best[i]);
    const auto sens = [&](int c) {
        double s = 0;
        for (int d = 0; d < NC; ++d)
            if (d != c) s += opp[d] * (1 - opp[d]) * model->ctr[m::pair(c, d)] * model->ctr[m::pair(c, d)];
        return s;
    };
    std::stable_sort(rest.begin(), rest.end(), [&](int a, int b) { return sens(a) < sens(b); });
    order.insert(order.end(), rest.begin(), rest.end());
    return order;
}

} // namespace aph::mapfeat
