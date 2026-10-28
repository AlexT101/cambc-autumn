// Mirrors tools/mapgen/grid.mjs, generate.mjs metrics() and draftlab/features.mjs extras() step for
// step, rounding included (the model was fit on the rounded values): change them together.
#include "map_features.h"
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <limits>
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

    // grid.mjs travel: walking 1, from level 1 a dash (2 king steps; the middle tile must not be in
    // `block`) DASH_COST, from level 2 a crystal (range 3) TELE_COST; only from tiles near something
    // unwalkable. Any exact shortest-path order gives the same distances.
    void travel(const std::vector<int>& starts, const std::vector<std::uint8_t>& pass, const std::vector<std::uint8_t>& block,
                int level, std::vector<int>& dist) const {
        dist.assign(n, -1);
        std::vector<std::uint8_t> near(n, 0);
        const int R = level > 1 ? 2 : 1;
        for (int i = 0; i < n; ++i) {
            if (pass[i]) continue;
            const int x = i % W, y = i / W;
            for (int dy = -R; dy <= R; ++dy)
                for (int dx = -R; dx <= R; ++dx)
                    if (inside(x + dx, y + dy)) near[(y + dy) * W + x + dx] = 1;
        }
        // Dash ends at Chebyshev 2 and their middle tiles, king-adjacent to both ends.
        struct Dash {
            int dx, dy, mids;
            int mid[3][2];
        };
        static const auto dashes = [] {
            std::vector<Dash> out;
            for (int dy = -2; dy <= 2; ++dy)
                for (int dx = -2; dx <= 2; ++dx) {
                    if (std::max(std::abs(dx), std::abs(dy)) < 2) continue;
                    Dash d{dx, dy, 0, {}};
                    for (int a = -1; a <= 1; ++a)
                        for (int b = -1; b <= 1; ++b) {
                            const bool ax = std::abs(dx) == 2 ? a == dx / 2 : dx ? a == 0 || a == dx : true;
                            const bool by = std::abs(dy) == 2 ? b == dy / 2 : dy ? b == 0 || b == dy : true;
                            if (ax && by && (a || b) && std::max(std::abs(dx - a), std::abs(dy - b)) <= 1)
                                d.mid[d.mids][0] = a, d.mid[d.mids][1] = b, ++d.mids;
                        }
                    out.push_back(d);
                }
            return out;
        }();
        constexpr int B = tele_cost + 1;
        std::vector<int> buckets[B];
        int pending = 0;
        const auto relax = [&](int j, int d) {
            if (dist[j] < 0 || d < dist[j]) dist[j] = d, buckets[d % B].push_back(j), ++pending;
        };
        for (const int s : starts)
            if (pass[s]) relax(s, 0);
        const auto free_tile = [&](int x, int y) { return inside(x, y) && !block[y * W + x]; };
        for (int d = 0; pending; ++d) {
            auto& bucket = buckets[d % B];
            while (!bucket.empty()) {
                const int i = bucket.back();
                bucket.pop_back();
                --pending;
                if (dist[i] != d) continue;
                const int x = i % W, y = i / W;
                for (const auto& s : n8) {
                    const int nx = x + s[0], ny = y + s[1];
                    if (inside(nx, ny) && pass[ny * W + nx]) relax(ny * W + nx, d + 1);
                }
                if (!near[i]) continue;
                for (const auto& e : dashes) {
                    const int nx = x + e.dx, ny = y + e.dy;
                    if (!inside(nx, ny) || !pass[ny * W + nx]) continue;
                    for (int m = 0; m < e.mids; ++m)
                        if (free_tile(x + e.mid[m][0], y + e.mid[m][1])) {
                            relax(ny * W + nx, d + dash_cost);
                            break;
                        }
                }
                if (level < 2) continue;
                for (int dy = -3; dy <= 3; ++dy)
                    for (int dx = -3; dx <= 3; ++dx) {
                        const int nx = x + dx, ny = y + dy;
                        if (std::max(std::abs(dx), std::abs(dy)) >= 2 && inside(nx, ny) && pass[ny * W + nx])
                            relax(ny * W + nx, d + tele_cost);
                    }
            }
        }
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

    // grid.mjs clearance: walls, holes, altars 0, walkable edge tiles 1, then a BFS whose queue
    // mixes the two in index order, so a tile can read one more than its true distance. Capped at 6
    // by its one reader, so tiles at 6 or more are not expanded: everything below 6 is unchanged,
    // as later queue entries are at most one below earlier ones.
    std::vector<int> clearance6() const {
        std::vector<int> d(n, -1), q;
        q.reserve(n);
        for (int i = 0; i < n; ++i) {
            const int x = i % W, y = i / W;
            if (!walk_tile(i)) d[i] = 0, q.push_back(i);
            else if (x == 0 || y == 0 || x == W - 1 || y == H - 1) d[i] = 1, q.push_back(i);
        }
        for (std::size_t h = 0; h < q.size(); ++h) {
            const int i = q[h];
            if (d[i] >= 6) continue;
            const int x = i % W, y = i / W;
            for (const auto& s : n8) {
                const int nx = x + s[0], ny = y + s[1];
                if (inside(nx, ny) && d[ny * W + nx] < 0) d[ny * W + nx] = d[i] + 1, q.push_back(ny * W + nx);
            }
        }
        for (auto& v : d) v = v < 0 ? 6 : std::min(v, 6);
        return d;
    }
};

struct Group {
    std::vector<int> members; // indices into Input::camps
    int lo, mlo;
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

std::array<double, count> compute(const Input& in, WalkField walk) {
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
    // block(side) in spawnFields: walls and the other spawn (no camp blockers in the fields we travel).
    const auto block_for = [&](int side) {
        std::vector<std::uint8_t> m(n);
        for (int i = 0; i < n; ++i) m[i] = in.t[i] == wall;
        for (const int i : g.spawn_tiles(1 - side)) m[i] = 1;
        return m;
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
            g.travel(a, g.pass_for(0, nullptr), block_for(0), 2, fA);
            g.travel(b, g.pass_for(1, nullptr), block_for(1), 2, fB);
            S = spawn_dist(fA);
            if (!std::isfinite(S)) throw std::runtime_error("map features: spawns not connected");
        }
    }
    const int Si = static_cast<int>(S);

    const double area = static_cast<double>(n);
    int reach = 0;
    for (int i = 0; i < n; ++i) reach += openA[i] >= 0;
    std::vector<int> front(Si + 2, 0);
    for (int i = 0; i < n; ++i)
        if (fA[i] >= 0 && fA[i] <= Si) ++front[fA[i]];
    double choke = inf;
    for (int d = static_cast<int>(std::floor(S * 0.25)); d <= static_cast<int>(std::ceil(S * 0.75)); ++d)
        choke = std::min(choke, static_cast<double>(front[d]));
    double clear_sum = 0;
    {
        const auto clear = g.clearance6();
        for (int i = 0; i < n; ++i)
            if (openA[i] >= 0) clear_sum += clear[i];
    }
    int bushes = 0, holes = 0;
    for (int i = 0; i < n; ++i) bushes += in.t[i] == bush, holes += in.t[i] == hole;

    // Altars: the nearest (by own distance, then ratio) reachable one's contest ratio; centrality.
    int altars = 0;
    bool any_ratio = false;
    double best_d = 0, best_ratio = 0, centre_sum = 0;
    const double cx = (g.W - 1) / 2.0, cy = (g.H - 1) / 2.0, half = std::max(g.W, g.H) / 2.0;
    for (int i = 0; i < n; ++i) {
        if (in.t[i] != altar) continue;
        ++altars;
        const int x = i % g.W, y = i / g.W, dA = g.reach_near(fA, x, y), dB = g.reach_near(fB, x, y);
        centre_sum += std::max(std::abs(x - cx), std::abs(y - cy)) / half;
        if (dA >= 0 && dB >= 0) {
            const double r = dA / std::max(1.0, static_cast<double>(dA + dB));
            if (!any_ratio || dA < best_d || (dA == best_d && r < best_ratio)) best_d = dA, best_ratio = r;
            any_ratio = true;
        }
    }

    // sideGroups(g, open): our side's groups (a non-shared group's mirror is the enemy's), and shared ones.
    const auto groups = groups_of(g);
    const auto near = [&](const std::vector<int>& d, const Group& q) {
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
            const double dA = near(openA, q), dB = near(openB, q);
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
    int dash_short = 0;
    {
        std::vector<int> dash;
        g.travel(a, g.pass_for(0, nullptr), block_for(0), 1, dash);
        for (int i = 0; i < n; ++i)
            if (openA[i] >= 0 && dash[i] >= 0 && openA[i] - dash[i] >= 6) ++dash_short;
    }

    const auto& s = in;
    const int bx = s.sym == vertical ? s.sx : g.W - 1 - s.sx, by = s.sym == horizontal ? s.sy : g.H - 1 - s.sy;
    const int cheby = std::max(std::abs(bx - s.sx), std::abs(by - s.sy)) - s.sw + 1;
    const double camps_all = static_cast<double>(in.camps.size());
    return {
        area,
        r3(reach / area),
        S,
        r2(S / std::max(1, cheby)),
        std::isfinite(choke) ? r2(choke / std::sqrt(std::max(1.0, static_cast<double>(reach)))) : nan,
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
    // model.mjs champValues: b + w.z + counters against the ladder prior's champion frequencies.
    double value[NC];
    for (int c = 0; c < NC; ++c) {
        double s = model->b[c];
        for (int k = 0; k < count; ++k) s += model->w[c][k] * z[k];
        for (int d = 0; d < NC; ++d)
            if (d != c) s += model->q[d] * (c < d ? 1 : -1) * model->ctr[m::pair(c, d)];
        value[c] = s;
    }
    // rankTeams: the first best team in lexicographic order (the JS sort is stable).
    int cur[5], best[5];
    double best_s = -inf;
    bool found = false;
    const auto rec = [&](auto&& self, int at, int from) -> void {
        if (at == picks) {
            double s = 0;
            for (int i = 0; i < picks; ++i) {
                s += value[cur[i]];
                for (int j = i + 1; j < picks; ++j) s += model->syn[m::pair(cur[i], cur[j])];
            }
            if (!found || s > best_s) found = true, best_s = s, std::copy(cur, cur + picks, best);
            return;
        }
        for (int c = from; c < NC; ++c) cur[at] = c, self(self, at + 1, c + 1);
    };
    rec(rec, 0, 0);
    // pickOrder: least opponent-dependent first.
    const auto sens = [&](int c) {
        double s = 0;
        for (int d = 0; d < NC; ++d)
            if (d != c) {
                const double t = model->ctr[m::pair(c, d)];
                s += model->q[d] * (1 - model->q[d]) * (t * t);
            }
        return s;
    };
    std::vector<int> team(best, best + picks);
    std::stable_sort(team.begin(), team.end(), [&](int x, int y) { return sens(x) < sens(y); });
    return team;
}

} // namespace aph::mapfeat
