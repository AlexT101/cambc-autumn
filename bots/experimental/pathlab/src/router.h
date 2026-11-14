#pragma once
// A* over turns: each turn an optional dash (when its cooldown allows) and then a walk or a wait.
// A turn costs `turn_cost`, plus `danger_cost` if it ends in the danger area, plus the damage of
// every awake camp member whose reach it ends in. A tracked camp group sleeps after 2 turns
// ended out of all its awake members' reach (rules camps.sleep), so the state carries each
// tracked group's empty camp phases (0, 1, 2 = asleep) and the dash cooldown. Per tile, only
// states no other state there beats on cost, cooldown and every group's sleep progress are kept.
// Beyond `horizon` turns the rest is the tail field's steps, turned into a lower bound on turns.
#include <cambc.h>
#include <algorithm>
#include <cstdint>
#include <span>
#include <vector>

namespace router {

using cambc::bitboard;
using cambc::vec2;

inline constexpr std::uint16_t unreachable = cambc::distance_field::unreachable;
inline constexpr int max_groups = 3;

// An awake camp member: it hits us (damage) at the next camp phase if our turn ends within reach.
struct Camp {
    vec2 pos;
    int reach;
    int damage;
    int group; // 0..groups-1: a tracked group that can fall asleep; -1: always awake
};

struct Query {
    vec2 start;
    const bitboard* walls = nullptr;  // no walk or landing, but onto goals
    const bitboard* solid = nullptr;  // tiles a dash path cannot cross (walls, visible units, camps, their spawn)
    const bitboard* goals = nullptr;
    const bitboard* danger = nullptr; // ending a turn here costs danger_cost
    const cambc::distance_field* tail = nullptr; // steps to the goals; for dashers over dash-crossable walls
    std::span<const Camp> camps;
    int groups = 0;
    bool dasher = false;
    int cooldown = 0; // turns until the dash is ready; 0: ready now
    int horizon = 12;
    int turn_cost = 16, danger_cost = 24;
};

struct Plan {
    bool found = false;
    vec2 to{-1, -1};          // where the first turn ends
    bool dash = false;
    vec2 landing{-1, -1};     // the first turn's dash landing, then the walk to `to`
    int cost = 0;             // the whole route's, tail included
    int expanded = 0, generated = 0;
};

namespace detail_ {

inline long long prof[4];
inline std::uint64_t fuel_now() { return cambc::fuel_remaining(); }

struct Label {
    std::int32_t g, f;
    std::int32_t next;        // the next label on the same tile
    std::uint16_t tile;
    std::uint16_t first_to, first_landing; // the first turn's end and dash landing (0xFFFF: none)
    std::uint8_t c, k, t, dead;
};

struct Scratch {
    std::vector<std::int32_t> head;
    std::vector<std::uint32_t> stamp;
    std::vector<Label> labels;
    std::vector<std::uint64_t> heap; // f << 32 | label
    std::uint32_t query = 0;
    int W = 0, H = 0;
};

inline Scratch& scratch() {
    static Scratch s;
    const int W = cambc::map::width(), H = cambc::map::height();
    if (s.W != W || s.H != H) {
        s.W = W, s.H = H;
        s.head.assign(static_cast<std::size_t>(W * H), -1);
        s.stamp.assign(static_cast<std::size_t>(W * H), 0);
        s.labels.reserve(4096);
        s.heap.reserve(4096);
    }
    return s;
}

// Fewest turns that can cover `steps` king steps from cooldown c: a dash turn moves 3 (walk and
// dash), the 7 turns after it 1 each.
inline int turns_for(int steps, int c, bool dasher) {
    if (!dasher || steps <= c) return steps;
    const int r = steps - c, cycles = r / 10, rem = r % 10;
    return c + 8 * cycles + (rem == 0 ? 0 : rem <= 3 ? 1 : rem - 2);
}

// Sleep progress of group j in packed k (2 bits each).
inline int k_of(int k, int j) { return k >> (2 * j) & 3; }

// a is at least as good as b everywhere: cost, cooldown and each group's sleep progress.
inline bool covers(const Label& a, std::int32_t g, int c, int k, int groups) {
    if (a.g > g || a.c > c) return false;
    for (int j = 0; j < groups; ++j)
        if (k_of(a.k, j) < k_of(k, j)) return false;
    return true;
}

} // namespace detail_

inline Plan route(const Query& q) {
    using namespace detail_;
    auto& s = scratch();
    const int W = s.W, H = s.H;
    const auto stride = cambc::detail::layout().chunk_stride;
    const auto chunks = static_cast<int>(cambc::detail::layout().chunked_width);
    const std::uint64_t* walls = q.walls->ptr();
    const std::uint64_t* solid = q.solid ? q.solid->ptr() : walls;
    const std::uint64_t* goals = q.goals->ptr();
    const std::uint64_t* danger = q.danger ? q.danger->ptr() : nullptr;
    const std::uint16_t* tail = q.tail->ptr();
    const auto bit = [&](const std::uint64_t* b, int x, int y) {
        return (b[(y >> 3) * stride + (x >> 3)] >> ((y & 7) * 8 + (x & 7))) & 1;
    };
    const auto tail_at = [&](int x, int y) -> int { return tail[((y >> 3) * chunks + (x >> 3)) * 64 + (y & 7) * 8 + (x & 7)]; };
    const int groups = std::min(q.groups, max_groups);

    if (++s.query == 0) std::fill(s.stamp.begin(), s.stamp.end(), 0), s.query = 1;
    s.labels.clear();
    s.heap.clear();
    Plan plan;

    const auto heap_push = [&](std::int32_t f, std::int32_t i) {
        auto& h = s.heap;
        const std::uint64_t v = static_cast<std::uint64_t>(static_cast<std::uint32_t>(f)) << 32 | static_cast<std::uint32_t>(i);
        h.push_back(v);
        std::size_t c = h.size() - 1;
        while (c) {
            const std::size_t p = (c - 1) >> 1;
            if (h[p] <= v) break;
            h[c] = h[p];
            c = p;
        }
        h[c] = v;
    };
    const auto heap_pop = [&]() {
        auto& h = s.heap;
        const std::uint64_t top = h[0], last = h.back();
        h.pop_back();
        if (!h.empty()) {
            std::size_t i = 0;
            const std::size_t n = h.size();
            for (;;) {
                std::size_t c = 2 * i + 1;
                if (c >= n) break;
                if (c + 1 < n && h[c + 1] < h[c]) ++c;
                if (h[c] >= last) break;
                h[i] = h[c];
                i = c;
            }
            h[i] = last;
        }
        return static_cast<std::int32_t>(top & 0xFFFFFFFFu);
    };
    const auto h_of = [&](int x, int y, int c) -> std::int32_t {
        const int d = tail_at(x, y);
        return d == unreachable ? -1 : turns_for(d, c, q.dasher) * q.turn_cost;
    };
    // Adds a state unless one on its tile covers it; marks the ones it covers dead.
    const auto offer = [&](int tile, std::int32_t g, int c, int k, int t, std::uint16_t first_to, std::uint16_t first_landing) {
        const int x = tile % W, y = tile / W;
        const std::int32_t h = h_of(x, y, c);
        if (h < 0) return;
        if (s.stamp[static_cast<std::size_t>(tile)] != s.query) s.stamp[static_cast<std::size_t>(tile)] = s.query, s.head[static_cast<std::size_t>(tile)] = -1;
        for (std::int32_t i = s.head[static_cast<std::size_t>(tile)]; i >= 0; i = s.labels[static_cast<std::size_t>(i)].next)
            if (!s.labels[static_cast<std::size_t>(i)].dead && covers(s.labels[static_cast<std::size_t>(i)], g, c, k, groups)) return;
        Label n;
        for (std::int32_t i = s.head[static_cast<std::size_t>(tile)]; i >= 0; i = s.labels[static_cast<std::size_t>(i)].next) {
            auto& l = s.labels[static_cast<std::size_t>(i)];
            if (l.dead) continue;
            n.g = g, n.c = static_cast<std::uint8_t>(c), n.k = static_cast<std::uint8_t>(k);
            if (covers(n, l.g, l.c, l.k, groups)) l.dead = 1;
        }
        n = {g, g + h, s.head[static_cast<std::size_t>(tile)], static_cast<std::uint16_t>(tile), first_to, first_landing,
             static_cast<std::uint8_t>(c), static_cast<std::uint8_t>(k), static_cast<std::uint8_t>(t), 0};
        const auto i = static_cast<std::int32_t>(s.labels.size());
        s.labels.push_back(n);
        s.head[static_cast<std::size_t>(tile)] = i;
        heap_push(n.f, i);
        ++plan.generated;
    };

    const vec2 st = q.start;
    offer(st.y * W + st.x, 0, q.dasher ? q.cooldown : 0, 0, 0, 0xFFFF, 0xFFFF);
    // The 49 offsets within 3 king steps, as bits by (dy + 3) * 7 + dx + 3.
    while (!s.heap.empty()) {
        const auto pp = fuel_now();
        const std::int32_t li = heap_pop();
        prof[3] += static_cast<long long>(pp - fuel_now());
        const Label cur = s.labels[static_cast<std::size_t>(li)];
        if (cur.dead) continue;
        ++plan.expanded;
        const int x = cur.tile % W, y = cur.tile / W;
        if (bit(goals, x, y) || cur.t >= q.horizon) {
            plan.found = cur.first_to != 0xFFFF || cur.t == 0;
            plan.cost = cur.f;
            if (cur.first_to != 0xFFFF) plan.to = {cur.first_to % W, cur.first_to / W};
            else plan.to = st;
            if (cur.first_landing != 0xFFFF) plan.dash = true, plan.landing = {cur.first_landing % W, cur.first_landing / W};
            return plan;
        }
        // End tiles of this turn: within 1 by walking; with a ready dash, within 1 of a landing.
        const auto p0 = fuel_now();
        std::uint64_t ends = 0;           // 7x7 bits around us
        std::uint8_t via[49];             // for dash ends: the landing's offset index (0xFF: walked)
        const auto open = [&](int ex, int ey) {
            return ex >= 0 && ey >= 0 && ex < W && ey < H && (!bit(walls, ex, ey) || bit(goals, ex, ey));
        };
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx)
                if ((dx == 0 && dy == 0) || open(x + dx, y + dy)) {
                    const int b = (dy + 3) * 7 + dx + 3;
                    ends |= std::uint64_t{1} << b;
                    via[b] = 0xFF;
                }
        const bool dash_now = q.dasher && cur.c == 0;
        if (dash_now) {
            std::uint64_t tested = ends; // walk ends are open; the rest tested once
            for (int ly = -2; ly <= 2; ++ly)
                for (int lx = -2; lx <= 2; ++lx) {
                    const int m = std::max(lx < 0 ? -lx : lx, ly < 0 ? -ly : ly);
                    if (m == 0) continue;
                    const int lb = (ly + 3) * 7 + lx + 3;
                    if (m == 1) {
                        if (!(ends >> lb & 1)) continue;
                    } else {
                        if (!open(x + lx, y + ly)) continue;
                        // A path of two king steps through any crossable tile next to us.
                        bool path = false;
                        for (int my = -1; my <= 1 && !path; ++my)
                            for (int mx = -1; mx <= 1 && !path; ++mx) {
                                if ((mx == 0 && my == 0) || lx - mx > 1 || mx - lx > 1 || ly - my > 1 || my - ly > 1) continue;
                                const int ix = x + mx, iy = y + my;
                                path = ix >= 0 && iy >= 0 && ix < W && iy < H && !bit(solid, ix, iy);
                            }
                        if (!path) continue;
                    }
                    for (int dy = -1; dy <= 1; ++dy)
                        for (int dx = -1; dx <= 1; ++dx) {
                            const int ex = lx + dx, ey = ly + dy;
                            if (ex < -3 || ex > 3 || ey < -3 || ey > 3) continue;
                            const int b = (ey + 3) * 7 + ex + 3;
                            if (ends >> b & 1) continue; // a walk alone or an earlier landing gets there
                            if (!(tested >> b & 1)) {
                                tested |= std::uint64_t{1} << b;
                                if (!open(x + ex, y + ey)) {
                                    tested |= std::uint64_t{1} << b; // closed: never retried
                                    continue;
                                }
                            } else {
                                continue; // tested before and closed
                            }
                            ends |= std::uint64_t{1} << b;
                            via[b] = static_cast<std::uint8_t>(lb);
                        }
                }
        }
        const auto p1 = fuel_now();
        prof[0] += static_cast<long long>(p0 - p1);
        for (std::uint64_t left = ends; left; left &= left - 1) {
            const auto p2 = fuel_now();
            const int b = __builtin_ctzll(left);
            const int ex = x + b % 7 - 3, ey = y + b / 7 - 3;
            const bool dashed = via[b] != 0xFF;
            std::int32_t g = cur.g + q.turn_cost;
            if (danger && bit(danger, ex, ey)) g += q.danger_cost;
            int k = cur.k, hit_groups = 0;
            for (const auto& m : q.camps) {
                const int d = std::max(m.pos.x > ex ? m.pos.x - ex : ex - m.pos.x, m.pos.y > ey ? m.pos.y - ey : ey - m.pos.y);
                if (d > m.reach) continue;
                if (m.group < 0) g += m.damage;
                else if (k_of(k, m.group) < 2) g += m.damage, hit_groups |= 1 << m.group;
            }
            for (int j = 0; j < groups; ++j) {
                const int kj = k_of(k, j);
                const int nk = hit_groups >> j & 1 ? 0 : kj < 2 ? kj + 1 : 2;
                k = (k & ~(3 << (2 * j))) | nk << (2 * j);
            }
            const int c = dashed ? 7 : (cur.c > 0 ? cur.c - 1 : 0);
            const int tile = ey * W + ex;
            std::uint16_t first_to = cur.first_to, first_landing = cur.first_landing;
            if (cur.t == 0) {
                first_to = static_cast<std::uint16_t>(tile);
                first_landing = dashed ? static_cast<std::uint16_t>((y + via[b] / 7 - 3) * W + x + via[b] % 7 - 3) : 0xFFFF;
            }
            const auto p3 = fuel_now();
            offer(tile, g, c, k, cur.t + 1, first_to, first_landing);
            const auto p4 = fuel_now();
            prof[1] += static_cast<long long>(p2 - p3);
            prof[2] += static_cast<long long>(p3 - p4);
        }
    }
    return plan;
}

} // namespace router
