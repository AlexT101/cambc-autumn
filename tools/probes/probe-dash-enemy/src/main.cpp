// probe-dash-enemy: can a dash path cross a visible enemy champion?
// Self-play on interlock: the bottom-left team's Vesper Vale stands at (15,22); the other team's Ryth parks
// on open ground at (16,23). The dash to (17,24) has exactly one 2-step path, through (16,23). If it is
// refused, a control dash to (17,22) (mids (16,21), (16,22) free) shows the dash itself was castable.
// Eight rounds later the same pair is repeated from (17,24) back to (15,22).
//   cambc run tools/probes/probe-dash-enemy tools/probes/probe-dash-enemy \
//     --map 00interlock --rounds 100 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::team;
using cambc::vec2;
using D = cambc::champion_draft;

namespace {

bool dasher_side() { return cambc::map::spawn_region(team::ally).positions().front().y < 20; }

const vec2 PARK{ 16, 23 };
int g_role = -1; // 0 dasher, 1 hider, 2 idle
int g_tries = 0, g_last = -100;

void try_dash(vec2 to, const char* what) {
    auto& me = cambc::self();
    const vec2 from = me.position();
    bool ok = false;
    std::string err;
    try {
        ok = me.abilities()[1].use(to);
    } catch (const cambc::error& e) {
        err = e.message();
    }
    std::printf("PROBE %d dash %s (%d,%d)->(%d,%d) ok=%d err=\"%s\" now=(%d,%d)\n", (int)cambc::round_number(), what, from.x, from.y, to.x,
                to.y, (int)ok, err.c_str(), me.position().x, me.position().y);
}

void play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (g_role < 0) {
        if (dasher_side() && me.champion_name() == cambc::champion_type::vesper_vale) g_role = 0;
        else if (!dasher_side() && me.champion_name() == cambc::champion_type::ryth) g_role = 1;
        else g_role = 2;
    }
    if (!me.is_alive() || g_role == 2) return;
    if (g_role == 1) {
        if (me.position() != PARK && me.can_move()) me.move_towards(PARK);
        return;
    }
    const vec2 start = g_tries % 2 == 0 ? vec2{ 15, 22 } : vec2{ 17, 24 };
    if (me.position() != start) {
        if (me.can_move()) me.move_towards(start);
        return;
    }
    if (g_tries >= 2 || r < 60 || r < g_last + 8) return;
    bool seen = false;
    for (const auto& e : cambc::champions(team::enemy))
        if (e.is_visible() && e.position() == PARK) seen = true;
    std::printf("PROBE %d dasher at=(%d,%d) enemy_visible_on_mid=%d\n", r, me.position().x, me.position().y, (int)seen);
    const vec2 over = g_tries % 2 == 0 ? vec2{ 17, 24 } : vec2{ 15, 22 };
    const vec2 control = g_tries % 2 == 0 ? vec2{ 17, 22 } : vec2{ 15, 24 };
    try_dash(over, "over_enemy_only_mid");
    if (me.position() == start) try_dash(control, "control_side_mids_free");
    ++g_tries;
    g_last = r;
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end(); };
    (void)theirs;
    const std::vector<D> a{ D::vesper_vale, D::stellar, D::prism, D::willow, D::tavi };
    const std::vector<D> b{ D::ryth, D::vendetta, D::varg, D::willow, D::tavi };
    for (auto d : dasher_side() ? a : b)
        if (!taken(d)) {
            cambc::draft::pick(d);
            return;
        }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE err %s\n", e.message().c_str());
        } catch (const std::exception& e) {
            std::printf("PROBE err %s\n", e.what());
        }
        cambc::end_turn();
    }
}
