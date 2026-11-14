// Benchmark for router.h: on its first turn, champion 0 runs seeded random queries on the map and
// prints fuel per query (run with a large --fuel). Every other turn yields.
#include <cambc.h>
#include <algorithm>
#include <array>
#include <cstdio>
#include <vector>
#include "router.h"
#include "cba.h"
#include "bitroute.h"
#include "winroute.h"
#include "localroute.h"

using cambc::bitboard;
using cambc::vec2;

namespace {

std::uint32_t seed = 12345;
int rnd(int n) {
    seed = seed * 1103515245u + 12345u;
    return static_cast<int>((seed >> 8) % static_cast<std::uint32_t>(n));
}

struct Member {
    vec2 pos;
    int reach, damage, group;
};

[[gnu::noinline]] int calib_sum(const std::vector<int>& v) {
    int s = 0;
    for (const int x : v) s += x;
    return s;
}
[[gnu::noinline]] int calib_bits(const std::uint64_t* w, int n, int stride) {
    int s = 0;
    for (int i = 0; i < n; ++i) {
        const int x = i & 31, y = (i >> 5) & 31;
        s += static_cast<int>((w[(y >> 3) * stride + (x >> 3)] >> ((y & 7) * 8 + (x & 7))) & 1);
    }
    return s;
}
struct Rec { int a, b, c; short d, e; };
[[gnu::noinline]] int calib_push(std::vector<Rec>& v, int n) {
    v.clear();
    for (int i = 0; i < n; ++i) v.push_back({i, i, i, 1, 2});
    return static_cast<int>(v.size());
}

void calibrate() {
    std::vector<int> v(10000, 1);
    std::vector<Rec> r;
    r.reserve(10000);
    const auto& walls = cambc::map::walls();
    const auto stride = static_cast<int>(cambc::detail::layout().chunk_stride);
    auto f0 = cambc::fuel_remaining();
    volatile int x = calib_sum(v);
    auto f1 = cambc::fuel_remaining();
    x = calib_bits(walls.ptr(), 10000, stride);
    auto f2 = cambc::fuel_remaining();
    x = calib_push(r, 10000);
    auto f3 = cambc::fuel_remaining();
    (void)x;
    std::printf("PL calib per iteration: sum %.2f bits %.2f push %.2f\n", (f0 - f1) / 10000.0, (f1 - f2) / 10000.0, (f2 - f3) / 10000.0);
}

// The comms session's router window search (river pathing.htb weigh() + route's first-step choice), ported.
namespace peer {
constexpr int window = 5, side = 2 * window + 1;
const vec2 dirs[8] = {{0, 1}, {1, 1}, {1, 0}, {1, -1}, {0, -1}, {-1, -1}, {-1, 0}, {-1, 1}};
[[gnu::always_inline]] inline bool tile_set(const bitboard& b, vec2 p) {
    const auto& layout = cambc::detail::layout();
    return (b.ptr()[(p.y >> 3) * layout.chunk_stride + (p.x >> 3)] >> (((p.y & 7) << 3) | (p.x & 7))) & 1;
}
inline int steps_at(const cambc::distance_field& f, vec2 p) {
    const int chunks = static_cast<int>(cambc::detail::layout().chunked_width);
    return f.ptr()[((p.y >> 3) * chunks + (p.x >> 3)) * 64 + (p.y & 7) * 8 + (p.x & 7)];
}
struct Boards { const bitboard *enemy_reach, *enemy_edge, *camp_reach, *camp_edge; };
inline int weight(const Boards& w, vec2 p) {
    return (tile_set(*w.enemy_reach, p) ? 12 : tile_set(*w.enemy_edge, p) ? 4 : 0) + (tile_set(*w.camp_reach, p) ? 8 : tile_set(*w.camp_edge, p) ? 2 : 0);
}
// Returns the chosen first step.
[[gnu::noinline]] vec2 route(vec2 me, const bitboard& walls, const cambc::distance_field& field, const Boards& wb) {
    const int W = cambc::map::width(), H = cambc::map::height();
    const auto in_bounds = [&](vec2 p) { return p.x >= 0 && p.y >= 0 && p.x < W && p.y < H; };
    std::array<int, side * side> to_go;
    to_go.fill(-1);
    std::array<int, side * side> weight_of{};
    static std::array<std::uint32_t, side * side * 9> heap;
    int n = 0;
    const auto push = [&](int cost, int k) {
        std::uint32_t v = static_cast<std::uint32_t>(cost) << 8 | static_cast<std::uint32_t>(k);
        int i = n++;
        for (; i > 0 && heap[(i - 1) / 2] > v; i = (i - 1) / 2) heap[i] = heap[(i - 1) / 2];
        heap[i] = v;
    };
    const auto pop = [&]() {
        const std::uint32_t top = heap[0], last = heap[--n];
        int i = 0;
        for (;;) {
            int c = 2 * i + 1;
            if (c >= n) break;
            if (c + 1 < n && heap[c + 1] < heap[c]) ++c;
            if (heap[c] >= last) break;
            heap[i] = heap[c], i = c;
        }
        if (n > 0) heap[i] = last;
        return top;
    };
    for (int dy = -window; dy <= window; ++dy)
        for (int dx = -window; dx <= window; ++dx) {
            const vec2 p{me.x + dx, me.y + dy};
            const int k = (dy + window) * side + dx + window;
            weight_of[k] = -1;
            if (!in_bounds(p) || (tile_set(walls, p) && !(p.x == me.x && p.y == me.y))) continue;
            weight_of[k] = weight(wb, p);
            int cost = -1;
            const int st = steps_at(field, p);
            if (st == 0) cost = 0;
            else if ((dx == -window || dx == window || dy == -window || dy == window) && st != router::unreachable) cost = 8 * st;
            if (cost >= 0) to_go[k] = cost, push(cost, k);
        }
    while (n > 0) {
        const std::uint32_t top = pop();
        const int k = static_cast<int>(top & 255), cost = static_cast<int>(top >> 8);
        if (cost != to_go[k]) continue;
        const int x = k % side, y = k / side;
        const int via = cost + 8 + weight_of[k];
        for (const auto d : dirs) {
            const int nx = x + d.x, ny = y + d.y;
            if (nx < 0 || ny < 0 || nx >= side || ny >= side) continue;
            const int j = ny * side + nx;
            if (weight_of[j] < 0 || (to_go[j] >= 0 && to_go[j] <= via)) continue;
            to_go[j] = via;
            push(via, j);
        }
    }
    vec2 best{-1, -1};
    int best_cost = -1;
    for (const auto d : dirs) {
        const vec2 p{me.x + d.x, me.y + d.y};
        if (!in_bounds(p) || tile_set(walls, p)) continue;
        const int c = to_go[(d.y + window) * side + d.x + window];
        if (c < 0) continue;
        const int total = c + 8 + weight(wb, p);
        if (best_cost < 0 || total < best_cost) best_cost = total, best = p;
    }
    return best;
}
} // namespace peer

void bench() {
    calibrate();
    const int W = cambc::map::width(), H = cambc::map::height();
    // Walls for walking: walls, holes, altars, camp tiles, the enemy spawn. Dash paths: walls,
    // camp tiles and the enemy spawn.
    bitboard walls = cambc::map::walls();
    walls |= cambc::map::holes();
    walls |= cambc::map::altars();
    walls |= cambc::map::spawn_region(cambc::team::enemy);
    bitboard solid = cambc::map::walls();
    solid |= cambc::map::spawn_region(cambc::team::enemy);
    std::vector<Member> members;
    const auto groups = cambc::map::camp_groups();
    int g_index = 0;
    for (const auto& g : groups) {
        for (const auto& c : g.camps()) {
            const auto p = c.spawn_position();
            walls.set(p);
            solid.set(p);
            const auto t = c.kind();
            const int dmg = t == cambc::camp_type::wolf ? 20 : t == cambc::camp_type::elk ? 60 : t == cambc::camp_type::golem ? 120 : t == cambc::camp_type::monolith ? 200 : 0;
            const int reach = t == cambc::camp_type::wolf ? 3 : t == cambc::camp_type::monolith ? 5 : 4;
            if (dmg) members.push_back({p, reach, dmg, g_index});
        }
        ++g_index;
    }
    // Dashers' tail: holes and altars a dash may cross are open.
    bitboard dash_walls = cambc::map::walls();
    dash_walls |= cambc::map::spawn_region(cambc::team::enemy);
    for (const auto& m : members) dash_walls.set(m.pos);

    // helios's search: static walls, camp tiles hard.
    map_info::width = W, map_info::height = H, map_info::me_field_cap = W + H;
    map_info::static_block = cambc::map::walls();
    map_info::static_block |= cambc::map::holes();
    map_info::static_block |= cambc::map::altars();
    map_info::static_block |= cambc::map::spawn_region(cambc::team::enemy);
    bitboard camp_tiles;
    for (const auto& m : members) camp_tiles.set(m.pos);
    std::vector<vec2> open;
    for (int y = 0; y < H; ++y)
        for (int x = 0; x < W; ++x)
            if (!walls.is_set({x, y})) open.push_back({x, y});
    cambc::distance_field walk_field, dash_field;
    bitboard visited, goals, danger;
    int window_mismatch = 0, bit_notfound = 0, win_notfound = 0, win_nostep = 0, loc_notfound = 0;
    std::vector<int> fuel_loc_walk, fuel_loc_dash;
    std::vector<int> fuel_win_walk, fuel_win_dash, lv_walk, lv_dash;
    std::vector<int> fuel_bit_walk, fuel_bit_dash, bk_walk, bk_dash;
    std::uint64_t prof_window[prof::COUNT] = {};
    std::vector<int> fuel_cba_window, fuel_cba, fuel_cba_quiet, fuel_field, walk_d, fuel_peer, fuel_walk, fuel_dash, fuel_walk_quiet, fuel_dash_quiet, exp_walk, exp_dash;
    int queries = 0;
    for (int attempt = 0; attempt < 400 && queries < 20; ++attempt) {
        const vec2 start = open[static_cast<std::size_t>(rnd(static_cast<int>(open.size())))];
        // A goal 10-30 king steps away.
        vec2 goal{-1, -1};
        for (int tries = 0; tries < 50; ++tries) {
            const vec2 c = open[static_cast<std::size_t>(rnd(static_cast<int>(open.size())))];
            const int d = std::max(std::abs(c.x - start.x), std::abs(c.y - start.y));
            if (d >= 10 && d <= 30) { goal = c; break; }
        }
        if (goal.x < 0) continue;
        goals.clear();
        goals.set(goal);
        walk_field.compute(walls, goals, visited);
        if (walk_field.get(start) == router::unreachable) continue;
        dash_field.compute(dash_walls, goals, visited);
        // Awake: the striking groups with a member within 8 of the start, up to 3 tracked.
        std::vector<router::Camp> camps;
        int tracked[64];
        std::fill(tracked, tracked + 64, -1);
        int ngroups = 0;
        for (const auto& m : members) {
            if (std::max(std::abs(m.pos.x - start.x), std::abs(m.pos.y - start.y)) > 8 + m.reach) continue;
            int gi = -1;
            if (m.group < 64) {
                if (tracked[m.group] < 0 && ngroups < router::max_groups) tracked[m.group] = ngroups++;
                gi = tracked[m.group];
            }
            camps.push_back({m.pos, m.reach, m.damage * 8 / 40, gi});
        }
        // Danger: an enemy's reach square (radius 3) around a tile near the midpoint.
        danger.clear();
        const vec2 mid{(start.x + goal.x) / 2 + rnd(5) - 2, (start.y + goal.y) / 2 + rnd(5) - 2};
        danger.draw_chebyshev(mid, 3.0f);
        {
            static bitboard creach, cedge, eedge, t1;
            creach.clear();
            for (const auto& m : camps) creach.draw_chebyshev(m.pos, static_cast<float>(m.reach));
            cedge.clear();
            for (const auto& m : camps) cedge.draw_chebyshev(m.pos, static_cast<float>(m.reach + 1));
            cedge &= ~creach;
            eedge.clear();
            eedge.draw_chebyshev(mid, 4.0f);
            eedge &= ~danger;
            const peer::Boards wb{&danger, &eedge, &creach, &cedge};
            const auto before = cambc::fuel_remaining();
            (void)peer::route(start, walls, walk_field, wb);
            fuel_peer.push_back(static_cast<int>(before - cambc::fuel_remaining()));
        }
        {
            static bitboard soft;
            soft = danger;
            for (const auto& m : camps) soft.draw_chebyshev(m.pos, static_cast<float>(m.reach));
            ++map_info::turn;
            const auto before = cambc::fuel_remaining();
            bool gave = false;
            const int d = pathgrid::cba::search(start, goals, camp_tiles, soft, &gave);
            int best = -1;
            for (int dy = -1; dy <= 1; ++dy)
                for (int dx = -1; dx <= 1; ++dx)
                    if (dx || dy) {
                        const int v = pathgrid::cba::dist_of(start.x + dx, start.y + dy);
                        if (v >= 0 && (best < 0 || v < best)) best = v;
                    }
            fuel_cba.push_back(static_cast<int>(before - cambc::fuel_remaining()));
            if (d < 0) std::printf("PL cba none %d %d gave %d\n", start.x, start.y, gave);
            static bitboard none;
            ++map_info::turn;
            const auto b2 = cambc::fuel_remaining();
            const int d2 = pathgrid::cba::search(start, goals, camp_tiles, none, &gave);
            fuel_cba_quiet.push_back(static_cast<int>(b2 - cambc::fuel_remaining()));
            static cambc::distance_field hf;
            static bitboard hroot, hscratch;
            hroot.clear();
            hroot.set(start);
            const auto b3 = cambc::fuel_remaining();
            hf.compute(map_info::static_block, hroot, hscratch, static_cast<std::uint16_t>(std::min(W + H, std::max(32, 30 + 24))));
            fuel_field.push_back(static_cast<int>(b3 - cambc::fuel_remaining()));
            walk_d.push_back(d2);
            // Windowed: goals inside a radius-8 square and its ring as seeds (the ring at its host steps),
            // everything outside the square hard.
            {
                static bitboard sq, inner, hard_w, seeds;
                const auto b4 = cambc::fuel_remaining();
                sq.clear();
                sq.draw_chebyshev(start, 8.0f);
                inner.clear();
                inner.draw_chebyshev(start, 7.0f);
                seeds = sq;
                seeds &= ~inner;
                {
                    bitboard g = goals;
                    g &= sq;
                    seeds |= g;
                }
                hard_w = ~sq;
                hard_w |= camp_tiles;
                for (auto& t : prof::total) t = 0;
                pathgrid::cba::seed_offsets = &walk_field;
                pathgrid::cba::scan_cx0 = std::max(0, (start.x - 8) >> 3), pathgrid::cba::scan_cx1 = std::min((W - 1) >> 3, (start.x + 8) >> 3);
                pathgrid::cba::scan_cy0 = std::max(0, (start.y - 8) >> 3), pathgrid::cba::scan_cy1 = std::min((H - 1) >> 3, (start.y + 8) >> 3);
                pathgrid::cba::chebyshev_h = true;
                ++map_info::turn;
                const int d3 = pathgrid::cba::search(start, seeds, hard_w, soft, &gave);
                pathgrid::cba::seed_offsets = nullptr;
                pathgrid::cba::scan_cx0 = -1;
                pathgrid::cba::chebyshev_h = false;
                fuel_cba_window.push_back(static_cast<int>(b4 - cambc::fuel_remaining()));
                for (int i = 0; i < prof::COUNT; ++i) prof_window[i] += prof::total[i];
                if (d3 >= 0 && d >= 0 && d3 != d) ++window_mismatch;
            }
        }
        {
            // bitroute: exact turn states in a 15x15 window.
            static bitboard eedge2;
            eedge2.clear();
            eedge2.draw_chebyshev(mid, 4.0f);
            eedge2 &= ~danger;
            std::vector<bitroute::Camp> bc;
            std::array<int, bitroute::max_groups> dmg{};
            std::array<int, bitroute::max_groups> cnt{};
            for (const auto& c : camps) {
                bc.push_back({c.pos, c.reach, c.group < bitroute::max_groups ? c.group : -1});
                if (c.group >= 0 && c.group < bitroute::max_groups) dmg[c.group] += c.damage, ++cnt[c.group];
            }
            for (int j = 0; j < bitroute::max_groups; ++j) dmg[j] = cnt[j] ? std::max(1, (dmg[j] / cnt[j] + 2) / 4) : 1;
            for (const bool dasher : {false, true}) {
                bitroute::Query q;
                q.start = start;
                q.walls = &walls;
                q.solid = &solid;
                q.goals = &goals;
                q.danger = &danger;
                q.edge = &eedge2;
                q.tail = dasher ? &dash_field : &walk_field;
                q.camps = bc;
                q.groups = std::min(ngroups, bitroute::max_groups);
                q.damage = dmg;
                q.dasher = dasher;
                q.cooldown = 0;
                const auto b5 = cambc::fuel_remaining();
                const auto plan = bitroute::route(q);
                (dasher ? fuel_bit_dash : fuel_bit_walk).push_back(static_cast<int>(b5 - cambc::fuel_remaining()));
                (dasher ? bk_dash : bk_walk).push_back(plan.buckets);
                if (!plan.found) ++bit_notfound;
            }
        }
        {
            static bitboard creach2, eedge3;
            creach2.clear();
            for (const auto& c : camps) creach2.draw_chebyshev(c.pos, static_cast<float>(c.reach));
            eedge3.clear();
            eedge3.draw_chebyshev(mid, 4.0f);
            for (const bool dasher : {false, true}) {
                winroute::Query q;
                q.start = start;
                q.walls = &walls;
                q.solid = dasher ? &solid : nullptr;
                q.goals = &goals;
                q.steps = &walk_field;
                q.weights[0] = {&danger, 3};
                q.weights[1] = {&creach2, 4};
                q.weights[2] = {&eedge3, 1};
                q.n_weights = 3;
                q.dash_cost = dasher ? 6 : 0;
                const auto b6 = cambc::fuel_remaining();
                const auto r = winroute::route(q);
                (dasher ? fuel_win_dash : fuel_win_walk).push_back(static_cast<int>(b6 - cambc::fuel_remaining()));
                (dasher ? lv_dash : lv_walk).push_back(r.levels);
                {
                    localroute::Query lq;
                    lq.start = start;
                    lq.walls = &walls;
                    lq.solid = dasher ? &solid : nullptr;
                    lq.goals = &goals;
                    lq.steps = &walk_field;
                    lq.weights[0] = {&danger, 3};
                    lq.weights[1] = {&creach2, 4};
                    lq.weights[2] = {&eedge3, 1};
                    lq.n_weights = 3;
                    lq.dash_cost = dasher ? 6 : 0;
                    const auto b7 = cambc::fuel_remaining();
                    const auto lr = localroute::route(lq);
                    (dasher ? fuel_loc_dash : fuel_loc_walk).push_back(static_cast<int>(b7 - cambc::fuel_remaining()));
                    if (!lr.found) ++loc_notfound;
                }
                if (!r.found) ++win_notfound;
                else if (!dasher) {
                    // A first step must exist among the 8 neighbours.
                    bool step = false;
                    for (int dy = -1; dy <= 1; ++dy)
                        for (int dx = -1; dx <= 1; ++dx)
                            if ((dx || dy) && r.at(dx, dy) >= 0 && r.at(dx, dy) < r.cost) step = true;
                    if (!step) ++win_nostep;
                }
            }
        }
        for (int variant = 0; variant < 4; ++variant) {
            const bool dasher = variant & 1, quiet = variant & 2;
            router::Query q;
            q.start = start;
            q.walls = &walls;
            q.solid = &solid;
            q.goals = &goals;
            q.danger = quiet ? nullptr : &danger;
            q.tail = dasher ? &dash_field : &walk_field;
            q.camps = quiet ? std::span<const router::Camp>{} : std::span<const router::Camp>{camps};
            q.groups = quiet ? 0 : ngroups;
            q.dasher = dasher;
            q.cooldown = 0;
            q.horizon = 12;
            q.turn_cost = 8;
            q.danger_cost = 12;
            const auto before = cambc::fuel_remaining();
            const auto plan = router::route(q);
            const int used = static_cast<int>(before - cambc::fuel_remaining());
            (quiet ? (dasher ? fuel_dash_quiet : fuel_walk_quiet) : (dasher ? fuel_dash : fuel_walk)).push_back(used);
            if (!quiet) (dasher ? exp_dash : exp_walk).push_back(plan.expanded);
            if (!plan.found) std::printf("PL notfound %d %d -> %d %d dasher %d\n", start.x, start.y, goal.x, goal.y, dasher);
            if (queries < 3) std::printf("PL q%d v%d fuel %d expanded %d generated %d left %llu\n", queries, variant, used, plan.expanded, plan.generated, static_cast<unsigned long long>(cambc::fuel_remaining()));
        }
        ++queries;
    }
    // Fixed and per-expansion costs: start on the goal, then horizons 1, 2, 4 with nothing nearby.
    {
        const vec2 start = open[open.size() / 2];
        goals.clear();
        goals.set(start);
        walk_field.compute(walls, goals, visited);
        for (int h : {0, 1, 2, 4}) {
            router::Query q;
            q.start = start;
            q.walls = &walls;
            q.solid = &solid;
            q.goals = &goals;
            q.tail = &walk_field;
            q.horizon = h;
            if (h > 0) {
                // A goal far away so the horizon stops the search.
                goals.clear();
                goals.set(open[0]);
                walk_field.compute(walls, goals, visited);
            }
            const auto before = cambc::fuel_remaining();
            const auto plan = router::route(q);
            std::printf("PL probe horizon %d fuel %d expanded %d generated %d\n", h, static_cast<int>(before - cambc::fuel_remaining()), plan.expanded, plan.generated);
        }
        std::printf("PL prof ends %lld costs %lld offer %lld pop %lld\n", router::detail_::prof[0], router::detail_::prof[1], router::detail_::prof[2], router::detail_::prof[3]);
        const auto b2 = cambc::fuel_remaining();
        const auto b3 = cambc::fuel_remaining();
        std::printf("PL probe fuel_remaining call %d\n", static_cast<int>(b2 - b3));
    }
    const auto summary = [](const char* name, std::vector<int> v) {
        if (v.empty()) return;
        std::sort(v.begin(), v.end());
        long long sum = 0;
        for (int x : v) sum += x;
        std::printf("PL %s n %zu mean %lld median %d p90 %d max %d\n", name, v.size(), sum / static_cast<long long>(v.size()),
                    v[v.size() / 2], v[v.size() * 9 / 10], v.back());
    };
    std::printf("PL map %dx%d queries %d\n", W, H, queries);
    summary("fuel_cba", fuel_cba);
    summary("fuel_cba_window", fuel_cba_window);
    std::printf("PL window_mismatch %d bit_notfound %d\n", window_mismatch, bit_notfound);
    std::printf("PL win_notfound %d win_nostep %d\n", win_notfound, win_nostep);
    std::printf("PL win_prof masks %lld seeds %lld levels %lld (per query)\n", winroute::prof[0] / 40, winroute::prof[1] / 40, winroute::prof[2] / 40);
    std::printf("PL loc_notfound %d\n", loc_notfound);
    summary("fuel_loc_walk", fuel_loc_walk);
    summary("fuel_loc_dash", fuel_loc_dash);
    summary("fuel_win_walk", fuel_win_walk);
    summary("fuel_win_dash", fuel_win_dash);
    summary("levels_walk", lv_walk);
    summary("levels_dash", lv_dash);
    summary("fuel_bit_walk", fuel_bit_walk);
    summary("fuel_bit_dash", fuel_bit_dash);
    summary("buckets_walk", bk_walk);
    summary("buckets_dash", bk_dash);
    for (int i = 0; i < prof::COUNT; ++i) std::printf("PL prof_window %s %llu\n", prof::names[i], static_cast<unsigned long long>(prof_window[i] / 20));
    summary("fuel_cba_quiet", fuel_cba_quiet);
    summary("fuel_heuristic_field", fuel_field);
    summary("walk_distance", walk_d);
    summary("fuel_peer_window", fuel_peer);
    summary("fuel_walk", fuel_walk);
    summary("fuel_dash", fuel_dash);
    summary("fuel_walk_quiet", fuel_walk_quiet);
    summary("fuel_dash_quiet", fuel_dash_quiet);
    summary("expanded_walk", exp_walk);
    summary("expanded_dash", exp_dash);
}

} // namespace

int main() {
    bool done = false;
    while (true) {
        try {
            if (cambc::is_draft()) {
                for (const auto c : {cambc::champion_draft::vesper_vale, cambc::champion_draft::ryth, cambc::champion_draft::varg,
                                     cambc::champion_draft::willow, cambc::champion_draft::tavi}) {
                    try {
                        cambc::draft::pick(c);
                        break;
                    } catch (const cambc::error&) {
                    }
                }
            } else if (!done && cambc::self().champion_name() == cambc::champion_type::vesper_vale) {
                std::printf("PL team %d fuel %llu\n", static_cast<int>(cambc::detail::cached_my_team), static_cast<unsigned long long>(cambc::fuel_remaining()));
                done = true;
                bench();
            }
        } catch (const std::exception& e) {
            std::printf("PL error %s\n", e.what());
        }
        cambc::end_turn();
    }
}
