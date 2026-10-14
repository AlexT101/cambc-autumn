// probe-corner: can a champion walk or dash diagonally between two orthogonally adjacent blockers
// ("corner cutting"), per blocker type; does distance_field agree; does vision pass a diagonal gap?
// Map: rules-verification/probes/probe-corner/corner.map26a (built by makemap.mjs; stations listed there).
// Run: bash rules-verification/probes/probe-corner/run.sh
// Both teams run the same script, team B in mirrored (rotated) coordinates, so B tests the
// south-west squeeze. Vesper (tester) walks to each station S and tries the move or dash; Vendetta
// and Ryth stand on S+(1,0) and S+(0,1) of station H; Ryth leaves when shared memory byte 0 is 1.
#include <cambc.h>
#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

using cambc::bitboard;
using cambc::distance_field;
using cambc::vec2;

namespace {

bool team_a() { return cambc::map::spawn_region(cambc::team::ally).is_set({ 0, 0 }); }
vec2 T(vec2 p) { return team_a() ? p : vec2{ cambc::map::width() - 1 - p.x, cambc::map::height() - 1 - p.y }; }
vec2 TO(vec2 o) { return team_a() ? o : -o; }
std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
std::string tag() {
    return "PROBE r" + std::to_string(cambc::round_number()) + ' ' + (team_a() ? 'A' : 'B') + ' ' +
           cambc::to_string(cambc::self().champion_name()) + ' ';
}

struct Station { char id; vec2 s; const char* what; };
const Station STATIONS[] = {
    { 'A', { 6, 5 }, "one_wall@(1,0)" },   { 'B', { 11, 5 }, "two_holes" },     { 'C', { 16, 5 }, "one_hole@(1,0)" },
    { 'D', { 21, 5 }, "two_altars" },      { 'E', { 26, 5 }, "one_altar@(1,0)" }, { 'F', { 6, 11 }, "two_camps" },
    { 'G', { 11, 11 }, "one_camp@(1,0)" }, { 'H', { 16, 11 }, "allies" },        { 'I', { 21, 11 }, "diag_wall_line" },
    { 'J', { 26, 14 }, "two_walls" },
};
const Station& station(char id) {
    for (auto& s : STATIONS)
        if (s.id == id) return s;
    return STATIONS[0];
}
const vec2 CAMPS[] = { { 7, 11 }, { 6, 12 }, { 12, 11 } };
const vec2 H1{ 17, 11 }, H2{ 16, 12 }, H2_AWAY{ 13, 8 };

enum Kind { WALK, DASH, VISION, WAIT_HELPERS, SIGNAL, WAIT_EMPTY };
struct Test { char st; Kind kind; vec2 off; };
const std::vector<Test> TESTS = {
    { 'A', WALK, { 1, 1 } }, { 'A', DASH, { 1, 1 } }, { 'A', DASH, { 2, 0 } }, { 'A', DASH, { 2, 1 } },
    { 'B', WALK, { 1, 1 } }, { 'B', DASH, { 1, 1 } }, { 'B', DASH, { 2, 2 } },
    { 'C', WALK, { 1, 1 } },
    { 'D', WALK, { 1, 1 } }, { 'D', DASH, { 1, 1 } }, { 'D', DASH, { 2, 2 } },
    { 'E', WALK, { 1, 1 } },
    { 'J', VISION, {} },     { 'J', WALK, { 1, 1 } }, { 'J', DASH, { 1, 1 } }, { 'J', DASH, { 2, 2 } },
    { 'I', VISION, {} },     { 'I', WALK, { 1, 1 } }, { 'I', DASH, { 1, 1 } }, { 'I', DASH, { 2, 2 } },
    { 'H', WAIT_HELPERS, {} }, { 'H', WALK, { 1, 1 } }, { 'H', DASH, { 1, 1 } }, { 'H', DASH, { 2, 2 } },
    { 'H', SIGNAL, {} },     { 'H', WAIT_EMPTY, {} }, { 'H', WALK, { 1, 1 } }, { 'H', DASH, { 1, 1 } },
    { 'G', WALK, { 1, 1 } }, { 'G', DASH, { 1, 1 } }, { 'G', DASH, { 2, 0 } },
    { 'F', WALK, { 1, 1 } }, { 'F', DASH, { 1, 1 } }, { 'F', DASH, { 2, 2 } },
};

bitboard single(vec2 p) {
    bitboard b;
    b.set(p);
    return b;
}

bitboard dilate(const bitboard& b) {
    auto h = b | b.shift_right(1) | b.shift_right(-1);
    return h | h.shift_up(1) | h.shift_up(-1);
}

// Travel never passes next to a station blocker, so it never depends on corner cutting.
bitboard travel_walls(vec2 me, vec2 goal, bool avoid_helpers) {
    bitboard fixed = cambc::map::walls() | cambc::map::holes() | cambc::map::altars();
    for (auto c : CAMPS) fixed.set(T(c));
    if (avoid_helpers) {
        fixed.set(T(H1));
        fixed.set(T(H2));
    }
    auto w = dilate(fixed) | cambc::map::spawn_region(cambc::team::enemy) | cambc::vision::champion_tiles();
    w.set(goal, false);
    w.set(me, false);
    return w;
}

void travel(vec2 goal, bool avoid_helpers = true) {
    auto& me = cambc::self();
    if (!me.can_move()) return;
    const vec2 here = me.position();
    if (here == goal) return;
    const auto walls = travel_walls(here, goal, avoid_helpers);
    distance_field f;
    bitboard visited;
    f.compute_to(walls, single(goal), single(here), visited);
    for (auto d : f.next_moves_from(here)) {
        try {
            if (me.move_absolute(here + d)) return;
        } catch (const cambc::error& e) {
            std::cout << tag() << "travel step " << P(here + d) << " error " << e.what() << '\n';
        }
    }
    std::cout << tag() << "travel stuck at " << P(here) << " goal " << P(goal) << " field=" << f.get(here) << '\n';
}

std::string dist(const distance_field& f, vec2 p) {
    if (!cambc::map::is_in_bounds(p)) return "oob";
    const auto d = f.get(p);
    return d == distance_field::unreachable ? "inf" : std::to_string(d);
}

// What the host search says about the squeeze, with the engine's live blockers.
void log_field(const Station& st) {
    const vec2 s = T(st.s);
    auto blockers = cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::vision::camp_tiles() |
                    cambc::vision::champion_tiles() | cambc::map::spawn_region(cambc::team::enemy);
    blockers.set(s, false);
    distance_field f;
    bitboard visited;
    f.compute(blockers, single(s), visited);
    std::cout << tag() << "field " << st.id << ' ' << st.what << " S=" << P(s);
    for (vec2 o : { vec2{ 1, 1 }, vec2{ 2, 2 }, vec2{ 2, 0 }, vec2{ 2, 1 } }) std::cout << " d" << P(o) << '=' << dist(f, s + TO(o));
    const auto reach1 = blockers.reachable_tiles(s, 1);
    const auto moves = f.next_moves_from(s + TO({ 1, 1 }));
    std::cout << " reach1_has(1,1)=" << reach1.is_set(s + TO({ 1, 1 })) << " next_from(1,1):";
    for (auto m : moves) std::cout << ' ' << P(team_a() ? m : -m);
    // The same with only the dash-path blockers (walls, camps).
    auto dash_blockers = cambc::map::walls() | cambc::vision::camp_tiles();
    dash_blockers.set(s, false);
    f.compute(dash_blockers, single(s), visited);
    std::cout << " dashfield";
    for (vec2 o : { vec2{ 1, 1 }, vec2{ 2, 2 }, vec2{ 2, 0 }, vec2{ 2, 1 } }) std::cout << " d" << P(o) << '=' << dist(f, s + TO(o));
    std::cout << '\n';
}

void log_vision(const Station& st) {
    const vec2 s = T(st.s);
    const auto seen = cambc::vision::visible_tiles();
    const auto cast = cambc::map::walls().shadow_cast(s, 8);
    std::cout << tag() << "vision " << st.id << " S=" << P(s) << " at=" << P(cambc::self().position());
    for (int k = 1; k <= 6; ++k) {
        const vec2 p = s + TO({ k, k });
        if (!cambc::map::is_in_bounds(p)) break;
        std::cout << " (" << k << ',' << k << ")=" << seen.is_set(p) << '/' << cast.is_set(p);
    }
    for (vec2 o : { vec2{ 1, 2 }, vec2{ 2, 1 }, vec2{ 2, 3 }, vec2{ 3, 2 } })
        std::cout << ' ' << P(o) << '=' << seen.is_set(s + TO(o)) << '/' << cast.is_set(s + TO(o));
    // Tiles strictly beyond the squeeze diagonal (x+y > S.x+S.y+1 in team A's frame), within the square.
    int beyond = 0, beyond_seen = 0, beyond_cast = 0;
    for (int dy = -8; dy <= 8; ++dy)
        for (int dx = -8; dx <= 8; ++dx) {
            if (dx + dy <= 1) continue;
            const vec2 p = s + TO({ dx, dy });
            if (!cambc::map::is_in_bounds(p) || cambc::map::walls().is_set(p)) continue;
            ++beyond;
            beyond_seen += seen.is_set(p);
            beyond_cast += cast.is_set(p);
        }
    std::cout << " beyond=" << beyond << " seen=" << beyond_seen << " cast=" << beyond_cast
              << " seen_xor_cast=" << (seen ^ cast).count() << '\n';
}

std::size_t next_test = 0;
std::vector<char> logged;

void tester() {
    auto& me = cambc::self();
    while (next_test < TESTS.size()) {
        const Test& t = TESTS[next_test];
        const Station& st = station(t.st);
        const vec2 s = T(st.s), here = me.position();
        if (here != s) {
            travel(s);
            return;
        }
        if (std::find(logged.begin(), logged.end(), t.st) == logged.end()) {
            logged.push_back(t.st);
            log_field(st);
        }
        const std::string what = std::string(1, t.st) + ' ' + st.what + ' ';
        if (t.kind == WALK || t.kind == DASH) {
            const bool dash = t.kind == DASH;
            if (dash ? !me.abilities()[1].is_ready() : !me.can_move()) return;
            const vec2 to = s + TO(t.off);
            std::string res;
            try {
                res = (dash ? me.abilities()[1].use(to) : me.move_absolute(to)) ? "ok" : "false";
            } catch (const cambc::error& e) {
                res = std::string("error ") + e.what();
            }
            std::cout << tag() << (dash ? "dash " : "walk ") << what << P(t.off) << " from " << P(s) << " to " << P(to)
                      << " res=" << res << " now=" << P(me.position()) << '\n';
        } else if (t.kind == VISION) {
            log_vision(st);
        } else if (t.kind == WAIT_HELPERS) {
            if (!cambc::vision::has_champion(T(H1)) || !cambc::vision::has_champion(T(H2))) return;
            std::cout << tag() << "helpers in place " << P(T(H1)) << ' ' << P(T(H2)) << '\n';
            log_field(st);
        } else if (t.kind == SIGNAL) {
            cambc::shared_memory[0] = std::uint8_t{ 1 };
        } else if (t.kind == WAIT_EMPTY) {
            if (cambc::vision::has_champion(T(H2))) return;
            std::cout << tag() << "H2 left; ally only on " << P(T(H1)) << '\n';
            log_field(st);
        }
        ++next_test;
    }
    if (next_test == TESTS.size()) {
        std::cout << tag() << "done\n";
        ++next_test;
    }
}

void play() {
    const auto name = cambc::self().champion_name();
    if (name == cambc::champion_type::vesper_vale) tester();
    else if (name == cambc::champion_type::vendetta) travel(T(H1), false);
    else travel(cambc::shared_memory[0] ? T(H2_AWAY) : T(H2), false);
}

void draft() {
    const cambc::champion_draft order[] = { cambc::champion_draft::vesper_vale, cambc::champion_draft::vendetta,
                                            cambc::champion_draft::ryth };
    const auto ours = cambc::draft::current_draft(cambc::team::ally);
    cambc::draft::pick(order[ours.size()]);
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) draft();
            else play();
        } catch (const std::exception& e) {
            std::cout << "PROBE error " << e.what() << '\n';
        }
        cambc::end_turn();
    }
}
