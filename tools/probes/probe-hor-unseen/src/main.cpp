// probe-hor-unseen: does Heart of Ruin's dash landing hit (damage + stun) an enemy champion HoR cannot see (in a bush)?
// Self-play on interlock: the bottom-left team drafts heart_of_ruin; the other team's Ryth walks into bush (13,22)
// and stays. HoR stands at (16,22), checks the bush tile and Ryth are unseen, then dashes onto (14,22) (non-bush,
// adjacent to the bush). Ryth logs its own hp, buffs and can_move/can_attack every turn.
//   cambc run tools/probes/probe-hor-unseen tools/probes/probe-hor-unseen \
//     --map 00interlock --rounds 90 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;

namespace {

bool hor_side() { return cambc::map::spawn_region(team::ally).positions().front().y < 20; }

const vec2 BUSH{ 13, 22 }, HOR_AT{ 16, 22 }, LAND{ 14, 22 };
int g_role = -1;  // 0 hor, 1 hider, 2 idle
int g_cast = -1;

void log_self(const char* tag) {
    auto& me = cambc::self();
    const auto b = me.buffs();
    std::printf("PROBE %d %s %s pos=(%d,%d) hp=%.2f stun=%d stun_dur=%d can_move=%d can_attack=%d\n", (int)cambc::round_number(), tag,
                cambc::to_string(me.champion_name()).c_str(), me.position().x, me.position().y, me.health(), (int)b.has_stun(),
                b.has_stun() ? (int)b.get<cambc::buff_stun>().duration : -1, (int)me.can_move(), (int)me.can_attack());
}

void log_enemies(const char* tag) {
    const auto vis = cambc::vision::visible_tiles();
    std::printf("PROBE %d %s bush_tile_visible=%d land_visible=%d\n", (int)cambc::round_number(), tag, (int)vis.is_set(BUSH),
                (int)vis.is_set(LAND));
    for (const auto& e : cambc::champions(team::enemy)) {
        if (!e.is_visible()) { std::printf("PROBE %d %s enemy %s unseen\n", (int)cambc::round_number(), tag, cambc::to_string(e.champion_name()).c_str()); continue; }
        std::printf("PROBE %d %s enemy %s@(%d,%d) hp=%.2f\n", (int)cambc::round_number(), tag,
                    cambc::to_string(e.champion_name()).c_str(), e.position().x, e.position().y, e.health());
    }
}

void play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (g_role < 0) {
        if (me.champion_name() == cambc::champion_type::heart_of_ruin) g_role = 0;
        else if (!hor_side() && me.champion_name() == cambc::champion_type::ryth) g_role = 1;
        else g_role = 2;
        std::printf("PROBE %d init %s role=%d focus=%.2f hp=%.2f bush(13,22)=%d bush(14,22)=%d bush(12,22)=%d\n", r,
                    cambc::to_string(me.champion_name()).c_str(), g_role, me.focus(), me.health(),
                    (int)cambc::map::bushes().is_set(BUSH), (int)cambc::map::bushes().is_set(LAND), (int)cambc::map::bushes().is_set({ 12, 22 }));
    }
    if (!me.is_alive() || g_role == 2) return;
    if (g_role == 1) {
        if (me.position() != BUSH && me.can_move()) me.move_towards(BUSH);
        if (r >= 40) log_self("hider");
        return;
    }
    if (me.position() != HOR_AT && g_cast < 0 && me.can_move()) me.move_towards(HOR_AT);
    if (g_cast >= 0) {
        if (r <= g_cast + 3) { log_self("hor-after"); log_enemies("hor-after"); }
        return;
    }
    if (me.position() != HOR_AT || r < 70) return;
    const auto ab = me.abilities()[1];
    log_self("hor-before");
    log_enemies("hor-before");
    std::printf("PROBE %d hor dash is_dash=%d dmg_amount=%.2f\n", r, (int)ab.is_dash(), ab.damage_amount());
    const bool ok = ab.use(LAND);
    std::printf("PROBE %d hor dash_used=%d\n", r, (int)ok);
    log_self("hor-cast");
    log_enemies("hor-cast");
    g_cast = r;
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::heart_of_ruin, D::stellar, D::prism, D::willow, D::tavi, D::vesper_vale };
    const std::vector<D> b{ D::ryth, D::vendetta, D::varg, D::vesper_vale, D::willow, D::tavi };
    for (auto d : hor_side() ? a : b) if (!taken(d)) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE err %s\n", e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE err %s\n", e.what()); }
        cambc::end_turn();
    }
}
