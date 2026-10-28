// probe-teleport-dead-member: can a teleport crystal target the tile of a dead camp member while its group still lives?
// Map tpmember.map26a (makemap.mjs): spawn (0..2,0..2), one-tile gold cluster G1 (4,1), two-member gold group X (5,3) +
// Y (6,3). Both teams run this in their own (rotated) coordinates; only Ren acts (melee, no splash, so Y survives).
//   1. From (4,2) kill G1 and X (not Y); capture G1 for 20 gold.
//   2. From spawn (2,2), buy a crystal and teleport onto X's tile while Y lives. On rejection, try walking onto X.
//   node tools/probes/probe-teleport-dead-member/makemap.mjs
//   cambc run tools/probes/probe-teleport-dead-member tools/probes/probe-teleport-dead-member \
//     --map tools/probes/probe-teleport-dead-member/tpmember.map26a --rounds 60 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <variant>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
using CO = cambc::consumable_type;
namespace M = cambc::map;

namespace {

bool team_a() { return M::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 T(vec2 p) { return team_a() ? p : vec2{ M::width() - 1 - p.x, M::height() - 1 - p.y }; }
int R() { return (int)cambc::round_number(); }

const vec2 G1{ 4, 1 }, X{ 5, 3 }, Y{ 6, 3 }, KILL_AT{ 4, 2 }, HOME{ 2, 2 };

const M::camp_group& group(vec2 at) {
    static std::vector<M::camp_group> gs = M::camp_groups();
    for (auto& g : gs) for (auto& c : g) if (c.spawn_position() == T(at)) return g;
    return gs.front();
}

// -2 alive, -1 cleared, >=0 respawning timer
int gstate(vec2 at) {
    try {
        auto s = group(at).state();
        if (std::holds_alternative<M::camp_group_alive>(s)) return -2;
        if (std::holds_alternative<M::camp_group_reward_available>(s)) return -1;
        return std::get<M::camp_group_respawning>(s).timer;
    } catch (const cambc::error&) { return -9; }
}

bool live(vec2 at) {
    for (const auto& c : cambc::vision::camps()) if (c.position() == T(at)) return true;
    return false;
}

int members() { int n = 0; for (auto& c : group(X)) { (void)c; ++n; } return n; }

int phase = 0;
const char* PH[] = { "kill", "cap1", "tp", "chan", "walk", "after" };

void log(const char* tag) {
    auto& me = cambc::self();
    int ch = -1;
    try { ch = me.remaining_channel_time(); } catch (const cambc::error&) {}
    const vec2 p = T(me.position());
    std::printf("PROBE r%d %c %s/%s pos=(%d,%d) gold=%d crystal=%u tp=%d ch=%d | G1 st=%d live=%d | XY group st=%d X.live=%d "
                "Y.live=%d members=%d\n",
                R(), team_a() ? 'A' : 'B', PH[phase], tag, p.x, p.y, (int)me.gold_count(),
                me.consumables()[CO::tp_crystal].count(), (int)me.is_teleporting(), ch, gstate(G1), (int)live(G1),
                gstate(X), (int)live(X), (int)live(Y), members());
}

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != T(t) && me.can_move()) me.move_towards(T(t));
}

int after = 0;

void ren() {
    auto& me = cambc::self();
    switch (phase) {
    case 0:
        go(KILL_AT);
        if (me.position() == T(KILL_AT))
            for (const auto& c : cambc::vision::camps())
                if ((c.position() == T(G1) || c.position() == T(X)) && me.can_attack()) me.attack(c);
        if (gstate(G1) == -1 && !live(X)) phase = 1;
        break;
    case 1:
        go(G1);
        if (gstate(G1) >= 0) phase = 2;
        break;
    case 2: {
        go(HOME);
        if (me.position() != T(HOME)) break;
        if (me.consumables()[CO::tp_crystal].count() == 0) {
            if (!me.can_buy(CO::tp_crystal)) break;
            me.buy(CO::tp_crystal);
        }
        log("pre");
        try {
            const bool ok = me.consumables()[CO::tp_crystal].use(T(X));
            std::printf("PROBE r%d %c TELEPORT to X returned %d\n", R(), team_a() ? 'A' : 'B', (int)ok);
            phase = 3;
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d %c TELEPORT to X REJECTED code=%d %s\n", R(), team_a() ? 'A' : 'B', (int)e.code(),
                        e.message().c_str());
            phase = 4;
        }
        break;
    }
    case 3:
        if (!me.is_teleporting() && ++after >= 3) phase = 5;
        break;
    case 4:
        try {
            go(X);
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d %c WALK to X REJECTED code=%d %s\n", R(), team_a() ? 'A' : 'B', (int)e.code(),
                        e.message().c_str());
        }
        if (++after >= 8) phase = 5;
        break;
    default: break;
    }
    log("end");
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto d : { D::ren, D::vesper_vale, D::ryth })
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive() && cambc::self().champion_name() == CT::ren) ren();
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %d %s\n", R(), (int)e.code(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
