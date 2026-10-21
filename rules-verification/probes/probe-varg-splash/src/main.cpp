// probe-varg-splash: does Varg's basic attack on a camp splash enemy champions within 1 of the camp?
// Self-play on interlock: the team spawning at (37..39,37..39) drafts Varg first; the other team's two lowest-type
// champions stand next to the lone wolf (34,31) near Varg's spawn: one orthogonally adjacent, one diagonally, both
// at Chebyshev 2 from Varg. Varg hits the wolf once when both are in place, logging enemy hp before/after.
//   cambc run rules-verification/probes/probe-varg-splash rules-verification/probes/probe-varg-splash \
//     --map interlock --rounds 60 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <optional>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;

namespace {

bool bottom_left() { return cambc::map::spawn_region(team::ally).positions().front().y > 20; }

const vec2 WOLF{ 34, 31 }, VARG_AT{ 35, 32 }, ORTH{ 34, 30 }, DIAG{ 33, 30 };

void log_enemies(const char* tag) {
    for (const auto& e : cambc::champions(team::enemy)) {
        if (!e.is_visible()) continue;
        std::printf("PROBE %d %s %s@(%d,%d) hp=%.2f\n", (int)cambc::round_number(), tag,
                    cambc::to_string(e.champion_name()).c_str(), e.position().x, e.position().y, e.health());
    }
}

int g_role = -1;  // 0 varg, 1 orth, 2 diag, 3 idle
int g_attacked = -1;

void play_turn() {
    auto& me = cambc::self();
    const bool bl = bottom_left();
    const int r = (int)cambc::round_number();
    if (g_role < 0) {
        if (me.champion_name() == cambc::champion_type::varg) g_role = 0;
        else if (bl) g_role = 3;
        else {
            std::vector<int> types;
            for (const auto& c : cambc::champions(team::ally)) types.push_back((int)c.champion_name());
            std::sort(types.begin(), types.end());
            const int i = (int)(std::find(types.begin(), types.end(), (int)me.champion_name()) - types.begin());
            g_role = i == 0 ? 1 : i == 1 ? 2 : 3;
        }
        std::printf("PROBE %d init %s role=%d str=%.2f hp=%.2f\n", r, cambc::to_string(me.champion_name()).c_str(), g_role,
                    me.strength(), me.health());
        if (g_role == 0)
            for (const auto& g : cambc::map::camp_groups())
                for (const auto& c : g)
                    std::printf("PROBE %d mapcamp %s@(%d,%d)\n", r, cambc::to_string(c.kind()).c_str(), c.spawn_position().x, c.spawn_position().y);
    }
    if (!me.is_alive() || g_role == 3) return;
    const vec2 dest = (g_role == 0 ? VARG_AT : g_role == 1 ? ORTH : DIAG);
    if (me.position() != dest && me.can_move()) me.move_towards(dest);
    if (g_role != 0) {
        if (r >= 20) std::printf("PROBE %d self %s pos=(%d,%d) hp=%.2f\n", r, cambc::to_string(me.champion_name()).c_str(),
                                 me.position().x, me.position().y, me.health());
        return;
    }
    if (me.position() != dest) return;
    const vec2 wolf_pos = WOLF;
    std::optional<cambc::camp> wolf;
    for (const auto& c : cambc::vision::camps()) if (c.position() == wolf_pos) wolf = c;
    if (g_attacked >= 0) {
        if (r <= g_attacked + 3) {
            std::printf("PROBE %d varg pos=(%d,%d) hp=%.2f wolf_hp=%.2f\n", r, me.position().x, me.position().y, me.health(),
                        wolf ? wolf->health() : -1.f);
            log_enemies("later");
        }
        return;
    }
    int in_place = 0;
    for (const auto& e : cambc::champions(team::enemy))
        if (e.is_visible() && (e.position() == ORTH || e.position() == DIAG)) ++in_place;
    if (in_place < 2 || !wolf || !me.can_attack()) {
        std::printf("PROBE %d varg wait pos=(%d,%d) in_place=%d wolf=%d can_attack=%d\n", r, me.position().x, me.position().y,
                    in_place, (int)wolf.has_value(), (int)me.can_attack());
        for (const auto& c : cambc::vision::camps())
            if (c.position().chebyshev_distance(me.position()) <= 3)
                std::printf("PROBE %d camp %s@(%d,%d) hp=%.2f\n", r, cambc::to_string(c.kind()).c_str(), c.position().x, c.position().y, c.health());
        return;
    }
    std::printf("PROBE %d varg pos=(%d,%d) str=%.2f wolf@(%d,%d) wolf_hp_before=%.2f\n", r, me.position().x, me.position().y,
                me.strength(), wolf_pos.x, wolf_pos.y, wolf->health());
    log_enemies("before");
    me.attack(*wolf);
    std::printf("PROBE %d varg wolf_hp_after=%.2f\n", r, wolf->health());
    log_enemies("after");
    g_attacked = r;
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](D d) { return std::find(mine.begin(), mine.end(), d) != mine.end() || std::find(theirs.begin(), theirs.end(), d) != theirs.end(); };
    const std::vector<D> a{ D::varg, D::vesper_vale, D::stellar, D::prism, D::marcella, D::vendetta };
    const std::vector<D> b{ D::ryth, D::vendetta, D::stellar, D::prism, D::marcella, D::vesper_vale };
    for (auto d : bottom_left() ? a : b) if (!taken(d)) { cambc::draft::pick(d); return; }
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
