// probe-unseen-codes: the raw status each per-champion import returns for an enemy out of vision, and what
// champion_at / has_champion return on an empty tile in vision (for a shim that hides the enemy team).
// Run: cambc run tools/probes/probe-unseen-codes bots/idle --map 00corners --rounds 3 --fuel 50000000
#include <cambc.h>
#include <cstdio>

using namespace cambc::detail;

static void probe_enemy(std::uint32_t h) {
    champion_info info{};
    champion_identity id{};
    std::int32_t alive = -1, i32 = 0;
    std::uint32_t u32 = 0, n = 0, buf[64]{};
    std::uint8_t u8 = 0;
    std::uint64_t board[4096]{};
    buff_data buffs[8]{};
    ward_resources wards{};
    position wpos[4]{};
    ability_props props{};
    float f = 0;
    std::printf("PROBE enemy %u champion=%d identity=%d alive_code=%d alive=%d\n", h, sdk_champion(h, &info),
                sdk_champion_identity(h, &id), sdk_champion_is_alive(h, &alive), alive);
    std::printf("PROBE enemy %u restrictions=%d cooldown=%d items=%d consumables=%d gems=%d gold=%d\n", h,
                sdk_champion_restrictions(h, &u8), sdk_champion_cooldown(h, 0, &i32), sdk_champion_items(h, buf),
                sdk_champion_consumables(h, buf), sdk_champion_gems(h, &u32), sdk_champion_gold(h, &u32));
    std::printf("PROBE enemy %u vision=%d wards=%d ward_positions=%d channel=%d can_shop=%d can_sell=%d\n", h,
                sdk_bc_champion_vision(h, board), sdk_champion_wards(h, &wards), sdk_champion_ward_positions(h, wpos, 4, &n),
                sdk_champion_channel_time(h, &i32), sdk_champion_can_shop(h, 0, &i32), sdk_champion_can_sell(h, &i32));
    std::printf("PROBE enemy %u priority0=%d priority1=%d buffs=%d props=%d damage=%d heal=%d shield=%d\n", h,
                sdk_bc_champion_priority(h, 0, &i32), sdk_bc_champion_priority(h, 1, &i32), sdk_champion_buff_data(h, buffs, 8, &n),
                sdk_champion_ability_props(h, 0, &props), sdk_champion_ability_damage(h, 0, &f), sdk_champion_ability_heal(h, 0, &f),
                sdk_champion_ability_shield(h, 0, &f));
}

int main() {
    bool done = false;
    while (true) {
        if (!cambc::is_draft() && !done) {
            done = true;
            std::uint32_t handles[16]{}, n = 0;
            sdk_enemies(handles, 16, &n);
            for (std::uint32_t i = 0; i < n; ++i) probe_enemy(handles[i]);
            champion_info me{};
            sdk_champion(static_cast<std::uint32_t>(sdk_my_champion()), &me);
            // An empty tile in vision next to us.
            for (int dx = -2; dx <= 2; ++dx)
                for (int dy = -2; dy <= 2; ++dy) {
                    std::int32_t has = -1, seen = 0;
                    std::uint32_t h = 0;
                    const int x = me.x + dx, y = me.y + dy;
                    if (sdk_is_visible(x, y, &seen) != 0 || !seen) continue;
                    const int code = sdk_has_champion(x, y, &has);
                    if (code != 0 || has) continue;
                    std::printf("PROBE empty (%d,%d) has_champion=%d has=%d champion_at=%d handle=%u\n", x, y, code, has,
                                sdk_champion_at(x, y, &h), h);
                    dx = dy = 3;
                }
        }
        if (cambc::is_draft()) {
            for (int c = 0; c < 12; ++c)
                if (sdk_draft_champion(c) == 0) break;
        }
        cambc::end_turn();
    }
}
