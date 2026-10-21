// probe-sleep-range: does a camp group's sleep check use each member's own range (elk 4) or one group range (3)?
// Self-play on elkring. Team A (spawn (0,0)) Vesper Vale hits the elk (9,2) of group {elk (9,2), gem (9,3), gold (10,2)}
// from (6,2), then stands at (5,2): Chebyshev 4 from the elk and the gem cluster, 5 from the gold cluster. From W+9 it
// stands at (4,2), 5 from the elk, as a control that the group does fall asleep. Everyone else idles at spawn.
//   cambc run rules-verification/probes/probe-sleep-range rules-verification/probes/probe-sleep-range \
//     --map 00elkring --rounds 40 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <cstdio>
using cambc::team;
using cambc::vec2;
using D = cambc::champion_draft;

namespace {
const vec2 ELK{ 9, 2 }, WAKE_AT{ 6, 2 }, HOLD_AT{ 5, 2 }, CONTROL_AT{ 4, 2 };
int g_woke = -1;

void log_state(int r) {
    auto& me = cambc::self();
    std::printf("PROBE %d pos=(%d,%d) d_elk=%d hp=%.2f", r, me.position().x, me.position().y, (int)me.position().chebyshev_distance(ELK), (double)me.health());
    for (const auto& c : cambc::vision::camps())
        if (c.position().chebyshev_distance(ELK) <= 1)
            std::printf(" %s@(%d,%d):%s/%.0f/d%d", cambc::to_string(c.kind()).c_str(), c.position().x, c.position().y,
                        c.is_awake() ? "awake" : c.is_asleep() ? "asleep" : "dead", (double)c.health(), (int)c.position().chebyshev_distance(me.position()));
    std::printf("\n");
}

void play_turn() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    if (r == 1) std::printf("PROBE %d init %s spawn_y=%d\n", r, cambc::to_string(me.champion_name()).c_str(), cambc::map::spawn_region(team::ally).positions().front().y);
    if (cambc::map::spawn_region(team::ally).positions().front().y > 15) return;
    if (me.champion_name() != cambc::champion_type::vesper_vale) {
        int i = 0;
        for (const auto& c : cambc::champions(team::ally))
            if (c.champion_name() != cambc::champion_type::vesper_vale && (int)c.champion_name() < (int)me.champion_name()) ++i;
        const vec2 park[4]{ { 0, 2 }, { 1, 2 }, { 2, 2 }, { 2, 1 } };
        if (me.position() != park[i] && me.can_move()) me.move_towards(park[i]);
        return;
    }
    if (g_woke < 0) {
        std::printf("PROBE %d approach pos=(%d,%d)\n", r, me.position().x, me.position().y);
        if (me.position() != WAKE_AT) { if (me.can_move()) me.move_towards(WAKE_AT); return; }
        for (const auto& c : cambc::vision::camps())
            if (c.position() == ELK && me.can_attack()) {
                log_state(r);
                me.attack(c);
                g_woke = r;
                std::printf("PROBE %d attacked elk\n", r);
                log_state(r);
                return;
            }
        return;
    }
    log_state(r);
    const vec2 dest = r <= g_woke + 8 ? HOLD_AT : CONTROL_AT;
    if (me.position() != dest && me.can_move()) me.move_towards(dest);
    if (r > g_woke + 20) return;
}

void play_draft() {
    for (auto d : { D::vesper_vale, D::stellar, D::prism, D::marcella, D::vendetta, D::ryth, D::varg })
        try { cambc::draft::pick(d); return; } catch (const cambc::error&) {}
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) { std::printf("PROBE err %s\n", e.message().c_str()); }
        cambc::end_turn();
    }
}
