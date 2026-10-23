// probe-dash-hidden-camp: does a dash path crossing an unseen camp (on a bush) succeed, fail as a hidden
// blocker, or throw? Map from makemap.mjs: a lone gem cluster on a one-tile bush at (8,8). Team A's Vesper
// Vale stands at (7,7) and dashes to (9,9), whose only 2-step path is through (8,8). It then retries the
// same dash (tile now revealed?) and a control dash to (9,7) (mids (8,6), (8,7) free). Once the dash is
// ready again it repeats the geometry (7,13)->(9,15) over a visible camp on ground at (8,14).
//   cambc run tools/probes/probe-dash-hidden-camp tools/probes/probe-dash-hidden-camp \
//     --map tools/probes/probe-dash-hidden-camp/hiddencamp.map26a --rounds 40 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <string>
#include <vector>

using cambc::team;
using cambc::vec2;
using D = cambc::champion_draft;

namespace {

bool dasher_side() { return cambc::map::spawn_region(team::ally).positions().front().y < 15; }

const vec2 START{ 7, 7 }, CAMP{ 8, 8 }, OVER{ 9, 9 }, CONTROL{ 9, 7 };
const vec2 VSTART{ 7, 13 }, VCAMP{ 8, 14 }, VOVER{ 9, 15 };
int g_role = -1;
bool g_done = false, g_vdone = false;

void report(const char* what) {
    auto& me = cambc::self();
    std::printf("PROBE %d %s at=(%d,%d) camp_tile_visible=%d camp_tile_in_camp_tiles=%d cd=%d\n", (int)cambc::round_number(), what,
                me.position().x, me.position().y, (int)me.visible_tiles().is_set(CAMP), (int)cambc::vision::camp_tiles().is_set(CAMP),
                (int)me.abilities()[1].cooldown());
}

void try_dash(vec2 to, const char* what) {
    auto& me = cambc::self();
    const vec2 from = me.position();
    bool ok = false;
    std::string err = "none";
    try {
        ok = me.abilities()[1].use(to);
    } catch (const cambc::error& e) {
        err = e.message();
    }
    std::printf("PROBE %d dash %s (%d,%d)->(%d,%d) ok=%d err=\"%s\" now=(%d,%d) cd=%d\n", (int)cambc::round_number(), what, from.x, from.y,
                to.x, to.y, (int)ok, err.c_str(), me.position().x, me.position().y, (int)me.abilities()[1].cooldown());
}

void play_turn() {
    auto& me = cambc::self();
    if (g_role < 0) g_role = dasher_side() && me.champion_name() == cambc::champion_type::vesper_vale ? 0 : 2;
    if (!me.is_alive() || g_role != 0 || g_vdone) return;
    if (g_done) {
        if (me.position() != VSTART) {
            if (me.can_move()) me.move_towards(VSTART);
            return;
        }
        if (me.abilities()[1].cooldown() > 0) return;
        std::printf("PROBE %d visible_control at=(%d,%d) vcamp_visible=%d vcamp_in_camp_tiles=%d\n",(int)cambc::round_number(), me.position().x,
                    me.position().y, (int)me.visible_tiles().is_set(VCAMP), (int)cambc::vision::camp_tiles().is_set(VCAMP));
        try_dash(VOVER, "over_visible_camp_only_mid");
        g_vdone = true;
        return;
    }
    if (cambc::round_number() <= 1)
        for (const auto& grp : cambc::map::camp_groups())
            for (const auto& c : grp.camps()) std::printf("PROBE camp spawn=(%d,%d)\n",c.spawn_position().x, c.spawn_position().y);
    if (me.position() != START) {
        if (me.can_move()) me.move_towards(START);
        return;
    }
    report("before");
    try_dash(OVER, "over_hidden_camp_only_mid");
    report("after1");
    if (me.position() == START) {
        try_dash(OVER, "retry_same");
        if (me.position() == START) try_dash(CONTROL, "control_free_mids");
    }
    report("end");
    g_done = true;
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end(); };
    const std::vector<D> a{ D::vesper_vale, D::stellar, D::prism, D::willow, D::tavi };
    const std::vector<D> b{ D::ryth, D::varg, D::willow, D::tavi, D::stellar };
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
