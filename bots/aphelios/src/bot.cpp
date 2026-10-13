// Placeholder behaviour, roughly the starter bot's. Replace freely.
#include "bot.h"
#include <array>
#include "params.h"
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

using params::max_detour;

void buy_shards(Memory& memory) {
    auto& me = cambc::self();
    if (memory.shard_stat < 0) memory.shard_stat = static_cast<int>(random_below(3));
    const std::array items{cambc::item_type::power_shard_of_strength, cambc::item_type::power_shard_of_focus,
                           cambc::item_type::power_shard_of_health};
    const auto item = items[memory.shard_stat];
    const unsigned count = me.gold_count() / item.cost();
    if (count && me.can_buy(item, count)) me.buy(item, count);
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

void farm(const World& world, Pathing& pathing) {
    auto& me = cambc::self();
    const auto& map = world.map();
    const auto& groups = map.groups;
    const int range = world.me().facts().attack_range();
    if (attack_camp(world) && !world.me().facts().walk_and_attack_independent()) return;

    const vec2 here = me.position();
    const int on_group = map.group_at(here);
    if (on_group >= 0 && world.camps[on_group].state == CampState::cleared) return; // capturing

    // Skip groups still respawning when we would arrive, judged by straight-line distance.
    auto candidates = map.camp_tiles;
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& belief = world.camps[g];
        if (groups[g].has_monolith
            || (belief.state == CampState::respawning && belief.respawn_round - world.round > dist(here, groups[g].centre)))
            candidates &= ~groups[g].tiles();
    }
    const auto nearest = pathing.nearest(candidates);
    if (nearest.tiles.empty()) return;
    const int best = map.group_at(nearest.tiles.front());
    const int cap = nearest.steps + max_detour;
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

} // namespace

void play_turn(const World& world, Pathing& pathing, Memory& memory) {
    auto& me = cambc::self();
    if (!world.me().alive) {
        buy_shards(memory); // the dead can only shop
        return;
    }
    if (me.is_recalling() || me.is_submitting_gems() || me.is_teleporting()) return;

    const bool at_spawn = world.map().ally_spawn.is_set(me.position());
    if (at_spawn) buy_shards(memory);
    if (!at_spawn && me.health() < params::recall_health_fraction * me.max_health()) {
        try {
            me.recall();
        } catch (const cambc::error&) {
        }
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

} // namespace aph
