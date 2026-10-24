// probe-dash-diagonal: does a dash take paths with diagonal king steps across holes and altars and
// through diagonal squeezes, and does the bots' landing board (reachable_tiles(S, 2) over walls,
// camps, visible enemies and the enemy spawn, as astraeus's dash_landings_from) agree?
// Map: tools/probes/probe-dash-diagonal/dash.map26a (built by makemap.mjs; stations listed there).
// Run: bash tools/probes/probe-dash-diagonal/run.sh
// Both teams run the same script, team B in rotated coordinates. Vesper (tester) walks to each
// station S, logs the landing board's 5x5 around S (row dy=+2 first, '#' a landing, '.' not, 'S'
// itself) and dashes to S + offset.
#include <cambc.h>
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

struct Test { char id; vec2 s; vec2 off; const char* what; };
const std::vector<Test> TESTS = {
    { 'K', { 5, 5 }, { 2, 2 }, "diag_over_hole" },
    { 'L', { 11, 5 }, { 2, 1 }, "card_diag_over_hole" },
    { 'M', { 17, 5 }, { 2, 2 }, "squeeze_onto_hole" },
    { 'N', { 23, 5 }, { 2, 2 }, "diag_over_altar" },
    { 'O', { 5, 11 }, { 2, 2 }, "diag_over_wall" },
    { 'P', { 11, 11 }, { 2, 2 }, "double_squeeze" },
    { 'Q', { 17, 11 }, { 1, 2 }, "card_diag_over_holes_squeeze" },
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

// Travel keeps a tile off every station blocker, so it never depends on the rules under test.
void travel(vec2 goal) {
    auto& me = cambc::self();
    if (!me.can_move()) return;
    const vec2 here = me.position();
    if (here == goal) return;
    auto w = dilate(cambc::map::walls() | cambc::map::holes() | cambc::map::altars()) |
             cambc::map::spawn_region(cambc::team::enemy) | cambc::vision::champion_tiles();
    w.set(goal, false);
    w.set(here, false);
    distance_field f;
    bitboard visited;
    f.compute_to(w, single(goal), single(here), visited);
    for (auto d : f.next_moves_from(here)) {
        try {
            if (me.move_absolute(here + d)) return;
        } catch (const cambc::error& e) {
            std::cout << tag() << "travel step " << P(here + d) << " error " << e.what() << '\n';
        }
    }
    std::cout << tag() << "travel stuck at " << P(here) << " goal " << P(goal) << '\n';
}

// astraeus's dash_landings_from, from public SDK calls.
bitboard landings(vec2 s) {
    const auto enemies = cambc::vision::champion_tiles(cambc::team::enemy);
    auto excluded = cambc::map::walls() | cambc::vision::camp_tiles() | enemies | cambc::map::spawn_region(cambc::team::enemy);
    auto out = excluded.reachable_tiles(s, 2);
    out &= ~(cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::map::spawn_region(cambc::team::enemy) |
             cambc::vision::camp_tiles() | cambc::vision::champion_tiles());
    out.set(s, false);
    return out;
}

std::string board(vec2 s, const bitboard& b) {
    std::string out;
    for (int dy = 2; dy >= -2; --dy) {
        for (int dx = -2; dx <= 2; ++dx) {
            const vec2 p = s + TO({ dx, dy });
            out += (dx == 0 && dy == 0) ? 'S' : !cambc::map::is_in_bounds(p) ? '?' : b.is_set(p) ? '#' : '.';
        }
        if (dy > -2) out += '/';
    }
    return out;
}

std::size_t next_test = 0;

void tester() {
    auto& me = cambc::self();
    if (next_test >= TESTS.size()) return;
    const Test& t = TESTS[next_test];
    const vec2 s = T(t.s), to = s + TO(t.off);
    if (me.position() != s) {
        travel(s);
        return;
    }
    if (!me.abilities()[1].is_ready()) return;
    const auto b = landings(s);
    std::string res;
    try {
        res = me.abilities()[1].use(to) ? "ok" : "false";
    } catch (const cambc::error& e) {
        res = std::string("error ") + e.what();
    }
    std::cout << tag() << "dash " << t.id << ' ' << t.what << ' ' << P(t.off) << " from " << P(s) << " to " << P(to)
              << " sdk_landing=" << b.is_set(to) << " res=" << res << " now=" << P(me.position()) << " board=" << board(s, b)
              << '\n';
    if (++next_test == TESTS.size()) std::cout << tag() << "done\n";
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
            else if (cambc::self().champion_name() == cambc::champion_type::vesper_vale) tester();
        } catch (const std::exception& e) {
            std::cout << "PROBE error " << e.what() << '\n';
        }
        cambc::end_turn();
    }
}
