// Team sieges of Monoliths and altar-sealing groups, and kites of big shared groups.
#include "../bot_parts.h"

namespace aph {

namespace {

float team_power(const World& world) {
    float total = 0;
    for (const auto& a : world.allies)
        if (a.alive) total += camp_output(a);
    return total;
}

// The live members' health and summed Strength.
struct SiegeLoad {
    float health = 0, hit = 0;
    float strongest = 0; // the strongest live member's Strength
    vec2 pos{-1, -1};    // and its tile
};

SiegeLoad siege_load(const World& world, int g) {
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    SiegeLoad load;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        // A cleared group's c.health may still hold its last sighting.
        const float hp = c.state == CampState::cleared ? 0 : c.state == CampState::respawning ? G.members[i].max_health : c.health[i];
        if (hp <= 0) continue;
        load.health += hp;
        load.hit += G.members[i].strength;
        if (load.pos.x < 0 || G.members[i].strength > load.strongest) load.strongest = G.members[i].strength, load.pos = G.members[i].pos;
    }
    return load;
}

// A visible enemy stands in the group's reach: it, not we, takes the nearest-champion hits.
bool enemy_in_reach(const World& world, int g) {
    const auto& threat = world.map().groups[g].threat();
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && test(threat, e.pos)) return true;
    return false;
}

struct SiegeTarget {
    int g = -1;
    bool sealing = false;  // a group sealing the altars (seals())
    // Off Monolith-only maps, a live Monolith: `joining`, one the enemy is sieging (in its reach,
    // or our team already on it while it is awake); `bursting`, one whose known health the team
    // clears in a burst (params::burst_rounds).
    bool joining = false, bursting = false;
    bool home = false; // a Monolith hit from our spawn at no health (home_siege)
};

// The shortest of our attack ranges, the sturdiest home_survivable and the living, as siege_ready reads them.
struct HomeTeam {
    int range = unreachable, alive = 0;
    float survivable = 0;
};
HomeTeam home_team(const World& world) {
    HomeTeam t;
    for (const auto& a : world.allies)
        if (a.alive) t.survivable = std::max(t.survivable, home_survivable(a)), t.range = std::min(t.range, a.facts().attack_range()), ++t.alive;
    return t;
}

// Monolith group g's live strikers all fire on spawn stands the sturdiest of us outlasts (home_free):
// sieged from there it costs time, not health, and its health never comes back (rules camps.sleep).
bool home_siege(const World& world, int g) {
    const auto& map = world.map();
    // Static: a member within ranged reach of our spawn's box, read once a group, so far Monoliths
    // never build a StandReach (0 unread, 1 no, 2 yes).
    static std::vector<std::int8_t> near;
    if (near.size() < map.groups.size()) near.resize(map.groups.size(), 0);
    if (near[g] == 0) {
        near[g] = 1;
        const auto& tiles = map.ally_spawn_tiles;
        if (map.groups[g].has_monolith && !tiles.empty()) {
            vec2 lo = tiles[0], hi = tiles[0];
            for (const auto t : tiles) lo = {std::min(lo.x, t.x), std::min(lo.y, t.y)}, hi = {std::max(hi.x, t.x), std::max(hi.y, t.y)};
            for (const auto& m : map.groups[g].members)
                if (std::max({lo.x - m.pos.x, m.pos.x - hi.x, lo.y - m.pos.y, m.pos.y - hi.y}) <= ranged_range) near[g] = 2;
        }
    }
    if (near[g] != 2) return false;
    const auto& c = world.camps[g];
    if (c.state != CampState::alive && c.state != CampState::respawning) return false;
    const auto t = home_team(world);
    if (t.alive == 0) return false;
    const auto load = siege_load(world, g);
    return load.hit > 0 && home_free(world, g, t.range, t.survivable) >= load.hit - 0.5f;
}

// The Monolith or sealing group to siege; one the enemy holds or that returns too late is skipped.
SiegeTarget siege_candidate(const World& world, Pathing& pathing, const Memory& memory) {
    const auto& map = world.map();
    static std::vector<int> monoliths; // in group order
    static bool listed = false;
    if (!listed) {
        listed = true;
        for (int g = 0; g < static_cast<int>(map.groups.size()); ++g)
            if (map.groups[g].has_monolith) monoliths.push_back(g);
    }
    SiegeTarget best;
    float best_cost = 0;
    const bool farm_op = memory.mono_group >= 0 && memory.claim == memory.mono_group && !memory.siege;
    const auto consider = [&](int g, bool seal) {
        // A big group our kite works stays the kite's: melee at its camps would wake it on the casters.
        if (map.shared_gems && kite_owns(world, g)) return;
        const auto& c = world.camps[g];
        // Off Monolith-only maps a live Monolith counts only if it seals, the enemy is sieging it or
        // the team clears it in a burst. Members of farm's crew operation on a Monolith stay farm's
        // (allies join an operation through farm, so an ally's claim alone is no siege).
        if (!map.monolith_only && !seal && farm_op) return;
        const bool join = !map.monolith_only && !seal && c.state == CampState::alive && c.awake != Awake::asleep
                          && (enemy_in_reach(world, g) || (memory.siege && memory.claim == g));
        const bool burst = !map.monolith_only && !seal && !join && c.state == CampState::alive
                           && siege_load(world, g).health <= team_power(world) * static_cast<float>(params::burst_rounds);
        const bool home = !seal && !join && map.monolith_only && home_siege(world, g);
        if (!map.monolith_only && !seal && !join && !burst && c.state != CampState::cleared) return;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > params::siege_respawn_wait) return;
        if (c.state == CampState::cleared && c.holder == team::enemy) return;
        int steps = map.ally_steps(g);
        // A dasher's seals are on its own walk (altar_access), which crosses holes the walk from
        // spawn cannot.
        if (steps == unreachable && seal && world.me().facts().has_dash()) steps = pathing.centre_to_spawn(g);
        if (steps == unreachable) return;
        // The walk there from our spawn, the same for the whole team, and the wait for its return,
        // with the current target kept until another is clearly sooner: switching turns everyone around.
        float cost = static_cast<float>(std::max(steps, wait));
        if (memory.siege && memory.claim == g) cost -= static_cast<float>(params::siege_stickiness);
        if (best.g < 0 || cost < best_cost) best = {g, seal, join, burst, home}, best_cost = cost;
    };
    const bool sealed = altars_sealed(world, pathing);
    const auto& access = altar_access(world, pathing);
    for (const int g : monoliths) consider(g, sealed && seals(world, access, g));
    if (sealed) {
        // Other sealing groups: those blocking, and those awake.
        for (const int g : access.blocks)
            if (!map.groups[g].has_monolith) consider(g, true);
        world.each_stirring([&](int g) {
            if (!map.groups[g].has_monolith && seals(world, access, g)
                && std::find(access.blocks.begin(), access.blocks.end(), g) == access.blocks.end())
                consider(g, true);
        });
    }
    return best;
}

// The team's clear, at its current output, is quick enough and costs no more health than it can take:
// within the pool it brings, or in heal trips it keeps up while still clearing in time.
bool siege_ready(const World& world, const SiegeTarget& target, const SiegeLoad& load, bool committed) {
    if (load.health <= 0) return true;
    float power = team_power(world);
    float limit = world.map().monolith_only || target.sealing || target.joining ? params::siege_rounds
                  : target.bursting ? params::burst_rounds : 0;
    if (target.home) {
        // Only bodies on its stands hit it for free: the output those stands hold.
        const auto t = home_team(world);
        const int stands = std::popcount(home_reach(world, target.g, t.range));
        power *= std::min(1.0f, static_cast<float>(stands) / static_cast<float>(std::max(1, t.alive)));
        limit = std::max(limit, static_cast<float>(params::home_siege_rounds));
    }
    const float rounds = load.health / power;
    const float slack = committed ? params::siege_commit_slack : 1.0f;
    if (rounds > limit * slack) return false;
    // The pool in camp damage it absorbs: each body's health over its own camp_taken, at full for one
    // out of sight (only its liveness reads) or on our spawn, which heals it at its turn end.
    const auto& map = world.map();
    float pool = 0, survivable = 0;
    int alive = 0, range = unreachable; // the shortest of our attack ranges
    for (const auto& a : world.allies)
        if (a.alive) {
            const float health = (a.visible || a.is_self) && !test(map.ally_spawn, a.pos) ? a.health : a.max_health;
            pool += health / std::max(a.camp_taken, 0.01f), ++alive;
            survivable = std::max(survivable, home_survivable(a)), range = std::min(range, a.facts().attack_range());
        }
    // A member hits the nearest champion in its reach (rules camps.attack): a visible enemy, where it
    // stands now, takes its hits if nearer it than our nearest stand, our shortest range (ties to us).
    const auto& G = map.groups[target.g];
    const auto& c = world.camps[target.g];
    float tanked = 0;
    for (std::size_t i = 0; c.state == CampState::alive && i < G.members.size(); ++i) {
        const auto& m = G.members[i];
        if (c.health[i] <= 0 || m.strength <= 0) continue;
        bool enemy = false;
        for (const auto& e : world.enemies) enemy = enemy || (e.alive && e.visible && dist(e.pos, m.pos) < std::min(range, m.reach + 1));
        if (enemy) tanked += m.strength;
    }
    const float fire = load.hit - tanked;
    // A live member hit from a spawn stand whose fire the sturdiest of us, standing there, outlasts for
    // a phase costs no health: the turn end there heals it (rules rounds.turn_end; home_free).
    const float hit = std::max(0.0f, fire - home_free(world, target.g, range, survivable)) * params::siege_hit_share;
    if (rounds * hit <= params::siege_pool_share * pool * slack) return true;
    // Past the pool, heal trips (heal_trip, from the group's nearest stand off spawn): the health a
    // body brings above where siege() sends it home (a phase of the group's fire for each step out of
    // its reach or home, and its strongest hit) costs it a trip's rounds of output, which slows the clear.
    const int gap = home_gap(map, target.g, range);
    const float leave = fire * static_cast<float>(std::max(1, std::min(gap, map.groups[target.g].reach + 1))) + load.strongest;
    const float usable = pool / static_cast<float>(alive) - leave;
    if (usable <= 0) return false;
    const float trip = heal_trip(world, static_cast<float>(gap), static_cast<float>(map.ally_steps(target.g)));
    const float lost = hit * trip / usable * power / static_cast<float>(alive);
    return lost < power && load.health / (power - lost) <= limit * slack;
}

// This round's siege target whose stands we cannot hold even at full health (siege() sets it).
struct Declined {
    int round = -1, group = -1;
} declined;

bool siege_declines(const World& world, int g) { return declined.round == world.round && declined.group == g; }

bool stop_siege(Memory& memory) {
    memory.siege = false;
    memory.staged_since = -1;
    return false;
}

// Once the team is strong enough it goes together: melee adjacent, ranged at their range, the hurt
// stepping out to 4, where casters still cast.
bool siege(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    sieged = true;
    const auto& map = world.map();
    const auto target = siege_candidate(world, pathing, memory);
    const int g = target.g;
    if (g < 0) return stop_siege(memory);
    const bool ally_in = ally_claims(world, g);
    const auto load = siege_load(world, g);
    if (!siege_ready(world, target, load, (memory.siege && memory.claim == g) || ally_in)) return stop_siege(memory);
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state == CampState::cleared) {
        // The nearest take the capture, split to shorten the tributes; the rest farm.
        if (capture_taken(world, pathing, g, here)) return stop_siege(memory);
        memory.siege = true;
        memory.staged_since = -1;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    memory.siege = true;
    memory.claim = g;
    memory.crew = ally_in;
    siege_group() = g;
    const vec2 m = load.pos;
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    const bool fresh = c.state == CampState::respawning;
    const int stage = G.reach + 2; // just out of the group's reach

    // Waiting where the team gathers: within a step of the staging ring around any live member.
    const auto at_stage = [&](vec2 p) {
        for (std::size_t i = 0; i < G.members.size(); ++i)
            if ((c.health[i] > 0 || fresh) && dist(p, G.members[i].pos) <= stage + 1) return true;
        return false;
    };
    bool engaged = false;
    float staged = camp_output(world.me());
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible) continue;
        if (test(G.threat(), a.pos) && c.awake != Awake::asleep) engaged = true;
        if (at_stage(a.pos)) staged += camp_output(a);
    }
    if (!fresh && test(G.threat(), here) && c.awake != Awake::asleep) engaged = true;
    // Engage once enough of the team's output has gathered (us counted, coming or not), or after a wait.
    if (!engaged && !fresh) {
        if (memory.staged_since < 0 && at_stage(here)) memory.staged_since = world.round;
        engaged = staged >= params::siege_gather_share * team_power(world)
                  || (memory.staged_since >= 0 && world.round - memory.staged_since >= params::siege_max_wait);
    }

    const bool caster = spell_output(world.me()) > 0;
    bool tanked = false;
    for (const auto& a : world.allies)
        tanked |= !a.is_self && a.alive && a.visible && !a.facts().ranged && dist(a.pos, m) <= 1;
    // The members that hit us at p: each hits the nearest champion in its reach, so not one with a
    // visible ally strictly nearer it (ties count against us). An ally recalling home before our
    // next turn or teleporting is no cover. Cover does not depend on where we stand: the nearest
    // ally that covers each member.
    static std::vector<int> cover;
    cover.assign(G.members.size(), unreachable);
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && a.channel != Channel::teleport && !(real_recall(a) && a.channel_end_round <= world.round + 1))
            for (std::size_t i = 0; i < G.members.size(); ++i) cover[i] = std::min(cover[i], dist(a.pos, G.members[i].pos));
    struct Fire {
        float hit = 0, biggest = 0;
        int steps_out = 1;
    };
    const auto fire_at = [&](vec2 p) {
        Fire fire;
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            if (c.health[i] <= 0 && !fresh) continue;
            const auto& member = G.members[i];
            const int d = dist(p, member.pos);
            if (member.strength <= 0 || d > member.reach || cover[i] < d) continue;
            const float h = member.strength * camp_hit_factor();
            fire.hit += h;
            fire.biggest = std::max(fire.biggest, h);
            fire.steps_out = std::max(fire.steps_out, member.reach + 1 - d);
        }
        return fire;
    };
    const Fire fire_here = fire_at(here);
    const float hit = fire_here.hit, biggest = fire_here.biggest;
    const int steps_out = fire_here.steps_out;
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard inner{cambc::uninitialized}, goals{cambc::uninitialized}, all{cambc::uninitialized};
    clear_board(inner); // ranged: too near a live member to stand at full range
    for (std::size_t i = 0; range > 1 && i < G.members.size(); ++i)
        if (c.health[i] > 0 || fresh) draw_square(inner, G.members[i].pos, static_cast<float>(range - 1));
    // Leave while we can still walk out of reach or onto our spawn, where the turn end heals: the hits
    // on us for each step, and a round's slack. Targeted by none, we stand and hit; if the tank leaves,
    // we are the target next turn. On our spawn we need not leave while a phase's fire fits home_room.
    // On our spawn, the fire as home_stands reads it, so a stand it picked does not read low on arrival.
    const bool on_home = test(map.ally_spawn, here);
    // Set out home (Memory::camp_fled), or hurt out of reach, where siege_heal_trip keeps the recall
    // unless the walk is no slower.
    const bool heading_home = !on_home && (memory.camp_fled >= 0 || (hit <= 0 && my_health() < params::heal_trip_fraction * my_max_health()));
    const int home_steps = (hit > 0 || heading_home) && !on_home
                               ? home_exit_steps(world, pathing, safety, here, std::max(steps_out, walk_home_limit(recall_turns(world))))
                               : unreachable;
    const bool low = on_home ? hit > 0 && phase_fire(world, safety, here, g) > home_room(world, safety)
                             : hit > 0 && my_health() < hit * static_cast<float>(std::min(steps_out, std::max(1, home_steps))) + biggest;
    // Low, home by the walk when it is no slower than the recall. Once set out, until healed or home
    // (camp_fled): nearer home, `low` alone would turn us back before the heal.
    const bool walk_home = (low || heading_home) && !on_home && walk_home_beats(home_steps, recall_turns(world));
    if (walk_home && memory.camp_fled < 0) memory.camp_fled = my_health();

    // Tiles within r of a live member that see it; none if the fuel to build them is short. To fire
    // from, other groups' dead camp tiles count too (we hold a capture or a return there): in a
    // corridor of chained groups they can be the only tiles in range of the next one.
    const bool many = G.members.size() > 1;
    const auto tiles = [&](int r, bitboard& out, bool firing = true) __attribute__((always_inline)) {
        if (many ? pathing.prepare_attack_tiles(g, r, end_reserve) : pathing.prepare_member_tiles(g, r, 1u, end_reserve)) {
            if (many) pathing.attack_tiles(g, r, out);
            else and_into(pathing.member_attack_tiles(g, 0, r), map.standable, out); // off its camp tile
            static bitboard dead{cambc::uninitialized};
            for (std::size_t i = 0; firing && i < G.members.size(); ++i) {
                if (many ? c.health[i] <= 0 : i > 0) continue;
                for (const int h : map.groups_near(G.members[i].pos, r)) {
                    const auto& other = world.camps[h];
                    if (h == g || other.state == CampState::alive || (other.state == CampState::cleared && other.holder == team::enemy)) continue;
                    and_into(pathing.member_attack_tiles(g, static_cast<int>(i), r), map.groups[h].tiles(), dead);
                    out |= dead;
                }
            }
        } else {
            note_shortcut("siege-no-tiles");
            clear_board(out);
        }
    };
    // Out of reach: of the group's, and of every other group's that may be awake, whose fire would
    // otherwise fall on us while we wait.
    const auto out_of_reach = [&](bitboard& b) {
        drop(b, G.threat());
        world.each_stirring([&](int h) {
            if (h != g) drop(b, map.groups[h].threat());
        });
    };
    // Low on our spawn, a spawn tile whose fire fits is as good as the way out, and still heals.
    bool refuge = false;
    if (low && on_home && engaged && !fresh) {
        home_tiles(world, pathing, safety, goals);
        refuge = !board_empty(goals);
    }
    if (refuge) {
    } else if (walk_home) {
        home_tiles(world, pathing, safety, goals);
    } else if (!engaged || fresh) {
        tiles(stage, goals, false);
        out_of_reach(goals);
    } else if (low) {
        // Out of reach, the turn's recall is kept for a heal trip (siege_heal_trip); a caster
        // healthy enough stays at spell range to cast.
        tiles(caster && my_health() >= params::heal_trip_fraction * my_max_health() ? ability_range : stage,
              goals, false);
        out_of_reach(goals);
    } else if (f.ranged && caster && !tanked) {
        // With no ally nearer the Monolith to take its hits, cast from out of its reach.
        tiles(ability_range, goals);
        out_of_reach(goals);
        if (board_empty(goals)) {
            tiles(range, goals);
            drop(goals, inner);
        }
    } else if (f.ranged) {
        tiles(range, all);
        copy_into(all, goals);
        drop(goals, inner);
        if (board_empty(goals)) goals.swap(all);
    } else {
        tiles(1, goals);
    }
    // Stands on our spawn whose fire fits home_room cost no health (home_stands): the cheapest.
    const bool home_stand = engaged && !fresh && !low && !walk_home && home_stands(world, pathing, safety, goals, g, all);
    if (home_stand) goals.swap(all);
    if (board_empty(goals)) {
        draw_square(goals, m, static_cast<float>(stage));
        goals &= map.standable;
        out_of_reach(goals);
    }
    // Off our stand, `low` is judged at each stand as it is read there: read here, out of reach, it
    // holds no fire, so a hurt champion would step in, read low and step out. We walk only to stands
    // that hold at our health. The fire taken walking in is left out: a deeper stand that then reads
    // low is judged again with the lower health, so it is not taken up again until we heal. With
    // none, a heal helps if one would hold at full health: home by the walk, or out of reach while
    // siege_heal_trip keeps the recall (below heal_trip_fraction, when the walk is slower); else the
    // turn is farm's, and farm leaves the group alone this round.
    if (engaged && !fresh && !low && !walk_home && !home_stand && !test(goals, here)) {
        static bitboard held{cambc::uninitialized};
        clear_board(held);
        float least = std::numeric_limits<float>::infinity(); // the least health that holds a stand
        for (const vec2 p : goals.positions()) {
            const Fire f = test(G.threat(), p) ? fire_at(p) : Fire{};
            const float at = f.hit, biggest_at = f.biggest;
            const int out = f.steps_out;
            float need = 0;
            if (at > 0) {
                need = at * static_cast<float>(out) + biggest_at;
                // Near home the way out may be the walk home (the in-reach `low`'s min): priced only where it decides.
                if (need > my_health() && out > 1 && at + biggest_at <= my_max_health() && map.from_ally_spawn().at(p) < out)
                    need = at * static_cast<float>(std::max(1, std::min(out, home_exit_steps(world, pathing, safety, p, out)))) + biggest_at;
            }
            least = std::min(least, need);
            if (my_health() >= need) set_tile(held, p);
        }
        if (!board_empty(held)) {
            goals.swap(held);
        } else if (least <= my_max_health()) {
            const int home = home_exit_steps(world, pathing, safety, here, walk_home_limit(recall_turns(world)));
            if (my_health() < params::heal_trip_fraction * my_max_health() && !walk_home_beats(home, recall_turns(world))) {
                tiles(stage, goals, false);
                out_of_reach(goals);
                if (board_empty(goals)) {
                    draw_square(goals, m, static_cast<float>(stage));
                    goals &= map.standable;
                    out_of_reach(goals);
                }
            } else {
                memory.camp_fled = my_health();
                home_tiles(world, pathing, safety, goals);
            }
        } else {
            declined = {world.round, g};
            memory.siege = false;
            siege_group() = -1;
            return false;
        }
    }
    if (!test(goals, here)) {
        // With an enemy near, live routes walk round hole lines: a seal off the walk from spawn is
        // reached down our approach field, as farm walks.
        bool moved = pathing.step_towards_funded(goals, end_reserve);
        if (!moved && target.sealing && map.ally_steps(g) == unreachable)
            if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve))
                moved = pathing.walk_down(*field, &G.threat(), G.centre);
        if (engaged && !low) attack_camp(world, [&](int h) { return h == g; });
        if (engaged) cast_at_camp(world, g);
        if (engaged && !low) reset_and_attack_camp(world, g);
        // No step towards our stand (no route within the search's reach) and, engaged, no live member
        // in our attack or spell range here (whatever the cooldowns): the turn is farm's, whose camps
        // or bag may be what holds the way. The wait still counts from when we staged, so a stall at
        // the stage engages after siege_max_wait rather than restarting it.
        bool in_range = false;
        for (std::size_t i = 0; engaged && i < G.members.size(); ++i)
            in_range |= (fresh || c.health[i] > 0) && dist(here, G.members[i].pos) <= std::max(range, caster ? ability_range : 0);
        if (!moved && !in_range && my_can_move()) {
            memory.siege = false;
            siege_group() = -1;
            return false;
        }
        return true;
    }
    if (!engaged) return true;
    cast_at_camp(world, g);
    if (!low) {
        attack_camp(world, [&](int h) { return h == g; });
        reset_and_attack_camp(world, g);
    }
    return true;
}

// For a ground caster whose ground spell is down: whether stepping into (or staying in) group g's
// reach pays over two activations, damage dealt against the heal trips its camp hits cost; steps
// there if so. `interior`, already in reach: whether firing from here this activation pays.
bool kite_productive_action(const World& world, Pathing& pathing, int g, bool interior = false) {
    if (!interior && !my_can_move()) return false;
    const auto& map = world.map();
    const auto& self = world.me();
    const auto& f = self.facts();
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    if (c.state != CampState::alive) return false;
    const int horizon = interior ? 1 : 2;
    int slot = -1;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        // Ground centres are not priced here: a ground spell ready in the horizon is the stations'.
        if (a.kind == AbilityKind::damage && a.target == Targeting::ground && a.multiplier > 0
            && self.ability_ready(s, world.round + horizon - 1)) return false;
        if (a.kind == AbilityKind::attack_reset || (a.kind == AbilityKind::damage && a.target == Targeting::unit && a.multiplier > 0)) {
            if (slot >= 0) return false;
            slot = s;
        }
    }
    const vec2 here = my_position();
    if (interior && pathing.guard() && test(*pathing.guard(), here)) return false;
    int reach = f.attack_range();
    if (slot >= 0 && f.abilities[slot].kind == AbilityKind::damage && self.ability_ready(slot, world.round + horizon - 1))
        reach = std::max(reach, f.abilities[slot].range());
    bool reachable = false;
    for (std::size_t i = 0; i < G.members.size(); ++i)
        reachable |= c.health[i] > 0 && dist(here, G.members[i].pos) <= reach + (interior ? 0 : 1);
    if (!reachable) return false;
    const int home_steps = map.from_ally_spawn().at(here);
    if (home_steps == unreachable) return false;
    std::array<vec2, 9> endpoints;
    endpoints[0] = here;
    int count = 1;
    if (!interior) {
        const auto& blocked = pathing.blocked();
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                if (dx == 0 && dy == 0) continue;
                const vec2 p{here.x + dx, here.y + dy};
                if (in_bounds(p) && test(map.standable, p) && !test(blocked, p)
                    && (!pathing.guard() || !test(*pathing.guard(), p))) endpoints[count++] = p;
            }
    }
    struct Target { vec2 pos; float health, strength; std::uint16_t visible; };
    static std::vector<Target> targets;
    targets.clear();
    // Members no endpoint reaches take no damage below: only whether there are any matters.
    const int hits_within = std::max(f.attack_range(), slot >= 0 && f.abilities[slot].kind == AbilityKind::damage ? f.abilities[slot].range() : 0) + 1;
    bool any = false;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (c.health[i] <= 0) continue;
        const auto& m = G.members[i];
        // kite prepared range-5 viewers for the harmful members only; building one is too dear, so
        // a harmless member near enough to matter ends the search.
        if (m.strength <= 0) {
            if (dist(here, m.pos) <= ability_range + 1) return false;
            continue;
        }
        any = true;
        if (dist(here, m.pos) > hits_within) continue;
        const auto& viewers = pathing.member_attack_tiles(g, static_cast<int>(i), ability_range + 1);
        std::uint16_t visible = 0;
        for (int k = 0; k < count; ++k)
            if (test(viewers, endpoints[k])) visible |= std::uint16_t{1} << k;
        targets.push_back({m.pos, c.health[i], m.strength, visible});
    }
    if (!any) return false;
    const bool can_attack = my_can_attack(), can_cast = my_can_cast();
    const float dealt = damage_scale(f.passive, self.health, self.max_health) * camp_dealt_factor();
    const float strength = my_strength(), basic_damage = strength * dealt;
    const float spell_damage = slot < 0 ? 0 : f.abilities[slot].multiplier * my_record().focus * dealt;
    const float soften = camp_hit_factor();
    const float spare = my_health() - params::recall_health_fraction * my_max_health();
    const float lost_output = camp_output(self);
    world.throw_if_stale();
    static std::vector<float> remaining;
    remaining.resize(targets.size());
    // Our best damage from endpoints[k] over the horizon, the position held.
    const auto damage = [&](int k) {
        const vec2 p = endpoints[k];
        const std::uint16_t seen = std::uint16_t{1} << k;
        const bool moved = k != 0;
        const bool held = engagement_near(world, p, f.cast_reach());
        const bool reset_held = engagement_near(world, p, f.basic_reach() + (f.ranged ? 0 : 1));
        float best = 0;
        // No cast, cast now, or cast next activation: a slot cannot recur within this horizon.
        for (int use = 0; use <= horizon; ++use) {
            for (std::size_t i = 0; i < targets.size(); ++i) remaining[i] = targets[i].health;
            float total = 0;
            const auto basic = [&] {
                int at = -1;
                float score = -1;
                for (std::size_t i = 0; i < targets.size(); ++i)
                    if (remaining[i] > 0 && (targets[i].visible & seen) && dist(p, targets[i].pos) <= f.attack_range()) {
                        const float value = targets[i].strength / remaining[i];
                        if (value > score) at = static_cast<int>(i), score = value;
                    }
                if (at < 0) return false;
                const float hit = std::min(basic_damage, remaining[at]);
                remaining[at] -= hit;
                total += hit;
                return true;
            };
            for (int turn = 0; turn < horizon; ++turn) {
                const bool walk = turn == 0 && (moved || here != world.turn_start);
                const bool attack = turn > 0 || (can_attack && (!walk || !f.ranged));
                const bool cast = slot >= 0 && use == turn + 1 && (turn > 0 || can_cast)
                    && self.ability_ready(slot, world.round + turn) && !(walk && f.abilities[slot].excludes_walking);
                if (cast && f.abilities[slot].kind == AbilityKind::damage && !held) {
                    int at = -1;
                    float value = 0;
                    for (std::size_t i = 0; i < targets.size(); ++i)
                        if ((targets[i].visible & seen) && dist(p, targets[i].pos) <= f.abilities[slot].range())
                            if (const float hit = std::min(spell_damage, remaining[i]); hit > value) at = static_cast<int>(i), value = hit;
                    if (at >= 0) remaining[at] -= value, total += value;
                }
                const bool attacked = attack && basic();
                // The reset needs a spent attack: this one, or one spent before (a ranged walk, or
                // an attack earlier this turn).
                if (cast && f.abilities[slot].kind == AbilityKind::attack_reset && (attacked || !attack)) {
                    int at = -1;
                    for (std::size_t i = 0; i < targets.size(); ++i)
                        if (remaining[i] > 0 && (targets[i].visible & seen) && dist(p, targets[i].pos) <= f.attack_range()
                            && (at < 0 || remaining[i] < remaining[at])) at = static_cast<int>(i);
                    const bool refunded = at >= 0 && f.passive == Passive::reset_on_kill && remaining[at] <= basic_damage;
                    if (at >= 0 && (!reset_held || refunded)) {
                        const float hit = std::min(basic_damage, remaining[at]);
                        remaining[at] -= hit;
                        total += hit;
                    }
                }
            }
            best = std::max(best, total);
        }
        return best;
    };
    const auto exposure = [&](vec2 p, bool supported) {
        float hit = 0;
        for (const int h : map.groups_near(p, map.max_camp_reach)) {
            const auto& belief = world.camps[h];
            if (belief.state == CampState::cleared) continue;
            const auto& members = map.groups[h].members;
            for (std::size_t i = 0; i < members.size(); ++i) {
                const auto& m = members[i];
                if ((belief.state == CampState::alive && belief.health[i] <= 0) || m.strength <= 0 || dist(p, m.pos) > m.reach) continue;
                bool tanked = false;
                if (supported)
                    for (const auto& a : world.allies)
                        tanked |= !a.is_self && a.alive && a.visible && a.channel != Channel::teleport
                            && !(real_recall(a) && a.channel_end_round <= world.round + horizon)
                            && dist(a.pos, m.pos) < dist(p, m.pos);
                if (!tanked) hit += m.strength;
            }
        }
        return static_cast<float>(horizon) * hit * soften;
    };
    const float stay = damage(0) - heal_rounds(world, exposure(here, true), static_cast<float>(home_steps), static_cast<float>(home_steps)) * lost_output;
    if (interior) {
        const bool fire = exposure(here, false) <= spare && stay > 0;
        world.throw_if_stale();
        return fire;
    }
    int best = 0;
    float value = stay;
    for (int k = 1; k < count; ++k) {
        // Two camp phases, even if our damage would kill or stun a monster. Support prices only
        // recovery: the full raw hit reserve still applies if every other body walks away.
        if (exposure(endpoints[k], false) > spare) continue;
        const float gain = damage(k) - heal_rounds(world, exposure(endpoints[k], true), static_cast<float>(home_steps + 1), static_cast<float>(home_steps + 1)) * lost_output;
        if (gain > value) best = k, value = gain;
    }
    if (best == 0) return false;
    world.throw_if_stale();
    const bool moved = pathing.try_move(endpoints[best]);
    world.throw_if_stale();
    return moved;
}

// A champion's kite station spells (unit damage spells, ground ones if it kites with spells): the
// farthest reach of one, 0 if none; with `per_reach`, its output added at each spell's reach.
constexpr int max_spell_reach = 8;
int station_reach(const ChampionBelief& a, std::array<float, max_spell_reach + 1>* per_reach = nullptr) {
    int best = 0;
    for (const auto& s : a.facts().abilities)
        if (s.kind == AbilityKind::damage && s.multiplier > 0
            && (s.target == Targeting::unit || (s.target == Targeting::ground && kites_with_spells(a)))) {
            // A unit spell's target stands within its range, a ground one's within its 3x3 of it.
            const int r = std::min(s.range() + (s.target == Targeting::ground ? ground_radius : 0), max_spell_reach);
            best = std::max(best, r);
            if (per_reach) (*per_reach)[static_cast<std::size_t>(r)] += s.multiplier * a.focus / static_cast<float>(ability_cooldown);
        }
    return best;
}

// The team's kite of a big group: each striker falls to the spells that reach it from a standable
// tile out of every live striker's reach (casters take no hit), cast by any ally of the team (the
// dead respawn: ownership does not flip with a death).
// `rounds`: how long that takes, unreachable while a live striker has no such spell.
struct KitePlan {
    bool owned = false;          // some ally's station spells hit a live striker
    int reach = max_spell_reach + 1; // the least station spell reach that hits a live striker: casters reach that
    float rounds = unreachable;
};

KitePlan kite_plan(const World& world, int g) {
    // The team's spell output at each spell reach, once a round.
    static std::array<float, max_spell_reach + 1> output{};
    static int output_round = -1;
    if (output_round != world.round) {
        output_round = world.round;
        output.fill(0);
        for (const auto& a : world.allies) station_reach(a, &output);
    }
    const auto& G = world.map().groups[g];
    const auto& c = world.camps[g];
    KitePlan plan;
    if (c.state == CampState::cleared) return plan;
    const bool fresh = c.state == CampState::respawning;
    // Per striker, the least spell reach with a station tile, from the live members (kept while they
    // live, as kite()'s boards are). Unit spells' sight is left out.
    struct Geometry {
        std::vector<std::uint64_t> live;
        std::vector<std::uint8_t> least;
    };
    static std::vector<Geometry> geometry;
    if (geometry.size() < world.map().groups.size()) geometry.resize(world.map().groups.size());
    auto& geo = geometry[static_cast<std::size_t>(g)];
    const std::size_t n = G.members.size();
    const auto live = [&](std::size_t i) { return G.members[i].strength > 0 && (fresh || c.health[i] > 0); };
    static std::vector<std::uint64_t> now;
    now.assign((n + 63) / 64, 0);
    for (std::size_t i = 0; i < n; ++i) now[i / 64] |= std::uint64_t{live(i)} << (i % 64);
    if (geo.live != now || geo.least.size() != n) {
        geo.live = now;
        geo.least.assign(n, max_spell_reach + 1);
        static bitboard threat{cambc::uninitialized}, tiles{cambc::uninitialized};
        clear_board(threat);
        for (std::size_t i = 0; i < n; ++i)
            if (live(i)) draw_square(threat, G.members[i].pos, static_cast<float>(G.members[i].reach));
        for (std::size_t i = 0; i < n; ++i)
            for (int r = G.members[i].reach + 1; live(i) && r <= max_spell_reach; ++r) {
                clear_board(tiles);
                draw_square(tiles, G.members[i].pos, static_cast<float>(r));
                tiles &= world.map().standable;
                drop(tiles, threat);
                if (!board_empty(tiles)) {
                    geo.least[i] = static_cast<std::uint8_t>(r);
                    break;
                }
            }
    }
    float rounds = 0;
    bool complete = true;
    for (std::size_t i = 0; i < n; ++i) {
        if (!live(i)) continue;
        float out = 0;
        for (int r = geo.least[i]; r <= max_spell_reach; ++r) out += output[static_cast<std::size_t>(r)];
        const float hp = fresh ? G.members[i].max_health : c.health[i];
        if (out <= 0) {
            complete = false;
            continue;
        }
        plan.owned = true;
        rounds += hp / out;
        int least = geo.least[i];
        while (least <= max_spell_reach && output[static_cast<std::size_t>(least)] <= 0) ++least;
        plan.reach = std::min(plan.reach, least);
    }
    if (complete && plan.owned) plan.rounds = rounds;
    return plan;
}

// kite()'s station boards depend on the group, our ranges and which members live (not on health,
// so a hit each turn keeps them): the group's, and those of the other groups its loop looked at,
// which are the same while the group's live members are.
struct StationCache {
    bool valid = false, fresh = false, ground = false, unit = false, guard = false;
    int group = -1, range = 0, unit_range = 0, ground_range = 0;
    std::vector<std::uint64_t> live, beside_live;
    std::vector<int> beside;
    // A group that is not alive counts as one with no live member, as in the loop.
    static void add(const World& world, int h, bool all, bool alive, std::vector<std::uint64_t>& out) {
        const auto& health = world.camps[h].health;
        const std::size_t n = world.map().groups[h].members.size();
        for (std::size_t w = 0; w < n; w += 64) {
            std::uint64_t bits = 0;
            for (std::size_t i = w; i < std::min(n, w + 64); ++i) bits |= std::uint64_t{all || (alive && health[i] > 0)} << (i - w);
            out.push_back(bits);
        }
    }
    static void add_beside(const World& world, const std::vector<int>& groups, std::vector<std::uint64_t>& out) {
        out.clear();
        for (const int h : groups) add(world, h, false, world.camps[h].state == CampState::alive, out);
    }
    // Whether the boards kept are this call's; if not, set up for the loop to note what it reads.
    bool check(const World& world, int g, bool fresh_, bool ground_, bool unit_, bool guard_, int range_, int unit_range_, int ground_range_) {
        static std::vector<std::uint64_t> now;
        now.clear();
        add(world, g, fresh_, true, now);
        if (valid && group == g && fresh == fresh_ && ground == ground_ && unit == unit_ && guard == guard_ && range == range_
            && unit_range == unit_range_ && ground_range == ground_range_ && live == now) {
            add_beside(world, beside, now);
            if (beside_live == now) return true;
        }
        valid = false;
        group = g, fresh = fresh_, ground = ground_, unit = unit_, guard = guard_;
        range = range_, unit_range = unit_range_, ground_range = ground_range_;
        live.clear();
        add(world, g, fresh_, true, live);
        beside.clear();
        return false;
    }
    void note(int other) {
        if (std::find(beside.begin(), beside.end(), other) == beside.end()) beside.push_back(other);
    }
    void finish(const World& world) {
        add_beside(world, beside, beside_live);
        valid = true;
    }
};

// A big group cleared by stationary spells out of its monsters' reach, so that nobody takes a hit;
// harmless members fall to basic attacks from there, the rest once the monsters are dead.
bool kite(const World& world, Pathing& pathing, Memory& memory) {
    world.throw_if_stale();
    const auto& map = world.map();
    const vec2 here = my_position();
    int g = -1, best_cost = 0;
    // contest_capture's rule: a body of ours on a camp tile before their hold pays.
    const auto too_late = [&](int h) { return pathing.to_group(h).at(here) > enemy_hold_left(world, world.camps[h]); };
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h) {
        if (!big_group(map.groups[h])) continue;
        const auto& c = world.camps[h];
        // Without an ally whose stations hit its monsters, nobody would ever kite them: farm takes it.
        if (c.state != CampState::cleared && !kite_plan(world, h).owned) continue;
        const int steps = walk_to(world, pathing, h, here);
        if (c.state == CampState::cleared && ((c.holder == team::enemy && too_late(h)) || contest_manned(world, h, here))) continue;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > steps + params::kite_early) continue;
        const int cost = std::max(steps, wait);
        if (g < 0 || cost < best_cost) g = h, best_cost = cost;
    }
    if (g < 0) return false;
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    if (c.state == CampState::cleared) {
        const auto& tiles = G.tiles();
        if (enemy_on(world, tiles) || c.holder == team::enemy) {
            if (!test(tiles, here) && too_late(g)) return false;
            memory.claim = g;
            memory.crew = false;
            if (test(tiles, here)) return true; // our tile keeps their hold from counting
            const auto& free = free_tiles(tiles);
            if (!board_empty(free)) pathing.step_towards_funded(free, end_reserve);
            return true;
        }
        if (capture_taken(world, pathing, g, here) || dist(here, G.centre) > 2 * vision_radius) return false;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    const bool fresh = c.state == CampState::respawning;
    const auto plan = kite_plan(world, g);
    static bitboard threat{cambc::uninitialized}, near{cambc::uninitialized}, goals{cambc::uninitialized},
        basic{cambc::uninitialized}, stations{cambc::uninitialized}, forbidden{cambc::uninitialized},
        seen_stations{cambc::uninitialized}, basic_goals{cambc::uninitialized};
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    int ground_range = 0, unit_range = 0;
    for (const auto& a : f.abilities) {
        if (a.kind != AbilityKind::damage || a.multiplier <= 0) continue;
        if (a.target == Targeting::ground) ground_range = std::max(ground_range, a.range());
        if (a.target == Targeting::unit) unit_range = std::max(unit_range, a.range());
    }
    const int spell_reach = std::max(unit_range, ground_range > 0 ? ground_range + 1 : 0);
    // A unit spell needs sight of its target: its stations see the member, as ground stations do.
    bool ground_stations = ground_range > 0 && kites_with_spells(world.me()), unit_stations = !ground_stations && unit_range > 0;
    const int sight_range = ground_stations ? ground_range + 1 : unit_range;
    // The boards below depend on the group, these ranges and which members (ours and those of the
    // groups beside) live, not on health: a hit each turn keeps them. Prepared tiles are never dropped.
    static StationCache cache;
    // Champions whose spells hit no striker stand guard with the casters, for the fights and the capture.
    const bool guarding = station_reach(world.me()) < plan.reach;
    if (guarding) ground_stations = unit_stations = false;
    const bool same = cache.check(world, g, fresh, ground_stations, unit_stations, guarding, range, unit_range, ground_range);
    if (!same && !guarding && (ground_stations || unit_stations))
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            if ((!fresh && c.health[i] <= 0) || G.members[i].strength <= 0) continue;
            const bool ready = pathing.prepare_member(g, static_cast<int>(i), sight_range, end_reserve);
            world.throw_if_stale();
            // Prepared tiles are kept: the rest is made next turn, and the turn stays the kite's.
            if (!ready) {
                memory.claim = g;
                return true;
            }
        }
    // A ground cast reaches a member from ability_range + ground_radius: guards stand a step beyond
    // that, so that no caster's tile is theirs.
    const int cast_reach = ability_range + ground_radius;
    static bool attackers = false;
    if (!same) {
        clear_board(threat);
        clear_board(near);
        clear_board(basic);
        attackers = false;
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            if (!fresh && c.health[i] <= 0) continue;
            const vec2 p = G.members[i].pos;
            if (G.members[i].strength > 0) {
                attackers = true;
                draw_square(threat, p, static_cast<float>(G.members[i].reach));
                if (unit_stations) near |= pathing.member_attack_tiles(g, static_cast<int>(i), unit_range);
                if (ground_stations) {
                    const auto& viewers = pathing.member_attack_tiles(g, static_cast<int>(i), ground_range + 1);
                    if (unit_range > 0) {
                        clear_board(stations);
                        draw_square(stations, p, static_cast<float>(unit_range));
                        and_into(viewers, stations, seen_stations);
                        near |= seen_stations;
                    }
                    // Centres whose 3x3 would also hit (and wake) another live group are left out.
                    clear_board(forbidden);
                    for (const int other : map.groups_near(p, 2 * ground_radius)) {
                        if (other == g) continue;
                        cache.note(other);
                        if (world.camps[other].state != CampState::alive) continue;
                        const auto& members = map.groups[other].members;
                        for (std::size_t j = 0; j < members.size(); ++j)
                            if (world.camps[other].health[j] > 0) draw_square(forbidden, members[j].pos, ground_radius);
                    }
                    clear_board(stations);
                    for (int dy = -1; dy <= 1; ++dy)
                        for (int dx = -1; dx <= 1; ++dx) {
                            const vec2 centre{p.x + dx, p.y + dy};
                            if (in_bounds(centre) && !test(forbidden, centre)) draw_square(stations, centre, static_cast<float>(ground_range));
                        }
                    and_into(viewers, stations, seen_stations);
                    near |= seen_stations;
                }
            } else {
                draw_square(basic, p, static_cast<float>(range));
            }
        }
        if (guarding) {
            clear_board(near);
            clear_board(forbidden);
            for (std::size_t i = 0; i < G.members.size(); ++i) {
                if ((!fresh && c.health[i] <= 0) || G.members[i].strength <= 0) continue;
                draw_square(near, G.members[i].pos, static_cast<float>(cast_reach + 1));
                draw_square(forbidden, G.members[i].pos, static_cast<float>(cast_reach));
            }
            drop(near, forbidden);
        }
        world.throw_if_stale();
        cache.finish(world);
    }
    if (!attackers) return false; // only harmless members: farm clears them
    // A guard is wanted for the end of the clear, the fights and the capture: until then it farms. The
    // walk from our spawn, not from here, is the same from every tile on the way in.
    const int spawn_walk = map.ally_steps(g) != unreachable ? map.ally_steps(g) : dist(map.ally_spawn_centre, G.centre);
    if (guarding && plan.rounds > static_cast<float>(spawn_walk + params::kite_early)) return false;
    const int station_range = guarding ? cast_reach + 1 : ground_stations ? spell_reach : ability_range;
    and_into(near, map.standable, goals);
    drop(goals, threat);
    if (board_empty(goals)) return false;
    // The stations go to the casters claiming the group in index order (comms, the same from every
    // tile, unlike sight of who stands where): past the station tiles, kite has no work for us.
    if (!guarding) {
        std::uint32_t ahead = 0;
        for (const auto& a : world.allies)
            ahead += !a.is_self && a.index < world.me().index && comms::claim_of(world, a.index) == g && station_reach(a) >= plan.reach;
        if (ahead >= goals.count()) return false;
    }
    // Walk at the stations nobody we see stands on.
    if (!test(goals, here))
        if (const auto& free = free_tiles(goals); !board_empty(free)) copy_into(free, goals);
    memory.claim = g;
    memory.crew = ally_claims(world, g);
    // Ranged: where a basic attack also reaches a harmless member, if that is a safe walk away.
    and_into(basic, goals, basic_goals);
    const bool basic_first = f.ranged && !board_empty(basic_goals);
    const bool safe_here = !test(threat, here);
    const auto hit = [&] {
        if (fresh) return false;
        const bool cast = cast_at_camp(world, g, false, true);
        const bool attacked = attack_camp(world, [&](int h) { return h == g; }) >= 0;
        if (attacked) reset_and_attack_camp(world, g);
        return cast || attacked;
    };
    if (!safe_here && ground_stations && kite_productive_action(world, pathing, g, true)) {
        const bool hit_now = hit();
        const bool reset = reset_and_attack_camp(world, g);
        if (hit_now || reset) return true;
    }
    const auto& first = basic_first ? basic_goals : goals;
    if (safe_here) {
        const bool placed = test(first, here);
        if (hit()) return true;
        if (placed) {
            if (ground_stations && kite_productive_action(world, pathing, g)) {
                hit();
                reset_and_attack_camp(world, g);
            }
            return true;
        }
    }
    // Far off, the static walk to within reach; the live route around the monsters once near. With
    // the walk spent (a ranged attack after the strike search), none of it moves us.
    const bool walks = my_can_move();
    if (walks && dist(here, G.centre) > vision_radius + station_range) {
        if (const auto* field = pathing.approach(g, station_range)) {
            if (pathing.step_towards(*field)) return true;
        } else if (pathing.step_closer(G.centre)) return true;
        if (!ground_stations) return true;
    }
    // A short way to a basic attack's tile, else any safe one: the long way round to the far side
    // of the monsters costs more than the attacks pay.
    const int cap = 2 * (vision_radius + station_range);
    bool moved = walks && basic_first && pathing.step_towards(basic_goals, &threat, vision_radius);
    if (walks && !moved && !test(goals, here)) moved = pathing.step_towards(goals, &threat, cap);
    // A sleeping group hits nobody passing through its reach.
    if (walks && !moved && !test(goals, here) && c.awake == Awake::asleep) moved = pathing.step_towards(goals, nullptr, cap);
    // No way within the cap (round a lake): the static walk.
    if (walks && !moved && !test(goals, here))
        if (const auto* field = pathing.approach(g, station_range))
            moved = pathing.step_towards(*field, c.awake == Awake::asleep ? nullptr : &threat);
    if (walks && !moved && !safe_here) {
        static bitboard out{cambc::uninitialized};
        copy_into(map.standable, out);
        drop(out, threat);
        pathing.step_towards(out, nullptr, 2 * G.reach);
    }
    const bool hit_safe = !test(threat, my_position()) && hit();
    if (ground_stations && !moved && !hit_safe && safe_here && !test(goals, my_position())) return false;
    return true;
}

// Live big groups some ally's kite stations hit are kite()'s, not farm's.
bool kite_owns(const World& world, int g) { return big_group(world.map().groups[g]) && kite_plan(world, g).owned; }

// Where big groups fall to spells from out of reach (kite): a melee champion casts from there, and
// takes Focus for it, only if its damage spells out-damage its basic attacks a turn (with the
// reset's). Ryth's stunning ground spell does not unless it buys Focus, so it melees like a
// champion without spells.
bool kites_with_spells(const ChampionBelief& c) {
    const auto& f = c.facts();
    if (f.ranged) return true;
    float spells = 0;
    for (const auto& a : f.abilities)
        if (a.kind == AbilityKind::damage) spells += a.multiplier * c.focus / static_cast<float>(ability_cooldown);
    return spells > c.strength * (1 + (f.has_attack_reset() ? 1.0f / static_cast<float>(ability_cooldown) : 0.0f));
}

} // namespace

} // namespace aph
