#include "fish_math.h"
#include <algorithm>
#include <cmath>

namespace aph::fish {

int band(float health, float shield, float max_health, int gems) {
    if (max_health <= 0) return 0;
    const float share = std::min(1.0f, (health + shield) / max_health) * (gems > 0 ? gem_health_factor : 1.0f);
    return std::clamp(static_cast<int>(std::floor(4.0f * (1.0f - share))), 0, 3);
}

float reach_damage(const ChampionBelief& c, int d, int round) {
    if (!c.alive) return 0;
    const auto& f = c.facts();
    const int range = f.attack_range(), walk = f.ranged ? 0 : 1;
    const float s = c.strength, focus = c.focus;
    float best = 0;
    for (int slot = 0; slot < 2; ++slot) {
        const auto& a = f.abilities[slot];
        if (!c.ability_ready(slot, round)) continue;
        if (a.kind == AbilityKind::damage) {
            const int reach = ability_range + (a.target == Targeting::ground ? 1 : 0);
            if (d <= reach) best = std::max(best, a.multiplier * focus + (d <= range ? s : 0.0f));
        } else if (a.lands()) {
            if (d <= ability_range) best = std::max(best, a.multiplier * focus + s);
        } else if (a.kind == AbilityKind::dash) {
            if (d <= range + walk + dash_range) best = std::max(best, s);
        } else if (a.kind == AbilityKind::attack_reset) {
            if (d <= range + walk) best = std::max(best, 2 * s);
        }
    }
    if (d <= range + walk) best = std::max(best, s);
    return best * damage_scale(f.passive, c.health, c.max_health);
}

float danger(const World& world, vec2 tile, float own_ehp) {
    float sum = 0;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && !e.stun_pending) sum += reach_damage(e, dist(tile, e.pos), world.round);
    return sum / std::max(1.0f, own_ehp);
}

float threat(const World& world, vec2 tile) {
    float sum = 0;
    for (const auto& e : world.enemies)
        if (e.alive && e.visible) sum += reach_damage(e, dist(tile, e.pos), world.round);
    return sum;
}

bool kill_available(const World& world, vec2 start, vec2 p) {
    const auto& me = world.me();
    const auto& f = me.facts();
    const int reset = f.slot_of(AbilityKind::attack_reset);
    const bool reset_ready = reset >= 0 && me.ability_ready(reset, world.round);
    const float hit = reach_damage(me, f.ranged ? ranged_range : melee_range, world.round);
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible || hit < ehp(e)) continue;
        const bool can = f.ranged ? dist(p, e.pos) <= ranged_range && (p == start || reset_ready)
                                  : dist(p, e.pos) <= melee_range || dist(start, e.pos) <= melee_range;
        if (can) return true;
    }
    return false;
}

bool acceptable(const World& world, vec2 start, vec2 p) {
    const auto& me = world.me();
    if (kill_available(world, start, p)) return true;
    return health_fraction(me) > accept_health && danger(world, p, ehp(me)) <= accept_danger;
}

float side_ehp_ratio(const World& world, vec2 at) {
    float ours = ehp(world.me()), theirs = 0;
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && dist(at, a.pos) <= vision_radius) ours += ehp(a);
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(at, e.pos) <= vision_radius) theirs += ehp(e);
    return theirs > 0 ? ours / theirs : 1e9f;
}

int holder_rank(cambc::champion_type type) {
    using T = cambc::champion_type;
    switch (type) {
    case T::marcella: return 0;
    case T::vesper_vale: return 1;
    case T::vendetta: return 2;
    case T::heart_of_ruin: return 3;
    case T::cassi: return 4;
    case T::issac: return 5;
    case T::willow: return 6;
    default: return 7;
    }
}

int priority_rank(const World& world, int index) {
    // Heart of Ruin sorts as if its type index came before Varg's.
    const auto order = [](cambc::champion_type t) {
        const int i = static_cast<int>(t);
        return t == cambc::champion_type::heart_of_ruin ? static_cast<int>(cambc::champion_type::varg) * 2 - 1 : i * 2;
    };
    const auto& c = world.allies[static_cast<std::size_t>(index)];
    const float hp = c.facts().health.base;
    int place = 0;
    for (const auto& o : world.allies) {
        if (&o == &c) continue;
        const float ohp = o.facts().health.base;
        place += ohp > hp || (ohp == hp && order(o.type) < order(c.type));
    }
    return 2 + place;
}

} // namespace aph::fish
