// Altar control (research/ideas-2026-11-05/altar.md): on a one-altar map, when the enemy is near the
// win and well ahead, or while one of us carries a winning bag, our strongest bodies hold the altar,
// where a kill takes the bag, while the rest farm and bank there.
#include "../bot_parts.h"

namespace aph {

namespace {

// The altar held: the only one; -1 on a map with several or none.
int guarded_altar(const World& world) { return world.map().altars.size() == 1 ? 0 : -1; }

// A body of ours carries a winning bag (as seen, else as posted): its long channel is cancelled by any
// enemy stun or lock that reaches it.
bool escorting(const World& world) {
    if (world.map().altars.size() != 1) return false;
    int best = 0;
    for (const auto& a : world.allies)
        if (a.alive) best = std::max(best, a.is_self ? static_cast<int>(my_gems()) : a.visible ? a.gems : comms::bag_of(world, a.index));
    return world.score.ally + best >= static_cast<int>(cambc::constants::winning_gems);
}

// Scores are read by every body alike, so the team agrees without comms.
bool guarding(const World& world) {
    static bool on = false;
    const int lead = world.score.enemy - world.score.ally;
    if (!on) on = world.score.enemy >= params::altar_enemy_min && lead >= params::altar_gap;
    else if (lead < params::altar_gap_off) on = false;
    return (on || escorting(world)) && guarded_altar(world) >= 0;
}

// Fighting weight by type: a linked pair last, since one death hands over both bags.
float guard_power(const ChampionBelief& c) {
    const auto& f = c.facts();
    const float p = f.health.base * f.strength.base;
    return f.passive == Passive::linked_pair ? p * 0.25f : p;
}

// Our rank among living allies by guard_power (ties by index), or -1 past params::altar_guards.
int guard_rank(const World& world) {
    const auto& me = world.me();
    const float mine = guard_power(me);
    int rank = 0;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive) continue;
        const float p = guard_power(a);
        rank += p > mine || (p == mine && a.index < me.index);
    }
    int alive = 0;
    for (const auto& a : world.allies) alive += a.alive;
    return rank < std::min(params::altar_guards, alive - params::altar_farmers_min) ? rank : -1;
}

// Stand tiles by the guarded altar, best first: out of every camp member's reach (unless none is),
// bushes first (unseen from outside, and attacking from one does not reveal us), then nearer the
// altar, then nearer our spawn.
const std::vector<vec2>& stands(const World& world, int a) {
    static std::vector<vec2> tiles;
    static int built = -1;
    if (built == a) return tiles;
    built = a;
    tiles.clear();
    const auto& map = world.map();
    const vec2 alt = map.altars[a].pos;
    const auto in_camp_reach = [&](vec2 p) {
        for (const auto& g : map.groups)
            for (const auto& m : g.members)
                if (m.strength > 0 && dist(m.pos, p) <= m.reach) return true;
        return false;
    };
    struct Scored {
        int score;
        vec2 p;
    };
    std::vector<Scored> all, safe;
    const int r = params::altar_stand_radius;
    for (int dx = -r; dx <= r; ++dx)
        for (int dy = -r; dy <= r; ++dy) {
            const vec2 p{alt.x + dx, alt.y + dy};
            if (!in_bounds(p) || !test(map.standable, p) || test(map.near_enemy_spawn, p)) continue;
            const int home = map.from_ally_spawn().at(p);
            if (home == unreachable) continue;
            const bool bush = test(map.bushes, p);
            const Scored s{(bush ? 0 : 1 << 20) + (dist(p, alt) << 12) + std::min(home, 4095), p};
            all.push_back(s);
            if (!in_camp_reach(p)) safe.push_back(s);
        }
    auto& use = safe.empty() ? all : safe;
    std::sort(use.begin(), use.end(), [](const Scored& x, const Scored& y) {
        return x.score != y.score ? x.score < y.score : (x.p.x != y.p.x ? x.p.x < y.p.x : x.p.y < y.p.y);
    });
    for (const auto& s : use) tiles.push_back(s.p);
    return tiles;
}

// Our lock on the guarded altar is kept up while guarding (place_lock counts it as our side).
bool keep_guard_lock(const World& world, int a) { return guarding(world) && a == guarded_altar(world); }

// A guard's turn after the bag and the shop: fight an enemy by the altar (chase prices it), else hold
// our stand tile. False for a non-guard or when not guarding.
bool guard_turn(const World& world, Pathing& pathing, Safety& safety, Memory& memory, const Pathing::GuardState& strike_guard) {
    if (!guarding(world)) return false;
    const int rank = guard_rank(world);
    if (rank < 0) return false;
    const int a = guarded_altar(world);
    const auto& tiles = stands(world, a);
    if (tiles.empty()) return false;
    memory.claim = -1;
    memory.farm_group = -1;
    const vec2 alt = world.map().altars[a].pos;
    bool near = false;
    for (const auto& e : world.enemies) near |= e.alive && e.visible && dist(e.pos, alt) <= params::altar_leash;
    if (near) {
        const auto work_guard = pathing.held_guard();
        pathing.restore_guard(strike_guard);
        if (chase(world, pathing, safety)) return true;
        strike_guard_known(pathing, my_position());
        pathing.restore_guard(work_guard);
    }
    decision = Branch::guard_altar;
    const int i = rank % static_cast<int>(tiles.size());
    const vec2 stand = tiles[static_cast<std::size_t>(i)];
    if (!my_can_move() || my_position() == stand) return true;
    static std::vector<std::optional<Field>> fields;
    if (fields.size() < tiles.size()) fields.resize(tiles.size());
    auto& field = fields[static_cast<std::size_t>(i)];
    if (!field) {
        static bitboard goal{cambc::uninitialized};
        clear_board(goal);
        set_tile(goal, stand);
        field.emplace(make_field(pathing.static_walls(), goal));
    }
    step_safely(world, pathing, *field, safety);
    return true;
}

} // namespace

} // namespace aph
