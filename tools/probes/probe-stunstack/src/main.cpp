// probe-stunstack (elkring, self-play): do two stuns landing before the victim's next turn cost it one turn or two?
// Side 1's Vesper (priority -5, last of its team) shuttles between (12,19) and (12,20). Side 0's Cassi (9,16) and
// Prism (9,17) (priority 10, first of theirs) stun it: Cassi alone at SINGLE_ROUND (control), both at DOUBLE_ROUND.
// PRISM_LATE=1 gives Prism priority -10, so in odd rounds it acts after the victim (last of team A's six bodies).
//   cambc run tools/probes/probe-stunstack tools/probes/probe-stunstack --map elkring --rounds 60 --fuel 50000000
#include <cambc.h>
#include <algorithm>
#include <cstdio>

#ifndef SINGLE_ROUND
#define SINGLE_ROUND 30
#endif
#ifndef PRISM_LATE
#define PRISM_LATE 0
#endif
#ifndef DOUBLE_ROUND
#define DOUBLE_ROUND 45
#endif

using cambc::team;
using cambc::vec2;
using cambc::champion_draft;
using cambc::champion_type;

namespace {

int side = -1;

int my_side() {
    const auto a = cambc::map::spawn_region(team::ally).positions();
    const auto e = cambc::map::spawn_region(team::enemy).positions();
    return (a.front().y * 1000 + a.front().x) < (e.front().y * 1000 + e.front().x) ? 0 : 1;
}


void play_draft() {
    if (side < 0) side = my_side();
    const auto mine = cambc::draft::current_draft(team::ally);
    const auto theirs = cambc::draft::current_draft(team::enemy);
    auto taken = [&](champion_draft p) {
        return std::find(mine.begin(), mine.end(), p) != mine.end() || std::find(theirs.begin(), theirs.end(), p) != theirs.end();
    };
    const champion_draft s0[] = { champion_draft::cassi_and_issac, champion_draft::prism, champion_draft::stellar,
                                  champion_draft::willow, champion_draft::varg };
    const champion_draft s1[] = { champion_draft::vesper_vale, champion_draft::vendetta, champion_draft::ryth,
                                  champion_draft::marcella, champion_draft::tavi, champion_draft::ren };
    for (const auto p : side == 0 ? std::vector<champion_draft>(std::begin(s0), std::end(s0))
                                  : std::vector<champion_draft>(std::begin(s1), std::end(s1)))
        if (!taken(p)) { cambc::draft::pick(p); return; }
    for (int i = 0; i < 11; ++i)
        if (!taken(static_cast<champion_draft>(i))) { cambc::draft::pick(static_cast<champion_draft>(i)); return; }
}

void play_turn() {
    auto& me = cambc::self();
    const int r = static_cast<int>(cambc::round_number());
    if (side < 0) side = my_side();
    if (!me.is_alive()) return;
    const auto who = me.champion_name();
    if (side == 1 && who == champion_type::vesper_vale) {
        if (me.priority() != -5) me.set_priority(-5);
        const auto b = me.buffs();
        const int stun = b.has_stun() ? b.get<cambc::buff_stun>().duration : -1;
        const vec2 a{ 12, 19 }, c{ 12, 20 };
        bool moved = false;
        const vec2 before = me.position();
        if (r < 25) { if (me.position() != a && me.can_move()) moved = me.move_towards(a); }
        else { const vec2 dst = me.position() == a ? c : a; moved = me.move_towards(dst); }
        std::printf("PROBE %d victim pos=%d,%d restr=%u stun_dur=%d moved=%d hp=%.0f\n", r, before.x, before.y,
                    static_cast<unsigned>(me.restrictions().bits()), stun, moved ? 1 : 0, me.health());
        return;
    }
    const bool cassi = side == 0 && who == champion_type::cassi, prism = side == 0 && who == champion_type::prism;
    if (!cassi && !prism) {
        const int t = static_cast<int>(who);
        const vec2 park = side == 0 ? vec2{ t % 3, 4 + t / 3 } : vec2{ 29 - t % 3, 25 - t / 3 };
        if (me.position() != park && me.can_move()) me.move_towards(park);
        return;
    }
    const int prio = prism && PRISM_LATE ? -10 : 10;
    if (me.priority() != prio) me.set_priority(prio);
    const vec2 post = cassi ? vec2{ 9, 16 } : vec2{ 9, 17 };
    if (me.position() != post && me.can_move()) me.move_towards(post);
    const bool fire = r == DOUBLE_ROUND || (cassi && r == SINGLE_ROUND);
    if (!fire) return;
    for (const auto& e : cambc::vision::champions(team::enemy)) {
        if (e.champion_name() != champion_type::vesper_vale) continue;
        const auto abs = me.abilities();
        const auto& ab = abs[cassi ? 1 : 0];
        const bool ok = ab.is_ready() && ab.use(e);
        std::printf("PROBE %d %s stun ok=%d dist=%d victim_pos=%d,%d\n", r, cassi ? "cassi" : "prism", ok ? 1 : 0,
                    static_cast<int>(me.position().chebyshev_distance(e.position())), e.position().x, e.position().y);
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
