// Intercontinental Fish's farm turn: the destination's decisions (FISH_MODEL.md 7.2), the camp
// attack target (7.3), holders and entry (7.4), camp micro (7.5) and the payout's home trip (8.2).
#include "farm.h"

namespace aph {

namespace {

namespace fish_farm {

fish::FarmMemory& mem(const World& world) { return fish::memory_of(world); }

float health_frac() { return my_max_health() > 0 ? my_health() / my_max_health() : 1.0f; }

// 8.2's home gate: necessary, not sufficient.
bool home_gate() { return health_frac() <= 0.63f || my_gold() >= shard_price; }

// The union state of g now, and its respawn round.
int union_state(const World& world, int g, int* respawn_round = nullptr) {
    bool from_team = false;
    const auto& s = fish::union_sighting(mem(world), g, from_team);
    if (respawn_round) *respawn_round = s.respawn_round;
    return s.round >= 0 ? s.state : fish::st_unknown;
}

// Recall turns left of a visible ally (ours as the turn started), 0 if none.
int recall_timer_of(const World& world, const ChampionBelief& a) {
    if (a.is_self) return mem(world).timer;
    if (!a.visible || a.channel != Channel::recall) return 0;
    std::int32_t t = 0;
    return cambc::detail::sdk_champion_channel_time(static_cast<std::uint32_t>(a.handle), &t) == 0 ? t : 0;
}

// The highest-ranked visible living ally but us on G's tiles (ties to the lower index), and how many.
const ChampionBelief* best_holder(const World& world, const CampGroup& G, int* count = nullptr) {
    const ChampionBelief* best = nullptr;
    int n = 0;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !in_bounds(a.pos) || !test(G.tiles(), a.pos)) continue;
        ++n;
        if (!best || fish::holder_rank(a.type) < fish::holder_rank(best->type)) best = &a;
    }
    if (count) *count = n;
    return best;
}

bool outranks(const ChampionBelief& me, const ChampionBelief& other) {
    const int a = fish::holder_rank(me.type), b = fish::holder_rank(other.type);
    return a < b || (a == b && me.index < other.index);
}

Choice decide_now(const World& world, int reason, int origin, int exclude, const char* why) {
    auto& m = mem(world);
    const auto c = choose(world, reason, origin, exclude);
    m.target = c.group, m.origin = origin, m.target_round = world.round;
    m.target_state = c.group >= 0 ? union_state(world, c.group) : fish::st_unknown;
    m.redecide = false, m.exclude = -1;
    debug_block({ std::printf("FDEC %d %u %s g%d\n", world.round, my_handle(), why, c.group); });
    return c;
}

} // namespace fish_farm

void fish_farm::drop_home() { fish::farm_memory.home = false; }

bool fish_farm::holder_stays(const World& world, Pathing& pathing, int g, vec2 here) {
    const auto& G = world.map().groups[g];
    const auto* best = best_holder(world, G);
    if (!best || outranks(world.me(), *best)) return true;
    // A lower-ranked holder (third cohort, 75%): with the best holder's recall still early, leave
    // while healthy; else leave only on an early recall of ours with room to step off.
    if (recall_timer_of(world, *best) > 3) return !(health_frac() > 0.406f);
    if (recall_timer_of(world, world.me()) <= 3) return true;
    const auto& blocked = pathing.blocked();
    int exits = 0;
    for (const auto d : directions) {
        const vec2 p = here + d;
        exits += in_bounds(p) && !test(G.tiles(), p) && !test(blocked, p);
    }
    return exits <= 3;
}

void fish_farm::events(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    (void)safety;
    auto& m = mem(world);
    fish::observe_camps(world);
    if (!world.me().alive) {
        m.spawn_pending = true, m.home = false, m.target = -1, m.was_alive = false, m.end_group = -1;
        return;
    }
    const auto& map = world.map();
    const vec2 here = my_position();
    const bool on_spawn = test(map.ally_spawn, here);
    const auto state = my_state();
    m.timer = state.contains(cambc::champion_state::recalling) ? my_channel_time() : 0;
    if ((on_spawn && !m.was_home) || !m.was_alive) m.source = -1, m.spawn_pending = true, m.home = false;
    m.was_home = on_spawn, m.was_alive = true;
    if (on_spawn) m.home = false;
    const int round = world.round;
    const int gems = static_cast<int>(my_gems()), gold = static_cast<int>(my_gold());
    // A capture we held at our last turn's end paid while we stood there.
    const int eg = m.end_group;
    const bool paid = eg >= 0 && m.end_cleared && here == m.end_pos && round - m.end_round <= 2
                      && world.camps[static_cast<std::size_t>(eg)].state == CampState::respawning;
    const bool tributed = m.end_gems > 0 && gems == 0 && !paid;
    m.end_cleared = false;
    if (!state.contains(cambc::champion_state::submitting_gems) && !state.contains(cambc::champion_state::teleporting)) {
        if (paid) {
            // ECONOMY.md 3's forecast: home goes only through the gate.
            const Choice c = decide_now(world, 0, eg, eg, "payout");
            const Next next = payout_forecast(world, pathing, c, gems - m.end_gems, gold - m.end_gold);
            m.home = next == Next::home && home_gate();
            debug_block({ std::printf("FPAY %d %u g%d gems %d gold %d -> %c%s\n", round, my_handle(), eg, gems - m.end_gems, gold - m.end_gold,
                                      next == Next::home ? 'H' : next == Next::tribute ? 'T' : 'F', m.home ? " home" : ""); });
        } else if (m.spawn_pending && on_spawn && (m.target < 0 || m.origin != -1 || round - m.target_round >= 5)) {
            // Once on arrival, then again every 5 rounds on spawn (a mend): the exit's own turn is not known yet.
            decide_now(world, 1, -1, -1, "spawn");
        } else if (!on_spawn && !m.home) {
            const int t = m.target;
            int respawn_round = -1;
            const int now = t >= 0 ? union_state(world, t, &respawn_round) : fish::st_unknown;
            const char* why = t < 0 ? "none"
                              : m.redecide ? "redecide"
                              : tributed ? "tribute"
                              : now == fish::st_respawning && m.target_state != fish::st_respawning ? "taken"
                                                                                                     : nullptr;
            if (why) decide_now(world, 0, tributed ? -1 : m.origin, m.redecide ? m.exclude : -1, why);
            // A target that came back counts as taken once it turns respawning again.
            else if (t >= 0 && now != fish::st_respawning) m.target_state = now;
        }
    }
    const int t = m.target;
    memory.farm_group = t;
    if (t >= 0) {
        memory.claim = t, memory.crew = false;
        // A Monolith is ours to hit (camp_attack_targets skips other Monoliths).
        if (map.groups[static_cast<std::size_t>(t)].has_monolith) siege_group() = t;
    }
}

namespace fish_farm {

// 7.3: the camp to hit in basic range, argmin (hp, y, x, id): among group `only`'s if it is at
// least 0, else among every group's but Monoliths other than `target`.
bool hit_group(const World& world, int only, int target) {
    if (!my_can_attack()) return false;
    const auto& map = world.map();
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    const auto& live = live_camp_tiles();
    std::array<CampAttackTarget, 16> found;
    int n = 0;
    for (const auto p : positions_within(live, here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (only >= 0 && g != only) || world.camps[static_cast<std::size_t>(g)].state != CampState::alive) continue;
        if (only < 0 && g != target && map.groups[static_cast<std::size_t>(g)].has_monolith) continue;
        const auto& G = map.groups[static_cast<std::size_t>(g)];
        for (int i = 0; i < static_cast<int>(G.members.size()); ++i)
            if (G.members[i].pos == p && n < static_cast<int>(found.size())) found[static_cast<std::size_t>(n++)] = {g, i, 0.0f};
    }
    const auto key = [&](const CampAttackTarget& t) {
        const float hp = world.camps[static_cast<std::size_t>(t.group)].health[static_cast<std::size_t>(t.member)];
        const auto& mb = map.groups[static_cast<std::size_t>(t.group)].members[t.member];
        return std::tuple{hp > 0 ? hp : mb.max_health, mb.pos.y, mb.pos.x, mb.handle};
    };
    std::sort(found.begin(), found.begin() + n, [&](const auto& a, const auto& b) { return key(a) < key(b); });
    for (int k = 0; k < n; ++k)
        if (attack_camp_target(world, found[static_cast<std::size_t>(k)])) return true;
    return false;
}

bool group_in_range(const World& world, int g) {
    if (g < 0 || world.camps[static_cast<std::size_t>(g)].state != CampState::alive) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    const auto& live = live_camp_tiles();
    for (const auto& mb : world.map().groups[static_cast<std::size_t>(g)].members)
        if (dist(here, mb.pos) <= range && test(live, mb.pos)) return true;
    return false;
}

// With prev's camps in range, hit among them; else, once the destination is in range, among every
// camp in range (7.3). Walking to it, nothing in passing. The group hit, or -1.
int hit_camps(const World& world, int target) {
    const int prev = mem(world).last_camp;
    const bool keep = group_in_range(world, prev);
    if (!keep && !group_in_range(world, target)) return -1;
    if (!hit_group(world, keep ? prev : -1, target)) return -1;
    return mem(world).last_camp;
}

// 7.5: at the camp range's edge under fire, about half step out (55% stay); deeper inside, stay.
bool edge_step(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {
    if (!my_can_move() || memory.damage <= 0) return false;
    const vec2 here = my_position();
    if (!(safety.camp_damage(here) > 0)) return false;
    const std::uint32_t h = (static_cast<std::uint32_t>(world.round) * 2654435761u) ^ (my_handle() * 40503u);
    if ((h >> 7) % 100 >= 45) return false;
    const auto& blocked = pathing.blocked();
    const auto& standable = world.map().standable;
    for (const auto d : directions) {
        const vec2 p = here + d;
        if (!in_bounds(p) || !test(standable, p) || test(blocked, p) || safety.camp_damage(p) > 0) continue;
        if (pathing.try_move(p)) {
            debug_block({ std::printf("FEDGE %d %u\n", world.round, my_handle()); });
            return true;
        }
    }
    return false;
}

constexpr std::uint64_t approach_floor = 60000;

bool walk_to(World& world, Pathing& pathing, int g) {
    const auto& G = world.map().groups[static_cast<std::size_t>(g)];
    // A respawning group returns only once its camp tiles are empty: wait off them.
    const bitboard* off = world.camps[static_cast<std::size_t>(g)].state == CampState::respawning ? &G.tiles() : nullptr;
    // approach()'s walk round the live camps when made (prepare_next_turn searches it with spare
    // fuel), or searched now with plenty left: its search costs 50k and more on far targets in camp
    // mazes, which Fish's choice picks more often than astraeus's, and its estimate runs short.
    const int range = walk_range(world, g);
    if (const auto* field = pathing.approach_ready(g, range) ? pathing.approach(g, range) : pathing.prepare_approach(g, range, approach_floor))
        if (pathing.walk_down(*field, off, G.centre)) return true;
    // Else the static walk from the group's centre, made once a group, stepping round the camps it meets.
    if (const auto* centre = pathing.centre_field(g))
        if (pathing.descend(*centre, off, G.centre)) return true;
    note_shortcut("fish-crow-flies");
    return pathing.step_closer(G.centre, off, G.centre);
}

} // namespace fish_farm

bool fish_farm::farm_turn(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    auto& m = mem(world);
    const auto& map = world.map();
    const vec2 here = my_position();
    // Standing on a cleared group the holder rule leaves (decide's hold took the rest).
    if (const int on = map.group_at(here); on >= 0 && world.camps[static_cast<std::size_t>(on)].state == CampState::cleared && on == m.target) {
        decide_now(world, 0, on, on, "leave");
    }
    int g = m.target;
    if (g < 0) return false;
    memory.farm_group = memory.claim = g, memory.crew = false;
    const auto& G = map.groups[static_cast<std::size_t>(g)];
    const auto& c = world.camps[static_cast<std::size_t>(g)];
    const bool melee = world.me().facts().walk_and_attack_independent();
    if (edge_step(world, pathing, safety, memory)) {
        if (melee) hit_camps(world, g);
        return true;
    }
    // In range: hit (a ranged hit spends the walk).
    if (const int hit = hit_camps(world, g); hit >= 0) {
        if (melee && step_onto_cleared(world, pathing, hit)) return true;
        if (!melee || world.camps[static_cast<std::size_t>(hit)].state == CampState::alive) {
            cast_at_camp(world, hit);
            reset_and_attack_camp(world, hit);
            return true;
        }
    }
    if (world.is_stale()) return true;
    if (c.state == CampState::cleared) {
        // 7.4's entry: only past a lower-ranked holder, not at its last capture round when poor. A
        // higher-ranked holder seen from afar already sends us elsewhere.
        if (const auto* best = best_holder(world, G)) {
            const int timer = steps_to(G, here) <= 2 ? fresh_ally_capture(world, G) : -1;
            if (!outranks(world.me(), *best) || (timer >= 0 && timer <= 1 && my_gold() <= 12)) {
                m.redecide = true, m.exclude = g;
                debug_block({ std::printf("FDECLINE %d %u g%d\n", world.round, my_handle(), g); });
                decide_now(world, 0, m.origin, g, "decline");
                if ((g = m.target) < 0) return false;
                memory.farm_group = memory.claim = g;
            }
        }
    }
    if (!my_can_move()) return true;
    const bool walked = walk_to(world, pathing, g);
    if (!walked && world.camps[static_cast<std::size_t>(g)].state != CampState::respawning && steps_to(map.groups[static_cast<std::size_t>(g)], my_position()) > walk_range(world, g))
        m.redecide = true, m.exclude = g; // no way on: choose again next turn
    if (melee) {
        if (const int hit = hit_camps(world, g); hit >= 0) {
            if (!step_onto_cleared(world, pathing, hit)) {
                cast_at_camp(world, hit);
                reset_and_attack_camp(world, hit);
            }
        }
    } else if (walked) {
        cast_at_camp_on_approach(world, g);
    }
    return true;
}

bool fish_farm::home_walk(World& world, Pathing& pathing, Safety& safety) {
    auto& m = mem(world);
    if (!m.home || !my_can_move()) return false;
    const auto& field = pathing.to_ally_spawn();
    const int walk = field.at(my_position());
    if (walk == unreachable || walk > 5) return false;
    step_safely(world, pathing, field, safety);
    return true;
}

bool fish_farm::recall_idle(const World& world, Pathing& pathing, Safety& safety) {
    (void)safety;
    auto& m = mem(world);
    const vec2 here = my_position();
    if (m.home) {
        const int walk = pathing.to_ally_spawn().at(here);
        if (walk == unreachable || walk > 5) return true;
    }
    if (holding_capture(world, pathing)) return true;
    // Waiting out the destination's respawn with nothing alive in reach.
    const int g = m.target;
    if (g >= 0 && world.camps[static_cast<std::size_t>(g)].state == CampState::respawning
        && steps_to(world.map().groups[static_cast<std::size_t>(g)], here) <= walk_range(world, g)
        && world.camps[static_cast<std::size_t>(g)].respawn_round - world.round > 1
        && !camp_in_reach(world, here, world.me().facts().attack_range()))
        return true;
    return false;
}

void fish_farm::turn_end(const World& world) {
    auto& m = mem(world);
    if (!world.me().alive) {
        m.n_touched = 0, m.end_group = -1, m.end_gems = 0;
        return;
    }
    const auto& map = world.map();
    const vec2 here = my_position();
    const int on = in_bounds(here) ? map.group_at(here) : -1;
    const bool cleared = on >= 0 && world.camps[static_cast<std::size_t>(on)].state == CampState::cleared;
    if (cleared) m.touch(on);
    for (int i = 0; i < m.n_touched; ++i) {
        const int k = m.touched[static_cast<std::size_t>(i)];
        if (k == m.source) continue;
        ++m.visits[static_cast<std::size_t>(k)];
        if (!m.route(m.source, k)) m.routes.push_back(static_cast<std::uint32_t>(m.source + 1) << 16 | static_cast<std::uint32_t>(k));
        m.source = m.last_group = k;
    }
    m.n_touched = 0;
    if (!test(map.ally_spawn, here)) m.spawn_pending = false;
    m.end_pos = here, m.end_group = on, m.end_cleared = cleared, m.end_round = world.round;
    m.end_gems = static_cast<int>(my_gems()), m.end_gold = static_cast<int>(my_gold());
}

} // namespace

} // namespace aph
