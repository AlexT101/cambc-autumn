// probe-dash-spawn: can a dash path cross an enemy spawn tile (landing outside it)?
// Self-play: the team whose spawn has the smaller y sends Vesper Vale to a corner of the enemy spawn. For a
// corner C, the diagonal dash (C.x-1,C.y+1)->(C.x+1,C.y-1) (or its mirror) has exactly one 2-step path, through
// C. Both ends are outside the spawn. If refused, a control dash with a free middle shows the dash was castable.
// The other team walks off its spawn so no champion stands on C.
//   cambc run tools/probes/probe-dash-spawn tools/probes/probe-dash-spawn \
//     --map 00interlock --rounds 200 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

using cambc::team;
using cambc::vec2;
using D = cambc::champion_draft;

namespace {

bool dasher_side() {
    return cambc::map::spawn_region(team::ally).positions().front().y < cambc::map::spawn_region(team::enemy).positions().front().y;
}

bool open_tile(vec2 p) {
    using namespace cambc::map;
    return is_in_bounds(p) && !walls().is_set(p) && !holes().is_set(p) && !altars().is_set(p) && !spawn_region(team::enemy).is_set(p) &&
           !spawn_region(team::ally).is_set(p);
}

int g_role = -1;
bool g_have = false, g_done = false;
vec2 g_from, g_to, g_mid;

void pick_geometry() {
    const auto& es = cambc::map::spawn_region(team::enemy);
    const vec2 me = cambc::self().position();
    int best = 1 << 30;
    for (vec2 c : es.positions())
        for (int sx : { -1, 1 })
            for (int sy : { -1, 1 }) {
                const vec2 a{ c.x - sx, c.y + sy }, b{ c.x + sx, c.y - sy };
                if (!open_tile(a) || !open_tile(b)) continue;
                const int d = std::max(std::abs(a.x - me.x), std::abs(a.y - me.y));
                if (d < best) best = d, g_from = a, g_to = b, g_mid = c, g_have = true;
            }
    std::printf("PROBE geometry have=%d from=(%d,%d) mid=(%d,%d) to=(%d,%d)\n", (int)g_have, g_from.x, g_from.y, g_mid.x, g_mid.y, g_to.x, g_to.y);
}

bool try_dash(vec2 to, const char* what) {
    auto& me = cambc::self();
    const vec2 from = me.position();
    bool ok = false;
    std::string err = "none";
    try {
        ok = me.abilities()[1].use(to);
    } catch (const cambc::error& e) {
        err = std::to_string((int)e.code()) + " " + e.message();
    }
    std::printf("PROBE %d dash %s (%d,%d)->(%d,%d) ok=%d err=\"%s\" now=(%d,%d)\n", (int)cambc::round_number(), what, from.x, from.y, to.x,
                to.y, (int)ok, err.c_str(), me.position().x, me.position().y);
    return me.position() == to;
}

void play_turn() {
    auto& me = cambc::self();
    if (g_role < 0) g_role = dasher_side() ? (me.champion_name() == cambc::champion_type::vesper_vale ? 0 : 2) : 1;
    if (!me.is_alive() || g_role == 2) return;
    if (g_role == 1) {
        const vec2 away = cambc::map::spawn_region(team::enemy).positions().front();
        if (cambc::map::spawn_region(team::ally).is_set(me.position()) && me.can_move()) me.move_towards(away);
        return;
    }
    if (!g_have) pick_geometry();
    if (!g_have || g_done) return;
    if (me.position() != g_from) {
        if (me.can_move()) me.move_towards(g_from);
        return;
    }
    if ((int)cambc::round_number() < 120) return;
    bool mid_occupied = false;
    for (const auto& e : cambc::champions(team::enemy))
        if (e.is_visible() && e.position() == g_mid) mid_occupied = true;
    std::printf("PROBE %d at=(%d,%d) enemy_on_mid=%d mid_in_enemy_spawn=%d\n", (int)cambc::round_number(), me.position().x, me.position().y,
                (int)mid_occupied, (int)cambc::map::spawn_region(team::enemy).is_set(g_mid));
    if (!try_dash(g_to, "through_enemy_spawn_only_mid")) {
        const vec2 ctl{ g_from.x + (g_to.x - g_from.x), g_from.y - (g_to.y - g_from.y) };
        std::printf("PROBE control open=%d\n", (int)open_tile(ctl));
        try_dash(ctl, "control");
    }
    g_done = true;
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end(); };
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
