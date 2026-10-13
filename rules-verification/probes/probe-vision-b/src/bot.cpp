// probe-vision-b: passive/scripted opponent for probe-vision.
//   BSCEN 0: do nothing (all champions stay on spawn).               [used with probe-vision SCEN 1, 2]
//   BSCEN 1 (corners, with SCEN 3): champion 0 walks into the bush at (35,25), stays, attacks a visible enemy on round 40.
//   BSCEN 2 (corners, with SCEN 4): champion 0 sits in the bush at (35,25) and tries to step onto any visible teleport
//            reservation at (36,25); champion 1 places a ward 2 tiles west of its spawn tile on round 1.
#include <cambc.h>
#include "bot.h"
#include <iostream>
#include <string>

#ifndef BSCEN
#define BSCEN 2
#endif

using cambc::vec2; using cambc::team;
static std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }

void Bot::play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (idx < 0) {
        auto allies = cambc::champions(team::ally);
        for (size_t i = 0; i < allies.size(); ++i) if (allies[i] == me) idx = (int)i;
    }
    if (BSCEN == 2 && idx == 1 && r == 1) {
        const vec2 t = me.position() + vec2{-2, 0};
        std::string res;
        try { res = me.place_ward(t) ? "true" : "false"; } catch (const cambc::error& x) { res = cambc::to_string(x.code()); }
        std::cout << "PROBE " << r << " B_ward pos=" << P(me.position()) << " t=" << P(t) << " r=" << res << '\n';
    }
    if ((BSCEN != 1 && BSCEN != 2) || idx != 0) return;
    const vec2 bush{35, 25};
    if (me.position() != bush && me.can_move()) me.move_towards(bush);
    std::string seen;
    for (auto& e : cambc::vision::champions(team::enemy)) seen += P(e.position());
    std::string tps;
    for (auto& t : cambc::vision::teleports()) tps += P(t.position()) + (t.is_ally() ? "a:" : "e:") + std::to_string(t.remaining_time());
    if (BSCEN == 1 || !tps.empty() || r % 20 == 0)
        std::cout << "PROBE " << r << " B_" << cambc::to_string(me.champion_name()) << " pos=" << P(me.position())
                  << " hp=" << me.health() << " sees_enemies=[" << seen << "] tps=[" << tps << "]\n";
    if (BSCEN == 2 && me.position() == bush && cambc::vision::has_teleport({36, 25})) {
        std::string res;
        try { res = me.move_absolute({36, 25}) ? "true" : "false"; } catch (const cambc::error& x) { res = cambc::to_string(x.code()); }
        std::cout << "PROBE " << r << " B_move_onto_enemy_reservation r=" << res << " pos=" << P(me.position()) << '\n';
    }
    if (BSCEN == 1 && r == 40 && me.position() == bush) {
        for (auto& e : cambc::vision::champions(team::enemy)) {
            if (me.can_attack() && me.attack_tiles().is_set(e.position())) {
                try { me.attack(e); std::cout << "PROBE " << r << " B attacked " << P(e.position()) << '\n'; }
                catch (const cambc::error& x) { std::cout << "PROBE " << r << " B attack_err " << cambc::to_string(x.code()) << '\n'; }
                break;
            }
        }
    }
}
