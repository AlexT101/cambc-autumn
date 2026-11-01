// Team sieges of Monoliths and altar-sealing groups, and kites of big shared groups.
#include "../bot_parts.h"
#include "../trace.h"

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
};

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
        const auto& c = world.camps[g];
        // Off Monolith-only maps a live Monolith counts only if it seals, the enemy is sieging it or
        // the team clears it in a burst. Members of farm's crew operation on a Monolith stay farm's
        // (allies join an operation through farm, so an ally's claim alone is no siege).
        if (!map.monolith_only && !seal && farm_op) return;
        const bool join = !map.monolith_only && !seal && c.state == CampState::alive && c.awake != Awake::asleep
                          && (enemy_in_reach(world, g) || (memory.siege && memory.claim == g));
        const bool burst = !map.monolith_only && !seal && !join && c.state == CampState::alive
                           && siege_load(world, g).health <= team_power(world) * static_cast<float>(params::burst_rounds);
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
        if (best.g < 0 || cost < best_cost) best = {g, seal, join, burst}, best_cost = cost;
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

// The team's clear, at its current output, is quick enough and costs no more health than it can take.
bool siege_ready(const World& world, const SiegeTarget& target, const SiegeLoad& load, bool committed) {
    if (load.health <= 0) return true;
    const float rounds = load.health / team_power(world);
    const float slack = committed ? params::siege_commit_slack : 1.0f;
    const float limit = world.map().monolith_only || target.sealing || target.joining ? params::siege_rounds
                        : target.bursting ? params::burst_rounds : 0;
    if (rounds > limit * slack) return false;
    // While the enemy is in its reach, their bodies take the hits.
    if (target.joining && enemy_in_reach(world, target.g)) return true;
    float pool = 0;
    for (const auto& a : world.allies)
        if (a.alive) pool += a.max_health;
    return rounds * load.hit * camp_hit_factor() * params::siege_hit_share <= params::siege_pool_share * pool * slack;
}

bool stop_siege(Memory& memory) {
    memory.siege = false;
    memory.staged_since = -1;
    return false;
}

// Once the team is strong enough it goes together: melee adjacent, ranged at their range, the hurt
// stepping out to 4, where casters still cast.
bool siege(const World& world, Pathing& pathing, Memory& memory) {
    TRACE_SITE("siege");
    world.throw_if_stale();
    sieged = true;
    const auto& map = world.map();
    const auto target = siege_candidate(world, pathing, memory);
    const int g = target.g;
    if (g < 0) return stop_siege(memory);
    const bool ally_in = ally_claims(world, g);
    const auto load = siege_load(world, g);
    if (!siege_ready(world, target, load, (memory.siege && memory.claim == g) || ally_in)) {
        debug_block({
            if (memory.siege)
                trace::ev("siege", "g=%d ready=0 seal=%d join=%d burst=%d health=%.0f hit=%.0f ally_in=%d", g, target.sealing ? 1 : 0, target.joining ? 1 : 0,
                          target.bursting ? 1 : 0, static_cast<double>(load.health), static_cast<double>(load.hit), ally_in ? 1 : 0);
        });
        return stop_siege(memory);
    }
    const auto& G = map.groups[g];
    const auto& c = world.camps[g];
    const vec2 here = my_position();
    if (c.state == CampState::cleared) {
        // The nearest take the capture, split to shorten the tributes; the rest farm.
        if (capture_taken(world, g, here)) return stop_siege(memory);
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
    // The members that hit us here: each hits the nearest champion in its reach, so not one with a
    // visible ally strictly nearer it (ties count against us). An ally recalling home before our
    // next turn or teleporting is no cover.
    float hit = 0, biggest = 0;
    int steps_out = 1;
    // Scratch boards: allocating one costs more than the host operations on it.
    static bitboard inner{cambc::uninitialized}, goals{cambc::uninitialized}, all{cambc::uninitialized};
    clear_board(inner); // ranged: too near a live member to stand at full range
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (c.health[i] <= 0 && !fresh) continue;
        const auto& member = G.members[i];
        if (range > 1) draw_square(inner, member.pos, static_cast<float>(range - 1));
        const int d = dist(here, member.pos);
        if (member.strength <= 0 || d > member.reach) continue;
        bool covered = false;
        for (const auto& a : world.allies)
            covered |= !a.is_self && a.alive && a.visible && a.channel != Channel::teleport
                       && !(real_recall(a) && a.channel_end_round <= world.round + 1) && dist(a.pos, member.pos) < d;
        if (covered) continue;
        const float h = member.strength * camp_hit_factor();
        hit += h;
        biggest = std::max(biggest, h);
        steps_out = std::max(steps_out, member.reach + 1 - d);
    }
    // Leave while we can still walk out of reach: the hits on us for each step out, and a round's slack.
    // Targeted by none, we stand and hit; if the tank leaves, we are the target next turn.
    const bool low = hit > 0 && my_health() < hit * static_cast<float>(steps_out) + biggest;
    debug_block({
        trace::ev("siege", "g=%d ready=1 seal=%d join=%d burst=%d health=%.0f engaged=%d fresh=%d staged=%.0f since=%d hit=%.0f low=%d tanked=%d caster=%d",
                  g, target.sealing ? 1 : 0, target.joining ? 1 : 0, target.bursting ? 1 : 0, static_cast<double>(load.health), engaged ? 1 : 0,
                  fresh ? 1 : 0, static_cast<double>(staged), memory.staged_since, static_cast<double>(hit), low ? 1 : 0, tanked ? 1 : 0,
                  caster ? 1 : 0);
    });

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
    if (!engaged || fresh) {
        tiles(stage, goals, false);
        drop(goals, G.threat());
    } else if (low) {
        // Out of reach, the turn's recall is kept for a heal trip (siege_heal_trip); a caster
        // healthy enough stays at spell range to cast.
        tiles(caster && my_health() >= params::heal_trip_fraction * my_max_health() ? ability_range : stage,
              goals, false);
        drop(goals, G.threat());
    } else if (f.ranged && caster && !tanked) {
        // With no ally nearer the Monolith to take its hits, cast from out of its reach.
        tiles(ability_range, goals);
        drop(goals, G.threat());
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
    if (board_empty(goals)) {
        draw_square(goals, m, static_cast<float>(stage));
        goals &= map.standable;
        drop(goals, G.threat());
    }
    if (!test(goals, here)) {
        // Live routes walk round hole lines: a seal off the walk from spawn is reached down our
        // approach field, dashes included, as farm walks.
        if (!pathing.step_towards_funded(goals, end_reserve) && target.sealing && map.ally_steps(g) == unreachable)
            if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve))
                dash_across(world, pathing, *field) || pathing.descend(*field, &G.threat(), G.centre)
                    || pathing.step_towards(*field, &G.threat(), G.centre);
        if (engaged && !low) attack_camp(world, [&](int h) { return h == g; });
        if (engaged) cast_at_camp(world, g);
        if (engaged && !low) reset_and_attack_camp(world, g);
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
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (c.health[i] <= 0) continue;
        const auto& m = G.members[i];
        // kite prepared range-5 viewers for the harmful members only; building one is too dear, so
        // a harmless member near enough to matter ends the search.
        if (m.strength <= 0) {
            if (dist(here, m.pos) <= ability_range + 1) return false;
            continue;
        }
        const auto& viewers = pathing.member_attack_tiles(g, static_cast<int>(i), ability_range + 1);
        std::uint16_t visible = 0;
        for (int k = 0; k < count; ++k)
            if (test(viewers, endpoints[k])) visible |= std::uint16_t{1} << k;
        targets.push_back({m.pos, c.health[i], m.strength, visible});
    }
    if (targets.empty()) return false;
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
    const float stay = damage(0) - heal_rounds(world, exposure(here, true), static_cast<float>(home_steps)) * lost_output;
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
        const float gain = damage(k) - heal_rounds(world, exposure(endpoints[k], true), static_cast<float>(home_steps + 1)) * lost_output;
        if (gain > value) best = k, value = gain;
    }
    if (best == 0) return false;
    world.throw_if_stale();
    const bool moved = pathing.try_move(endpoints[best]);
    world.throw_if_stale();
    return moved;
}

// kite()'s stations hit the monsters: a unit damage spell, or a ground one cast from out of reach.
bool casts_from_stations(const ChampionBelief& c) {
    for (const auto& a : c.facts().abilities)
        if (a.kind == AbilityKind::damage && a.multiplier > 0
            && (a.target == Targeting::unit || (a.target == Targeting::ground && kites_with_spells(c))))
            return true;
    return false;
}

// A big group cleared by stationary spells out of its monsters' reach, so that nobody takes a hit;
// harmless members fall to basic attacks from there, the rest once the monsters are dead.
bool kite(const World& world, Pathing& pathing, Memory& memory) {
    TRACE_SITE("kite");
    world.throw_if_stale();
    const auto& map = world.map();
    const vec2 here = my_position();
    // Without a caster the stations only stand guard: nobody would ever hit the monsters, so farm takes the live groups.
    bool casters = false;
    for (const auto& a : world.allies) casters = casters || casts_from_stations(a);
    int g = -1, best_cost = 0;
    // contest_capture's rule: a body of ours on a camp tile before their hold pays.
    const auto too_late = [&](int h) { return steps_to(map.groups[h], here) > enemy_hold_left(world, world.camps[h]); };
    for (int h = 0; h < static_cast<int>(map.groups.size()); ++h) {
        if (!big_group(map.groups[h])) continue;
        const auto& c = world.camps[h];
        if (!casters && c.state != CampState::cleared) continue;
        const int steps = dist(here, map.groups[h].centre);
        if (c.state == CampState::cleared && ((c.holder == team::enemy && too_late(h)) || contest_manned(world, h, here))) continue;
        const int wait = c.state == CampState::respawning ? c.respawn_round - world.round : 0;
        if (wait > steps + params::kite_early) continue;
        const int cost = std::max(steps, wait);
        if (g < 0 || cost < best_cost) g = h, best_cost = cost;
    }
    if (g < 0) return false;
    debug_block({ trace::ev("kite", "g=%d cost=%d casters=%d state=%d", g, best_cost, casters ? 1 : 0, static_cast<int>(world.camps[g].state)); });
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
        if (capture_taken(world, g, here) || dist(here, G.centre) > 2 * vision_radius) return false;
        memory.claim = g;
        memory.crew = false;
        pathing.step_towards_funded(G.tiles(), end_reserve);
        return true;
    }
    const bool fresh = c.state == CampState::respawning;
    static bitboard threat{cambc::uninitialized}, near{cambc::uninitialized}, goals{cambc::uninitialized},
        basic{cambc::uninitialized}, stations{cambc::uninitialized}, forbidden{cambc::uninitialized},
        seen_stations{cambc::uninitialized};
    clear_board(threat);
    clear_board(near);
    clear_board(basic);
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
    if (ground_stations || unit_stations)
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            if ((!fresh && c.health[i] <= 0) || G.members[i].strength <= 0) continue;
            const bool ready = pathing.prepare_member(g, static_cast<int>(i), sight_range, end_reserve);
            world.throw_if_stale();
            if (!ready) {
                ground_stations = unit_stations = false;
                break;
            }
        }
    const int station_range = ground_stations ? spell_reach : ability_range;
    bool attackers = false;
    for (std::size_t i = 0; i < G.members.size(); ++i) {
        if (!fresh && c.health[i] <= 0) continue;
        const vec2 p = G.members[i].pos;
        if (G.members[i].strength > 0) {
            attackers = true;
            draw_square(threat, p, static_cast<float>(G.members[i].reach));
            if (unit_stations) near |= pathing.member_attack_tiles(g, static_cast<int>(i), unit_range);
            // Champions without spells stand guard with the casters, for the fights and the capture.
            else if (!ground_stations) draw_square(near, p, static_cast<float>(station_range));
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
                    if (other == g || world.camps[other].state != CampState::alive) continue;
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
    world.throw_if_stale();
    if (!attackers) return false; // only harmless members: farm clears them
    const bool ally_in = ally_claims(world, g);
    memory.claim = g;
    memory.crew = ally_in;
    and_into(near, map.standable, goals);
    drop(goals, threat);
    if (board_empty(goals)) return false;
    // Ranged: where a basic attack also reaches a harmless member, if that is a safe walk away.
    basic &= goals;
    const bool basic_first = f.ranged && !board_empty(basic);
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
    const auto& first = basic_first ? basic : goals;
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
    bool moved = walks && basic_first && pathing.step_towards(basic, &threat, vision_radius);
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
