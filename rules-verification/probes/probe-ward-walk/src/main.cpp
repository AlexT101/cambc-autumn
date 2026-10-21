// probe-ward-walk: do wards block walking or dash landings?
// Self-play; roles by ally order, the dash champion (Vesper Vale / Vendetta) separate:
//   own_next   r1 wards an adjacent free tile, r2 walks onto it.
//   own_same   r1 wards an adjacent free tile and walks onto it in the same turn; r11 wards a tile next to ally_walker.
//   ally_walk  r12 walks onto own_same's ward.
//   enemy      side A stops within 2 of a central tile C and wards it; side B waits next to C, walks onto it once it
//              sees the enemy ward there (or from r120 regardless).
//   dash       r6 wards a free tile at distance 2 and dashes onto it.
//   cambc run rules-verification/probes/probe-ward-walk rules-verification/probes/probe-ward-walk \
//     --map 00expanse --rounds 160 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using cambc::team;
using cambc::vec2;
namespace m = cambc::map;
namespace v = cambc::vision;
using D = cambc::champion_draft;

namespace {

int R() { return (int)cambc::round_number(); }
int cheb(vec2 a, vec2 b) { return std::max(std::abs(a.x - b.x), std::abs(a.y - b.y)); }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }

char side = 0;
std::string role;

void L(const std::string& s) {
    std::printf("PROBE %d %c %s %s %s\n", R(), side, cambc::to_string(cambc::self().champion_name()).c_str(), role.c_str(), s.c_str());
}

std::string state(vec2 t) {
    auto& me = cambc::self();
    std::string s = "pos=" + P(me.position()) + " t=" + P(t) + " vis(t)=" + std::to_string(v::visible_tiles().is_set(t)) +
                    " ward(t)=" + std::to_string(v::has_ward(t)) + " ally(t)=" + std::to_string(v::has_ward(t, team::ally)) +
                    " enemy(t)=" + std::to_string(v::has_ward(t, team::enemy)) + " mine=[";
    for (auto p : me.ward_positions()) s += P(p);
    s += "] wards=[";
    for (auto& w : v::wards()) s += P(w.position()) + (w.is_ally() ? "a" : "e");
    return s + "]";
}

bool on_map(vec2 t) { return t.x >= 0 && t.y >= 0 && t.x < m::width() && t.y < m::height(); }

bool static_free(vec2 t) {
    if (!on_map(t)) return false;
    if (m::walls().is_set(t) || m::holes().is_set(t) || m::altars().is_set(t) || m::spawn_region(team::enemy).is_set(t)) return false;
    for (const auto& g : m::camp_groups())
        for (const auto& c : g)
            if (c.spawn_position() == t) return false;
    return true;
}

bool free_now(vec2 t) { return static_free(t) && !v::champion_tiles().is_set(t) && !v::has_ward(t); }

vec2 pick(int lo, int hi, vec2 near_also = { -100, -100 }) {
    const vec2 me = cambc::self().position();
    for (int dy = -hi; dy <= hi; ++dy)
        for (int dx = -hi; dx <= hi; ++dx) {
            const vec2 t{ me.x + dx, me.y + dy };
            const int d = cheb(t, me);
            if (d < lo || d > hi || !free_now(t)) continue;
            if (near_also.x > -100 && cheb(t, near_also) != 1) continue;
            return t;
        }
    return { -1, -1 };
}

std::string attempt_ward(vec2 t) {
    try { return cambc::self().place_ward(t) ? "true" : "false"; }
    catch (const cambc::error& e) { return std::string("throw:") + cambc::to_string(e.code()); }
}

void walk(const std::string& tag, vec2 t) {
    L(tag + " before " + state(t) + " can_move=" + std::to_string(cambc::self().can_move()));
    std::string r;
    try { r = cambc::self().move_absolute(t) ? "true" : "false"; }
    catch (const cambc::error& e) { r = std::string("throw:") + cambc::to_string(e.code()); }
    L(tag + " move_absolute" + P(t) + "=" + r + " after " + state(t));
}

void approach(vec2 t) {
    auto& me = cambc::self();
    if (!me.can_move()) return;
    try { me.move_towards(t); } catch (const cambc::error&) {}
}

vec2 centre() {
    const vec2 c{ m::width() / 2, m::height() / 2 };
    for (int r = 0; r < 20; ++r)
        for (int dy = -r; dy <= r; ++dy)
            for (int dx = -r; dx <= r; ++dx) {
                const vec2 t{ c.x + dx, c.y + dy };
                if (cheb(t, c) == r && static_free(t) && !m::spawn_region(team::ally).is_set(t)) return t;
            }
    return c;
}

vec2 target{ -1, -1 };
int done_r = -1;

void play() {
    auto& me = cambc::self();
    const int r = R();
    if (role.empty()) {
        const vec2 a = m::spawn_region(team::ally).positions().front(), e = m::spawn_region(team::enemy).positions().front();
        side = (a.x < e.x || (a.x == e.x && a.y < e.y)) ? 'A' : 'B';
        bool dash = false;
        for (const auto& ab : me.abilities()) dash |= ab.is_dash();
        if (dash) role = "dash";
        else {
            int i = 0;
            for (const auto& c : cambc::champions(team::ally)) {
                if (c == me) break;
                bool d = false;
                for (const auto& ab : c.abilities()) d |= ab.is_dash();
                if (!d) ++i;
            }
            const char* roles[] = { "own_next", "enemy", "own_same", "ally_walk" };
            role = i < 4 ? roles[i] : "idle";
        }
        L("init pos=" + P(me.position()) + " map=" + std::to_string(m::width()) + "x" + std::to_string(m::height()));
    }
    if (!me.is_alive()) return;

    if (role == "own_next") {
        if (r == 1) { target = pick(1, 1); L("ward" + P(target) + "=" + attempt_ward(target) + " " + state(target)); }
        if (r == 2) walk("own_next", target);
        if (r >= 3 && r <= 4) L("check " + state(target));
    } else if (role == "own_same") {
        if (r == 1) {
            target = pick(1, 1);
            L("ward" + P(target) + "=" + attempt_ward(target) + " " + state(target));
            walk("own_same", target);
        }
        if (r == 2) L("check " + state(target));
        if (r == 11) {
            vec2 w{ -100, -100 };
            for (const auto& c : cambc::champions(team::ally))
                if (c.is_visible() && c.champion_name() == cambc::champion_type::marcella) w = c.position();
            target = pick(1, 2, w);
            L("ally_ward for walker@" + P(w) + " ward" + P(target) + "=" + attempt_ward(target) + " " + state(target));
        }
        if (r >= 12 && r <= 13) L("check " + state(target));
    } else if (role == "ally_walk") {
        if (r == 12) {
            for (const auto& w : v::wards())
                if (w.is_ally() && cheb(w.position(), me.position()) == 1) { target = w.position(); break; }
            if (target.x >= 0) walk("ally_walk", target);
            else L("no adjacent ally ward " + state(me.position()));
        }
        if (r == 13 && target.x >= 0) L("check " + state(target));
    } else if (role == "dash") {
        if (r == 6) {
            target = pick(2, 2);
            L("ward" + P(target) + "=" + attempt_ward(target) + " " + state(target) + " can_cast=" + std::to_string(me.can_cast()));
            for (const auto& ab : me.abilities())
                if (ab.is_dash()) {
                    std::string res;
                    try { res = ab.use(target) ? "true" : "false"; }
                    catch (const cambc::error& e) { res = std::string("throw:") + cambc::to_string(e.code()); }
                    L("dash" + P(target) + "=" + res + " after " + state(target));
                }
        }
        if (r >= 7 && r <= 8) L("check " + state(target));
    } else if (role == "enemy") {
        const vec2 c = centre();
        if (side == 'A') {
            if (done_r < 0) {
                if (cheb(me.position(), c) > 2) approach(c);
                if (cheb(me.position(), c) <= 2) {
                    L("ward" + P(c) + "=" + attempt_ward(c) + " " + state(c));
                    if (v::has_ward(c, team::ally)) done_r = r;
                }
            } else if (r % 5 == 0 || r <= done_r + 3) L("owner_check " + state(c));
        } else {
            if (done_r < 0) {
                if (cheb(me.position(), c) > 1) approach(c);
                if (cheb(me.position(), c) == 1 && (v::has_ward(c, team::enemy) || r >= 120)) {
                    walk("enemy_ward", c);
                    if (me.position() == c) done_r = r;
                } else if (cheb(me.position(), c) <= 1 && r % 5 == 0) L("waiting " + state(c));
            } else if (r <= done_r + 3 || r % 10 == 0) L("standing " + state(c));
        }
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const bool have_dash = std::find(mine.begin(), mine.end(), D::vesper_vale) != mine.end() ||
                           std::find(mine.begin(), mine.end(), D::vendetta) != mine.end();
    std::vector<D> pref{ D::ryth, D::stellar, D::prism, D::marcella, D::ren, D::varg, D::willow, D::tavi };
    if (!have_dash) pref.insert(pref.begin(), { D::vesper_vale, D::vendetta });
    for (auto d : pref) if (!taken(d)) { cambc::draft::pick(d); return; }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play();
        } catch (const cambc::error& e) {
            std::printf("PROBE %d err %s\n", R(), e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE %d err %s\n", R(), e.what()); }
        cambc::end_turn();
    }
}
