// Play: on each champion's first turn print live stats/abilities (to compare
// with the design dump), all champion handles, and the draft as seen in play.
// Turn 1 also tries a step of vec2::north to anchor direction vs the map.
#include <cambc.h>
#include "bot.h"
#include "dump.h"

void Bot::play_turn() {
    auto& me = cambc::self();
    const std::string w = cambc::to_string(me.champion_name());
    ++turns;
    if (turns > 3) return;
    std::cout << probe::P(w) << "turn pos=" << probe::pos(me.position()) << " my_team_abs=" << cambc::detail::sdk_my_team()
              << " handle=" << static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(me))
              << " fuel=" << cambc::fuel_remaining() << '\n';
    if (turns == 1) {
        std::cout << probe::P(w) << "live hp=" << me.health() << " max_hp=" << me.max_health() << " str=" << me.strength()
                  << " foc=" << me.focus() << " range=" << me.attack_range() << " gold=" << me.gold_count()
                  << " gems=" << me.gem_count() << " passive=" << cambc::to_string(me.passive())
                  << " visible_tiles=" << me.visible_tiles().count() << '\n';
        cambc::detail::champion_info ci{};
        cambc::detail::sdk_champion(static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(me)), &ci);
        std::cout << probe::P(w) << "live_raw move_speed=" << ci.move_speed << " attack_range=" << ci.attack_range
                  << " state=" << probe::hexu(ci.state) << " team=" << ci.team << " type=" << ci.type << '\n';
        for (std::uint32_t s = 0; s < 2; ++s) {
            cambc::detail::ability_props a{};
            int code = cambc::detail::sdk_champion_ability_props(static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(me)), s, &a);
            if (code) std::cout << probe::P(w) << "live_ability slot=" << s << " code=" << code << '\n';
            else probe::dump_ability(w, w + "-live", int(s), a);
            // Engine-computed effect amounts (before mitigation) for this slot.
            float dmg = -1, heal = -1, shield = -1;
            const auto h = static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(me));
            int c1 = cambc::detail::sdk_champion_ability_damage(h, s, &dmg);
            int c2 = cambc::detail::sdk_champion_ability_heal(h, s, &heal);
            int c3 = cambc::detail::sdk_champion_ability_shield(h, s, &shield);
            std::cout << probe::P(w) << "amount slot=" << s << " damage=" << dmg << "(c" << c1 << ") heal=" << heal
                      << "(c" << c2 << ") shield=" << shield << "(c" << c3 << ")\n";
        }
        for (auto side : {cambc::team::ally, cambc::team::enemy})
            for (const auto& c : cambc::champions(side)) {
                std::cout << probe::P(w) << "champ side=" << cambc::to_string(side)
                          << " handle=" << static_cast<std::uint32_t>(static_cast<cambc::handle_champion_t>(c));
                try { std::cout << " type=" << cambc::to_string(c.champion_name()) << " pos=" << probe::pos(c.position()); }
                catch (const std::exception& e) { std::cout << " hidden=" << e.what(); }
                std::cout << '\n';
            }
        probe::dump_draft_state(w);
        // Try one step north (+y) and report the engine position afterwards.
        try {
            auto target = me.position() + cambc::vec2::north;
            bool ok = me.move_absolute(target);
            std::cout << probe::P(w) << "move_north target=" << probe::pos(target) << " ok=" << ok
                      << " pos_after=" << probe::pos(me.position()) << '\n';
        } catch (const std::exception& e) {
            std::cout << probe::P(w) << "move_north err=" << e.what() << '\n';
        }
    }
}
