// probe-stunwake (elkring, self-play): does a damage-free stun wake a sleeping camp group?
// Side 0's Issac idles at (6,2) (C3 to the elk at (9,2)) from about round 6; Cassi stands at (5,2) (C4) and
// casts only her damage-free stun (slot 1) on the elk at round STUN_ROUND. Everyone else parks north of spawn, out of the elk's range.
//   cambc run tools/probes/probe-stunwake tools/probes/probe-stunwake --map elkring --rounds 40 --fuel 50000000
#include <cambc.h>
#include <algorithm>
#include <cstdio>

#ifndef STUN_ROUND
#define STUN_ROUND 15
#endif

using cambc::team;
using cambc::vec2;

namespace {

int side = -1;

int my_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions();
    const auto e = cambc::map::spawn_region(team::enemy).positions();
    return (a.front().y * 1000 + a.front().x) < (e.front().y * 1000 + e.front().x) ? 0 : 1;
}

void play_draft() {
    const auto chosen = cambc::draft::current_draft(team::ally);
    if (std::find(chosen.begin(), chosen.end(), cambc::champion_draft::cassi_and_issac) == chosen.end()) {
        cambc::draft::pick(cambc::champion_draft::cassi_and_issac);
        return;
    }
    for (int i = 0; i < 11; ++i) {
        const auto p = static_cast<cambc::champion_draft>(i);
        if (std::find(chosen.begin(), chosen.end(), p) == chosen.end()) { cambc::draft::pick(p); return; }
    }
}

void play_turn() {
    auto& me = cambc::self();
    const int r = static_cast<int>(cambc::round_number());
    if (side < 0) side = my_side();
    if (side != 0 || !me.is_alive()) return;
    const auto who = me.champion_name();
    const bool cassi = who == cambc::champion_type::cassi, issac = who == cambc::champion_type::issac;
    if (!cassi && !issac) {
        const int t = static_cast<int>(who);
        const vec2 park{ t % 3, 3 + t / 3 };
        if (me.position() != park && me.can_move()) me.move_towards(park);
        return;
    }
    const vec2 elk{ 9, 2 };
    const vec2 post = cassi ? vec2{ 5, 2 } : vec2{ 6, 2 };
    if (me.position() != post && me.can_move() && !me.move_towards(post))
        std::printf("PROBE %d %s move_failed\n", r, cassi ? "cassi" : "issac");
    for (const auto& c : cambc::vision::camps()) {
        if (c.spawn_position() != elk) continue;
        std::printf("PROBE %d %s pos=%d,%d hp=%.0f elk_hp=%.0f awake=%d asleep=%d\n", r, cassi ? "cassi" : "issac",
                    me.position().x, me.position().y, me.health(), c.health(), c.is_awake() ? 1 : 0, c.is_asleep() ? 1 : 0);
        if (cassi && r == STUN_ROUND && me.position() == post) {
            const auto abs = me.abilities();
            const auto& ab = abs[1];
            const bool ok = ab.is_ready() && ab.use(c);
            std::printf("PROBE %d cassi stun ok=%d dist=%d elk_hp=%.0f awake_after=%d\n", r, ok ? 1 : 0,
                        static_cast<int>(me.position().chebyshev_distance(c.position())), c.health(), c.is_awake() ? 1 : 0);
        }
    }
}

} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const std::exception& error) {
            std::printf("bot error: %s\n", error.what());
        }
        cambc::end_turn();
    }
}
