// probe-teleport-dead-camp: can a teleport crystal target a camp tile whose monster is dead?
// Map tpcamp.map26a (makemap.mjs): spawn (0..2,0..2), one-tile gold clusters G1 (4,1) and G2 (5,3). Both teams run this
// in their own (rotated) coordinates; only Varg acts.
//   1. Kill G1 and G2 from (4,2); capture G1 by standing on it (20 gold).
//   2. Case 1: from spawn (2,2), buy a crystal and teleport onto G2, cleared and uncaptured. On rejection, walk on instead.
//   3. Case 2: after G2 pays out, teleport from (2,2) onto G1, captured and respawning, well before it returns.
//   4. Case 3: teleport from (2,2) onto G2 when its respawn timer reads 2, so the channel spans its return.
//   node tools/probes/probe-teleport-dead-camp/makemap.mjs
//   cambc run tools/probes/probe-teleport-dead-camp tools/probes/probe-teleport-dead-camp \
//     --map tools/probes/probe-teleport-dead-camp/tpcamp.map26a --rounds 100 --fuel 50000000 -o <dir>
// Result (2026-10-27, both teams alike): every cast is accepted; "not a camp" means a tile holding a live camp.
//   1. Cast r18 onto cleared G2, landed r21 (turn start), capture ally/5 from r22, paid r27: the same as walking on.
//   2. Cast r30 onto G1 (respawning, timer 36), landed r33. Standing there did not stop G1's timer; it returned r66 after we left.
//   3. Cast r75 onto G2 (timer 2; due back r77). At r77 the champion was still channelling on spawn, yet G2 did not return:
//      the teleport reservation blocks the return like a champion on the tile. Landed r78; G2 stayed at timer 0 while we
//      stood there; we left in r81 and it returned r82.
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

const vec2 G1{ 4, 1 }, G2{ 5, 3 }, KILL_AT{ 4, 2 }, HOME{ 2, 2 };

const M::camp_group& group(vec2 at) {
    static std::vector<M::camp_group> gs = M::camp_groups();
    for (auto& g : gs) for (auto& c : g) if (c.spawn_position() == T(at)) return g;
    return gs.front();
}

const char* cap_name(M::camp_group_capture_type t) {
    switch (t) {
    case M::camp_group_capture_type::no_capture_available: return "none";
    case M::camp_group_capture_type::ally_capturing: return "ally";
    case M::camp_group_capture_type::contested: return "contested";
    case M::camp_group_capture_type::enemy_capturing: return "enemy";
    case M::camp_group_capture_type::capture_available: return "available";
    }
    return "?";
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

void gdesc(vec2 at, char* buf, int n) {
    char st[32], cap[32];
    const int s = gstate(at);
    if (s == -2) std::snprintf(st, sizeof st, "alive");
    else if (s == -1) std::snprintf(st, sizeof st, "cleared");
    else if (s == -9) std::snprintf(st, sizeof st, "ERR");
    else std::snprintf(st, sizeof st, "resp%d", s);
    try {
        auto c = group(at).capture_state();
        std::snprintf(cap, sizeof cap, "%s/%d", cap_name(c.state), c.timer);
    } catch (const cambc::error& e) { std::snprintf(cap, sizeof cap, "ERR%d", (int)e.code()); }
    int live = 0;
    for (const auto& c : cambc::vision::camps()) if (c.position() == T(at)) live = 1;
    std::snprintf(buf, n, "%s %s camp=%d", st, cap, live);
}

int phase = 0;
const char* PH[] = { "kill", "cap1", "case1", "tp1", "hold2", "case2", "tp2", "case3", "tp3", "after" };

void log(const char* tag) {
    auto& me = cambc::self();
    char a[96], b[96];
    gdesc(G1, a, sizeof a);
    gdesc(G2, b, sizeof b);
    int ch = -1;
    try { ch = me.remaining_channel_time(); } catch (const cambc::error&) {}
    const vec2 p = T(me.position());
    std::printf("PROBE r%d %c %s/%s pos=(%d,%d) gold=%d crystal=%u tp=%d ch=%d | G1 %s | G2 %s\n", R(), team_a() ? 'A' : 'B',
                PH[phase], tag, p.x, p.y, (int)me.gold_count(), me.consumables()[CO::tp_crystal].count(),
                (int)me.is_teleporting(), ch, a, b);
}

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != T(t) && me.can_move()) me.move_towards(T(t));
}

// Buy if needed and teleport; returns 1 accepted, 0 not yet (not home / no gold), -1 rejected.
int try_tp(vec2 target) {
    auto& me = cambc::self();
    go(HOME);
    if (me.position() != T(HOME)) return 0;
    if (me.consumables()[CO::tp_crystal].count() == 0) {
        if (!me.can_buy(CO::tp_crystal)) return 0;
        me.buy(CO::tp_crystal);
    }
    try {
        const bool ok = me.consumables()[CO::tp_crystal].use(T(target));
        std::printf("PROBE r%d %c TELEPORT to (%d,%d) returned %d\n", R(), team_a() ? 'A' : 'B', target.x, target.y, (int)ok);
        return 1;
    } catch (const cambc::error& e) {
        std::printf("PROBE r%d %c TELEPORT to (%d,%d) REJECTED code=%d %s\n", R(), team_a() ? 'A' : 'B', target.x, target.y,
                    (int)e.code(), e.message().c_str());
        return -1;
    }
}

int wait_after = 0;

void varg() {
    auto& me = cambc::self();
    switch (phase) {
    case 0: {
        go(KILL_AT);
        if (me.position() == T(KILL_AT))
            for (const auto& c : cambc::vision::camps())
                if ((c.position() == T(G1) || c.position() == T(G2)) && me.can_attack()) me.attack(c);
        if (gstate(G1) == -1 && gstate(G2) == -1) phase = 1;
        break;
    }
    case 1:
        go(G1);
        if (gstate(G1) >= 0) phase = 2;
        break;
    case 2: {
        const int r = try_tp(G2);
        if (r == 1) phase = 3;
        else if (r == -1) phase = 4;  // walk on instead
        break;
    }
    case 3:  // teleporting onto G2, then holding it
        if (!me.is_teleporting() && gstate(G2) >= 0) phase = 5;
        break;
    case 4:
        go(G2);
        if (gstate(G2) >= 0) phase = 5;
        break;
    case 5: {
        const int r = try_tp(G1);
        if (r != 0) { phase = r == 1 ? 6 : 7; wait_after = 0; }
        break;
    }
    case 6:
        if (!me.is_teleporting() && ++wait_after >= 3) phase = 7;
        break;
    case 7: {
        const int t = gstate(G2);
        if (me.position() != T(HOME) || t < 0 || t > 2) { go(HOME); if (me.consumables()[CO::tp_crystal].count() == 0 && me.can_buy(CO::tp_crystal)) me.buy(CO::tp_crystal); break; }
        if (try_tp(G2) != 0) { phase = 8; wait_after = 0; }
        break;
    }
    case 8:
        if (!me.is_teleporting() && ++wait_after >= 3) phase = 9;
        break;
    default: go(KILL_AT); break;  // step off G2 so it can return
    }
    log("end");
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto d : { D::varg, D::vesper_vale, D::ryth })
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive() && cambc::self().champion_name() == CT::varg) varg();
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %d %s\n", R(), (int)e.code(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
