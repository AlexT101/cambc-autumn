// Intercontinental Fish's camp destination (FISH_MODEL.md 7.2): a conditional logit over the
// candidate groups on team-union camp memory, weights fitted after a payout and after a spawn exit
// (research/fish-2026-11-05/farm3-fit.json, model farm3). Features as tools/fish/farm2_features.py
// computes them (sets base, hp, rate, home, stale, crew, size; gems at 3 gold, crew Strength in
// the clear time), from tools/fish/decision_data.py's candidates and routes_data.py's history.
// One walk field from our tile per decision; the static walks from both spawns once a game.
#include "../bot_parts.h"
#include "farm_memory.h"
#include <bit>

namespace aph {

namespace {

namespace fish_farm {

enum F {
    f_wait, f_logwait, f_respawn_part, f_alive_fight, f_alive_dps, f_monolith, f_golem, f_clusters_only, f_unknown, f_empty,
    f_respawning, f_gold, f_gems, f_allies_near, f_ally_recent, f_visited, f_route, f_terr, f_terr_neg, f_last, f_ally_closer,
    f_hp_fight, f_damaged, f_awake, f_part_frac, f_lograte, f_logworth, f_logR, f_logshare, f_enemy_near, f_empty_age,
    f_resp_expired, f_resp_expired_age, f_alive_age, f_crew_frac, f_crew_any, f_crew_kill, f_n_types, f_has_elk, f_wolves,
    f_gold_only, f_count
};
constexpr float payout_w[f_count] = {
    0.0503556049f, -2.61032613f, -1.0273997f, -0.446703324f, 0.4609616f, -2.1826838f, -0.557692026f, 0.225529676f,
    -0.959514382f, -3.73269155f, 0.720371779f, -0.552687945f, 0.00937057332f, -0.114452068f, -0.568233892f, 0.378915928f,
    0.655616931f, -0.253799149f, -0.113497734f, 0.0f, 0.45669365f, -0.0814690413f, 0.373777819f, 0.70193729f,
    -1.65783697f, -1.40030195f, 4.15614667f, -3.61708054f, 2.4455346f, -0.816121024f, 0.278459423f, -0.0403435885f,
    -0.255744127f, -0.294250958f, -0.155961098f, -0.302469519f, 0.00589948873f, -0.468858857f, 0.502496055f,
    -0.0156509693f, -0.391091465f};
constexpr float spawn_w[f_count] = {
    0.10925852f, -2.10250914f, -1.65467304f, -0.0199053182f, 0.358805718f, -0.182124173f, -0.00635804317f, 1.1811872f,
    -1.1355581f, -3.37805415f, 0.76884671f, -0.306402031f, -0.000335084674f, 0.0500294743f, -0.599935746f, 0.589625159f,
    0.592423036f, -1.2245083f, 0.274222111f, 0.313796126f, 0.452624227f, -0.394601719f, 0.644472297f, 0.22762229f,
    -1.00929927f, 0.987910694f, 0.994706808f, 0.519311568f, 0.00912288592f, -1.24809162f, 0.343811956f, -0.0568748441f,
    -0.410175614f, -0.538321894f, -0.118537467f, -0.217847737f, 0.0192258592f, -0.00522241874f, 0.671358647f,
    0.157935625f, -0.713353098f};

constexpr int no_walk = 999; // the features' "no walk"
constexpr float gem_gold = 3.0f;
constexpr int crew_radius = 4, near_radius = 3, recent_rounds = 10;
constexpr int scored = 20;        // candidates priced in full, soonest ready first
constexpr int walk_horizon = 80;  // the decision's walk field stops here: farther groups are no candidates

// Static per group, made once a game.
struct GroupStatic {
    int approach_first = 0, approach_count = 0; // its approach tiles (8-neighbours off its own tiles) in `approach`
    int from_us = no_walk, from_them = no_walk; // static walks from each spawn to an approach tile, every camp tile a wall
    int terr = 0;                               // Chebyshev to our spawn less to theirs, nearest camp tiles
    float fighter_hp = 0, fighter_strength = 0, full_hp = 0;
    int x0 = 0, x1 = 0, y0 = 0, y1 = 0; // its camp tiles' box
    int members = 0;
    bool monolith = false, golem = false, elk = false, wolf = false;
    float base[2][2] = {}; // [reason][alive]: the score of the features fixed by the group
};
struct Statics {
    bool ready = false;
    std::vector<GroupStatic> groups;
    std::vector<std::uint32_t> approach; // row-major tile indices
    float horizon = 100;
};
Statics statics;

// A field's distances row-major, read in our own code: a host read per tile costs ~27.
std::vector<std::uint16_t>& linear() {
    static std::vector<std::uint16_t> v;
    return v;
}
void export_field(const cambc::distance_field& f) {
    auto& v = linear();
    const std::size_t n = static_cast<std::size_t>(cambc::map::width()) * static_cast<std::size_t>(cambc::map::height());
    if (v.size() != n) v.resize(n);
    f.export_linear_buffer({v.data(), n});
}
inline int walk_at(std::uint32_t i) {
    const int d = linear()[i];
    return d >= no_walk ? no_walk : d;
}

// ln x for x > 0, within ~1e-6 relative: libm's costs far more, and a decision takes three a group.
inline float fast_log(float x) {
    const auto i = std::bit_cast<std::uint32_t>(x);
    const int e = static_cast<int>(i >> 23 & 255) - 127;
    const float m = std::bit_cast<float>((i & 0x7fffffu) | 0x3f800000u); // [1, 2)
    const float t = (m - 1) / (m + 1), t2 = t * t;                        // [0, 1/3)
    return 2 * t * (1 + t2 * (1.0f / 3 + t2 * (1.0f / 5 + t2 * (1.0f / 7 + t2 / 9)))) + static_cast<float>(e) * 0.693147181f;
}

// Chebyshev distance from p to a box.
inline int box_dist(vec2 p, int x0, int x1, int y0, int y1) {
    const int dx = std::max({x0 - p.x, 0, p.x - x1}), dy = std::max({y0 - p.y, 0, p.y - y1});
    return std::max(dx, dy);
}
inline int tiles_dist(const CampGroup& G, vec2 p) {
    int d = 1 << 20;
    for (const auto& m : G.members) d = std::min(d, dist(p, m.pos));
    return d;
}

// The features fixed by the group (and whether it is alive or unknown).
void static_features(const GroupStatic& st, const CampGroup& G, bool alive, std::array<float, f_count>& f) {
    f[f_alive_dps] = alive ? st.fighter_strength / 100 : 0.0f;
    f[f_monolith] = alive && st.monolith;
    f[f_golem] = alive && st.golem;
    f[f_clusters_only] = st.fighter_hp <= 0;
    f[f_gold] = static_cast<float>(G.gold) / 100;
    f[f_gems] = static_cast<float>(G.gems) / 10;
    f[f_terr] = static_cast<float>(std::max(0, st.terr)) / 10;
    f[f_terr_neg] = static_cast<float>(std::max(0, -st.terr)) / 10;
    f[f_logworth] = fast_log(1 + static_cast<float>(G.gems) * gem_gold + static_cast<float>(G.gold));
    const int us = st.from_us, them = st.from_them;
    const float share = us < no_walk && them < no_walk
                            ? std::min(1.0f, 2.0f * static_cast<float>(them) / static_cast<float>(std::max(1, us + them)))
                            : 1.0f;
    f[f_logshare] = fast_log(std::max(share, 0.05f));
    f[f_enemy_near] = them < no_walk && them <= us;
    f[f_n_types] = static_cast<float>(st.members) / 5;
    f[f_has_elk] = alive && st.elk;
    f[f_wolves] = alive && st.wolf;
    f[f_gold_only] = G.gems == 0;
}

[[gnu::noinline]] void build_statics(const World& world) {
    const auto& map = world.map();
    const int W = map.width;
    static cambc::distance_field field;
    static bitboard walls{cambc::uninitialized}, roots{cambc::uninitialized}, visited{cambc::uninitialized};
    or_into(map.blocked_for_us, map.camp_tiles, walls);
    copy_into(map.ally_spawn, roots);
    field.compute(walls, roots, visited);
    export_field(field);
    int ax0 = 1 << 20, ax1 = -1, ay0 = 1 << 20, ay1 = -1, ex0 = 1 << 20, ex1 = -1, ey0 = 1 << 20, ey1 = -1;
    for (const auto p : map.ally_spawn_tiles) {
        ax0 = std::min(ax0, p.x), ax1 = std::max(ax1, p.x), ay0 = std::min(ay0, p.y), ay1 = std::max(ay1, p.y);
        const vec2 q = map.mirror(p);
        ex0 = std::min(ex0, q.x), ex1 = std::max(ex1, q.x), ey0 = std::min(ey0, q.y), ey1 = std::max(ey1, q.y);
    }
    const auto& groups = map.groups;
    statics.groups.assign(groups.size(), GroupStatic{});
    statics.approach.clear();
    statics.approach.reserve(groups.size() * 24);
    // By tile, the group whose approach tiles hold it, + 1: static storage starts zeroed for free.
    static std::array<std::uint16_t, 100 * 100> stamp{};
    for (std::size_t g = 0; g < groups.size(); ++g) {
        const auto& G = groups[g];
        auto& s = statics.groups[g];
        s.members = static_cast<int>(G.members.size());
        s.x0 = s.y0 = 1 << 20, s.x1 = s.y1 = -1;
        int to_us = 1 << 20, to_them = 1 << 20;
        for (const auto& m : G.members) {
            s.x0 = std::min(s.x0, m.pos.x), s.x1 = std::max(s.x1, m.pos.x), s.y0 = std::min(s.y0, m.pos.y), s.y1 = std::max(s.y1, m.pos.y);
            s.full_hp += m.max_health;
            if (m.strength > 0) s.fighter_hp += m.max_health, s.fighter_strength += m.strength;
            using T = cambc::camp_type;
            s.monolith |= m.type == T::monolith, s.golem |= m.type == T::golem, s.elk |= m.type == T::elk, s.wolf |= m.type == T::wolf;
            to_us = std::min(to_us, box_dist(m.pos, ax0, ax1, ay0, ay1));
            to_them = std::min(to_them, box_dist(m.pos, ex0, ex1, ey0, ey1));
        }
        s.terr = to_us - to_them;
        s.approach_first = static_cast<int>(statics.approach.size());
        for (const auto& m : G.members)
            for (const auto d : directions) {
                const vec2 q = m.pos + d;
                if (q.x < 0 || q.y < 0 || q.x >= map.width || q.y >= map.height || map.group_at(q) == static_cast<int>(g)) continue;
                const auto i = static_cast<std::uint32_t>(q.x + q.y * W);
                if (stamp[i] == g + 1) continue;
                stamp[i] = static_cast<std::uint16_t>(g + 1);
                statics.approach.push_back(i);
                s.from_us = std::min(s.from_us, walk_at(i));
                const vec2 mq = map.mirror(q);
                s.from_them = std::min(s.from_them, walk_at(static_cast<std::uint32_t>(mq.x + mq.y * W)));
            }
        s.approach_count = static_cast<int>(statics.approach.size()) - s.approach_first;
    }
    statics.horizon = 100.0f * std::max(1.0f, static_cast<float>(std::max(map.width, map.height)) / 50.0f);
    for (std::size_t g = 0; g < groups.size(); ++g) {
        auto& st = statics.groups[g];
        for (int alive = 0; alive < 2; ++alive) {
            std::array<float, f_count> f{};
            static_features(st, groups[g], alive != 0, f);
            for (int reason = 0; reason < 2; ++reason) {
                const float* w = reason == 1 ? spawn_w : payout_w;
                float b = 0;
                for (int k = 0; k < f_count; ++k) b += w[k] * f[static_cast<std::size_t>(k)];
                st.base[reason][alive] = b;
            }
        }
    }
    statics.ready = true;
}

struct Choice {
    int group = -1;
    float score = 0;
    int walk = no_walk;
    // For the payout forecast (ECONOMY.md 3): over the other groups, the least max(walk, respawn
    // wait), that group's walk, and how many are ready within 10.
    int ready = no_walk, ready_walk = no_walk, n_ready10 = 0;
    int candidates = 0;
};

struct AllyNear {
    vec2 pos;
    float strength;
    bool home;
};

// reason 0: after a payout (also every other decision in the field), 1: after a spawn exit.
// `origin`: the group a payout or a capture we left was on (route), -1 from spawn. `exclude`: the
// group just paid out or left, not a candidate.
[[gnu::noinline]] Choice choose(const World& world, int reason, int origin, int exclude) {
    world.throw_if_stale();
    const std::uint64_t fuel_at = fuel();
    if (!statics.ready) build_statics(world);
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int W = map.width;
    auto& mem = fish::memory_of(world);
    const vec2 here = my_position();
    const int round = world.round;
    // The walk from here, visible living camps blocking (decision_data.py's `blocked`).
    static cambc::distance_field field;
    static bitboard walls{cambc::uninitialized}, roots{cambc::uninitialized}, visited{cambc::uninitialized};
    or_into(map.blocked_for_us, live_camp_tiles(), walls);
    clear_board(roots);
    set_tile(roots, here);
    set_tile(walls, here, false);
    const std::uint64_t fuel_pre = fuel();
    field.compute(walls, roots, visited, walk_horizon);
    const std::uint64_t fuel_field = fuel();
    export_field(field);
    const std::uint64_t fuel_export = fuel();
    const float S = std::max(1.0f, my_strength());
    std::array<AllyNear, 16> allies;
    int n_allies = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && n_allies < static_cast<int>(allies.size()))
            allies[static_cast<std::size_t>(n_allies++)] = {a.pos, a.strength, test(map.ally_spawn, a.pos)};
    const float* w = reason == 1 ? spawn_w : payout_w;
    Choice best;
    std::array<float, f_count> f{};
    // First the walks and waits: only the `scored` soonest ready are priced in full (a median 15
    // candidates in Fish's rows; the rest sit far behind on wait).
    static std::vector<int> walks, waits;
    const int n_groups = static_cast<int>(groups.size());
    walks.assign(static_cast<std::size_t>(n_groups), no_walk);
    waits.clear();
    for (int g = 0; g < n_groups; ++g) {
        if (g == exclude) continue;
        const auto& st = statics.groups[static_cast<std::size_t>(g)];
        bool from_team = false;
        const auto& s = fish::union_sighting(mem, g, from_team);
        const int state = s.round >= 0 ? s.state : fish::st_unknown;
        int walk = no_walk;
        if (state == fish::st_unknown || state == fish::st_alive) {
            for (int k = 0; k < st.approach_count; ++k) walk = std::min(walk, walk_at(statics.approach[static_cast<std::size_t>(st.approach_first + k)]));
        } else {
            for (const auto& m : groups[g].members) walk = std::min(walk, walk_at(static_cast<std::uint32_t>(m.pos.x + m.pos.y * W)));
        }
        if (walk >= no_walk) continue;
        walks[static_cast<std::size_t>(g)] = walk;
        const int respawn = state == fish::st_respawning ? std::max(0, s.respawn_round - round) : 0;
        const int wait = std::max(walk, respawn);
        if (wait < best.ready || (wait == best.ready && walk < best.ready_walk)) best.ready = wait, best.ready_walk = walk;
        best.n_ready10 += wait <= 10;
        ++best.candidates;
        waits.push_back(wait);
    }
    int cutoff = no_walk;
    if (static_cast<int>(waits.size()) > scored) {
        std::nth_element(waits.begin(), waits.begin() + (scored - 1), waits.end());
        cutoff = waits[static_cast<std::size_t>(scored - 1)];
    }
    for (int g = 0; g < n_groups; ++g) {
        const int walk = walks[static_cast<std::size_t>(g)];
        if (walk >= no_walk) continue;
        const auto& G = groups[g];
        const auto& st = statics.groups[static_cast<std::size_t>(g)];
        bool from_team = false;
        const auto& s = fish::union_sighting(mem, g, from_team);
        const int state = s.round >= 0 ? s.state : fish::st_unknown;
        const bool alive = state == fish::st_unknown || state == fish::st_alive;
        const int respawn = state == fish::st_respawning ? std::max(0, s.respawn_round - round) : 0;
        const int wait = std::max(walk, respawn);
        if (wait > cutoff) continue;
        const int age = s.round >= 0 ? round - s.round : 0;
        // Remembered live health and wakefulness: ours, unless the team's newer sighting changed the state.
        float hp_left = 0;
        bool awake = false;
        if (alive) {
            const auto& c = world.camps[static_cast<std::size_t>(g)];
            const bool own_alive = mem.own[static_cast<std::size_t>(g)].round >= 0 && mem.own[static_cast<std::size_t>(g)].state == fish::st_alive;
            if (state == fish::st_alive && own_alive && (!from_team || mem.team[static_cast<std::size_t>(g)].state == fish::st_alive)
                && c.state == CampState::alive) {
                for (std::size_t i = 0; i < G.members.size(); ++i) {
                    const float h = c.health[i];
                    hp_left += h < 0 ? G.members[i].max_health : h;
                }
                awake = c.awake != Awake::asleep;
            } else {
                hp_left = st.full_hp;
            }
        }
        // Allies in sight: crew within 4 (off spawn), any within 3, an off-spawn one nearer the group.
        const int mine = tiles_dist(G, here);
        float crew = 0;
        int n_crew = 0, n_near = 0;
        bool closer = false;
        for (int k = 0; k < n_allies; ++k) {
            const auto& a = allies[static_cast<std::size_t>(k)];
            const int lower = box_dist(a.pos, st.x0, st.x1, st.y0, st.y1);
            if (lower > crew_radius && (a.home || lower >= mine)) continue;
            const int d = tiles_dist(G, a.pos);
            n_near += d <= near_radius;
            if (!a.home && d <= crew_radius) crew += a.strength, ++n_crew;
            closer |= !a.home && d < mine;
        }
        const float worth = static_cast<float>(G.gems) * gem_gold + static_cast<float>(G.gold);
        const auto kill_rounds = [&](float strength) {
            return state == fish::st_empty ? 0.0f : state == fish::st_respawning ? st.full_hp / strength : hp_left / strength;
        };
        const float kill = kill_rounds(S + crew);
        const float R = std::max(1.0f, static_cast<float>(wait) + kill + (state == fish::st_empty ? 0.0f : 7.0f));
        const float logworth = fast_log(1 + worth);
        f[f_wait] = static_cast<float>(wait) / 10;
        f[f_logwait] = fast_log(1 + static_cast<float>(wait));
        f[f_respawn_part] = static_cast<float>(std::max(0, respawn - walk)) / 10;
        f[f_alive_fight] = alive ? st.fighter_hp / S / 100 : 0.0f;
        f[f_unknown] = state == fish::st_unknown;
        f[f_empty] = state == fish::st_empty;
        f[f_respawning] = state == fish::st_respawning;
        f[f_allies_near] = static_cast<float>(n_near);
        f[f_ally_recent] = mem.ally_last[static_cast<std::size_t>(g)] >= 0 && round - mem.ally_last[static_cast<std::size_t>(g)] <= recent_rounds;
        f[f_visited] = mem.visits[static_cast<std::size_t>(g)] > 0;
        f[f_route] = mem.route(origin, g);
        f[f_last] = g == mem.last_group;
        f[f_ally_closer] = closer;
        f[f_hp_fight] = alive ? hp_left / S / 100 : 0.0f;
        f[f_damaged] = alive && hp_left < st.full_hp - 1;
        f[f_awake] = alive && awake;
        f[f_part_frac] = alive ? 1.0f - hp_left / std::max(1.0f, st.full_hp) : 0.0f;
        const float logR = fast_log(R);
        f[f_lograte] = logworth - logR - fast_log(1 + R / statics.horizon);
        f[f_logR] = logR;
        f[f_empty_age] = state == fish::st_empty ? static_cast<float>(std::min(age, 100)) / 10 : 0.0f;
        const bool expired = state == fish::st_respawning && respawn == 0;
        f[f_resp_expired] = expired;
        f[f_resp_expired_age] = expired ? static_cast<float>(std::min(std::max(round - s.respawn_round, 0), 200)) / 50 : 0.0f;
        f[f_alive_age] = state == fish::st_alive ? static_cast<float>(std::min(age, 200)) / 50 : 0.0f;
        f[f_crew_frac] = crew / S;
        f[f_crew_any] = n_crew > 0;
        f[f_crew_kill] = alive ? (kill_rounds(S) - kill_rounds(S + crew)) / 10 : 0.0f;
        float score = st.base[reason == 1][alive];
        for (int k = 0; k < f_count; ++k) score += w[k] * f[static_cast<std::size_t>(k)];
        if (best.group < 0 || score > best.score) best.group = g, best.score = score, best.walk = walk;
    }
    debug_block({
        std::printf("FCH %d %u r%d o%d x%d -> g%d walk %d score %.2f n %d ready %d fuel %llu\n", round, my_handle(), reason, origin, exclude,
                    best.group, best.walk, static_cast<double>(best.score), best.candidates, best.ready,
                    static_cast<unsigned long long>(fuel_at - fuel()));
        std::printf("FCHF %llu %llu %llu %llu W %d H %d\n", (unsigned long long)(fuel_at - fuel_pre), (unsigned long long)(fuel_pre - fuel_field),
                    (unsigned long long)(fuel_field - fuel_export), (unsigned long long)(fuel_export - fuel()), map.width, map.height);
    });
    return best;
}

// ECONOMY.md 3's depth-4 tree after a payout: the next of farm, home and tribute (62.6% held out).
enum class Next { farm, home, tribute };
Next payout_forecast(const World& world, Pathing& pathing, const Choice& c, int payout_gems, int payout_gold) {
    const vec2 here = my_position();
    const auto walk_of = [](int d) { return d >= no_walk ? no_walk : d; };
    const int altar_walk = walk_of(pathing.to_any_altar().at(here));
    const int home_walk = walk_of(pathing.to_ally_spawn().at(here));
    if (altar_walk <= 8) {
        if (payout_gems > 6) return home_walk <= 586 || altar_walk <= 2 ? Next::tribute : Next::farm;
        return home_walk <= 8 && c.n_ready10 <= 3 ? Next::home : Next::farm;
    }
    if (payout_gold <= 74) return c.ready > 5 && home_walk <= 14 ? Next::home : Next::farm;
    return c.ready_walk <= 6 && home_walk > 6 ? Next::farm : Next::home;
}

} // namespace fish_farm

} // namespace

} // namespace aph
