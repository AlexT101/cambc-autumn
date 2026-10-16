#include "self_abilities.h"
#include <algorithm>
#include <array>
#include <optional>
#include <utility>
#include <vector>
#include "champions.h"
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

constexpr int camp_attack_range = 3;
constexpr int dash_steps = 2;
constexpr int reset_hold_margin = 2;      // an enemy this far beyond attack range keeps the reset off camps
constexpr int travel_dash_clearance = 10; // no visible enemy this close for a travel dash
constexpr float heal_min_share = 0.6f;    // of the heal amount restored
constexpr float heal_low_health = 0.5f;
constexpr int kept_recall_turns = 3; // channel left on a recall an ally has kept for a turn
constexpr float dash_min_health = 0.5f;
constexpr float chase_health = 0.4f;
constexpr int failed_search_pause = 4; // rounds without a travel-dash search after one finds no gain
constexpr float kill_value = 300;      // in enemy health points, over the health taken

std::optional<cambc::ability> ready(const World& world, AbilityKind kind) {
    const auto& self = world.me();
    const int slot = self.facts().slot_of(kind);
    // The belief is exact for ourselves at turn start; only a Vendetta kill readies a slot mid-turn.
    if (slot < 0 || !self.alive
        || (!self.ability_ready(slot, world.round) && self.facts().passive != Passive::reset_on_kill))
        return std::nullopt;
    auto& me = cambc::self();
    if (!me.can_cast()) return std::nullopt;
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

int threat_reach(const ChampionFacts& f) {
    int r = f.attack_range();
    for (const auto& a : f.abilities)
        if (a.hits_enemies()) r = std::max(r, a.reach());
    return r + (f.has_dash() ? dash_steps + 1 : 1);
}

bool enemy_within(const World& world, vec2 p, int r) {
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(p, e.pos) <= r) return true;
    return false;
}

// Groups with a camp tile within `radius`, found by bitboard so large maps cost no more.
std::vector<int> groups_near(const World& world, vec2 p, int radius) {
    const auto& map = world.map();
    std::vector<int> out;
    for (auto tile : positions_within(map.camp_tiles, p, radius)) {
        const int g = map.group_at(tile);
        if (g >= 0 && std::find(out.begin(), out.end(), g) == out.end()) out.push_back(g);
    }
    return out;
}

struct Threat {
    vec2 pos;
    int reach;
    bool camp;
};

// Enemies and awake monsters that could reach a tile within a dash of `here`.
std::vector<Threat> threats_near(const World& world, vec2 here) {
    std::vector<Threat> out;
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int reach = threat_reach(e.facts());
        if (dist(here, e.pos) <= reach + dash_steps) out.push_back({e.pos, reach, false});
    }
    const auto& groups = world.map().groups;
    for (int g : groups_near(world, here, camp_attack_range + dash_steps)) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
            const auto& m = groups[g].members[i];
            if (c.health[i] > 0 && m.strength > 0 && dist(here, m.pos) <= camp_attack_range + dash_steps)
                out.push_back({m.pos, camp_attack_range, true});
        }
    }
    return out;
}

// How deep a tile sits inside the threats' reach.
int danger(const std::vector<Threat>& threats, vec2 p) {
    int d = 0;
    for (const auto& t : threats) {
        const int depth = t.reach - dist(p, t.pos) + 1;
        if (depth > 0) d += t.camp ? 2 : depth;
    }
    return d;
}

// A hidden unit on a landing fails the cast without spending it, so a few are tried.
struct Landings {
    static constexpr int tries = 3;
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

bool dash_to_first(const cambc::ability& dash, Pathing& pathing, const Landings& landings) {
    for (int i = 0; i < landings.count; ++i)
        if (cast(dash, landings.tiles[i])) {
            pathing.invalidate();
            return true;
        }
    return false;
}

std::optional<cambc::ability> travel_dash_ready(const World& world) {
    if (enemy_within(world, cambc::self().position(), travel_dash_clearance)) return std::nullopt;
    return ready(world, AbilityKind::dash);
}

bool travel_dash(const World& world, Pathing& pathing, const cambc::ability& dash, int here_steps, auto steps_at) {
    if (here_steps == 0 || here_steps == unreachable) return false;
    const vec2 here = cambc::self().position();
    const auto threats = threats_near(world, here);
    const int here_danger = danger(threats, here);
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return steps_at(p); },
        [&](vec2 p, int steps) { return steps <= here_steps - dash_steps && danger(threats, p) <= here_danger; });
    return dash_to_first(dash, pathing, landings);
}

} // namespace

std::optional<cambc::champion> attack_target(const World& world, bool stunnable_only, const ChampionBelief* hold) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const int range = world.me().facts().attack_range();
    const bool splash = world.me().facts().passive == Passive::splash_attack;
    const float strength = me.strength(), health = me.health();
    const auto& enemy_spawn = world.map().enemy_spawn;
    struct Seen {
        cambc::champion c;
        vec2 pos;
        float health, retaliation;
        bool stunnable;
    };
    std::vector<Seen> seen;
    for (auto p : positions_within(live_champion_tiles(team::enemy), here, range + (splash ? 1 : 0))) {
        try {
            auto c = cambc::vision::champion_at(p);
            const auto passive = facts(c.champion_name()).passive;
            const float retaliation = passive == Passive::retaliation ? retaliation_share * c.focus() : 0.0f;
            // Buffs are read only when asked for: building them allocates.
            const bool stunnable = stunnable_only && passive != Passive::stun_immune && !c.buffs().has_stun();
            seen.push_back({c, p, c.health(), retaliation, stunnable});
        } catch (const cambc::error&) {
        }
    }
    // An enemy on its spawn heals to full at its turn end: only a kill or a stun is worth anything.
    const auto worth = [&](const Seen& s) {
        if (s.health <= strength) return s.health + kill_value;
        return enemy_spawn.is_set(s.pos) ? 0.0f : strength;
    };
    std::optional<cambc::champion> best;
    float best_value = 0, best_health = 0;
    for (const auto& t : seen) {
        if (dist(here, t.pos) > range || (stunnable_only && !t.stunnable) || (hold && t.pos == hold->pos && t.health > strength))
            continue;
        float value = worth(t), retaliation = t.retaliation;
        if (splash)
            for (const auto& o : seen)
                if (&o != &t && dist(o.pos, t.pos) <= 1) value += worth(o), retaliation += o.retaliation;
        if ((value <= 0 && !stunnable_only) || retaliation >= health) continue;
        if (!splash) value = 0; // the weakest
        if (!best || value > best_value || (value == best_value && t.health < best_health))
            best = t.c, best_value = value, best_health = t.health;
    }
    return best;
}

bool reset_and_attack_enemy(const World& world, bool stunning_only, const ChampionBelief* hold) {
    auto& me = cambc::self();
    const auto& f = world.me().facts();
    if (me.can_attack()) return false;
    const int slot = f.slot_of(AbilityKind::attack_reset);
    if (stunning_only && (slot < 0 || !f.abilities[slot].stuns)) return false;
    const auto reset = ready(world, AbilityKind::attack_reset);
    if (!reset) return false;
    const auto target = attack_target(world, stunning_only, hold);
    if (!target || !cast(*reset)) return false;
    try {
        me.attack(*target);
    } catch (const cambc::error&) {
    }
    return true;
}

bool reset_and_attack_camp(const World& world, int group) {
    auto& me = cambc::self();
    if (me.can_attack()) return false;
    const vec2 here = me.position();
    const auto& f = world.me().facts();
    const int range = f.attack_range();
    const auto reset = ready(world, AbilityKind::attack_reset);
    if (!reset) return false;
    const auto& map = world.map();
    std::optional<cambc::camp> best;
    float best_health = 0;
    for (auto p : positions_within(live_camp_tiles(), here, range)) {
        const int g = map.group_at(p);
        if (g < 0 || (group >= 0 ? g != group : map.groups[g].has_monolith)) continue;
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
    const bool refunded = f.passive == Passive::reset_on_kill && best_health <= me.strength();
    if (!refunded && enemy_within(world, here, range + reset_hold_margin)) return false;
    if (!cast(*reset)) return false;
    try {
        me.attack(*best);
    } catch (const cambc::error&) {
    }
    return true;
}

bool dash_towards(const World& world, Pathing& pathing, const Field& field) {
    const auto dash = travel_dash_ready(world);
    return dash
           && travel_dash(world, pathing, *dash, field.at(cambc::self().position()), [&](vec2 p) { return field.at(p); });
}

bool dash_towards(const World& world, Pathing& pathing, const bitboard& goals) {
    static int paused_until = -1;
    if (world.round < paused_until) return false;
    // Most champions have no dash: check before anything costly.
    const auto dash = travel_dash_ready(world);
    if (!dash) return false;
    const vec2 here = cambc::self().position();
    // A goal within a dash is a walk or two away: not worth the cooldown or the search.
    if (any_within(goals, here, dash_steps)) return false;
    const int layers = std::max(world.map().width + world.map().height, max_field_layers()); // a maze runs deeper
    if (!fuel_ok(search_cost_estimate(layers) + params::end_reserve)) return false;
    static bitboard open_goals{cambc::uninitialized}, origin, visited{cambc::uninitialized};
    static cambc::distance_field field;
    const auto& walls = pathing.blocked();
    // goals & ~walls
    open_goals.clear();
    open_goals |= goals;
    open_goals &= walls;
    open_goals ^= goals;
    if (open_goals.is_empty()) return false;
    // Searching out from the goals until it reaches us labels every tile nearer than ours.
    origin.clear();
    origin.set(here);
    field.compute_to(walls, open_goals, origin, visited);
    if (visited.is_set(here)
        && travel_dash(world, pathing, *dash, field.get(here),
                       [&](vec2 p) { return visited.is_set(p) ? static_cast<int>(field.get(p)) : unreachable; }))
        return true;
    paused_until = world.round + failed_search_pause;
    return false;
}

bool dash_to_attack(const World& world, Pathing& pathing, const ChampionBelief* target, const ChampionBelief* hold) {
    auto& me = cambc::self();
    const bool target_given = target != nullptr;
    if (!me.can_attack() || (!target_given && me.health() < dash_min_health * me.max_health())) return false;
    const vec2 here = me.position();
    const int range = world.me().facts().attack_range();
    if (enemy_within(world, here, range)) return false;
    const auto dash = ready(world, AbilityKind::dash);
    if (!dash) return false;
    const float strength = me.strength();
    const float my_fraction = health_fraction(me);
    for (const auto& e : world.enemies) {
        if (target_given) break;
        if (!e.alive || !e.visible || dist(here, e.pos) > range + dash_steps || world.map().enemy_spawn.is_set(e.pos))
            continue;
        const float fraction = e.health / e.max_health;
        const bool finish = e.health <= strength || (fraction < chase_health && fraction < my_fraction && &e != hold);
        if (finish && (!target || e.health < target->health)) target = &e;
    }
    if (!target || dist(here, target->pos) > range + dash_steps) return false;
    const auto threats = threats_near(world, here);
    const auto& spawn = world.map().from_ally_spawn();
    const auto landings = ranked(
        within(pathing.dash_landings(), target->pos, range),
        [&](vec2 p) { return danger(threats, p) * 1000 + spawn.at(p); }, [](vec2, int) { return true; });
    return dash_to_first(*dash, pathing, landings);
}

bool dash_away(const World& world, Pathing& pathing, const Field& home) {
    if (!world.me().facts().has_dash()) return false;
    const auto dash = ready(world, AbilityKind::dash);
    if (!dash) return false;
    const vec2 here = cambc::self().position();
    const auto threats = threats_near(world, here);
    const int here_danger = danger(threats, here);
    if (here_danger == 0) return false;
    const auto landings = ranked(
        pathing.dash_landings(), [&](vec2 p) { return danger(threats, p) * 1000 + std::min<int>(home.at(p), 999); },
        [&](vec2, int score) { return score / 1000 < here_danger; });
    return dash_to_first(*dash, pathing, landings);
}

bool heal_ally(const World& world) {
    const int slot = world.me().facts().slot_of(AbilityKind::heal);
    if (slot < 0) return false;
    const auto heal = ready(world, AbilityKind::heal);
    if (!heal) return false;
    const float amount = heal->heal_amount();
    const vec2 here = cambc::self().position();
    const int range = world.me().facts().abilities[slot].range();
    std::optional<cambc::champion> best;
    float best_gain = 0, best_fraction = 0;
    // Read live: allies come into sight as we move.
    for (auto p : positions_within(live_champion_tiles(team::ally), here, range)) {
        if (p == here || world.map().ally_spawn.is_set(p)) continue;
        try {
            auto c = cambc::vision::champion_at(p);
            if (!c.is_ally()) continue;
            // Allies start a recall at every turn end and cancel it unless wanted, so only one
            // they kept going will reach spawn and heal there.
            if (c.is_recalling() && c.remaining_channel_time() <= kept_recall_turns) continue;
            const float gain = std::min(amount, c.max_health() - c.health());
            const float fraction = health_fraction(c);
            if (gain <= 0 || (gain < heal_min_share * amount && fraction >= heal_low_health)) continue;
            if (!best || gain > best_gain || (gain == best_gain && fraction < best_fraction))
                best = c, best_gain = gain, best_fraction = fraction;
        } catch (const cambc::error&) {
        }
    }
    return best && cast(*heal, *best);
}

bool shield_if_needed(const World& world, int farmed) {
    const auto& f = world.me().facts();
    const auto shield = ready(world, AbilityKind::shield);
    if (!shield) return false;
    auto& me = cambc::self();
    const vec2 here = me.position();
    if (world.map().ally_spawn.is_set(here)) return false;
    bool danger = false;
    for (const auto& e : world.enemies)
        danger |= e.alive && e.visible && dist(here, e.pos) <= threat_reach(e.facts());
    if (danger) return cast(*shield);
    const auto& groups = world.map().groups;
    for (int g : groups_near(world, here, camp_attack_range)) {
        if (danger) break;
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || groups[g].strength <= 0) continue;
        const bool hit = g == farmed || !me.can_attack();
        bool in_reach = false, hitting = false;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i) {
            if (c.health[i] <= 0) continue;
            const int d = dist(here, groups[g].members[i].pos);
            in_reach |= d <= camp_attack_range && groups[g].members[i].strength > 0;
            hitting |= hit && d <= f.attack_range();
        }
        danger = in_reach && (c.awake != Awake::asleep || hitting);
    }
    return danger && cast(*shield);
}

} // namespace aph
