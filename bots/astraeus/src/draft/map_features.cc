// Mirrors tools/mapgen/grid.mjs, generate.mjs metrics() and draftlab/features.mjs extras() step for
// step, rounding included (the model was fit on the rounded values): change them together.
#include "map_features.h"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdlib>
#include <limits>
#include <memory>
#include <stdexcept>
#include <utility>
#include "draft_model.h"

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
constexpr const char* names[count] = {"area", "reach_frac", "spawn_dist", "detour", "choke_rel", "openness", "bushes",
                                      "holes", "altars", "altar_ratio", "altar_centre", "gems_side", "gold_side",
                                      "big_share", "cluster_share", "contested_share", "big_camp_share", "dash_short",
                                      "camp_near"};
constexpr bool names_match() {
    for (int k = 0; k < count; ++k)
        if (!same(names[k], draft_model::feature_names[k])) return false;
    return draft_model::features == count;
}
static_assert(names_match(), "draft_model.h has another feature list: update compute()");

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
const Dashes& dashes() {
    static const Dashes t = [] {
        Dashes t{};
        int e = 0;
        for (int dy = -2; dy <= 2; ++dy)
            for (int dx = -2; dx <= 2; ++dx) {
                if (std::max(std::abs(dx), std::abs(dy)) < 2) continue;
                t.dx[e] = dx, t.dy[e] = dy;
                for (int k = 0; k < 8; ++k) {
                    const int a = n8[k][0], b = n8[k][1];
                    const bool ax = std::abs(dx) == 2 ? a == dx / 2 : dx ? a == 0 || a == dx : true;
                    const bool by = std::abs(dy) == 2 ? b == dy / 2 : dy ? b == 0 || b == dy : true;
                    if (ax && by && std::max(std::abs(dx - a), std::abs(dy - b)) <= 1) t.mid[e][t.mids[e]++] = k;
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
    }();
    return t;
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
    // the same tiles: the tiles beside something unwalkable try their dashes and crystals in `base`
    // order, and Dial's algorithm runs only from the tiles they improve (any exact order gives the
    // same distances). Fills `dist` if given; returns the tiles brought 6 or more nearer (dash_short).
    // For fuel: a grid padded by 3 blocked tiles, so no bounds checks, and `d` holding distance + 1
    // (0 where blocked, -1 on holes and altars, which a dash crosses).
    int travel(int side, const std::vector<int>& base, int level, std::vector<int>* dist) const {
        constexpr int pad = 3, far = std::numeric_limits<int>::max();
        const int w = W, h = H, S = w + 2 * pad, N = S * (h + 2 * pad);
        int step[8], end[16], mid[16][3], tele[40], teles = 0;
        for (int k = 0; k < 8; ++k) step[k] = n8[k][1] * S + n8[k][0];
        for (int dy = -3; dy <= 3; ++dy)
            for (int dx = -3; dx <= 3; ++dx)
                if (std::max(std::abs(dx), std::abs(dy)) >= 2) tele[teles++] = dy * S + dx;
        const auto& t = dashes();
        for (int e = 0; e < 16; ++e) {
            end[e] = t.dy[e] * S + t.dx[e];
            for (int m = 0; m < t.mids[e]; ++m) mid[e][m] = step[t.mid[e][m]];
        }
        std::vector<int> d_v(static_cast<std::size_t>(N), 0);
        std::vector<std::uint8_t> beside_v(d_v.size(), 0), near_v(level > 1 ? d_v.size() : 0, 0);
        int* const d = d_v.data();
        std::uint8_t *const beside = beside_v.data(), *const near = level > 1 ? near_v.data() : nullptr;
        const int* const bd = base.data();
        const auto unwalkable = [&](int q, int v) {
            d[q] = v;
            for (const int o : step) beside[q + o] = 1;
            if (near)
                for (int dy = -2; dy <= 2; ++dy)
                    for (int dx = -2; dx <= 2; ++dx) near[q + dy * S + dx] = 1;
        };
        int top = -1;
        {
            const std::uint8_t* const tile = in.t.data();
            for (int y = 0, i = 0; y < h; ++y)
                for (int x = 0, q = (y + pad) * S + pad; x < w; ++x, ++i, ++q)
                    if (tile[i] == ground || tile[i] == bush) {
                        d[q] = bd[i] >= 0 ? bd[i] + 1 : far;
                        top = std::max(top, bd[i]);
                    } else unwalkable(q, tile[i] == wall ? 0 : -1);
        }
        for (const int i : spawn_tiles(1 - side)) unwalkable((i / w + pad) * S + i % w + pad, 0);
        // Those tiles' lists by walking distance.
        std::vector<int> head(static_cast<std::size_t>(top + 1), -1);
        const auto next = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(N));
        for (int y = 0; y < h; ++y)
            for (int x = 0, q = (y + pad) * S + pad; x < w; ++x, ++q)
                if (beside[q] && d[q] > 0 && d[q] != far) next[q] = head[static_cast<std::size_t>(d[q] - 1)], head[static_cast<std::size_t>(d[q] - 1)] = q;
        // Dial's buckets: a bucket holds one distance at a time, and a tile at most once a distance.
        constexpr int B = tele_cost + 1;
        const auto pool = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(B * n));
        int size[B] = {}, pending = 0, gained = 0;
        const auto relax = [&](int j, int v) {
            if (v + 1 < d[j]) d[j] = v + 1, pool[v % B * n + size[v % B]++] = j, ++pending;
        };
        // Dashes and crystals from i at v. A dash over a walkable middle tile never beats walking
        // through it (2 < DASH_COST), so only ends whose middle tiles are all unwalkable are tried.
        const auto leap = [&](int i, int v, unsigned blocked) {
            for (unsigned c = t.over[blocked]; c; c &= c - 1) {
                const int e = std::countr_zero(c), j = i + end[e];
                if (d[j] <= v + 1 + dash_cost) continue;
                for (int m = 0; m < t.mids[e]; ++m)
                    if (d[i + mid[e][m]]) {
                        relax(j, v + dash_cost);
                        break;
                    }
            }
            if (!near || !near[i]) return;
            for (int k = 0; k < teles; ++k) relax(i + tele[k], v + tele_cost);
        };
        for (int v = 0; v <= top || pending; ++v) {
            // A tile improved since is popped at its new distance instead.
            if (v <= top)
                for (int i = head[static_cast<std::size_t>(v)]; i >= 0; i = next[i])
                    if (d[i] == v + 1) {
                        unsigned blocked = 0;
                        for (int k = 0; k < 8; ++k) blocked |= d[i + step[k]] <= 0 ? 1u << k : 0u;
                        leap(i, v, blocked);
                    }
            int* const bucket = &pool[v % B * n];
            for (int& left = size[v % B]; left;) {
                const int i = bucket[--left];
                --pending;
                if (d[i] != v + 1) continue;
                if (const int was = bd[(i / S - pad) * w + i % S - pad]; was >= 0 && was - v >= 6) ++gained;
                unsigned blocked = 0;
                for (int k = 0; k < 8; ++k)
                    if (d[i + step[k]] > 0) relax(i + step[k], v + 1);
                    else blocked |= 1u << k;
                leap(i, v, blocked);
            }
        }
        if (dist) {
            dist->resize(static_cast<std::size_t>(n));
            int* const out = dist->data();
            for (int y = 0, i = 0; y < h; ++y)
                for (int x = 0, q = (y + pad) * S + pad; x < w; ++x, ++i, ++q) out[i] = d[q] > 0 && d[q] != far ? d[q] - 1 : -1;
        }
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
    int clearance_sum(const std::vector<int>& reach) const {
        constexpr std::uint8_t unset = 0xff;
        const int w = W, h = H, S = w + 2;
        std::vector<std::uint8_t> d_v(static_cast<std::size_t>(S * (h + 2)), 0);
        const auto q = std::make_unique_for_overwrite<int[]>(static_cast<std::size_t>(n));
        std::uint8_t* const d = d_v.data();
        const std::uint8_t* const t = in.t.data();
        int tail = 0;
        for (int y = 0, i = 0; y < h; ++y)
            for (int x = 0, p = (y + 1) * S + 1; x < w; ++x, ++i, ++p)
                if (t[i] != ground && t[i] != bush) d[p] = 0, q[tail++] = p;
                else if (x == 0 || y == 0 || x == w - 1 || y == h - 1) d[p] = 1, q[tail++] = p;
                else d[p] = unset;
        int step[8];
        for (int k = 0; k < 8; ++k) step[k] = n8[k][1] * S + n8[k][0];
        for (int k = 0; k < tail; ++k) {
            const int p = q[k];
            const std::uint8_t v = d[p];
            if (v >= 6) continue;
            for (const int o : step)
                if (d[p + o] == unset) d[p + o] = static_cast<std::uint8_t>(v + 1), q[tail++] = p + o;
        }
        int sum = 0;
        const int* const r = reach.data();
        for (int y = 0, i = 0; y < h; ++y)
            for (int x = 0, p = (y + 1) * S + 1; x < w; ++x, ++i, ++p)
                if (r[i] >= 0) sum += d[p] == unset ? 6 : d[p];
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
    std::vector<int> at(g.n, -1);
    for (std::size_t k = 0; k < all.size(); ++k) at[all[k].y * g.W + all[k].x] = static_cast<int>(k);
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
                const int j = at[ny * g.W + nx];
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

} // namespace

std::array<double, count> compute(const Input& in, WalkField walk, bool crystals) {
    if (in.W <= 0 || in.H <= 0 || static_cast<int>(in.t.size()) != in.W * in.H || in.sw <= 0 || in.sh <= 0)
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
    field(0, false, openA), field(1, false, openB);
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
    if (std::isfinite(S)) field(1, true, fB);
    else {
        fA = openA, fB = openB;
        S = spawn_dist(fA);
        if (!std::isfinite(S)) {
            if (!crystals) throw std::runtime_error("map features: spawns joined only by dash or crystal");
            g.travel(0, openA, 2, &fA), g.travel(1, openB, 2, &fB);
            S = spawn_dist(fA);
            if (!std::isfinite(S)) throw std::runtime_error("map features: spawns not connected");
        }
    }
    const int Si = static_cast<int>(S);

    const double area = static_cast<double>(n);
    // One pass: reach, the walking front, bushes, holes and the altars (the nearest reachable one by
    // own distance, then ratio, gives the contest ratio; centrality).
    int reach = 0, bushes = 0, holes = 0, altars = 0;
    std::vector<int> front(Si + 2, 0);
    bool any_ratio = false;
    double best_d = 0, best_ratio = 0, centre_sum = 0;
    const double cx = (g.W - 1) / 2.0, cy = (g.H - 1) / 2.0, half = std::max(g.W, g.H) / 2.0;
    for (int i = 0; i < n; ++i) {
        reach += openA[i] >= 0;
        if (fA[i] >= 0 && fA[i] <= Si) ++front[fA[i]];
        const auto k = in.t[i];
        bushes += k == bush, holes += k == hole;
        if (k != altar) continue;
        ++altars;
        const int x = i % g.W, y = i / g.W, dA = g.reach_near(fA, x, y), dB = g.reach_near(fB, x, y);
        centre_sum += std::max(std::abs(x - cx), std::abs(y - cy)) / half;
        if (dA >= 0 && dB >= 0) {
            const double r = dA / std::max(1.0, static_cast<double>(dA + dB));
            if (!any_ratio || dA < best_d || (dA == best_d && r < best_ratio)) best_d = dA, best_ratio = r;
            any_ratio = true;
        }
    }
    // The narrowest walking front in the middle half; the range is never empty, so never null.
    int choke = front[Si / 4];
    for (int d = Si / 4; d <= (3 * Si + 3) / 4; ++d) choke = std::min(choke, front[d]);
    const double clear_sum = g.clearance_sum(openA);

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
    int ratios = 0, contested = 0, big_members = 0;
    for (const auto& q : groups) {
        if (q.members.size() >= 3) big_members += static_cast<int>(q.members.size());
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
    const int dash_short = g.travel(0, openA, 1, nullptr);

    // metrics' detour: from team A's spawn corner to its mirror, less the spawn's width (even where
    // its height is the gap's axis).
    const int bx = in.sym == vertical ? in.sx : g.W - 1 - in.sx, by = in.sym == horizontal ? in.sy : g.H - 1 - in.sy;
    const int cheby = std::max(std::abs(bx - in.sx), std::abs(by - in.sy)) - in.sw + 1;
    const double camps_all = static_cast<double>(in.camps.size());
    return {
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

std::vector<int> model_team(const std::array<double, count>& raw, int picks) {
    namespace m = draft_model;
    const m::PickModel* model = nullptr;
    for (const auto& p : m::models)
        if (p.picks == picks) model = &p;
    if (!model) return {};
    constexpr int NC = m::champions;
    std::array<double, count> z{};
    for (int k = 0; k < count; ++k) {
        double v = raw[k];
        if (std::isfinite(v)) v = m::transforms[k] == m::tf_log ? std::log(std::max(v, 1.0)) : m::transforms[k] == m::tf_log1p ? std::log1p(std::max(v, 0.0)) : v;
        v = (v - m::mean[k]) / m::sd[k];
        z[k] = std::isfinite(v) ? std::max(-4.0, std::min(4.0, v)) : 0.0;
    }
    // model.mjs champValues without counter terms (deployedTeam): b + w.z.
    double value[NC];
    for (int c = 0; c < NC; ++c) {
        double s = model->b[c];
        for (int k = 0; k < count; ++k) s += model->w[c][k] * z[k];
        value[c] = s;
    }
    // rankTeams: the first best team in lexicographic order (the JS sort is stable), its terms
    // added in teamValue's order; the pick count a constant, so the scoring unrolls.
    double syn[NC][NC];
    for (int i = 0; i < NC; ++i)
        for (int j = i + 1; j < NC; ++j) syn[i][j] = model->syn[m::pair(i, j)];
    int best[5];
    const auto rank = [&]<int P>() {
        int cur[P];
        for (int i = 0; i < P; ++i) cur[i] = i;
        double best_s = -inf;
        for (bool more = true; more;) {
            double s = 0;
            for (int i = 0; i < P; ++i) {
                s += value[cur[i]];
                for (int j = i + 1; j < P; ++j) s += syn[cur[i]][cur[j]];
            }
            if (s > best_s) best_s = s, std::copy(cur, cur + P, best);
            int i = P - 1;
            while (i >= 0 && cur[i] == NC - P + i) --i;
            if ((more = i >= 0)) {
                ++cur[i];
                for (int j = i + 1; j < P; ++j) cur[j] = cur[j - 1] + 1;
            }
        }
    };
    if (picks == 3) rank.template operator()<3>();
    else if (picks == 4) rank.template operator()<4>();
    else rank.template operator()<5>();
    // In champion id order: with no counter terms, no pick depends on the opponent's.
    return {best, best + picks};
}

} // namespace aph::mapfeat
