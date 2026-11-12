#include "abilities.h"
#include <algorithm>
#include <array>
#include <optional>
#include <vector>
#include "../bot_parts.h"
#include "../emblems.h"
#include "../model/safety.h"
#include "../params.h"
#include "../model/pathing.h"
#include "../model/world.h"

namespace aph {

namespace {

// In enemy health points. A landing moves us off the goal's way and into the enemies' reach, which
// nothing here prices.
constexpr float min_landing_value = 250;

bool cast_walked(const World& world) { return my_position() != world.turn_start; }

// Landings a hidden unit failed this turn (the failed use spent nothing), kept off its next plans.
struct FailedLandings {
    bitboard tiles{cambc::uninitialized};
    int round = -1;
    std::uint32_t champion = 0;
};
FailedLandings& failed_landings() {
    static FailedLandings f;
    return f;
}

bool failed_this_turn(const World& world) {
    const auto& f = failed_landings();
    return f.round == world.round && f.champion == static_cast<std::uint32_t>(world.me().handle);
}

void note_failed_landing(vec2 p) {
    auto& f = failed_landings();
    const auto round = static_cast<int>(turn_round());
    const auto me = static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(cambc::self()));
    if (f.round != round || f.champion != me) clear_board(f.tiles), f.round = round, f.champion = me;
    set_tile(f.tiles, p);
}

bool landing_failed(const World& world, vec2 p) { return failed_this_turn(world) && test(failed_landings().tiles, p); }

// `off` and this turn's failed landings: the `also` of dash_landings_from.
const bitboard* landings_off(const World& world, const bitboard* off) {
    if (!failed_this_turn(world)) return off;
    if (!off) return &failed_landings().tiles;
    static bitboard both{cambc::uninitialized};
    or_into(*off, failed_landings().tiles, both);
    return &both;
}

bool castable(const World& world, int slot) {
    const auto& a = world.me().facts().abilities[slot];
    return a.hits_enemies() && !(a.excludes_walking && cast_walked(world)) && world.me().ability_ready(slot, world.round);
}

struct Cast {
    int slot = -1;
    float value = 0;
    std::optional<cambc::handle_champion_t> champion;
    std::optional<cambc::camp> camp;
    vec2 tile{-1, -1};
    bool dash = false; // a landing on `tile`

    void offer(const Cast& other) {
        if (other.slot >= 0 && other.value > value) *this = other;
    }
    bool execute() const {
        if (slot < 0) return false;
        try {
            if (champion) return cast_slot_on(slot, *champion);
            if (camp) return cast_slot_on(slot, static_cast<cambc::handle_camp_t>(*camp));
            const bool cast = cast_slot(slot, tile);
            outside_dashes() += cast && dash;
            // Refused without an error: a hidden unit holds the landing.
            if (!cast && dash) note_failed_landing(tile);
            return cast;
        } catch (const cambc::error&) {
            return false;
        }
    }
};

// A landing cast that a hidden unit failed is planned again without that landing; capped, for fuel, at
// the other champions (each failure is a different unit).
template <class Plan> bool execute_retrying(const World& world, Plan plan, bool* attempted = nullptr) {
    auto cast = plan();
    if (attempted) *attempted = cast.slot >= 0;
    for (int tries = static_cast<int>(world.allies.size() - 1 + world.enemies.size());; --tries) {
        world.throw_if_stale();
        if (cast.execute()) return true;
        if (!cast.dash || tries <= 0 || !landing_failed(world, cast.tile)) return false;
        cast = plan();
        if (cast.slot < 0) return false;
    }
}

float raw_damage(int slot) {
    try {
        return my_damage(slot);
    } catch (const cambc::error&) {
        return 0;
    }
}

// Health lost after mitigation and shields, capped at health. `native`: the engine's figure; else raw
// (which has Collectors) with Skirmish and the target's `taken`, shields aside.
float damage_to(int slot, cambc::handle_champion_t target, float raw, float taken, bool* native = nullptr) {
    if (native) *native = false;
    if (raw <= 0) return 0;
    try {
        const float damage = my_damage_to(slot, target);
        if (native) *native = true;
        return damage;
    } catch (const cambc::error&) {
        return std::min(raw * skirmish_dealt_factor() * taken, record_of(target).health);
    }
}

// hit_worth, and for damage short of a kill off its spawn, the recall it cancels.
float hit_worth_of(const World& world, const ChampionBelief& e, float damage, float health, bool on_spawn) {
    const float v = hit_worth(damage, health, on_spawn, params::gem_value * static_cast<float>(pair_gems(world, e)),
                              partner_bound(world, e), std::max(e.max_health, health));
    return damage > 0 && damage < health - 0.01f && !on_spawn && recall_kept(e) ? v + params::recall_value : v;
}

} // namespace

bool recall_kept(const ChampionBelief& e) {
    return e.channel == Channel::recall && e.visible && aph::kept_recall(e.handle, e.recall_turns());
}

float hit_worth(float damage, float health, bool spawn, float bag, float partner, float full) {
    if (health <= 0) return 0;
    if (damage >= health - 0.01f) return kill_distance(health, full, bag);
    if (spawn) return 0;
    const float left = std::min(health, partner), useful = useful_damage(damage, health, partner);
    // The rest still costs the body its own health, as any damage short of a kill does.
    return params::chip_value * (damage - useful) + kill_distance(left, full, bag) - kill_distance(left - useful, full, bag);
}

float kill_stops(const World& world, const ChampionBelief& e) {
    if (e.channel != Channel::tribute) return 0;
    // A tribute that ends the game is worth every gem of it.
    return params::tribute_value
           + (enemy_tribute_wins(world, e) ? params::gem_value * static_cast<float>(cambc::constants::winning_gems) : 0.0f);
}

float stun_worth(const World& world, const ChampionBelief& e, bool damaging) {
    if (e.facts().passive == Passive::stun_immune) return 0;
    // The turn it loses: in sight, what that turn's strike deals at our nearest body (cooldowns as
    // they will be then); else its damage a turn. A stunned tributer keeps its bag: the stun only
    // puts off its tribute, by the lost turn and a channel restarted whole.
    float v = output(e);
    if (e.visible && !e.cooldowns_uncertain()) {
        int d = dist(e.pos, my_position());
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible) d = std::min(d, dist(e.pos, a.pos));
        v = strike(e, next_turn_round(world, e)).at(d);
    }
    if (e.channel == Channel::tribute) {
        const int restart = next_turn_round(world, e) + 1;
        const int delay = std::max(1, restart + tribute_turns(e.gems, e.fast_tribute) - e.channel_end_round);
        v += kill_stops(world, e) + params::gem_value * static_cast<float>(e.gems) * static_cast<float>(delay) / params::stun_tribute_horizon;
    }
    if (!damaging && recall_kept(e)) v += params::recall_value;
    // A cancelled teleport wastes its channel and crystal, as a cancelled recall does.
    if (e.teleport_pending()) v += params::recall_value;
    return v;
}

bool landing_wakes(const World& world, vec2 p, int radius) {
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(p, radius)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0 || g == siege_group()) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i)
            if (c.health[i] > 0 && dist(p, groups[g].members[i].pos) <= radius) return true;
    }
    return false;
}

bool unseen_suicidal(const ChampionBelief& e, float health, float taken) {
    const float back = e.retaliation() * taken;
    return e.alive && !e.visible && e.tracked && back > 0 && back >= health && !board_empty(e.possible)
           && static_cast<int>(board_count(e.possible)) <= max_unseen_tiles;
}

namespace {

struct Target {
    vec2 pos;
    float weight; // chance the enemy is on this tile
    float worth;  // if hit
};

// The scratch vectors and boards here are kept across calls: allocating costs more than the work.

void draw_alive_members(const World& world, int g, bitboard& out, int radius = ground_radius) {
    const auto& members = world.map().groups[g].members;
    for (std::size_t i = 0; i < members.size(); ++i)
        if (world.camps[g].health[i] > 0) draw_square(out, members[i].pos, static_cast<float>(radius));
}

// Ground centres to skip: their 3x3 would hit a member of a sleeping group, which wakes whole,
// with a monster near us, or of a sleeping Monolith group other than the siege target. In a
// scratch board valid until the next call.
const bitboard& wake_risk(const World& world, vec2 here, int reach) {
    const auto& groups = world.map().groups;
    static bitboard risk{cambc::uninitialized};
    clear_board(risk);
    for (int g : world.map().groups_near(here, reach)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.fully_awake() || groups[g].strength <= 0) continue;
        bool near = groups[g].has_monolith && g != siege_group();
        for (std::size_t i = 0; i < groups[g].members.size() && !near; ++i)
            near = c.health[i] > 0 && groups[g].members[i].strength > 0 && c.maybe_asleep(i)
                   && dist(here, groups[g].members[i].pos) <= groups[g].members[i].reach;
        if (near) draw_alive_members(world, g, risk);
    }
    return risk;
}

// Centres within `range` of `here`, off `skip`. `harmful`: only centres whose 3x3 holds two of these.
Cast best_ground(int slot, float min_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip, const std::vector<vec2>* harmful = nullptr) {
    constexpr int max_range = ability_range; // every caller's range
    Cast best;
    if (targets.empty()) return best;
    range = std::min(range, max_range);
    const int side = 2 * range + 1;
    std::array<float, (2 * max_range + 1) * (2 * max_range + 1)> value;
    // Only the cells around a target are read: clear those alone when fewer.
    const auto around = [&](const Target& t, auto&& f) {
        for (int dy = -1; dy <= 1; ++dy)
            for (int dx = -1; dx <= 1; ++dx) {
                const int x = t.pos.x + dx - here.x + range, y = t.pos.y + dy - here.y + range;
                if (x >= 0 && x < side && y >= 0 && y < side) f(value[static_cast<std::size_t>(y * side + x)]);
            }
    };
    if (9 * targets.size() < static_cast<std::size_t>(side * side))
        for (const auto& t : targets) around(t, [](float& v) { v = 0; });
    else
        std::fill_n(value.begin(), side * side, 0.0f);
    static bitboard centres{cambc::uninitialized};
    clear_board(centres);
    for (const auto& t : targets) {
        if (dist(t.pos, here) > range + 1) continue; // no centre in range
        draw_square(centres, t.pos, 1);
        around(t, [&](float& v) { v += t.weight * t.worth; });
    }
    static bitboard box{cambc::uninitialized};
    clear_board(box);
    draw_square(box, here, static_cast<float>(range));
    and_into(centres, box, centres);
    drop(centres, skip);
    // In board order, which breaks ties.
    for (auto c : Tiles<17 * 17>{centres}) {
        const float v = value[(c.y - here.y + range) * side + (c.x - here.x + range)];
        if (!(v > best.value && v >= min_value)) continue;
        if (harmful) {
            int hits = 0;
            for (auto p : *harmful)
                if (dist(c, p) <= 1 && ++hits >= 2) break;
            if (hits < 2) continue;
        }
        best.slot = slot, best.value = v, best.tile = c;
    }
    return best;
}

// The landing that `keep` accepts whose `radius` around it hits most, nearest `here` on ties.
template <class Keep>
Cast best_landing(int slot, float min_value, const std::vector<Target>& targets, const bitboard& landings, vec2 here,
                  int radius, Keep keep) {
    Cast best;
    if (targets.empty()) return best;
    // Each cell adds its targets in their order, as summing per landing would.
    constexpr int reach = dash_range, side = 2 * reach + 1;
    std::array<float, side * side> value{};
    for (const auto& t : targets) {
        const int x0 = std::max(t.pos.x - radius, here.x - reach), x1 = std::min(t.pos.x + radius, here.x + reach);
        const int y0 = std::max(t.pos.y - radius, here.y - reach), y1 = std::min(t.pos.y + radius, here.y + reach);
        for (int y = y0; y <= y1; ++y)
            for (int x = x0; x <= x1; ++x) value[(y - here.y + reach) * side + (x - here.x + reach)] += t.weight * t.worth;
    }
    int best_dist = 0;
    for (auto p : Tiles<5 * 5>{landings}) {
        const int d = dist(p, here);
        const float v = value[(p.y - here.y + reach) * side + (p.x - here.x + reach)];
        if (v < min_value || v < best.value || (v == best.value && d >= best_dist) || !keep(p)) continue;
        best.slot = slot, best.value = v, best.tile = p, best.dash = true, best_dist = d;
    }
    return best;
}

// Our hit with one slot, against a Ren's retaliation.
struct SlotHit {
    int slot;
    float raw;            // before the target's mitigation
    float taken, health;  // ours; health with our shield, which absorbs the retaliation
    // A damaging hit on Ren costs its retaliation, as the plan search prices it.
    float back(const ChampionBelief& e) const { return raw > 0 ? e.retaliation() * taken : 0.0f; }
    bool suicidal(const ChampionBelief& e) const { return raw > 0 && e.retaliation() * taken >= health; }
};

// The enemies an area (ground cast or landing) could hit from `here`: visible ones within its
// reach, and tracked unseen ones on few tiles, weighted over them. Centres within the area's
// radius of a Ren whose retaliation kills us go in `off`; with `lethal`, those within it of a
// visible enemy the engine says the hit kills go there.
void area_targets(const World& world, const AbilityFacts& a, const SlotHit& hit, vec2 here, std::vector<Target>& targets,
                  bitboard& off, bitboard* lethal) {
    const int radius = a.lands() ? a.radius : ground_radius;
    const auto& enemy_spawn = world.map().enemy_spawn;
    targets.clear();
    clear_board(off);
    if (lethal) clear_board(*lethal);
    for (const auto& e : world.enemies) {
        if (!e.alive) continue;
        if (e.visible) {
            if (dist(here, e.pos) > a.reach()) continue;
            if (hit.suicidal(e)) {
                draw_square(off, e.pos, static_cast<float>(radius));
                continue;
            }
            const auto* live = visible_record(e.handle);
            if (!live) continue;
            const float health = live->health;
            bool native = false;
            const float damage = damage_to(hit.slot, e.handle, hit.raw, e.taken, lethal ? &native : nullptr);
            const float stun = health > 0 && damage >= health - 0.01f ? kill_stops(world, e)
                               : a.stuns && !e.stun_pending          ? stun_worth(world, e, hit.raw > 0)
                                                                     : 0;
            targets.push_back({e.pos, 1, hit_worth_of(world, e, damage, health, test(enemy_spawn, e.pos)) + stun - hit.back(e)});
            if (lethal && native && health > 0 && damage >= health) draw_square(*lethal, e.pos, static_cast<float>(radius));
        } else if (e.tracked && !board_empty(e.possible)) {
            const int n = static_cast<int>(board_count(e.possible));
            if (n > max_unseen_tiles) continue;
            const auto near = positions_within(e.possible, here, a.reach());
            if (near.empty()) continue;
            if (hit.suicidal(e)) {
                for (auto p : near) draw_square(off, p, static_cast<float>(radius));
                continue;
            }
            const float health = e.health > 0 ? e.health : e.max_health;
            const float damage = std::min(hit.raw * skirmish_dealt_factor() * e.taken, health);
            const float stun = damage >= health - 0.01f ? kill_stops(world, e) : a.stuns ? stun_worth(world, e, hit.raw > 0) : 0;
            // Off and on its spawn: the tiles differ only in that.
            const float off_spawn = hit_worth_of(world, e, damage, health, false) + stun - hit.back(e);
            const float on_spawn = hit_worth_of(world, e, damage, health, true) + stun - hit.back(e);
            for (auto p : near) targets.push_back({p, 1.0f / static_cast<float>(n), test(enemy_spawn, p) ? on_spawn : off_spawn});
        }
    }
}

// `escape_enemy`: see cast_at_enemies_for_escape.
Cast enemy_cast(const World& world, float walk, bool lethal_only = false, std::optional<int> escape_enemy = std::nullopt) {
    Cast best;
    if (!my_can_cast()) return best;
    const vec2 here = my_position();
    const auto& f = world.me().facts();
    // Most turns no enemy is in reach: skip the engine reads below.
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    int reach = -1;
    bool area = false;
    for (int s = 0; s < 2; ++s)
        if (ready[s]) reach = std::max(reach, f.abilities[s].reach()), area |= f.abilities[s].target == Targeting::ground || f.abilities[s].lands();
    int in_reach = 0;
    for (const auto& e : world.enemies)
        if (e.alive) in_reach += e.visible ? dist(here, e.pos) <= reach : area && e.tracked;
    if (in_reach == 0) return best;
    if (!my_can_move()) walk = 0;
    // A stun takes its target's walk as the cast takes ours: with every visible enemy that could
    // reach us next turn stunned, keeping the walk gains nothing.
    std::array<const ChampionBelief*, 16> reaching;
    int n_reaching = 0;
    bool unstoppable = false;
    if (walk > 0)
        for (const auto& e : world.enemies) {
            if (n_reaching == 16) break;
            if (!e.alive || !e.visible || !strike(e, next_turn_round(world, e)).hits(dist(here, e.pos))) continue;
            if (!visible_record(e.handle) || e.stun_pending) continue;
            unstoppable |= e.facts().passive == Passive::stun_immune;
            reaching[n_reaching++] = &e;
        }
    const bool walk_matters = n_reaching == 0 || unstoppable;
    static bitboard not_free{cambc::uninitialized}; // ground centres whose 3x3 misses a reaching enemy
    if (!walk_matters) {
        static bitboard free_stun{cambc::uninitialized}, around{cambc::uninitialized};
        clear_board(free_stun);
        draw_square(free_stun, reaching[0]->pos, 1);
        for (int i = 1; i < n_reaching; ++i) {
            clear_board(around);
            draw_square(around, reaching[i]->pos, 1);
            and_into(free_stun, around, free_stun);
        }
        not_into(free_stun, not_free);
    }
    const SlotHit base{0, 0, world.me().taken, my_health_and_shield(world)};
    const bitboard* risk = nullptr;
    for (int s = 0; s < 2; ++s) {
        if (!ready[s]) continue;
        const auto& a = f.abilities[s];
        if (lethal_only && !a.lands() && a.target != Targeting::unit) continue;
        // The escape proofs below: a unit cast, or a ground stun centred within 1 of the sole threat,
        // which hits it wherever the centre is.
        const bool escaping = escape_enemy && a.excludes_walking;
        const ChampionBelief* threat = nullptr;
        if (escaping && a.target != Targeting::unit) {
            if (a.target != Targeting::ground || !a.stuns || *escape_enemy < 0) continue;
            const auto& e = world.enemies[static_cast<std::size_t>(*escape_enemy)];
            if (!e.alive || !e.visible || e.stun_pending || e.facts().passive == Passive::stun_immune
                || turns_before_ours(world, e) != 1 || dist(here, e.pos) > a.range() + 1)
                continue;
            threat = &e;
        }
        const float threshold = cast_cost + (a.excludes_walking ? walk : 0.0f);
        SlotHit hit = base;
        hit.slot = s, hit.raw = raw_damage(s);
        if (a.target == Targeting::unit) {
            for (const auto& e : world.enemies) {
                if (!e.alive || !e.visible || dist(here, e.pos) > a.range() || (escaping && e.index != *escape_enemy) || hit.suicidal(e))
                    continue;
                const auto* live = visible_record(e.handle);
                if (!live) continue;
                const float health = live->health;
                bool native = false;
                const float damage = damage_to(s, e.handle, hit.raw, e.taken, escape_enemy || lethal_only ? &native : nullptr);
                if (lethal_only && !(native && health > 0 && damage >= health)) continue;
                const bool stuns = a.stuns && !e.stun_pending;
                // Escaping, a walk-excluding cast must kill the sole threat or stun it before it acts:
                // a stun takes its next turn, later this round or next round's before ours.
                if (escaping) {
                    const bool kills = native && health > 0 && damage >= health;
                    const bool controls = stuns && e.facts().passive != Passive::stun_immune && turns_before_ours(world, e) == 1;
                    if (!kills && !controls) continue;
                }
                const bool dies = health > 0 && damage >= health - 0.01f;
                const float v = hit_worth_of(world, e, damage, health, test(world.map().enemy_spawn, e.pos))
                                + (dies ? kill_stops(world, e) : stuns ? stun_worth(world, e, hit.raw > 0) : 0.0f) - hit.back(e);
                const bool free = a.stuns && !walk_matters && n_reaching == 1 && reaching[0] == &e;
                if (v >= (free ? cast_cost : threshold) && v > best.value) best = Cast{s, v, e.handle, std::nullopt, {}};
            }
            continue;
        }
        static std::vector<Target> targets;
        static bitboard off{cambc::uninitialized}, lethal{cambc::uninitialized};
        area_targets(world, a, hit, here, targets, off, lethal_only ? &lethal : nullptr);
        if (targets.empty()) continue;
        if (a.lands()) {
            // It moves us: worth at least min_landing_value, whatever walk it replaces.
            const bitboard* landings = &dash_landings_from(world.map(), here, landings_off(world, &off));
            if (lethal_only) {
                static bitboard eligible{cambc::uninitialized};
                and_into(*landings, lethal, eligible);
                landings = &eligible;
            }
            best.offer(best_landing(s, min_landing_value, targets, *landings, here, a.radius,
                                    [&](vec2 p) { return !landing_wakes(world, p, a.radius); }));
        } else {
            if (!risk) risk = &wake_risk(world, here, a.reach());
            static bitboard skip{cambc::uninitialized};
            or_into(*risk, off, skip);
            if (threat) {
                static bitboard far{cambc::uninitialized};
                clear_board(far);
                draw_square(far, threat->pos, 1);
                not_into(far, far);
                or_into(skip, far, skip);
            }
            best.offer(best_ground(s, threshold, targets, here, a.range(), skip));
            // A stun on every reaching enemy needs only cast_cost.
            if (a.stuns && threshold > cast_cost && !walk_matters) {
                or_into(skip, not_free, skip);
                best.offer(best_ground(s, cast_cost, targets, here, a.range(), skip));
            }
        }
    }
    return best;
}

// Other live groups' monsters that would reach a landing (within dash_range of `here`) but do not
// reach `here`, in a scratch vector.
struct MonsterReach {
    vec2 pos;
    int reach;
};
const std::vector<MonsterReach>& landing_threats(const World& world, int group, vec2 here) {
    static std::vector<MonsterReach> threats;
    threats.clear();
    const auto& map = world.map();
    for (int other : map.groups_near(here, map.max_camp_reach + dash_range)) {
        if (other == group || world.camps[other].state != CampState::alive) continue;
        const auto& ms = map.groups[other].members;
        for (std::size_t i = 0; i < ms.size(); ++i) {
            const int d = dist(here, ms[i].pos);
            if (world.camps[other].health[i] > 0 && ms[i].strength > 0 && d > ms[i].reach && d <= ms[i].reach + dash_range)
                threats.push_back({ms[i].pos, ms[i].reach});
        }
    }
    return threats;
}

// `approach`: see cast_at_camp_on_approach.
Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value, bool approach = false) {
    if (!my_can_cast()) return {};
    const auto& f = world.me().facts();
    const std::array<bool, 2> ready{castable(world, 0), castable(world, 1)};
    if (!ready[0] && !ready[1]) return {};
    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];
    const auto& belief = world.camps[group];
    const bool harmless_approach = approach && g.strength <= 0;
    if ((g.has_monolith && group != siege_group()) || belief.state != CampState::alive) return {};
    if (engagement_near(world, here, f.cast_reach())) return {};
    // A ranged walk also spends the basic: require our native position to be unchanged.
    const bool post_basic = !approach && !attackers_only && !my_can_attack() && !cast_walked(world);
    bool all_visible = post_basic;

    struct Member {
        int index; // in the group
        vec2 pos;
        float health, stun;
        bool harmful;
    };
    static std::vector<Member> members;
    static std::vector<vec2> harmful;
    members.clear();
    harmful.clear();
    // Members beyond every ready slot's hit are no target. They still decide sole_finish (all
    // visible, one alive), read only until it is settled false, and an attackers-only floor.
    int reach = 0;
    for (int s = 0; s < 2; ++s)
        if (const auto& a = f.abilities[s]; ready[s])
            reach = std::max(reach, a.lands() ? dash_range + a.radius
                                    : a.target == Targeting::unit ? a.range()
                                                                  : std::min(a.range(), ability_range) + ground_radius);
    int live = 0;
    for (int i = 0; i < static_cast<int>(g.members.size()); ++i) {
        const auto& m = g.members[i];
        const bool target = attackers_only || dist(here, m.pos) <= reach;
        if (!target && !(all_visible && live < 2)) continue;
        all_visible = all_visible && test(world.visible, m.pos);
        if ((!post_basic && belief.health[i] <= 0) || (attackers_only && m.strength <= 0) || !cambc::vision::has_camp(m.pos)) continue;
        static cambc::detail::camp_state record;
        const auto code = cambc::detail::sdk_camp(m.handle, &record);
        if (code == static_cast<std::int32_t>(cambc::error_code::api_not_in_vision)
            || code == static_cast<std::int32_t>(cambc::error_code::api_not_found)) {
            all_visible = false;
            continue;
        }
        ok(code);
        const float health = record.health;
        if (health <= 0) continue;
        ++live;
        if (!target) continue;
        // A stunned monster skips its next attack, which goes to the nearest champion: one of us
        // when any of us is in its reach, enemies being held off above.
        float stun = 0;
        if (stuns && m.strength > 0) {
            bool exposed = dist(here, m.pos) <= m.reach;
            for (std::size_t k = 0; k < world.allies.size() && !exposed; ++k) {
                const auto& ally = world.allies[k];
                exposed = ally.alive && ally.visible && dist(ally.pos, m.pos) <= m.reach;
            }
            // A stun at timer 0 was spent on this round's camp phase; a new one still skips the next.
            if (exposed && !camp_stunned(m.handle)) stun = m.strength;
        }
        const bool harms = m.strength > 0;
        members.push_back({i, m.pos, health, stun, harms});
        if (approach && harms) harmful.push_back(m.pos);
    }
    if (members.empty()) return {};
    // A spell clear has no basic attack to finish an attacker under the usual floor: it would stand
    // idle beside it for good. Every damage spell's raw exceeds the floor, so only finishing casts pass.
    float floor_value = cast_cost;
    if (attackers_only)
        for (const auto& m : members) floor_value = std::min(floor_value, m.health);
    const bool sole_finish = all_visible && live == 1;
    // Native raw includes outgoing passives and Collectors, but not Monster, which depends on the target.
    const float dealt = monster_dealt_factor();

    Cast best;
    for (int s = 0; s < 2; ++s) {
        const auto& a = f.abilities[s];
        if (!ready[s] || (harmless_approach && a.target != Targeting::ground)) continue;
        const float raw = raw_damage(s), dealt_raw = raw * dealt;
        const bool finishes = sole_finish && !a.lands() && dealt_raw >= members[0].health;
        const float floor = finishes ? 0.0f : any_value ? 1.0f : floor_value;
        const auto worth = [&](const Member& m) { return std::min(dealt_raw, m.health) + (a.stuns ? m.stun : 0); };
        if (a.target == Targeting::unit) {
            for (const auto& m : members) {
                if ((approach && !m.harmful) || dist(here, m.pos) > a.range()) continue;
                if (const float v = worth(m); v >= floor && v > best.value) best = Cast{s, v, std::nullopt, g.camp(m.index), {}};
            }
            continue;
        }
        // A ground cast or a landing; a dash off a cleared group gives up its capture.
        if (a.lands())
            if (const int at = world.map().group_at(here); at >= 0 && world.camps[at].state == CampState::cleared) continue;
        const int radius = a.lands() ? a.radius : ground_radius;
        static std::vector<Target> targets;
        targets.clear();
        for (const auto& m : members) targets.push_back({m.pos, 1, worth(m)});
        // Off other groups. Visible enemies are held off above; the area also hits unseen ones, so
        // keep it off a tracked Ren whose retaliation kills us, as enemy_cast does.
        static bitboard skip{cambc::uninitialized};
        clear_board(skip);
        for (int other : world.map().groups_near(here, a.reach()))
            if (other != group && world.camps[other].state == CampState::alive) draw_alive_members(world, other, skip, radius);
        if (raw > 0) {
            const float health = my_health_and_shield(world);
            for (const auto& e : world.enemies)
                if (unseen_suicidal(e, health, world.me().taken))
                    for (auto p : positions_within(e.possible, here, a.reach())) draw_square(skip, p, static_cast<float>(radius));
        }
        if (a.lands()) {
            // Not into the reach of another group's monsters.
            const auto& threats = landing_threats(world, group, here);
            best.offer(best_landing(s, floor, targets, dash_landings_from(world.map(), here, landings_off(world, &skip)), here, a.radius, [&](vec2 p) {
                for (const auto& t : threats)
                    if (dist(p, t.pos) <= t.reach) return false;
                return true;
            }));
        } else {
            best.offer(best_ground(s, floor, targets, here, a.range(), skip, approach && !harmless_approach ? &harmful : nullptr));
        }
    }
    // A unit cast overkilling a harmless group's last health goes to another harmless group in range.
    if (const int s = best.slot; s >= 0 && post_basic && !any_value && g.strength <= 0 && f.abilities[s].target == Targeting::unit) {
        const float raw = raw_damage(s) * dealt;
        if (best.value >= raw) return best;
        const auto& map = world.map();
        const int range = f.abilities[s].range();
        for (int other : map.groups_near(here, range)) {
            const auto& og = map.groups[other];
            if (other == group || og.has_monolith || og.strength > 0 || world.camps[other].state != CampState::alive) continue;
            for (int i = 0; i < static_cast<int>(og.members.size()); ++i) {
                const auto& m = og.members[i];
                if (dist(here, m.pos) > range || !test(world.visible, m.pos)) continue;
                static cambc::detail::camp_state record;
                if (cambc::detail::sdk_camp(m.handle, &record) != 0 || !(record.health > 0)) continue;
                if (const float v = std::min(raw, record.health); v > best.value) best = Cast{s, v, std::nullopt, og.camp(i), {}};
                if (best.value >= raw) return best;
            }
        }
    }
    return best;
}

template <class Plan> bool execute_camp_cast(const World& world, Plan plan) {
    const bool cast = execute_retrying(world, plan);
    world.throw_if_stale();
    camp_hits() += cast;
    return cast;
}

} // namespace

bool enemy_tribute_wins(const World& world, const ChampionBelief& e) {
    if (!e.alive || !e.visible || e.channel != Channel::tribute) return false;
    const int need = static_cast<int>(cambc::constants::winning_gems) - world.score.enemy;
    if (e.gems >= need) return true;
    const auto win = enemy_tributes_win(world);
    if (!win || win->lands < turn_start(world, e, e.channel_end_round)) return false;
    // Of the tributes landing by the win, those whose stop keeps it short; with none, every one must be stopped.
    if (win->gems - e.gems < need) return true;
    for (const auto& o : world.enemies)
        if (o.alive && o.visible && o.channel == Channel::tribute && !(win->lands < turn_start(world, o, o.channel_end_round))
            && win->gems - o.gems < need)
            return false;
    return true;
}

bool cast_at_enemies(const World& world, float walk, bool lethal_only, bool* attempted) {
    world.throw_if_stale();
    if (attempted) *attempted = false;
    try {
        return execute_retrying(world, [&] { return enemy_cast(world, walk, lethal_only); }, attempted);
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_enemies_for_escape(const World& world, int enemy, float walk, bool& attempted) {
    world.throw_if_stale();
    attempted = false;
    try {
        const bool accepted = execute_retrying(world, [&] { return enemy_cast(world, walk, false, enemy); }, &attempted);
        world.throw_if_stale();
        return accepted;
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value) {
    world.throw_if_stale();
    try {
        return execute_camp_cast(world, [&] { return camp_cast(world, group, attackers_only, any_value); });
    } catch (const cambc::error&) {
        return false;
    }
}

bool cast_at_camp_on_approach(const World& world, int group) {
    world.throw_if_stale();
    // A ranged champion whose casts outreach its attack hits from beyond it on the way in.
    if (const auto& f = world.me().facts(); !f.ranged || f.cast_reach() <= f.attack_range()
        || (!world.me().ability_ready(0, world.round) && !world.me().ability_ready(1, world.round))
        || !my_can_cast() || cast_walked(world))
        return false;
    const auto& c = world.camps[group];
    if (c.state != CampState::alive) return false;
    const auto& map = world.map();
    const auto& g = map.groups[group];
    const bool harmless = g.strength <= 0;
    // A harmless group is worth a cast only on two members; an attacker group only once awake.
    if (harmless ? g.members.size() <= 1 : c.awake != Awake::awake) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    // Not once the basic attack reaches a member, nor from inside any monster's reach.
    for (std::size_t i = 0; i < g.members.size(); ++i)
        if ((harmless || c.health[i] > 0) && dist(here, g.members[i].pos) <= range && cambc::vision::has_camp(g.members[i].pos))
            return false;
    for (int other : map.groups_near(here, map.max_camp_reach)) {
        if (world.camps[other].state != CampState::alive) continue;
        const auto& members = map.groups[other].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (world.camps[other].health[i] > 0 && members[i].strength > 0 && dist(here, members[i].pos) <= members[i].reach)
                return false;
    }
    try {
        return execute_camp_cast(world, [&] { return camp_cast(world, group, false, false, true); });
    } catch (const cambc::error&) {
        return false;
    }
}

} // namespace aph
