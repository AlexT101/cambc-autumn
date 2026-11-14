#pragma once
// Bit-parallel Dijkstra over turns in a 15x15 window around us. A WASM loop costs ~25 fuel a tile
// test, so tiles are never visited one at a time: each cost bucket's frontier is a 256-bit mask
// (rows of 16 bits), one turn's moves are a king dilation by word shifts, and the cost of where a
// turn ends (enemy reach, camp members' reach) splits the dilated mask into later buckets.
//
// State classes: the dash cooldown c (0 ready .. 7) and, per tracked awake camp group, its empty
// camp phases k (0, 1; 2 = asleep: it costs nothing more). A turn ending within an awake group's
// reach pays its members' damage and resets k; one ending outside advances k (rules camps.sleep).
// Each turn is an optional dash (c == 0; then c = 7) and a walk or a wait. The window's outer ring
// exits to the tail field: its steps to the goals as a lower bound on turns (dash cycles included).
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdint>
#include <span>

namespace bitroute {

using cambc::bitboard;
using cambc::vec2;

inline constexpr int R = 7, side = 2 * R + 1;      // window radius and width
inline constexpr int unit = 4;                     // cost unit: half a turn (a turn costs 8)
inline constexpr int max_groups = 2;
inline constexpr int max_buckets = 64;             // costs tracked for the trace back, in units
inline constexpr int ring_slots = 16;              // pending buckets ahead (largest step increment < 16)
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
// King moves and staying, kept inside `valid` (column 15 is never valid, so row wraps drop out).
inline M dilate(const M& a, const M& valid) {
    const M h = a | shl(a, 1) | shr(a, 1);
    return (h | shl(h, 16) | shr(h, 16)) & valid;
}

// A camp member that hits whoever ends a turn within its reach, while its group is awake.
struct Camp {
    vec2 pos;
    int reach;
    int group; // tracked group 0..groups-1, or -1: always awake
};

struct Query {
    vec2 start;
    const bitboard* walls = nullptr;   // no walk or landing, but onto goals
    const bitboard* solid = nullptr;   // no dash path through (walls, visible units and camps, their spawn)
    const bitboard* goals = nullptr;
    const bitboard* danger = nullptr;  // enemy reach: +3 units
    const bitboard* edge = nullptr;    // beside it: +1
    const cambc::distance_field* tail = nullptr;
    std::span<const Camp> camps;
    int groups = 0;
    std::array<int, max_groups> damage{}; // units per member in reach, per tracked group
    int untracked = 2;                    // units for a tile within an untracked member's reach
    bool dasher = false;
    int cooldown = 0;
};

struct Plan {
    bool found = false;
    vec2 to{-1, -1};      // where the first turn ends
    bool dash = false;
    vec2 landing{-1, -1}; // the first turn's dash landing (the walk goes on to `to`)
    int cost = 0;         // units, tail included
    int buckets = 0;
};

namespace detail_ {

inline int turns_for(int steps, int c, bool dasher) {
    if (!dasher || steps <= c) return steps;
    const int r = steps - c, cycles = r / 10, rem = r % 10;
    return c + 8 * cycles + (rem == 0 ? 0 : rem <= 3 ? 1 : rem - 2);
}

// Bits x0..x0+14 of row y of a board, 0 off the map.
inline std::uint32_t row_bits(const std::uint64_t* b, int stride, int y, int x0, int W, int H) {
    if (y < 0 || y >= H) return 0;
    const int k0 = x0 >> 3; // floor
    const std::uint64_t* row = b + (y >> 3) * stride;
    const int shift = (y & 7) * 8, chunks = (W + 7) >> 3;
    std::uint32_t v = 0;
    for (int k = 0; k < 3; ++k) {
        const int kk = k0 + k;
        if (kk >= 0 && kk < chunks) v |= static_cast<std::uint32_t>((row[kk] >> shift) & 0xFF) << (8 * k);
    }
    std::uint32_t out = (v >> (x0 - 8 * k0)) & 0x7FFF;
    if (x0 < 0) out &= ~0u << (-x0);
    if (x0 + side > W) out &= (W - x0 <= 0) ? 0u : ((1u << (W - x0)) - 1);
    return out;
}

inline M window_of(const bitboard& b, vec2 c, int W, int H, int stride) {
    M m{};
    const std::uint64_t* words = b.ptr();
    for (int r = 0; r < side; ++r) {
        const std::uint32_t bits = row_bits(words, stride, c.y - R + r, c.x - R, W, H);
        const int at = r * 16;
        m.w[at >> 6] |= static_cast<std::uint64_t>(bits) << (at & 63);
    }
    return m;
}

inline M square_mask(int r0, int c0, int reach) {
    M m{};
    const int lo_c = std::max(0, c0 - reach), hi_c = std::min(side - 1, c0 + reach);
    if (lo_c > hi_c) return m;
    const std::uint64_t run = ((std::uint64_t{1} << (hi_c - lo_c + 1)) - 1) << lo_c;
    for (int r = std::max(0, r0 - reach); r <= std::min(side - 1, r0 + reach); ++r) {
        const int at = r * 16;
        m.w[at >> 6] |= run << (at & 63);
    }
    return m;
}

struct Piece {
    M m;
    int inc, k;
};

struct State {
    M visited[24];
    M pending[ring_slots][24];
    std::uint32_t dirty[ring_slots];
    M hist[max_buckets][24];
    std::uint32_t has[max_buckets];
};

inline State& state() {
    static State s;
    return s;
}

} // namespace detail_

inline Plan route(const Query& q) {
    using namespace detail_;
    Plan plan;
    const int W = cambc::map::width(), H = cambc::map::height();
    const auto stride = static_cast<int>(cambc::detail::layout().chunk_stride);
    const int chunks = static_cast<int>(cambc::detail::layout().chunked_width);
    const vec2 s0 = q.start;
    const auto tail_at = [&](int x, int y) -> int { return q.tail->ptr()[((y >> 3) * chunks + (x >> 3)) * 64 + (y & 7) * 8 + (x & 7)]; };

    // Window masks.
    M valid{};
    for (int r = 0; r < side; ++r) {
        const int y = s0.y - R + r;
        if (y < 0 || y >= H) continue;
        const int lo = std::max(0, R - s0.x), hi = std::min(side - 1, W - 1 - s0.x + R);
        if (lo > hi) continue;
        const std::uint64_t run = ((std::uint64_t{1} << (hi - lo + 1)) - 1) << lo;
        valid.w[(r * 16) >> 6] |= run << ((r * 16) & 63);
    }
    const M goal = window_of(*q.goals, s0, W, H, stride) & valid;
    M open = andnot(valid, window_of(*q.walls, s0, W, H, stride)) | goal;
    set(open, R, R);
    const M cross = q.dasher ? andnot(valid, window_of(*q.solid, s0, W, H, stride)) : M{};
    const M danger = q.danger ? window_of(*q.danger, s0, W, H, stride) & valid : M{};
    const M edge = q.edge ? andnot(window_of(*q.edge, s0, W, H, stride) & valid, danger) : M{};
    M ring = valid;
    {
        M inner{};
        for (int r = 1; r < side - 1; ++r) {
            const int at = r * 16;
            inner.w[at >> 6] |= ((std::uint64_t{1} << (side - 2)) - 1) << 1 << (at & 63);
        }
        ring = andnot(valid, inner);
    }
    // Camp levels: per tracked group, tiles within reach of at least 1, 2, 3 members; and the
    // untracked members' reach.
    const int G = std::min(q.groups, q.dasher ? 1 : max_groups);
    M lvl[max_groups][3]{};
    M fixed{};
    for (const auto& m : q.camps) {
        const M sq = square_mask(m.pos.y - s0.y + R, m.pos.x - s0.x + R, m.reach) & valid;
        if (m.group < 0 || m.group >= G) {
            fixed = fixed | sq;
            continue;
        }
        auto* l = lvl[m.group];
        l[2] = l[2] | (l[1] & sq);
        l[1] = l[1] | (l[0] & sq);
        l[0] = l[0] | sq;
    }
    // Static cost classes (exclusive): danger +3, edge +1, untracked camp +untracked.
    struct Static {
        M m;
        int inc;
    } statics[6];
    int n_static = 0;
    {
        const M parts[3] = {danger, edge, andnot(andnot(valid, danger), edge)};
        const int incs[3] = {3, 1, 0};
        for (int i = 0; i < 3; ++i) {
            const M in = parts[i] & fixed, out = andnot(parts[i], fixed);
            if (any(out)) statics[n_static++] = {out, incs[i]};
            if (any(in)) statics[n_static++] = {in, incs[i] + q.untracked};
        }
    }

    const int K = G == 0 ? 1 : G == 1 ? 3 : 9;    // sleep-progress codes
    const int C = q.dasher ? 8 : 1;                // cooldowns
    const int classes = C * K;
    auto& st = state();
    for (int i = 0; i < classes; ++i) st.visited[i] = M{};
    std::fill(st.dirty, st.dirty + ring_slots, 0u);
    const auto k_of = [&](int k, int j) { return j == 0 ? k % 3 : k / 3; };
    const auto add = [&](int b, int cls, const M& m) {
        auto& slot = st.pending[b % ring_slots][cls];
        const std::uint32_t bit = 1u << cls;
        if (st.dirty[b % ring_slots] & bit) slot = slot | m;
        else slot = m, st.dirty[b % ring_slots] |= bit;
    };
    // The classes a settled class dominates: higher cooldown, no more sleep progress per group.
    const auto dominates = [&](int a, int b) {
        const int ca = a / K, cb = b / K, ka = a % K, kb = b % K;
        if (ca > cb) return false;
        for (int j = 0; j < G; ++j)
            if (k_of(ka, j) < k_of(kb, j)) return false;
        return true;
    };
    // Splits a turn's end tiles by what ending there costs, from sleep progress k.
    Piece pieces[64];
    const auto split = [&](const M& ends, int k, int& n) {
        n = 0;
        for (int i = 0; i < n_static; ++i) {
            const M part = ends & statics[i].m;
            if (any(part)) pieces[n++] = {part, 2 + statics[i].inc, 0};
        }
        for (int j = 0; j < G; ++j) {
            const int kj = k_of(k, j), mult = j == 0 ? 1 : 3;
            const int m0 = n;
            for (int i = 0; i < m0; ++i) {
                Piece p = pieces[i];
                if (kj == 2) { // asleep: no cost, stays asleep
                    pieces[i].k += 2 * mult;
                    continue;
                }
                const M l1 = lvl[j][0], l2 = lvl[j][1], l3 = lvl[j][2];
                const M out = andnot(p.m, l1);
                const M at1 = andnot(p.m & l1, l2), at2 = andnot(p.m & l2, l3), at3 = p.m & l3;
                pieces[i] = {out, p.inc, p.k + (kj + 1) * mult};
                if (any(at1)) pieces[n++] = {at1, p.inc + q.damage[j], p.k};
                if (any(at2)) pieces[n++] = {at2, p.inc + 2 * q.damage[j], p.k};
                if (any(at3)) pieces[n++] = {at3, p.inc + 3 * q.damage[j], p.k};
            }
        }
    };

    const int c0 = q.dasher ? std::clamp(q.cooldown, 0, 7) : 0;
    const int cls0 = c0 * K; // every tracked group awake, k = 0
    if (get(goal, R, R)) {
        plan.found = true, plan.to = s0;
        return plan;
    }
    M start{};
    set(start, R, R);
    add(0, cls0, start);
    int best = 1 << 30, best_cls = -1, best_r = -1, best_c = -1, best_b = -1;
    int b = 0;
    for (; b < max_buckets && b < best; ++b) {
        st.has[b] = 0;
        const std::uint32_t due = st.dirty[b % ring_slots];
        st.dirty[b % ring_slots] = 0;
        if (!due) continue;
        for (std::uint32_t left = due; left; left &= left - 1) {
            const int cls = __builtin_ctz(left);
            const M F = andnot(st.pending[b % ring_slots][cls], st.visited[cls]);
            if (!any(F)) continue;
            st.hist[b][cls] = F;
            st.has[b] |= 1u << cls;
            for (int other = 0; other < classes; ++other)
                if (dominates(cls, other)) st.visited[other] = st.visited[other] | F;
            const int c = cls / K, k = cls % K;
            // Goals and the ring end the route.
            const M at_goal = F & goal;
            if (any(at_goal) && b < best) {
                for (int r = 0; r < side && best_cls < 0; ++r)
                    for (int cc = 0; cc < side; ++cc)
                        if (get(at_goal, r, cc)) { best = b, best_cls = cls, best_r = r, best_c = cc, best_b = b; break; }
                best_cls = cls;
            }
            const M exits = andnot(F & ring, goal);
            for (int r = 0; r < side; ++r) {
                const int at = r * 16;
                std::uint32_t bits = static_cast<std::uint32_t>(exits.w[at >> 6] >> (at & 63)) & 0x7FFF;
                for (; bits; bits &= bits - 1) {
                    const int cc = __builtin_ctz(bits);
                    const int d = tail_at(s0.x - R + cc, s0.y - R + r);
                    if (d == unreachable) continue;
                    const int total = b + 2 * turns_for(d, c, q.dasher);
                    if (total < best) best = total, best_cls = cls, best_r = r, best_c = cc, best_b = b;
                }
            }
            const M inner = andnot(andnot(F, ring), goal);
            if (!any(inner)) continue;
            // Walk (or wait): cooldown ticks.
            const M ends = dilate(inner, valid) & open;
            int n;
            split(ends, k, n);
            const int cw = c > 0 ? c - 1 : 0;
            for (int i = 0; i < n; ++i) add(b + pieces[i].inc, cw * K + pieces[i].k, pieces[i].m);
            if (q.dasher && c == 0) {
                const M near = dilate(inner, valid);
                const M landings = (near & open) | (dilate(near & cross, valid) & open);
                const M dash_ends = andnot(dilate(landings, valid) & open, ends);
                if (any(dash_ends)) {
                    split(dash_ends, k, n);
                    for (int i = 0; i < n; ++i) add(b + pieces[i].inc, 7 * K + pieces[i].k, pieces[i].m);
                }
            }
        }
    }
    plan.buckets = b;
    if (best_cls < 0) return plan;
    plan.found = true;
    plan.cost = best;

    // Trace back from the end to the start through the recorded frontiers.
    int r = best_r, cc = best_c, cls = best_cls, bb = best_b;
    int prev_r = r, prev_c = cc;
    bool prev_dash = false;
    while (!(r == R && cc == R && bb == 0)) {
        const int c = cls / K, k = cls % K;
        // Predecessor cooldowns: c == 7 only from a dash turn at 0; else c + 1, or 0 -> 0.
        int pcs[2], npc = 0;
        bool dash_turn = false;
        if (q.dasher && c == 7) pcs[npc++] = 0, dash_turn = true;
        else {
            if (c + 1 <= (q.dasher ? 7 : 0)) pcs[npc++] = c + 1;
            if (c == 0) pcs[npc++] = 0;
        }
        bool found = false;
        for (int ip = 0; ip < npc && !found; ++ip) {
            // Predecessor sleep codes.
            for (int pk = 0; pk < K && !found; ++pk) {
                int inc = 2;
                for (int i = 0; i < n_static; ++i)
                    if (get(statics[i].m, r, cc)) { inc += statics[i].inc; break; }
                bool ok = true;
                for (int j = 0; j < G && ok; ++j) {
                    const int was = k_of(pk, j), now = k_of(k, j);
                    const int level = get(lvl[j][2], r, cc) ? 3 : get(lvl[j][1], r, cc) ? 2 : get(lvl[j][0], r, cc) ? 1 : 0;
                    int expect;
                    if (was == 2) expect = 2;
                    else if (level > 0) expect = 0, inc += level * q.damage[j];
                    else expect = was + 1;
                    ok = expect == now;
                }
                if (!ok) continue;
                const int pb = bb - inc, pcls = pcs[ip] * K + pk;
                if (pb < 0 || !(st.has[pb] >> pcls & 1)) continue;
                const M& H0 = st.hist[pb][pcls];
                const int span = dash_turn ? 3 : 1;
                for (int dy = -span; dy <= span && !found; ++dy)
                    for (int dx = -span; dx <= span && !found; ++dx) {
                        const int pr = r + dy, pc = cc + dx;
                        if (pr < 0 || pc < 0 || pr >= side || pc >= side || !get(H0, pr, pc)) continue;
                        if (dash_turn) {
                            // Some landing within 2 of the origin (by a dash path) and within 1 of the end.
                            M o{};
                            set(o, pr, pc);
                            const M near = dilate(o, valid);
                            const M landings = (near & open) | (dilate(near & cross, valid) & open);
                            M e{};
                            set(e, r, cc);
                            if (!any(landings & dilate(e, valid))) continue;
                        }
                        prev_r = r, prev_c = cc, prev_dash = dash_turn;
                        r = pr, cc = pc, cls = pcls, bb = pb;
                        found = true;
                    }
            }
        }
        if (!found) {
            plan.found = false;
            return plan;
        }
    }
    plan.to = {s0.x - R + prev_c, s0.y - R + prev_r};
    if (prev_dash) {
        M o{};
        set(o, R, R);
        const M near = dilate(o, valid);
        const M landings = (near & open) | (dilate(near & cross, valid) & open);
        M e{};
        set(e, prev_r, prev_c);
        const M both = landings & dilate(e, valid);
        for (int rr = 0; rr < side && !plan.dash; ++rr)
            for (int c2 = 0; c2 < side; ++c2)
                if (get(both, rr, c2)) {
                    plan.dash = true, plan.landing = {s0.x - R + c2, s0.y - R + rr};
                    break;
                }
    }
    return plan;
}

} // namespace bitroute
