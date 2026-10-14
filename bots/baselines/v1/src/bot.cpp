// Placeholder behaviour, roughly the starter bot's. Replace freely.
#include "bot.h"
#include <algorithm>
#include <array>
#include <cmath>
#include "params.h"
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

using params::max_detour;

constexpr int camp_attack_range = 3;

// Strength throughout; Jungle first for -30% camp damage, then Monster, then Power (6 shards' stats).
void buy_shards() {
    using I = cambc::item_type;
    struct Family {
        I shard, emblem;
        int cap;
    };
    static constexpr Family plan[] = {
        {I::jungle_shard_of_strength, I::jungle_emblem_of_strength, 5},
        {I::monster_shard_of_strength, I::monster_emblem_of_strength, 5},
        {I::power_shard_of_strength, I::power_emblem_of_strength, 1 << 20},
    };
    auto& me = cambc::self();
    const auto owned = me.item_count();
    for (const auto& f : plan) {
        const int have = static_cast<int>(owned[f.shard] + 5 * owned[f.emblem]);
        const unsigned count = std::min<unsigned>(f.cap - std::min(have, f.cap), me.gold_count() / I{f.shard}.cost());
        if (!count) continue;
        if (!me.can_buy(f.shard, count)) return;
        try {
            me.buy(f.shard, count);
        } catch (const cambc::error&) {
            return;
        }
    }
}

bool attack_enemy(const World& world) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const int range = world.me().facts().attack_range();
    const ChampionBelief* target = nullptr;
    for (const auto& e : world.enemies)
        if (e.visible && dist(here, e.pos) <= range && (!target || e.health < target->health)) target = &e;
    if (!target || !me.can_attack()) return false;
    try {
        me.attack(cambc::vision::champion_at(target->pos));
        return true;
    } catch (const cambc::error&) {
        return false;
    }
}

bool attack_camp(const World& world) {
    auto& me = cambc::self();
    if (!me.can_attack()) return false;
    const int range = world.me().facts().attack_range();
    const auto& map = world.map();
    for (auto p : (cambc::vision::camp_tiles() & square(me.position(), range)).positions()) {
        const int g = map.group_at(p);
        if (g < 0 || map.groups[g].has_monolith) continue;
        const auto& members = map.groups[g].members;
        for (int i = 0; i < static_cast<int>(members.size()); ++i) {
            if (members[i].pos != p) continue;
            try {
                me.attack(map.groups[g].camp(i));
                return true;
            } catch (const cambc::error&) {
            }
        }
    }
    return false;
}

void bank_gems(const World& world, Pathing& pathing) {
    auto& me = cambc::self();
    const vec2 here = me.position();
    const auto& altars = world.map().altars;
    bool any_locked = false;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        any_locked |= world.altars[a].enemy_lock;
        if (world.altars[a].enemy_lock || dist(here, altars[a].pos) > cambc::constants::submit_gems_range) continue;
        try {
            me.submit_gems(altars[a].pos);
            return;
        } catch (const cambc::error&) {
        }
    }
    // One cached field covers every altar; per-altar fields are needed only to skip locked ones.
    if (!any_locked) {
        pathing.step_towards(pathing.to_any_altar());
        return;
    }
    int best = -1, best_steps = unreachable;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock) continue;
        const int steps = pathing.to_altar(a).at(here);
        if (steps < best_steps) best = a, best_steps = steps;
    }
    if (best >= 0) pathing.step_towards(pathing.to_altar(best));
}

constexpr int capture_rounds = 6;

// Damage taken clearing a group alone with basic attacks, killing the deadliest first; also
// the rounds it takes.
float min_camp_damage(const CampGroup& group, const CampBelief& belief, float strength, float* rounds) {
    struct Left {
        float health, strength;
    };
    std::array<Left, 8> left{};
    int n = 0;
    const bool fresh = belief.state == CampState::respawning;
    for (std::size_t i = 0; i < group.members.size() && n < static_cast<int>(left.size()); ++i) {
        const float hp = fresh ? group.members[i].max_health : belief.health[i];
        if (hp > 0) left[n++] = {hp, group.members[i].strength};
    }
    std::sort(left.begin(), left.begin() + n,
              [](const Left& a, const Left& b) { return a.strength * b.health > b.strength * a.health; });
    float damage = 0, elapsed = 0;
    for (int i = 0; i < n; ++i) {
        elapsed += std::ceil(left[i].health / strength);
        damage += left[i].strength * (elapsed - 1);
    }
    *rounds = elapsed;
    return damage;
}

bool ally_engaged(const World& world, int group) {
    for (const auto& a : world.allies)
        if (!a.is_self && a.alive && a.visible && world.map().groups[group].threat().is_set(a.pos)) return true;
    return false;
}

void farm(const World& world, Pathing& pathing) {
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    if (attack_camp(world) && !world.me().facts().walk_and_attack_independent()) return;

    // One holder keeps a capture going, and sharers split the reward: the lowest id stays.
    const auto ally_holding = [&](int g, bool lower_only) {
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && groups[g].tiles().is_set(a.pos)
                && (!lower_only || a.index < world.me().index))
                return true;
        return false;
    };

    const vec2 here = me.position();
    const int on_group = map.group_at(here);
    if (on_group >= 0 && world.camps[on_group].state == CampState::cleared && !ally_holding(on_group, true)) return;

    if (!fuel_ok(field_cost_estimate())) return;
    bitboard origin;
    origin.set(here, true);
    const Field from_here = make_field(map.blocked_for_us, origin);
    const float strength = std::max(1.0f, world.me().strength);
    const float spare_health = me.health() - params::recall_health_fraction * me.max_health();
    // Unaffordable groups only when nothing else is left: idling is worse.
    int best = -1, best_steps = unreachable, risky = -1, risky_steps = unreachable;
    float best_value = 0, risky_value = 0;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& group = groups[g];
        const auto& belief = world.camps[g];
        if (group.has_monolith || group.gems == 0 || (belief.state == CampState::cleared && ally_holding(g, false)))
            continue;
        const int steps = from_here.at(group.centre);
        if (steps == unreachable) continue;
        // Skip groups still respawning when we would arrive.
        if (belief.state == CampState::respawning && belief.respawn_round - world.round > steps) continue;
        float clear_rounds = 0, damage = 0;
        if (belief.state != CampState::cleared) {
            damage = min_camp_damage(group, belief, strength, &clear_rounds);
        }
        const float value = static_cast<float>(group.gems) / (static_cast<float>(steps) + clear_rounds + capture_rounds);
        if (damage > spare_health && !ally_engaged(world, g)) {
            if (value > risky_value) risky = g, risky_value = value, risky_steps = steps;
        } else if (value > best_value) {
            best = g, best_value = value, best_steps = steps;
        }
    }
    if (best < 0) best = risky, best_steps = risky_steps;
    if (best < 0) return;
    const int cap = best_steps + max_detour;
    if (world.camps[best].state == CampState::cleared) {
        pathing.step_towards(groups[best].tiles(), nullptr, cap);
        return;
    }
    auto goals = pathing.attack_tiles(best, range);
    // In range and sight with the attack unspent, so the attack failed here: try another tile.
    if (goals.is_set(here) && me.can_attack()) goals.set(here, false);
    if (goals.is_set(here)) return; // attacked from here; stay
    if (!fuel_ok(search_cost_estimate(cap))) return;
    if (pathing.step_towards(goals, nullptr, cap) || pathing.step_towards(groups[best].adjacent(), nullptr, cap))
        attack_camp(world);
}

void place_ward(const World& world, Pathing& pathing) {
    if (world.round % params::ward_period != 0 || cambc::self().ward_cooldown() > 0) return;
    const auto& spawn_field = world.map().from_ally_spawn();
    std::optional<vec2> best;
    int best_steps = -1;
    for (auto p : pathing.ward_targets().positions()) {
        const int steps = spawn_field.at(p);
        if (steps != unreachable && steps > best_steps) best = p, best_steps = steps;
    }
    if (!best) return;
    try {
        cambc::self().place_ward(*best);
    } catch (const cambc::error&) {
    }
}

int threat_reach(const ChampionFacts& f) {
    int r = f.attack_range();
    for (const auto& a : f.abilities)
        if (a.hits_enemies()) r = std::max(r, a.reach());
    return r + (f.has_dash() ? 2 : 1);
}

// Anything that could damage us before our next turn, and so cancel a recall.
bool threatened(const World& world) {
    const vec2 here = cambc::self().position();
    const auto& groups = world.map().groups;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep) continue;
        for (std::size_t i = 0; i < groups[g].members.size(); ++i)
            if (c.health[i] > 0 && dist(here, groups[g].members[i].pos) <= camp_attack_range) return true;
    }
    for (const auto& e : world.enemies)
        if (e.alive && e.visible && dist(here, e.pos) <= threat_reach(e.facts())) return true;
    return false;
}

// Retreating from an awake camp takes its hits anyway, and the clear is lost.
bool finishing_camp(const World& world) {
    const vec2 here = cambc::self().position();
    const auto& groups = world.map().groups;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep || !groups[g].threat().is_set(here)) continue;
        float rounds = 0;
        const float damage = min_camp_damage(groups[g], c, std::max(1.0f, world.me().strength), &rounds);
        return damage < params::finish_camp_health_fraction * cambc::self().health();
    }
    return false;
}

bool want_home(const World& world) {
    const auto& me = cambc::self();
    return !world.map().ally_spawn.is_set(me.position()) && me.health() < params::recall_health_fraction * me.max_health()
        && !finishing_camp(world);
}

bool can_tribute_here(const World& world) {
    const auto& me = cambc::self();
    if (me.gem_count() == 0) return false;
    const auto& altars = world.map().altars;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a)
        if (!world.altars[a].enemy_lock && dist(me.position(), altars[a].pos) <= cambc::constants::submit_gems_range) return true;
    return false;
}

void decide(const World& world, Pathing& pathing) {
    auto& me = cambc::self();
    if (!world.me().alive) {
        buy_shards(); // the dead can only shop
        return;
    }
    if (me.is_submitting_gems() || me.is_teleporting()) return;
    if (me.is_recalling()) {
        if (want_home(world) && !threatened(world) && !can_tribute_here(world)) return;
        try {
            me.cancel_recall();
        } catch (const cambc::error&) {
            return;
        }
    }

    if (world.map().ally_spawn.is_set(me.position()) || world.me().facts().passive == Passive::remote_shop)
        buy_shards();
    // Healing needs a turn end on spawn; a recall arrives at turn start.
    if (world.map().ally_spawn.is_set(me.position()) && me.health() < me.max_health()) {
        attack_enemy(world);
        return;
    }
    if (want_home(world)) {
        // A tribute survives damage; a recall does not.
        if (can_tribute_here(world)) bank_gems(world, pathing);
        else pathing.step_towards(pathing.to_ally_spawn());
        return;
    }

    const bool attacked = attack_enemy(world);
    place_ward(world, pathing);
    if (me.gem_count() > 0) {
        bank_gems(world, pathing); // a tribute can still start after a ranged attack
        return;
    }
    if (attacked && !world.me().facts().walk_and_attack_independent()) return;
    farm(world, pathing);
}

// Recalling every turn end and cancelling next turn when not wanted makes a wanted recall a
// turn shorter. Damage before then cancels it at no cost.
void start_recall(const World& world) {
    auto& me = cambc::self();
    if (!world.me().alive || me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()
        || world.map().ally_spawn.is_set(me.position()))
        return;
    try {
        me.recall();
    } catch (const cambc::error&) {
    }
}

} // namespace

void play_turn(const World& world, Pathing& pathing, Memory&) {
    decide(world, pathing);
    start_recall(world);
}

} // namespace aph
