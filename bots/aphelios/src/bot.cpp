// Placeholder behaviour, roughly the starter bot's, that exercises the scaffold end to end:
// shop on spawn, recall when hurt, hit enemies in range, bank gems, farm camps the world believes
// are up. Replace freely.
#include "bot.h"
#include <algorithm>
#include <array>
#include "pathing.h"
#include "world.h"

namespace aph {

namespace {

void buy_shards(Memory& memory) {
    auto& me = cambc::self();
    if (memory.shard_stat < 0) memory.shard_stat = static_cast<int>(random_below(3));
    const std::array items{cambc::item_type::power_shard_of_strength, cambc::item_type::power_shard_of_focus,
                           cambc::item_type::power_shard_of_health};
    const auto item = items[memory.shard_stat];
    const unsigned count = me.gold_count() / item.cost();
    if (count && me.can_buy(item, count)) me.buy(item, count);
}

// Basic-attack the weakest enemy champion in range that we saw this turn.
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

// Basic-attack a visible monster in range.
bool attack_camp(const World& world) {
    auto& me = cambc::self();
    if (!me.can_attack()) return false;
    const int range = world.me().facts().attack_range();
    const auto& map = world.map();
    for (auto p : (cambc::vision::camp_tiles() & square(me.position(), range)).positions()) {
        const int g = map.group_at(p);
        if (g < 0) continue;
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
    int best = -1, best_steps = unreachable;
    for (int a = 0; a < static_cast<int>(altars.size()); ++a) {
        if (world.altars[a].enemy_lock) continue;
        if (dist(here, altars[a].pos) <= cambc::constants::submit_gems_range) {
            try {
                me.submit_gems(altars[a].pos);
                return;
            } catch (const cambc::error&) {
                continue;
            }
        }
        const int steps = pathing.to_altar(a).at(here);
        if (steps < best_steps) best = a, best_steps = steps;
    }
    if (best >= 0) pathing.step_towards(pathing.to_altar(best));
}

// Head for the nearest group worth visiting: stand on a cleared one to capture it, otherwise get
// in attack range of a live one. The Monolith is left alone.
void farm(const World& world, Pathing& pathing) {
    auto& me = cambc::self();
    const auto& groups = world.map().groups;
    const int range = world.me().facts().attack_range();
    if (attack_camp(world) && !world.me().facts().walk_and_attack_independent()) return;

    vec2 here = me.position();
    const int on_group = world.map().group_at(here);
    if (on_group >= 0 && world.camps[on_group].state == CampState::cleared) return; // capturing

    // Shortlist the 3 nearest by straight-line distance (no sorting: WASM compute is costly),
    // then compare walking steps on the static fields.
    std::array<std::pair<int, int>, 3> shortlist;
    shortlist.fill({unreachable, -1});
    for (int g = 0; g < static_cast<int>(groups.size()); ++g) {
        const auto& belief = world.camps[g];
        if (groups[g].has_monolith) continue;
        const int d = dist(here, groups[g].centre);
        if (belief.state == CampState::respawning && belief.respawn_round - world.round > d) continue;
        if (d >= shortlist[2].first) continue;
        shortlist[2] = {d, g};
        if (shortlist[2].first < shortlist[1].first) std::swap(shortlist[2], shortlist[1]);
        if (shortlist[1].first < shortlist[0].first) std::swap(shortlist[1], shortlist[0]);
    }
    const Field* best = nullptr;
    int best_steps = unreachable;
    for (auto [d, g] : shortlist) {
        if (g < 0) continue;
        const Field& field = world.camps[g].state == CampState::cleared ? pathing.to_group(g)
                                                                         : pathing.to_group_attack(g, range);
        const int steps = field.at(here);
        if (steps < best_steps) best = &field, best_steps = steps;
    }
    if (best && pathing.step_towards(*best)) attack_camp(world);
}

// Every 20 rounds, ward the legal tile farthest from our spawn (a free action).
void place_ward(const World& world, Pathing& pathing) {
    if (world.round % 20 != 0 || cambc::self().ward_cooldown() > 0) return;
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
    if (!at_spawn && me.health() < 0.35f * me.max_health()) {
        try {
            me.recall();
        } catch (const cambc::error&) {
        }
        return;
    }

    attack_enemy(world);
    place_ward(world, pathing);
    if (me.gem_count() > 0) {
        bank_gems(world, pathing);
        return;
    }
    farm(world, pathing);
}

} // namespace aph
