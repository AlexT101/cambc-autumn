#include "../fish/switches.h"
#if !FISH_PRIORITY
#include "turn_order_astraeus.inc"
#else
// Fish's priority encoding (FISH_MODEL section 5): priority = -rank - (N+1) L, rank by base max
// health (fish::priority_rank), L by mode: dead -1; late (at a contested camp) band + 5; contact
// (an enemy in reach) 99 + j acting last when the enemy starts the round it applies to, else
// -101 - j acting first; quiet band. Written only on change. No payload: comms is in the shared bytes.
#include "turn_order.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include "../fish/fish_math.h"
#include "follow.h"
#include "world.h"

namespace aph {

namespace {

std::int32_t turn_priority = 0;
bool turn_priority_valid = false;

// reach in the selector: a basic's with a melee walk, 3 ranged and 2 melee.
int basic_reach(const ChampionBelief& c) { return c.facts().ranged ? ranged_range : melee_range + 1; }

// A visible awake fighter has us in range, and a visible enemy is within its reach + 1 of an awake
// member of its group.
bool contested_camp(const World& world, vec2 here) {
    const auto& map = world.map();
    for (std::size_t g = 0; g < map.groups.size(); ++g) {
        const auto& G = map.groups[g];
        const auto& c = world.camps[g];
        if (c.state != CampState::alive || c.awake == Awake::asleep || G.strength <= 0) continue;
        if (dist(here, G.centre) > G.threat_radius()) continue;
        bool in_range = false;
        for (std::size_t i = 0; i < G.members.size() && !in_range; ++i) {
            const auto& m = G.members[i];
            in_range = m.strength > 0 && c.health[i] > 0 && !c.member_asleep(i) && test(world.visible, m.pos) && dist(here, m.pos) <= m.reach;
        }
        if (!in_range) continue;
        for (std::size_t i = 0; i < G.members.size(); ++i) {
            const auto& m = G.members[i];
            if (m.strength <= 0 || c.health[i] <= 0 || c.member_asleep(i)) continue;
            for (const auto& e : world.enemies)
                if (e.alive && e.visible && dist(e.pos, m.pos) <= m.reach + 1) return true;
        }
    }
    return false;
}

bool enemy_in_reach(const World& world, const ChampionBelief& self, vec2 here) {
    for (const auto& e : world.enemies) {
        if (!e.alive || !e.visible) continue;
        const int d = dist(here, e.pos);
        if (d <= basic_reach(e) || d <= basic_reach(self)) return true;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && dist(a.pos, e.pos) <= basic_reach(e)) return true;
    }
    return false;
}

bool we_start(const World& world, int round) { return world.map().team_a == (round % 2 == 1); }

int level(const World& world) {
    const auto& me = world.me();
    const auto& info = my_record();
    if (!me.alive || info.x < 0) return -1;
    const vec2 here{info.x, info.y};
    const float shield = my_live_shield(world);
    const int band = fish::band(info.health, shield, info.max_health, static_cast<int>(my_gems()));
    if (contested_camp(world, here)) return band + 5;
    if (enemy_in_reach(world, me, here)) {
        const float ehp = std::max(1.0f, info.health + shield);
        const int j = std::min(16, static_cast<int>(std::floor(16.0f * fish::threat(world, here) / ehp)));
        return we_start(world, world.round + 1) ? -101 - j : 99 + j;
    }
    return band;
}

} // namespace

void set_turn_order(const World& world, Safety&) {
    world.throw_if_stale();
    follow::posting = {};
    follow::own = {};
    const int n = static_cast<int>(world.allies.size());
    turn_priority = -fish::priority_rank(world, world.me().index) - (n + 1) * level(world);
    turn_priority_valid = true;
}

void publish_turn_order(const World&, std::uint32_t) {
    if (!turn_priority_valid) return;
    try {
        static std::int32_t next;
        ok(cambc::detail::sdk_bc_champion_priority(my_handle(), 1, &next));
        if (turn_priority != next) {
            throw_if_stale();
            cambc::self().set_priority(turn_priority);
            debug_block({ std::printf("FP %d %u %d\n", cambc::round_number(), my_handle(), turn_priority); });
        }
    } catch (const cambc::error&) {
    }
}

} // namespace aph

#endif
