#pragma once
#include "globals.h"
#include "types.h"
#include <array>
#include <cambc.h>

// What we know of a champion: fixed facts, then what we observed. pos has its own round
// (other sources may set it later); the rest is as of the last time we saw it.
struct champ_info {
    // fixed for the game, set by champs::init()
    bool is_ally;
    cambc::champion_type type;

    // observed
    vec2 pos;
    i32 pos_observed = -1;    // -1 never
    i32 vision_observed = -1; // -1 never
    cambc::champion_state state;
    f32 health, max_health, strength, focus;
    i32 move_speed, attack_range;
    cambc::buff_restrictions restrictions;
    std::array<cambc::detail::buff_data, u32(cambc::detail::buff_kind::count)> buffs;
    u32 n_buffs;
    std::array<i32, 2> cooldowns; // per ability slot
    i32 channel;                 // rounds left of a recall, tribute or teleport; 0 none
    i32 priority, prev_priority; // next round's, and this round's
    u32 gems;                    // carried
    u32 gold;                    // allies only: the engine refuses enemies'
    cambc::enum_map<cambc::item_type> items;
    std::array<u32, 4> consumables; // by consumable_type; the engine writes 4 counts

    // Gold it has had to spend: what it holds, and its items at cost (30 a shard, 5 to an
    // emblem). Allies only: the engine refuses enemies' gold.
    f32 wealth() const {
        u32 shards = 0;
        for (u32 i = 0; i < u32(cambc::item_type::count); ++i)
            shards += items.ptr()[i] * (i % 2 ? 5 : 1); // odd items are emblems
        return f32(gold) + 30 * f32(shards);
    }
};

namespace champs {
    constexpr u32 max_champs = 12; // 6 per side with c&i

    inline u32 my_id;
    inline u32 n;

    // in draft order
    inline u32 allies[max_champs / 2], n_allies;
    inline u32 enemies[max_champs / 2], n_enemies;

    inline champ_info info[max_champs];

    // our own entry, read this turn like everyone else's
    inline champ_info& my_info() {
        return info[my_id];
    }

    inline void init() {
        using namespace cambc::detail;

        u32 na, ne;
        check(sdk_num_allies(&na)), check(sdk_num_enemies(&ne));
        n = na + ne, my_id = u32(sdk_my_champion());

        for (u32 id = 0; id < n; ++id) {
            champion_identity identity;
            check(sdk_champion_identity(id, &identity));
            info[id].is_ally = identity.team == g::my_team;
            info[id].type = cambc::champion_type(identity.type);

            if (info[id].is_ally)
                allies[n_allies++] = id;
            else
                enemies[n_enemies++] = id;
        }
    }

    // info[] for every champion in our own sight, ourselves included
    inline void start_turn() {
        using namespace cambc::detail;
        using cambc::error_code;
        const i32 now = g::round;

        for (u32 id = 0; id < n; ++id) {
            champion_info raw;
            const i32 rc = sdk_champion(id, &raw);
            if (rc == i32(error_code::api_not_in_vision))
                continue; // keep what we saw before
            check(rc);

            champ_info& c = info[id];
            c.pos = {raw.x, raw.y}, c.pos_observed = now, c.vision_observed = now;
            c.state = cambc::champion_state::from_bits_retain(u32(raw.state));
            c.health = raw.health, c.max_health = raw.max_health;
            c.strength = raw.strength, c.focus = raw.focus;
            c.move_speed = raw.move_speed, c.attack_range = raw.attack_range;

            u8 restrictions;
            check(sdk_champion_restrictions(id, &restrictions));
            c.restrictions = cambc::buff_restrictions::from_bits_retain(restrictions);
            check(
                sdk_champion_buff_data(id, c.buffs.data(), c.buffs.size(), &c.n_buffs));
            for (u32 slot = 0; slot < 2; ++slot)
                check(sdk_champion_cooldown(id, slot, &c.cooldowns[slot]));

            const i32 channel = sdk_champion_channel_time(id, &c.channel);
            if (channel ==
                i32(error_code::invalid_action_cancel_channel_not_channeling))
                c.channel = 0;
            else
                check(channel);

            check(sdk_bc_champion_priority(id, 1, &c.priority));
            check(sdk_bc_champion_priority(id, 0, &c.prev_priority));
            check(sdk_champion_gems(id, &c.gems));
            if (c.is_ally)
                check(sdk_champion_gold(id, &c.gold));
            check(sdk_champion_items(id, c.items.ptr()));
            check(sdk_champion_consumables(id, c.consumables.data()));
        }
    }
} // namespace champs
