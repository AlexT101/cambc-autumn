#include "self_abilities.h"
#include <algorithm>
#include <array>
#include <bit>
#include <optional>
#include <vector>
#include "abilities.h"
#include "champions.h"
#include "params.h"
#include "pathing.h"
#include "plan.h"
#include "safety.h"
#include "world.h"

namespace aph {

namespace {

constexpr int dash_steps = 2;
constexpr int reset_hold_margin = 2;      // an enemy this far beyond attack range keeps the reset off camps
constexpr int travel_dash_clearance = 10; // no visible enemy this close for a travel dash
constexpr float heal_min_share = 0.6f;    // of the heal amount restored
constexpr float heal_low_health = 0.5f;
constexpr float dash_min_health = 0.5f;
constexpr float chase_health = 0.4f;
constexpr int failed_search_pause = 4; // rounds without a travel-dash search after one finds no gain

std::optional<cambc::ability> ready(const World& world, AbilityKind kind) {
    const auto& self = world.me();
    const int slot = self.facts().slot_of(kind);
    // The belief is exact for ourselves at turn start; only a Vendetta kill readies a slot mid-turn.
    if (slot < 0 || !self.alive
        || (!self.ability_ready(slot, world.round) && self.facts().passive != Passive::reset_on_kill))
        return std::nullopt;
    auto& me = cambc::self();
    if (!my_can_cast()) return std::nullopt;
    auto ability = me.abilities()[slot];
    if (ability.cooldown() > 0) return std::nullopt;
    return ability;
}

template <class... Target> bool cast(const cambc::ability& ability, const Target&... target) {
    try {
        return ability.use(target...);
    } catch (const cambc::error&) {
        return false;
    }
}

float health_fraction(const cambc::champion& c) { return c.health() / c.max_health(); }

struct Hazard {
    vec2 pos;
    int reach;
    bool camp;
};

// Enemies and awake monsters that could reach a tile within a dash of `here` before our next turn.
// A scratch vector, valid until the next call: allocating costs more than the work.
const std::vector<Hazard>& threats_near(const World& world, vec2 here) {
    static std::vector<Hazard> out;
    out.clear();
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int reach = threat_strike(world, e).reach;
        if (reach >= 0 && dist(here, e.pos) <= reach + dash_steps) out.push_back({e.pos, reach, false});
    }
    const auto& groups = world.map().groups;
    for (int g : world.map().groups_near(here, world.map().max_camp_reach + dash_steps)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] > 0 && m.strength > 0 && !c.member_asleep(i) && dist(here, m.pos) <= m.reach + dash_steps)
                out.push_back({m.pos, m.reach, true});
        }
    }
    return out;
}

// How deep a tile sits inside the threats' reach.
int danger(const std::vector<Hazard>& threats, vec2 p) {
    int d = 0;
    for (const auto& t : threats) {
        const int depth = t.reach - dist(p, t.pos) + 1;
        if (depth > 0) d += t.camp ? 2 : depth;
    }
    return d;
}

// A hidden unit on a landing fails the cast without spending it, and a guarded one is skipped, so a
// few are tried.
struct Landings {
    static constexpr int tries = 6;
    std::array<vec2, tries> tiles;
    int count = 0;
};

// The first landings in increasing `score`, ties in board order, keeping only those `keep` accepts.
template <class Score, class Keep> Landings ranked(const bitboard& landings, Score score, Keep keep) {
    Landings out;
    std::array<int, Landings::tries> scores{};
    for (auto p : Tiles<5 * 5>{landings}) {
        const int s = score(p);
        if (!keep(p, s)) continue;
        int i = out.count < Landings::tries ? out.count++ : Landings::tries;
        for (; i > 0 && scores[i - 1] > s; --i)
            if (i < Landings::tries) out.tiles[i] = out.tiles[i - 1], scores[i] = scores[i - 1];
        if (i < Landings::tries) out.tiles[i] = p, scores[i] = s;
    }
    return out;
}

// Heart of Ruin's landing hits camps beside it: keep it off sleeping groups that strike.
bool wakes_camp(const World& world, vec2 p) {
    const int slot = world.me().facts().slot_of(AbilityKind::dash);
    return slot >= 0 && world.me().facts().abilities[slot].lands() && landing_wakes(world, p, world.me().facts().abilities[slot].radius);
}

bool dash_to_first(const cambc::ability& dash, Pathing& pathing, const Landings& landings) {
    for (int i = 0; i < landings.count; ++i)
        if (pathing.landing_clear(landings.tiles[i]) && cast(dash, landings.tiles[i])) {
            pathing.invalidate();
            return true;
        }
    return false;
}

// A travel dash waits while an enemy may want it for a fight or an escape (W4-D: Safety::engaged_within).
bool travel_dash_held(const World& world, Pathing&) { return enemy_within(world, my_position(), travel_dash_clearance); }

std::optional<cambc::ability> travel_dash_ready(const World& world, Pathing& pathing) {
    if (!world.me().facts().has_dash()) return std::nullopt;
    if (travel_dash_held(world, pathing)) return std::nullopt;
    return ready(world, AbilityKind::dash);
}

bool travel_dash(const World& world, Pathing& pathing, const cambc::ability& dash, int here_steps, auto steps_at) {
    if (here_steps == 0 || here_steps == unreachable) return false;
    const vec2 here = my_position();
    const auto& threats = threats_near(world, here);
    const int here_danger = danger(threats, here);
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return steps_at(p); },
        [&](vec2 p, int steps) {
            return steps <= here_steps - dash_steps && danger(threats, p) <= here_danger && !wakes_camp(world, p);
        });
    return dash_to_first(dash, pathing, landings);
}

} // namespace

std::optional<cambc::champion> attack_target(const World& world, bool stunnable_only) {
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const auto& enemy_spawn = world.map().enemy_spawn;
    struct Seen {
        cambc::champion c;
        vec2 pos;
        float health, retaliation;
        bool stunnable;
        float partner; // Cassi or Issac: the visible other body's health
    };
    static std::vector<Seen> seen; // kept across calls: allocating costs more than the work
    seen.clear();
    for (auto p : positions_within(live_champion_tiles(team::enemy), here, range + (splash ? 1 : 0))) {
        try {
            auto c = cambc::vision::champion_at(p);
            const auto passive = facts(c.champion_name()).passive;
            const float retaliation = passive == Passive::retaliation ? retaliation_share * c.focus() : 0.0f;
            // Buffs are read only when asked for: building them allocates.
            const bool stunnable = stunnable_only && passive != Passive::stun_immune && !c.buffs().has_stun();
            float partner = 1e9f;
            if (passive == Passive::linked_pair)
                for (const auto& e : world.enemies)
                    if (e.alive && e.visible && e.pos != p && e.facts().passive == Passive::linked_pair) partner = e.health;
            // A shield must be hit through before health: counted as health.
            float shield = 0;
            if (facts(c.champion_name()).has(AbilityKind::shield))
                for (const auto& e : world.enemies)
                    if (e.alive && e.visible && e.pos == p) shield = e.shield;
            seen.push_back({c, p, c.health() + shield, retaliation, stunnable, partner});
        } catch (const cambc::error&) {
        }
    }
    if (seen.empty()) return std::nullopt;
    const float health = my_health(), strength = my_strength() * damage_scale(world.me().facts().passive, health, my_max_health());
    // An enemy on its spawn heals to full at its turn end: only a kill or a stun is worth anything.
    const auto worth = [&](const Seen& s) {
        if (s.health <= strength) return s.health + params::life_value;
        return test(enemy_spawn, s.pos) ? 0.0f : useful_damage(strength, s.health, s.partner);
    };
    std::optional<cambc::champion> best;
    float best_value = 0, best_health = 0, best_pair = 0;
    for (const auto& t : seen) {
        if (dist(here, t.pos) > range || (stunnable_only && !t.stunnable)) continue;
        float value = worth(t), retaliation = t.retaliation;
        if (splash)
            for (const auto& o : seen)
                if (&o != &t && dist(o.pos, t.pos) <= 1) value += worth(o), retaliation += o.retaliation;
        if ((value <= 0 && !stunnable_only) || retaliation >= health) continue;
        if (!splash) value = 0; // the weakest, a pair by its weaker body
        const float pair = std::min(t.health, t.partner);
        if (!best || value > best_value || (value == best_value && (pair < best_pair || (pair == best_pair && t.health < best_health))))
            best = t.c, best_value = value, best_health = t.health, best_pair = pair;
    }
    return best;
}

bool reset_and_attack_enemy(const World& world, bool stunning_only, Safety* safety) {
    auto& me = cambc::self();
    const auto& f = world.me().facts();
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (slot < 0 || (stunning_only && !f.abilities[slot].stuns) || my_can_attack()) return false;
    const auto reset = ready(world, AbilityKind::attack_reset);
    if (!reset) return false;
    const auto target = attack_target(world, stunning_only);
    if (!target) return false;
    // Under visible fire, the heal or shield due here is worth more than a hit that does not kill.
    if (const bool kills = target->health() <= me.strength(); !kills && safety) {
        // Strike bounds Reach: with no visible foe's Strike reaching here, vis_mask is 0.
        const vec2 here = my_position();
        std::uint16_t reaching = 0;
        safety->strike_sum(here, &reaching);
        if (reaching && mend_due(world, *safety, -1) && safety->tile(here).vis_mask) return false;
    }
    if (!cast(*reset)) return false;
    try {
        me.attack(*target);
    } catch (const cambc::error&) {
    }
    return true;
}

// Monsters never move: the tiles within each range of a camp tile are kept.
bool camp_in_reach(const World& world, vec2 p, int range) {
    static std::array<std::optional<bitboard>, 4> near;
    if (range < 0 || range >= static_cast<int>(near.size())) return true;
    auto& tiles = near[static_cast<std::size_t>(range)];
    if (!tiles) {
        tiles.emplace();
        for (const auto& g : world.map().groups)
            for (const auto& m : g.members) tiles->draw_chebyshev(m.pos, static_cast<float>(range));
    }
    return tiles->is_set(p);
}

namespace {

// The reset is kept off camps while an enemy may want it for a fight (W4-D: Safety::engaged_within).
bool camp_reset_held(const World& world, Safety*, vec2 here, int range) { return enemy_within(world, here, range + reset_hold_margin); }

} // namespace

bool reset_and_attack_camp(const World& world, Safety* safety, int group) {
    Phase phase{"reset_and_attack_camp"};
    auto& me = cambc::self();
    const auto& f = world.me().facts();
    if (!f.has_attack_reset() || my_can_attack()) return false;
    const vec2 here = my_position();
    const int range = f.attack_range();
    if (!camp_in_reach(world, here, range)) return false;
    const auto reset = ready(world, AbilityKind::attack_reset);
    if (!reset) return false;
    const auto& map = world.map();
    std::optional<cambc::camp> best;
    float best_health = 0;
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (map.groups[g].has_monolith && g != siege_group()) || g != group) continue;
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            try {
                auto camp = map.groups[g].camp(i);
                const float h = camp.health();
                if (!best || h < best_health) best = camp, best_health = h;
            } catch (const cambc::error&) {
            }
        }
    }
    if (!best) return false;
    // A Vendetta kill readies the reset again, so it need not be held.
    const bool refunded = f.passive == Passive::reset_on_kill && best_health <= my_strength();
    if (!refunded && camp_reset_held(world, safety, here, range)) return false;
    if (!cast(*reset)) return false;
    try {
        me.attack(*best);
    } catch (const cambc::error&) {
    }
    ++camp_hits();
    return true;
}

bool dash_towards(const World& world, Pathing& pathing, const Field& field) {
    const auto dash = travel_dash_ready(world, pathing);
    return dash
           && travel_dash(world, pathing, *dash, field.at(my_position()), [&](vec2 p) { return field.at(p); });
}

bool dash_across(const World& world, Pathing& pathing, const Field& field) {
    Phase phase{"dash_across"};
    if (!world.me().facts().has_dash() || !any_within(world.map().crossable, my_position(), 1)) return false;
    const auto dash = ready(world, AbilityKind::dash);
    const vec2 here = my_position();
    const int here_steps = field.at(here);
    if (!dash || here_steps == 0 || here_steps == unreachable) return false;
    // The walk goes into camp reach anyway; only enemies are kept from.
    static std::vector<Hazard> enemies;
    enemies.clear();
    for (const auto& t : threats_near(world, here))
        if (!t.camp) enemies.push_back(t);
    const int here_danger = danger(enemies, here);
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return field.at(p); },
        [&](vec2 p, int steps) { return steps <= here_steps - dash_steps && danger(enemies, p) <= here_danger && !wakes_camp(world, p); });
    return dash_to_first(*dash, pathing, landings);
}

bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals, int max_steps) {
    Phase phase{"dash_towards"};
    static int paused_until = -1;
    if (world.round < paused_until) return false;
    // Most champions have no dash: check before anything costly.
    const auto dash = travel_dash_ready(world, pathing);
    if (!dash) return false;
    const vec2 here = my_position();
    // A goal within a dash is a walk or two away: not worth the cooldown or the search.
    if (any_within(goals, here, dash_steps)) return false;
    static bitboard open_goals{cambc::uninitialized}, origin, visited{cambc::uninitialized};
    static cambc::distance_field field;
    const auto& walls = pathing.blocked();
    // goals & ~walls
    and_into(goals, walls, open_goals);
    xor_into(open_goals, goals, open_goals);
    if (board_empty(open_goals)) return false;
    // Searching out from the goals until it reaches us labels every tile nearer than ours.
    clear_board(origin);
    set_tile(origin, here);
    field.compute_to(walls, open_goals, origin, visited, static_cast<std::uint16_t>(std::min<int>(max_steps, unreachable)));
    if (test(visited, here)
        && travel_dash(world, pathing, *dash, steps_at(field, here),
                       [&](vec2 p) { return test(visited, p) ? steps_at(field, p) : unreachable; }))
        return true;
    paused_until = world.round + failed_search_pause;
    return false;
}

bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief& target_belief) {
    const ChampionBelief* target = &target_belief;
    if (!world.me().facts().has_dash()) return false;
    auto& me = cambc::self();
    const bool target_given = target != nullptr;
    if (!my_can_attack() || (!target_given && my_health() < dash_min_health * my_max_health())) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    if (enemy_within(world, here, range)) return false;
    const auto dash = ready(world, AbilityKind::dash);
    if (!dash) return false;
    const float strength = my_strength() * damage_scale(world.me().facts().passive, my_health(), my_max_health());
    const float my_fraction = health_fraction(me);
    for (const auto& e : world.enemies) {
        if (target_given) break;
        if (!e.alive || !e.visible || dist(here, e.pos) > range + dash_steps || test(world.map().enemy_spawn, e.pos))
            continue;
        const float fraction = e.health / e.max_health;
        const bool finish = e.health <= strength || (fraction < chase_health && fraction < my_fraction);
        if (finish && (!target || e.health < target->health)) target = &e;
    }
    // A melee walk is free of the attack: a landing a step short of range still strikes.
    const int walk = target_given && world.me().facts().walk_and_attack_independent() && me.can_move() ? 1 : 0;
    if (!target || dist(here, target->pos) > range + walk + dash_steps) return false;
    const auto& threats = threats_near(world, here);
    const auto& spawn = world.map().from_ally_spawn();
    const vec2 at = target->pos;
    const auto landings = ranked(
        within(pathing.dash_landings(), at, range + walk),
        [&](vec2 p) { return (dist(p, at) > range ? 1000000 : 0) + danger(threats, p) * 1000 + std::min<int>(spawn.at(p), 999); },
        [&](vec2 p, int) { return !wakes_camp(world, p); });
    return dash_to_first(*dash, pathing, landings);
}

bool dash_away(const World& world, Pathing& pathing, const Field& home) {
    if (!world.me().facts().has_dash()) return false;
    const auto dash = ready(world, AbilityKind::dash);
    if (!dash) return false;
    const vec2 here = my_position();
    const auto& threats = threats_near(world, here);
    const int here_danger = danger(threats, here);
    if (here_danger == 0) return false;
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return danger(threats, p) * 1000 + std::min<int>(home.at(p), 999); },
        [&](vec2 p, int score) { return score / 1000 < here_danger && !wakes_camp(world, p); });
    return dash_to_first(*dash, pathing, landings);
}

bool worth_healing(float amount, float gain, float fraction) {
    return gain > 0 && (gain >= heal_min_share * amount || fraction < heal_low_health);
}

namespace {

// Willow: the ally the heal restores most (`gain`), if it restores enough or the ally is low.
// Read live: allies come into sight as we move.
std::optional<cambc::champion> heal_choice(const World& world, const cambc::ability& heal, float& gain) {
    const auto& f = world.me().facts();
    const float amount = heal.heal_amount();
    const vec2 here = my_position();
    const int range = f.abilities[f.slot_of(AbilityKind::heal)].range();
    std::optional<cambc::champion> best;
    float best_fraction = 0;
    gain = 0;
    for (auto p : positions_within(live_champion_tiles(team::ally), here, range)) {
        if (p == here || test(world.map().ally_spawn, p)) continue;
        try {
            auto c = cambc::vision::champion_at(p);
            if (!c.is_ally()) continue;
            // Allies start a recall at every turn end and cancel it unless wanted, so only one
            // they kept going will reach spawn and heal there.
            if (kept_recall(c)) continue;
            const float g = std::min(amount, c.max_health() - c.health());
            const float fraction = health_fraction(c);
            if (!worth_healing(amount, g, fraction)) continue;
            if (!best || g > gain || (g == gain && fraction < best_fraction)) best = c, gain = g, best_fraction = fraction;
        } catch (const cambc::error&) {
        }
    }
    return best;
}

// The real hits at p the shield would absorb: the visible enemies' blows and the camps that pick
// us (tile(p)), plus every member in reach of a group we hit this turn, asleep ones included:
// `farmed`, hit from attack range, or once our attack is spent any group in attack range.
struct ShieldHits {
    float vis = 0, camp = 0, hit = 0;
};

ShieldHits shield_hits(const World& world, Safety& safety, int farmed, vec2 p) {
    const bool attacked = !my_can_attack();
    const int hit_group = attacked ? -2 : farmed;
    static int memo_round = -1, memo_group = -1;
    static std::uint32_t memo_generation = 0;
    static vec2 memo_p{-1, -1};
    static ShieldHits memo;
    if (memo_round == world.round && memo_generation == safety.generation() && memo_p == p && memo_group == hit_group) return memo;
    ShieldHits h;
    if (!test(world.map().ally_spawn, p)) {
        h.camp = safety.camp_damage(p);
        // tile(p).vis, summed in its order, without filling the row's unseen columns. Strike bounds
        // Reach, so only foes whose Strike reaches p can hit it.
        std::uint16_t reaching_foes = 0;
        safety.strike_sum(p, &reaching_foes);
        for (auto left = reaching_foes; left; left &= left - 1)
            if (const auto b = safety.blow(world.enemies[static_cast<std::size_t>(std::countr_zero(left))], p); b.hits) h.vis += b.damage;
        const auto& groups = world.map().groups;
        const int range = world.me().facts().attack_range();
        const auto add_hit = [&](int g) {
            const auto& c = world.camps[g];
            if (c.state != CampState::alive || groups[g].strength <= 0) return;
            const auto& members = groups[g].members;
            bool hitting = false;
            float reaching = 0;
            for (std::size_t i = 0; i < members.size(); ++i) {
                if (c.health[i] <= 0) continue;
                const int d = dist(p, members[i].pos);
                hitting |= d <= range;
                if (d <= members[i].reach) reaching += members[i].strength;
            }
            if (hitting) h.hit += reaching;
        };
        if (attacked)
            for (int g : world.map().groups_near(p, world.map().max_camp_reach)) add_hit(g);
        else if (farmed >= 0 && farmed < static_cast<int>(groups.size()))
            add_hit(farmed);
    }
    memo_round = world.round, memo_generation = safety.generation(), memo_p = p, memo_group = hit_group, memo = h;
    return h;
}

// The one heal and shield valuer: the heal's gain on the ally it picks, else shield_cap against
// shield_hits. No champion has both.
struct Mending {
    std::optional<cambc::ability> ability;
    std::optional<cambc::champion> ally; // the heal's
    float value = 0;
    ShieldHits hits;
};

Mending judge(const World& world, Safety& safety, int farmed) {
    Mending m;
    if (const auto heal = ready(world, AbilityKind::heal)) {
        float gain = 0;
        if (auto ally = heal_choice(world, *heal, gain)) {
            m.ability = heal, m.ally = ally, m.value = gain;
            return m;
        }
    }
    const auto shield = ready(world, AbilityKind::shield);
    if (!shield) return m;
    float amount = 0;
    try {
        amount = shield->shield_amount();
    } catch (const cambc::error&) {
        return m;
    }
    const auto& f = world.me().facts();
    m.ability = shield;
    m.hits = shield_hits(world, safety, farmed, my_position());
    m.value = shield_cap(amount, f.abilities[f.slot_of(AbilityKind::shield)].duration, m.hits.vis + m.hits.camp + m.hits.hit);
    return m;
}

} // namespace

bool mend_due(const World& world, Safety& safety, int farmed) { return judge(world, safety, farmed).value > 0; }

bool mend(const World& world, Safety& safety, int farmed, char site) {
    Phase phase{"mend"};
    const auto m = judge(world, safety, farmed);
    if (m.value <= 0) return false;
    const bool cast_ok = m.ally ? cast(*m.ability, *m.ally) : cast(*m.ability);
    debug_block({
        static int mended_round = -1;
        std::printf("MEND %d %c %c %.0f %.0f %.0f %.0f\n", world.round, site, cast_ok ? (m.ally ? 'h' : 's') : '-', m.value,
                    m.hits.vis, m.hits.camp, m.hits.hit);
        if (cast_ok && mended_round == world.round) std::printf("MEND-TWICE %d\n", world.round);
        if (cast_ok) mended_round = world.round;
    });
    return cast_ok;
}

} // namespace aph
