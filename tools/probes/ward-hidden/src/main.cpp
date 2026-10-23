// ward-hidden probe: placing a ward on a tile that already holds a ward, allied or enemy, seen or unseen.
// Both teams run it on corners, whose central bush column (x=35) is unseen from outside:
//   cambc run tools/probes/ward-hidden tools/probes/ward-hidden --map corners --rounds 80 --fuel 50000000
// side s = -1 (left team) or +1 (right team); stand tiles are mirrored, bush targets differ by side.
//   A  visible allied ward: champion 2 wards its own tile on round 1; champion 1 places onto it on round 2.
//   B  unseen allied ward:  champion 0 wards bush (35,24|29) from (35+2s,same y); champion 1, standing outside
//      the bush within 2, places onto it on round 40, again in the same round, and on rounds 41-42.
//   C  unseen enemy ward:   left champion 2 wards bush (35,45) from (33,45); right champion 2, at (37,45),
//      places onto it on round 45, again in the same round, and on round 46.
//   D  visible enemy ward:  left champion 1 wards open (35,20) from (34,21) on round 50+; right champion 1,
//      at (36,21), places onto it on round 60.
#include <cambc.h>
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <string>

using cambc::team;
using cambc::vec2;
namespace m = cambc::map;
namespace v = cambc::vision;

namespace {

int R() { return static_cast<int>(cambc::round_number()); }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
int side = 0;
void L(const std::string& s) {
    std::cout << "PROBE " << R() << " " << (side < 0 ? "left" : "right") << " "
              << cambc::to_string(cambc::self().champion_name()) << " " << s << std::endl;
}
int cheb(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }

int my_index() {
    int i = 0;
    for (auto& c : cambc::champions(team::ally)) {
        if (c == cambc::self()) return i;
        ++i;
    }
    return -1;
}

std::string state(vec2 t) {
    auto& me = cambc::self();
    std::string s = "pos=" + P(me.position()) + " cd=" + std::to_string(me.ward_cooldown()) + " mine=[";
    for (auto p : me.ward_positions()) s += P(p);
    s += "] vis(t)=" + std::to_string(v::visible_tiles().is_set(t)) + " bush(t)=" + std::to_string(m::bushes().is_set(t)) +
         " has_ward(t)=" + std::to_string(v::has_ward(t)) + " ally=" + std::to_string(v::has_ward(t, team::ally)) +
         " enemy=" + std::to_string(v::has_ward(t, team::enemy)) + " wards=[";
    for (auto& w : v::wards()) s += P(w.position()) + (w.is_ally() ? "a" : "e");
    return s + "]";
}

void place(const std::string& tag, vec2 t) {
    L(tag + " before " + state(t));
    std::string r;
    try {
        r = cambc::self().place_ward(t) ? "true" : "false";
    } catch (const cambc::error& e) {
        r = std::string("throw:") + cambc::to_string(e.code());
    }
    L(tag + " place_ward" + P(t) + "=" + r + " after " + state(t));
}

bool go(vec2 p) {
    auto& me = cambc::self();
    if (me.position() == p) return true;
    if (me.can_move()) {
        try {
            me.move_towards(p);
        } catch (const cambc::error&) {
        }
    }
    return me.position() == p;
}

void turn(int i) {
    const int r = R();
    auto& me = cambc::self();
    const bool left = side < 0;
    if (i == 0) {
        static bool done = false;
        const int y = left ? 24 : 29;
        if (go({35 + 2 * side, y}) && !done) {
            done = true;
            place("B_owner", {35, y});
        }
    } else if (i == 1) {
        if (r == 2)
            for (auto& w : v::wards())
                if (w.is_ally() && cheb(w.position(), me.position()) <= 2) {
                    place("A_visible_ally", w.position());
                    break;
                }
        if (r < 50) {
            const vec2 t{35, left ? 24 : 29};
            if (r > 2) go({35 + 2 * side, left ? 26 : 27});
            if (r == 40) {
                place("B_unseen_ally#1", t);
                place("B_unseen_ally#2", t);
            }
            if (r == 41) place("B_unseen_ally#3", t);
            if (r == 42) place("B_unseen_ally#4", t);
        } else {
            const vec2 t{35, 20};
            static bool done = false;
            if (go({35 + side, 21}) && left && !done) {
                done = true;
                place("D_owner", t);
            }
            if (!left && r == 60) place("D_visible_enemy", t);
        }
    } else if (i == 2) {
        if (r == 1) place("A_owner", me.position());
        if (r < 3) return;
        const vec2 t{35, 45};
        static bool done = false;
        if (go({35 + 2 * side, 45}) && left && !done && r >= 30) {
            done = true;
            place("C_owner", t);
        }
        if (!left && r == 45) {
            place("C_unseen_enemy#1", t);
            place("C_unseen_enemy#2", t);
        }
        if (!left && r == 46) place("C_unseen_enemy#3", t);
        if (left && r >= 44 && r <= 48) L("C_owner_check " + state(t));
    }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) {
                using cd = cambc::champion_draft;
                const cd prefs[] = {cd::varg, cd::ryth, cd::ren, cd::marcella, cd::vendetta};
                const auto chosen = cambc::draft::current_draft(team::ally);
                for (auto p : prefs)
                    if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) {
                        cambc::draft::pick(p);
                        break;
                    }
            } else if (cambc::self().is_alive()) {
                if (side == 0) side = cambc::self().position().x < 35 ? -1 : 1;
                turn(my_index());
            }
        } catch (const std::exception& e) {
            L(std::string("uncaught ") + e.what());
        }
        cambc::end_turn();
    }
}
