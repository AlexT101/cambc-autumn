#pragma once
// helios's chunked bitmask A* (Cambridge-Battlecode-Fall bots/helios/src/pathing.cpp, pathgrid::cba), copied
// verbatim for measurement, with its few dependencies stubbed.
#include <cambc.h>
#include <wasm_simd128.h>
#include <algorithm>
#include <cstdint>

namespace map_info {
inline int width = 0, height = 0, me_field_cap = 120, turn = 0;
inline cambc::bitboard static_block;
}  // namespace map_info
namespace config {
inline constexpr bool PROFILE = true;
}
namespace prof {
enum { MI_FIELD, PATH_CHUNK, PATH_LOCAL, PATH_RESOLVE, PATH_SEARCH, PATH_SETUP, PATH_VISITS, PS_FIELD, PS_MISC, PS_NSEEDS, PS_NWORDS, PS_SCAN, PS_SEEDS, COUNT };
inline const char* names[COUNT] = {"field", "chunk_build", "finish_local", "resolve", "run", "setup", "visits", "ps_field", "ps_misc", "nseeds", "nwords", "scan", "seeds"};
inline std::uint64_t total[COUNT];
inline void add(int id, std::uint64_t v) { total[id] += v; }
struct Scope {
    int id;
    std::uint64_t start;
    explicit Scope(int i) : id(i), start(cambc::fuel_remaining()) {}
    ~Scope() { total[id] += start - cambc::fuel_remaining(); }
};
}  // namespace prof
namespace fuel {
inline void mark(const char*) {}
}
namespace pathgrid {
inline constexpr int SOFT_COST = 5;
}
namespace pathgrid::cba {
using cambc::bitboard;
using cambc::vec2;
// When set, a seed (target) tile starts at this field's value (its cost beyond the window) instead of 0.
inline const cambc::distance_field* seed_offsets = nullptr;
// When scan_cx0 >= 0: targets lie only in chunks [scan_cx0, scan_cx1] x [scan_cy0, scan_cy1] (the window), and
// with chebyshev_h the heuristic is the chebyshev distance from `from`, written into those chunks only.
inline int scan_cx0 = -1, scan_cx1 = -1, scan_cy0 = -1, scan_cy1 = -1;
inline bool chebyshev_h = false;
inline int search(vec2 from, const bitboard& targets, const bitboard& hard, const bitboard& soft, bool* gave_up);
inline void settle_to(int level);
inline int dist_of(int x, int y);
}  // namespace pathgrid::cba
namespace pathgrid::cba {
namespace {

constexpr int MAXC = 13;          // 8x8 chunks per side (100 / 8 rounded up)
constexpr int CB = MAXC + 2;      // chunk grid with a closed border
constexpr int NCH = CB * CB;
constexpr int R = 8;              // level ring: relaxation offsets 0..6
constexpr int VISIT_CAP = 6000;
constexpr int kLocal = 2;
int hfx = 0, hfy = 0;
// The heuristic field is kept across turns (a landmark): from any origin P, h(q) = field_P(q) - field_P(from)
// is a valid, consistent lower bound (triangle inequality), and while P lies behind us on the way to the
// same destination it is (unweighted-)exact toward the targets. Recomputed from `from` when the destination
// changes, after LM_MAX_AGE turns, or when the field does not reach the targets.
constexpr int LM_MAX_AGE = 10;
// A fresh field from `from` every search, with camps (hard) as walls too: the exact unit distance from `from`, a
// tighter heuristic. (Reusing it across turns is only valid with static walls: camps die and respawn, and a stale
// camp wall overestimates -- measured: different decisions. Fresh + camp walls measured slightly cheaper overall.)
constexpr bool LM_REUSE = false;
constexpr bool LM_HARD_WALLS = true;
static_assert(!(LM_REUSE && LM_HARD_WALLS), "a reused field must not hold camp walls (they change)");
cambc::distance_field lm_field;
bitboard lm_scratch;
int lm_turn = -1000, lm_depth = 0, lm_sig = -1;
  // hard bound on chunk visits per query (worst-case fuel)
constexpr std::uint64_t COL0 = 0x0101010101010101ull, COL7 = 0x8080808080808080ull;
constexpr std::uint64_t NC0 = ~COL0, NC7 = ~COL7;

struct Chunk {
    std::uint64_t O, A;           // open (walkable, not hard); still unsettled = A
    std::uint64_t K[3];           // open tiles with h % 3 == j
    std::uint64_t Nk[3], Sk[3];   // normal / soft open tiles of class j
    std::uint64_t B[R];           // pending tiles per level (mod R)
    std::uint32_t stamp;
    int fbase;                    // this chunk's 64 values in the distance field
};
Chunk ch[NCH];
// What each chunk visit settled: (level, mask), linked per chunk. A settled tile's exact distance to the
// targets is its level minus h -- no per-tile writes.
constexpr int MAXV = VISIT_CAP + 64;
std::uint64_t vmask_[MAXV];
std::int16_t vlev_[MAXV];
std::int16_t vnext_[MAXV];
std::int16_t vhead_[NCH];
int nv = 0;
std::uint32_t qid = 0;
std::uint16_t wl[R][NCH];
int wn[R] = {};
std::uint8_t queued[R][NCH] = {};

int W = 0, H = 0, CW = 0, CH = 0, STRIDE = 0;
bool ready = false;
const std::uint64_t *st_c = nullptr, *hd_c = nullptr, *sf_c = nullptr;
const std::uint16_t* mf = nullptr;
int cap = 0, shift = 0;
int bx0 = 0, by0 = 0, bx1 = -1, by1 = -1;   // target bounding box

// Seeds (target tiles, g = 0) bucketed by their level h: a linked list per level.
constexpr int MAXSEED = 4096;
int seed_c[MAXSEED];
std::uint64_t seed_b[MAXSEED];
int seed_next[MAXSEED];
int seed_head[256];
std::uint32_t seed_stamp[256];
int nseeds = 0, seed_lo = 0, seed_hi = -1;

// resumable level loop
int cur_f = 0, idle = 0, visits = 0, fs_found = -1;
bool dead = false, gave = false;
int fc = 0;
std::uint64_t fbit = 0;

std::uint32_t vmark[100 * 100];   // resolve visited marks
std::uint32_t vrun = 0;

inline bool in_map(int x, int y) { return x >= 0 && y >= 0 && x < W && y < H; }
inline int cidx(int cx, int cy) { return (cy + 1) * CB + (cx + 1); }
inline int fld(int x, int y) { return mf[(((y >> 3) * CW + (x >> 3)) << 6) + ((y & 7) << 3) + (x & 7)]; }
inline int hval(int x, int y) {
    const int m = std::min(fld(x, y), cap);
    return std::min(m > shift ? m - shift : 0, 255);
}

void setup() {
    if (ready) return;
    W = map_info::width;
    H = map_info::height;
    const auto& md = cambc::detail::layout();
    STRIDE = static_cast<int>(md.chunk_stride);
    CW = static_cast<int>(md.chunked_width);
    CH = static_cast<int>(md.chunked_height);
    // `ch` is a zero-initialised global: the border stays closed forever (O = A = 0; ensure_idx never builds it)
    // and stamp 0 never equals a query id (qid >= 1). Re-filling it here cost ~36k fuel (1 per byte) on each
    // champion's first search -- a guaranteed timeout.
    ready = true;
}

[[gnu::noinline]] void build(int c, int cx, int cy) {
    prof::Scope pb(prof::PATH_CHUNK);
    Chunk& k = ch[c];
    k.stamp = qid;
    const int wi = cy * STRIDE + cx;
    std::uint64_t valid = ~0ull;
    const int cols = W - cx * 8, rows = H - cy * 8;
    if (cols < 8) valid &= COL0 * ((1u << cols) - 1);
    if (rows < 8) valid &= (1ull << (rows * 8)) - 1;
    const std::uint64_t O = ~(st_c[wi] | hd_c[wi]) & valid;
    const std::uint64_t S = O & sf_c[wi];
    k.O = O;
    k.A = O;
    for (auto& b : k.B) b = 0;
    k.fbase = (cy * CW + cx) << 6;
    vhead_[c] = -1;
    // h % 3 per tile, 8 lanes at a time: h <= 255, so h / 3 == (h * 171) >> 9 exactly
    const std::uint16_t* f = mf + k.fbase;
    const v128_t cap16 = wasm_i16x8_splat(static_cast<std::int16_t>(cap));
    const v128_t sh16 = wasm_i16x8_splat(static_cast<std::int16_t>(shift));
    const v128_t m171 = wasm_i16x8_splat(171), three = wasm_i16x8_splat(3);
    const v128_t z = wasm_i16x8_splat(0), one = wasm_i16x8_splat(1);
    std::uint64_t K0 = 0, K1 = 0;
    const v128_t adx = wasm_i16x8_abs(wasm_i16x8_sub(wasm_i16x8_add(wasm_i16x8_splat(static_cast<std::int16_t>(cx * 8)),
                                                                    wasm_i16x8_const(0, 1, 2, 3, 4, 5, 6, 7)),
                                                     wasm_i16x8_splat(static_cast<std::int16_t>(hfx))));
    for (int r = 0; r < 8; ++r) {
        const v128_t h = wasm_u16x8_min(wasm_u16x8_sub_sat(wasm_u16x8_min(wasm_v128_load(f + r * 8), cap16), sh16),
                                        wasm_i16x8_splat(255));
        const v128_t q = wasm_u16x8_shr(wasm_i16x8_mul(h, m171), 9);
        const v128_t rem = wasm_i16x8_sub(h, wasm_i16x8_mul(q, three));
        K0 |= static_cast<std::uint64_t>(wasm_i16x8_bitmask(wasm_i16x8_eq(rem, z))) << (r * 8);
        K1 |= static_cast<std::uint64_t>(wasm_i16x8_bitmask(wasm_i16x8_eq(rem, one))) << (r * 8);
    }
    K0 &= O;
    K1 &= O;
    const std::uint64_t K2 = O & ~K0 & ~K1;
    k.K[0] = K0;
    k.K[1] = K1;
    k.K[2] = K2;
    const std::uint64_t Nm = O & ~S;
    for (int j = 0; j < 3; ++j) {
        k.Nk[j] = Nm & k.K[j];
        k.Sk[j] = S & k.K[j];
    }
}
inline void ensure_idx(int c) {
    if (ch[c].stamp == qid) return;
    const int cx = c % CB - 1, cy = c / CB - 1;
    if (cx < 0 || cy < 0 || cx >= CW || cy >= CH) return;   // border: closed
    build(c, cx, cy);
}

inline std::uint64_t dil(std::uint64_t m) {
    const std::uint64_t t = m | ((m << 1) & NC0) | ((m >> 1) & NC7);
    return t | (t << 8) | (t >> 8);
}
inline std::uint64_t vspread(std::uint64_t e) { return e | (e << 8) | (e >> 8); }
inline std::uint64_t hspread(std::uint64_t e) { return e | ((e << 1) & NC0) | ((e >> 1) & NC7); }

[[gnu::always_inline]] inline void add(int c, std::uint64_t m, int lvl) {
    Chunk& k = ch[c];
    m &= k.A;
    if (!m) return;
    const int r = lvl & (R - 1);
    k.B[r] |= m;
    if (!queued[r][c]) {
        queued[r][c] = 1;
        wl[r][wn[r]++] = static_cast<std::uint16_t>(c);
    }
}

// Tiles of chunk nc reached from sources split by h class (e_j = spilled masks of class-j sources) at base
// level `base` = f + cost: a target of class j is at base - 1 from class j + 1, base from j, base + 1 from j - 1.
[[gnu::always_inline]] inline void targets_in(int nc, std::uint64_t e0, std::uint64_t e1, std::uint64_t e2, int base) {
    ensure_idx(nc);
    const Chunk& n = ch[nc];
    const std::uint64_t A = n.A;
    e0 &= A;
    e1 &= A;
    e2 &= A;
    if (!(e0 | e1 | e2)) return;
    const std::uint64_t K0 = n.K[0], K1 = n.K[1], K2 = n.K[2];
    add(nc, (e1 & K0) | (e2 & K1) | (e0 & K2), base - 1);
    add(nc, (e0 & K0) | (e1 & K1) | (e2 & K2), base);
    add(nc, (e2 & K0) | (e0 & K1) | (e1 & K2), base + 1);
}

// Spill class-split sources s0..s2 of chunk c into its 8 neighbours.
void spill(int c, std::uint64_t s0, std::uint64_t s1, std::uint64_t s2, int base) {
    const std::uint64_t all = s0 | s1 | s2;
    if (all & COL7) targets_in(c + 1, vspread((s0 & COL7) >> 7), vspread((s1 & COL7) >> 7), vspread((s2 & COL7) >> 7), base);
    if (all & COL0) targets_in(c - 1, vspread((s0 & COL0) << 7), vspread((s1 & COL0) << 7), vspread((s2 & COL0) << 7), base);
    if (all & 0xFFull) targets_in(c - CB, hspread(s0 << 56), hspread(s1 << 56), hspread(s2 << 56), base);
    if (all >> 56) targets_in(c + CB, hspread(s0 >> 56), hspread(s1 >> 56), hspread(s2 >> 56), base);
    if (all & (1ull << 7))
        targets_in(c - CB + 1, ((s0 >> 7) & 1) << 56, ((s1 >> 7) & 1) << 56, ((s2 >> 7) & 1) << 56, base);
    if (all & 1ull) targets_in(c - CB - 1, (s0 & 1) << 63, (s1 & 1) << 63, (s2 & 1) << 63, base);
    if (all >> 63) targets_in(c + CB + 1, s0 >> 63, s1 >> 63, s2 >> 63, base);
    if (all & (1ull << 56))
        targets_in(c + CB - 1, ((s0 >> 56) & 1) << 7, ((s1 >> 56) & 1) << 7, ((s2 >> 56) & 1) << 7, base);
}

// Settle chunk c's pending tiles at level f; true when `from` settles.
bool visit(int c, int f) {
    Chunk& k = ch[c];
    const int r = f & (R - 1);
    std::uint64_t L = k.B[r] & k.A;
    k.B[r] = 0;
    if (!L) return false;
    if constexpr (config::PROFILE) prof::add(prof::PATH_VISITS, 1);
    // 0-cost closure inside the chunk: a normal tile of class j -> a neighbour of class j - 1
    const std::uint64_t A0 = k.A;
    const std::uint64_t N0 = k.Nk[0], N1 = k.Nk[1], N2 = k.Nk[2];
    const std::uint64_t K0 = k.K[0], K1 = k.K[1], K2 = k.K[2];
    // Frontier rounds: only the tiles added last round are dilated (a neighbour of an older tile was added when that
    // tile was the frontier), and d_j = dil(L & N_j) accumulates (dil distributes over |): the same L and d_j as
    // re-dilating all of L each round. A class absent from the frontier skips its dilation (the frontier is mostly
    // one class: a 0-cost step turns class j into j - 1).
    std::uint64_t d0 = 0, d1 = 0, d2 = 0;   // == dil(L & N_j) of the final L: reused by the relaxations
    std::uint64_t fr = L;
    while (true) {
        const std::uint64_t f0 = fr & N0, f1 = fr & N1, f2 = fr & N2;
        const std::uint64_t e0 = f0 ? dil(f0) : 0, e1 = f1 ? dil(f1) : 0, e2 = f2 ? dil(f2) : 0;
        d0 |= e0;
        d1 |= e1;
        d2 |= e2;
        const std::uint64_t a = ((e0 & K2) | (e1 & K0) | (e2 & K1)) & A0 & ~L;
        if (!a) break;
        L |= a;
        fr = a;
    }
    k.A = A0 & ~L;
    if (nv < MAXV) {   // log the visit: these tiles settled at level f
        vmask_[nv] = L;
        vlev_[nv] = static_cast<std::int16_t>(f);
        vnext_[nv] = vhead_[c];
        vhead_[c] = static_cast<std::int16_t>(nv);
        ++nv;
    }
    const bool hit = c == fc && (L & fbit);
    // relaxations from normal sources (cost 1): in-chunk class j at f + 1, class j + 1 at f + 2
    const std::uint64_t n0 = L & N0, n1 = L & N1, n2 = L & N2;
    if (n0 | n1 | n2) {
        add(c, (d0 & K0) | (d1 & K1) | (d2 & K2), f + 1);
        add(c, (d2 & K0) | (d0 & K1) | (d1 & K2), f + 2);
        spill(c, n0, n1, n2, f + 1);
    }
    const std::uint64_t s0 = L & k.Sk[0], s1 = L & k.Sk[1], s2 = L & k.Sk[2];
    if (s0 | s1 | s2) {   // soft sources (cost SOFT_COST)
        const int base = f + SOFT_COST;
        const std::uint64_t e0 = dil(s0), e1 = dil(s1), e2 = dil(s2);
        add(c, (e1 & K0) | (e2 & K1) | (e0 & K2), base - 1);
        add(c, (e0 & K0) | (e1 & K1) | (e2 & K2), base);
        add(c, (e2 & K0) | (e0 & K1) | (e1 & K2), base + 1);
        spill(c, s0, s1, s2, base);
    }
    return hit;
}

// Process levels until `from` settles (stop_at_from) or past `limit` (>= 0). Resumable.
void run(int limit, bool stop_at_from) {
    prof::Scope ps(prof::PATH_SEARCH);
    while (!dead) {
        if (stop_at_from && fs_found >= 0) return;
        if (limit >= 0 && cur_f > limit) return;
        if (cur_f <= seed_hi && seed_stamp[cur_f] == qid)
            for (int i = seed_head[cur_f]; i >= 0; i = seed_next[i]) {
                ensure_idx(seed_c[i]);   // target chunks are built when their seeds' level comes up
                add(seed_c[i], seed_b[i], cur_f);
            }
        const int r = cur_f & (R - 1);
        if (wn[r] == 0) {
            if (cur_f >= seed_hi && ++idle > R) {   // nothing pending anywhere: unreachable
                dead = true;
                return;
            }
            ++cur_f;
            continue;
        }
        idle = 0;
        while (wn[r] > 0) {
            const int c = wl[r][--wn[r]];
            queued[r][c] = 0;
            if (visit(c, cur_f) && fs_found < 0) {
                fs_found = cur_f;
                if (stop_at_from) return;   // mid-level: settle_to resumes this level
            }
            if (++visits > VISIT_CAP) {
                dead = gave = true;
                return;
            }
        }
        ++cur_f;
    }
}

// `from` settled mid-level: finish this level only in the block of chunks around it, so the tied
// neighbours of `from` settle too (bit-parallel) and need no tight-path certification. Spills further out
// stay queued (settle_to picks them up).
void finish_local() {
    prof::Scope pl(prof::PATH_LOCAL);
    const int r = cur_f & (R - 1);
    for (int guard = 0; guard < 64; ++guard) {
        int pick = -1;
        for (int i = 0; i < wn[r]; ++i) {
            const int c = wl[r][i];
            const int dx = c % CB - fc % CB, dy = c / CB - fc / CB;
            if (dx >= -kLocal && dx <= kLocal && dy >= -kLocal && dy <= kLocal) {
                pick = i;
                break;
            }
        }
        if (pick < 0) return;
        const int c = wl[r][pick];
        wl[r][pick] = wl[r][--wn[r]];
        queued[r][c] = 0;
        visit(c, cur_f);
        ++visits;
    }
}

}  // namespace

inline int search(vec2 from, const bitboard& targets, const bitboard& hard, const bitboard& soft, bool* gave_up) {
    std::uint64_t f_setup0 = 0;
    if constexpr (config::PROFILE) f_setup0 = cambc::fuel_remaining();
    setup();
    if (gave_up) *gave_up = false;
    dead = gave = false;
    fs_found = -1;
    if (!in_map(from.x, from.y)) return -1;
    ++qid;
    for (int r = 0; r < R; ++r)   // a search that stopped early left chunks queued
        while (wn[r] > 0) queued[r][wl[r][--wn[r]]] = 0;
    st_c = map_info::static_block.ptr();
    hd_c = hard.ptr();
    sf_c = soft.ptr();
    std::uint64_t fcp = 0;   // PROFILE checkpoints of the setup's parts
    auto cp = [&](int id) {
        if constexpr (config::PROFILE) {
            const std::uint64_t now = cambc::fuel_remaining();
            if (fcp) prof::add(id, fcp - now);
            fcp = now;
        }
    };
    if constexpr (config::PROFILE) prof::add(prof::PS_MISC, f_setup0 - cambc::fuel_remaining());
    cp(prof::PS_MISC);
    // Targets straight from the board's words (no host call, no allocation): pass 1 = the box of the open
    // targets. Two words per SIMD step (target sets are a few chunks); a set word is bounded with bit tricks,
    // and the span (farthest target, chebyshev) is the box's farthest extent from `from`.
    const std::uint64_t* tw = targets.ptr();
    bx0 = W; by0 = H; bx1 = -1; by1 = -1;
    {
        const std::uint64_t lastcol = (W & 7) ? COL0 * ((1u << (W & 7)) - 1) : ~0ull;
        const std::uint64_t lastrow = (H & 7) ? (1ull << ((H & 7) * 8)) - 1 : ~0ull;
        auto word_box = [&](int wi, int cx, int cy) {
            std::uint64_t w = tw[wi] & ~(st_c[wi] | hd_c[wi]);
            if (cx == CW - 1) w &= lastcol;   // in-map bits only
            if (cy == CH - 1) w &= lastrow;
            if (!w) return;
            std::uint64_t c = w | (w >> 32);
            c |= c >> 16;
            c |= c >> 8;
            const unsigned cols = static_cast<unsigned>(c) & 0xFFu;
            bx0 = std::min(bx0, cx * 8 + __builtin_ctz(cols));
            bx1 = std::max(bx1, cx * 8 + 31 - __builtin_clz(cols));
            by0 = std::min(by0, cy * 8 + (__builtin_ctzll(w) >> 3));
            by1 = std::max(by1, cy * 8 + ((63 - __builtin_clzll(w)) >> 3));
        };
        // Only the target board is read while scanning (4 words per test); open-ness is applied to set words.
        if (scan_cx0 >= 0) {
            for (int cy = scan_cy0; cy <= scan_cy1; ++cy)
                for (int cx = scan_cx0; cx <= scan_cx1; ++cx)
                    if (tw[cy * STRIDE + cx]) word_box(cy * STRIDE + cx, cx, cy);
        }
        for (int cy = 0; cy < CH && scan_cx0 < 0; ++cy) {
            const std::uint64_t* p = tw + cy * STRIDE;
            int cx = 0;
            for (; cx + 3 < CW; cx += 4, p += 4) {
                if (!wasm_v128_any_true(wasm_v128_or(wasm_v128_load(p), wasm_v128_load(p + 2)))) continue;
                for (int i = 0; i < 4; ++i)
                    if (p[i]) word_box(cy * STRIDE + cx + i, cx + i, cy);
            }
            for (; cx < CW; ++cx, ++p)
                if (*p) word_box(cy * STRIDE + cx, cx, cy);
        }
    }
    if (bx1 < 0) return -1;
    fuel::mark("scan");
    const int span = std::max(std::max(from.x - bx0, bx1 - from.x), std::max(from.y - by0, by1 - from.y));
    cp(prof::PS_SCAN);
    // heuristic: the native field from our turn-start tile, as deep as the farthest target + slack, shifted
    // to `from` (pathgrid does the same); a maze can put every target beyond that depth: then full depth
    hfx = from.x;
    hfy = from.y;
    const int sig = ((bx0 * 128 + by0) * 128 + bx1) * 128 + by1;   // the destination
    auto any_within = [&](int depth) {   // some target inside the field's depth?
        for (int cy = by0 >> 3; cy <= by1 >> 3; ++cy)
            for (int cx = bx0 >> 3; cx <= bx1 >> 3; ++cx) {
                const int wi = cy * STRIDE + cx;
                for (std::uint64_t w = tw[wi] & ~(st_c[wi] | hd_c[wi]); w; w &= w - 1) {
                    const int b = __builtin_ctzll(w), x = cx * 8 + (b & 7), y = cy * 8 + (b >> 3);
                    if (x < W && y < H && fld(x, y) < depth) return true;
                }
            }
        return false;
    };
    bool reuse = LM_REUSE && sig == lm_sig && map_info::turn - lm_turn <= LM_MAX_AGE;
    if (reuse) {
        mf = lm_field.ptr();
        reuse = fld(from.x, from.y) < lm_depth && any_within(lm_depth);   // we and a target inside it
    }
    if (!reuse && chebyshev_h && scan_cx0 >= 0) {
        prof::Scope pf(prof::MI_FIELD);
        std::uint16_t* out = lm_field.ptr();
        const v128_t lane = wasm_i16x8_const(0, 1, 2, 3, 4, 5, 6, 7);
        for (int cy = scan_cy0; cy <= scan_cy1; ++cy)
            for (int cx = scan_cx0; cx <= scan_cx1; ++cx) {
                std::uint16_t* f = out + ((cy * CW + cx) << 6);
                const v128_t dx = wasm_i16x8_abs(wasm_i16x8_sub(wasm_i16x8_add(wasm_i16x8_splat(static_cast<std::int16_t>(cx * 8)), lane),
                                                                wasm_i16x8_splat(static_cast<std::int16_t>(from.x))));
                for (int r = 0; r < 8; ++r) {
                    const int dy = std::abs(cy * 8 + r - from.y);
                    wasm_v128_store(f + r * 8, wasm_i16x8_max(dx, wasm_i16x8_splat(static_cast<std::int16_t>(dy))));
                }
            }
        mf = lm_field.ptr();
        lm_depth = 255;
        lm_turn = map_info::turn;
        lm_sig = -1;
    } else if (!reuse) {
        prof::Scope pf(prof::MI_FIELD);
        int depth = std::min(map_info::me_field_cap, std::max(32, span + 24));
        static bitboard lm_walls, lm_root;
        if constexpr (LM_HARD_WALLS) {
            cambc::detail::check(cambc::detail::sdk_Bitboard_Union(map_info::static_block.ptr(), hard.ptr(), lm_walls.ptr()));
        } else {
            cambc::detail::check(cambc::detail::sdk_Bitboard_Union(map_info::static_block.ptr(), map_info::static_block.ptr(), lm_walls.ptr()));
        }
        lm_root.clear();
        lm_root.ptr()[(from.y >> 3) * STRIDE + (from.x >> 3)] |= 1ull << (((from.y & 7) << 3) | (from.x & 7));
        lm_field.compute(lm_walls, lm_root, lm_scratch, static_cast<std::uint16_t>(depth));
        mf = lm_field.ptr();
        // A maze can put every target beyond that depth: then full depth.
        if (!any_within(depth)) {
            depth = map_info::me_field_cap;
            lm_field.compute(lm_walls, lm_root, lm_scratch, static_cast<std::uint16_t>(depth));
        }
        lm_depth = depth;
        lm_turn = map_info::turn;
        lm_sig = sig;
    }
    cap = lm_depth;
    shift = std::min<int>(fld(from.x, from.y), cap);
    fuel::mark("field");
    cp(prof::PS_FIELD);
    // pass 2: seeds, bucketed by level h(t). (Their chunks are built only when the search reaches their level:
    // the far side of a target ring often never is.)
    {   // (globals into locals: the seed arrays' stores would otherwise reload them every iteration)
        int ns = 0, lo = 256, hi = -1;
        const std::uint32_t q = qid;
        const std::uint64_t *stc = st_c, *hdc = hd_c;
        const std::uint16_t* mfp = mf;
        const int cw = CW, chh = CH, stride = STRIDE, cp = cap, sh = shift;
        const std::uint64_t lastcol = (W & 7) ? COL0 * ((1u << (W & 7)) - 1) : ~0ull;
        const std::uint64_t lastrow = (H & 7) ? (1ull << ((H & 7) * 8)) - 1 : ~0ull;
        for (int cy = by0 >> 3; cy <= by1 >> 3; ++cy)
            for (int cx = bx0 >> 3; cx <= bx1 >> 3; ++cx) {
                const int wi = cy * stride + cx;
                std::uint64_t w = tw[wi] & ~(stc[wi] | hdc[wi]);
                if (cx == cw - 1) w &= lastcol;   // == the chunk's O: open and in the map
                if (cy == chh - 1) w &= lastrow;
                if (!w) continue;
                const int c = cidx(cx, cy);
                const int fb = (cy * cw + cx) << 6;
                for (; w && ns < MAXSEED; w &= w - 1) {
                    const int b = __builtin_ctzll(w);
                    const int m = std::min<int>(mfp[fb + b], cp);   // == hval(x, y): the field slot of bit b
                    const int g0 = seed_offsets ? std::min<int>(seed_offsets->ptr()[fb + b], 200) : 0;
                    const int f = std::min((m > sh ? m - sh : 0) + g0, 255);
                    seed_c[ns] = c;
                    seed_b[ns] = 1ull << b;
                    if (seed_stamp[f] != q) {
                        seed_stamp[f] = q;
                        seed_head[f] = -1;
                    }
                    seed_next[ns] = seed_head[f];
                    seed_head[f] = ns;
                    ++ns;
                    lo = std::min(lo, f);
                    hi = std::max(hi, f);
                }
            }
        nseeds = ns;
        seed_lo = lo;
        seed_hi = hi;
    }
    cp(prof::PS_SEEDS);
    if constexpr (config::PROFILE) {
        prof::add(prof::PS_NSEEDS, static_cast<std::uint64_t>(nseeds));
        int nw = 0;
        for (int cy = by0 >> 3; cy <= by1 >> 3; ++cy)
            for (int cx = bx0 >> 3; cx <= bx1 >> 3; ++cx) nw += (tw[cy * STRIDE + cx] & ~(st_c[cy * STRIDE + cx] | hd_c[cy * STRIDE + cx])) != 0;
        prof::add(prof::PS_NWORDS, static_cast<std::uint64_t>(nw));
        fcp = cambc::fuel_remaining();
    }
    if (nseeds == 0) return -1;
    fc = cidx(from.x >> 3, from.y >> 3);
    ensure_idx(fc);
    fbit = 1ull << (((from.y & 7) << 3) | (from.x & 7));
    cur_f = seed_lo;
    idle = 0;
    visits = 0;
    nv = 0;
    cp(prof::PS_MISC);
    if constexpr (config::PROFILE) prof::add(prof::PATH_SETUP, f_setup0 - cambc::fuel_remaining());
    fuel::mark("seeds");
    run(-1, true);
    fuel::mark("ran");
    if (gave_up) *gave_up = gave;
    if (fs_found >= 0) finish_local();
    return fs_found;
}

inline void settle_to(int level) {
    if (!dead) run(level, false);
}

inline int dist_of(int x, int y) {
    if (!in_map(x, y)) return -1;
    const int c = cidx(x >> 3, y >> 3);
    const Chunk& k = ch[c];
    const int b = ((y & 7) << 3) | (x & 7);
    if (k.stamp != qid || !((k.O & ~k.A) >> b & 1)) return -1;
    for (int i = vhead_[c]; i >= 0; i = vnext_[i])
        if ((vmask_[i] >> b) & 1) return vlev_[i] - hval(x, y);
    return -1;
}

inline int cost_of(int x, int y) {
    if (!in_map(x, y)) return 0;
    const int wi = (y >> 3) * STRIDE + (x >> 3), b = ((y & 7) << 3) | (x & 7);
    if (((st_c[wi] | hd_c[wi]) >> b) & 1) return 0;
    return ((sf_c[wi] >> b) & 1) ? SOFT_COST : 1;
}

inline int h_of(int x, int y) { return in_map(x, y) ? hval(x, y) : 0; }

inline int box_dist(int x, int y) {
    const int dx = x < bx0 ? bx0 - x : (x > bx1 ? x - bx1 : 0);
    const int dy = y < by0 ? by0 - y : (y > by1 ? y - by1 : 0);
    return dx > dy ? dx : dy;
}

inline int resolve(int x, int y, int fs, int& budget) {
    prof::Scope pr(prof::PATH_RESOLVE);
    {   // already queued at `from`'s level: its level is fs (it is unsettled, so not below), i.e. tied
        const int c = cidx(x >> 3, y >> 3);
        if (ch[c].stamp == qid && ((ch[c].B[fs & (R - 1)] & ch[c].A) >> (((y & 7) << 3) | (x & 7)) & 1)) return 1;
    }
    // Level fs complete (no chunk queued at it anywhere: pending bits of the current level always have their
    // chunk queued, and the ring holds no other level there): every tile of level <= fs is settled, so this
    // unsettled one has level >= fs + 1, D >= fs - h >= fs - 1 + 1 -- it cannot tie. (Measured: ~95% of calls.)
    if (wn[fs & (R - 1)] == 0) return 0;
    ++vrun;
    static int stk[8 * 96 + 16];
    int sp = 0;
    vmark[y * W + x] = vrun;
    stk[sp++] = y * W + x;
    const int cxb = (bx0 + bx1) / 2, cyb = (by0 + by1) / 2;   // toward the target box: expanded first
    const std::uint64_t *st = st_c, *hd = hd_c, *sf = sf_c;
    static constexpr int ox[9] = {-1, 0, 1, -1, 1, -1, 0, 1, 0}, oy[9] = {-1, -1, -1, 0, 0, 1, 1, 1, 0};
    while (sp > 0) {
        const int i = stk[--sp];
        if (--budget < 0) return -1;
        const int px = i % W, py = i / W;
        const int hx = hval(px, py);
        const int tx = px + ((cxb > px) - (cxb < px)), ty = py + ((cyb > py) - (cyb < py));
        for (int k = 0; k <= 8; ++k) {
            int nx, ny;
            if (k < 8) {
                nx = px + ox[k];
                ny = py + oy[k];
                if (nx == tx && ny == ty) continue;
            } else {
                if (tx == px && ty == py) break;
                nx = tx;
                ny = ty;
            }
            if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
            const int wi = (ny >> 3) * STRIDE + (nx >> 3), b = ((ny & 7) << 3) | (nx & 7);
            if (((st[wi] | hd[wi]) >> b) & 1) continue;
            const int cy = ((sf[wi] >> b) & 1) ? SOFT_COST : 1;
            const int c = cidx(nx >> 3, ny >> 3);
            const Chunk& kk = ch[c];
            const int hy = hval(nx, ny);
            if (kk.stamp == qid && (((kk.O & ~kk.A) >> b) & 1)) {   // settled: exact level -> witness test
                int lv = -1;
                for (int v = vhead_[c]; v >= 0; v = vnext_[v])
                    if ((vmask_[v] >> b) & 1) { lv = vlev_[v]; break; }
                if (lv >= 0 && hx + cy + (lv - hy) <= fs) return 1;   // a shortest path through it
                continue;
            }
            if (hy - hx != cy || vmark[ny * W + nx] == vrun) continue;   // tight: h rises by the step's cost
            const int ddx = nx < bx0 ? bx0 - nx : (nx > bx1 ? nx - bx1 : 0), ddy = ny < by0 ? by0 - ny : (ny > by1 ? ny - by1 : 0);
            if (hy + (ddx > ddy ? ddx : ddy) > fs) continue;
            vmark[ny * W + nx] = vrun;
            if (sp < 8 * 96 + 8) stk[sp++] = ny * W + nx;
        }
    }
    return 0;
}

inline std::uint32_t query_id() { return qid; }

inline void neighbours(vec2 from, int cost_out[8], int dist_out[8], int h_out[8]) {
    // Globals into locals first: the int* outputs may alias them, which made every store reload them all.
    const int w = W, hg = H, stride = STRIDE, cw = CW, cp = cap, sh = shift;
    const std::uint64_t *st = st_c, *hd = hd_c, *sf = sf_c;
    const std::uint16_t* f = mf;
    const std::uint32_t q = qid;
    static constexpr int ox[8] = {-1, 0, 1, -1, 1, -1, 0, 1}, oy[8] = {-1, -1, -1, 0, 0, 1, 1, 1};
    int cost[8], dist[8], hh[8];
    for (int k = 0; k < 8; ++k) {
        const int x = from.x + ox[k], y = from.y + oy[k];
        cost[k] = 0;
        dist[k] = -1;
        hh[k] = 0;
        if (static_cast<unsigned>(x) >= static_cast<unsigned>(w) || static_cast<unsigned>(y) >= static_cast<unsigned>(hg)) continue;
        const int cx = x >> 3, cy = y >> 3, b = ((y & 7) << 3) | (x & 7);
        const int wi = cy * stride + cx;
        if (((st[wi] | hd[wi]) >> b) & 1) continue;
        cost[k] = ((sf[wi] >> b) & 1) ? SOFT_COST : 1;
        const int m = std::min<int>(f[((cy * cw + cx) << 6) + b], cp);
        const int hv = std::min(m > sh ? m - sh : 0, 255);
        hh[k] = hv;
        const int c = (cy + 1) * CB + (cx + 1);
        const Chunk& kk = ch[c];
        if (kk.stamp != q || !(((kk.O & ~kk.A) >> b) & 1)) continue;
        for (int v = vhead_[c]; v >= 0; v = vnext_[v])
            if ((vmask_[v] >> b) & 1) {
                dist[k] = vlev_[v] - hv;
                break;
            }
    }
    for (int k = 0; k < 8; ++k) {
        cost_out[k] = cost[k];
        dist_out[k] = dist[k];
        h_out[k] = hh[k];
    }
}

inline void target_box(int& x0, int& y0, int& x1, int& y1) {
    x0 = bx0;
    y0 = by0;
    x1 = bx1;
    y1 = by1;
}

}  // namespace pathgrid::cba
