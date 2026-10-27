// probe-capture-vision: is a cleared group's capture_state() readable with only SOME of its camp tiles in vision?
// Map capvis.map26a (makemap.mjs): gem clusters on (12,2),(13,2). Both teams run this in their own (rotated) coordinates.
// Varg kills both clusters from (12,1), then walks west along y=1 to (3,1), logging each turn which group tiles it sees
// and what state() / capture_state() return: at x=5 both tiles are in its radius-8 vision, at x=4 only (12,2), at x=3 neither.
// It then returns to (4,1) and sets shared byte 0; Vesper then stands on (13,2), out of Varg's sight.
//   node tools/probes/probe-capture-vision/makemap.mjs
//   cambc run tools/probes/probe-capture-vision tools/probes/probe-capture-vision \
//     --map tools/probes/probe-capture-vision/capvis.map26a --rounds 70 --fuel 50000000 -o <dir>
// Result (2026-10-27, both teams): from (4,1), seeing only (12,2), state() reads cleared and capture_state() available/5, then
// ally/5..1 with Vesper unseen on (13,2) (payout at her arrival + 6). From (3,1), seeing neither, both raise error 97.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <variant>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
namespace M = cambc::map;

namespace {

bool team_a() { return M::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 T(vec2 p) { return team_a() ? p : vec2{ M::width() - 1 - p.x, M::height() - 1 - p.y }; }
int R() { return (int)cambc::round_number(); }

const vec2 TA{ 12, 2 }, TB{ 13, 2 }, KILL_AT{ 12, 1 };

const M::camp_group& group() {
    static std::vector<M::camp_group> gs = M::camp_groups();
    for (auto& g : gs) for (auto& c : g) if (c.spawn_position() == T(TA)) return g;
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

void log_group(const char* tag) {
    auto& me = cambc::self();
    const auto vis = cambc::vision::visible_tiles();
    char st[48], cap[64];
    try {
        auto s = group().state();
        std::snprintf(st, sizeof st, "%s", std::holds_alternative<M::camp_group_alive>(s) ? "alive"
                                           : std::holds_alternative<M::camp_group_reward_available>(s) ? "cleared" : "respawning");
    } catch (const cambc::error& e) { std::snprintf(st, sizeof st, "ERR(%d)", (int)e.code()); }
    try {
        auto c = group().capture_state();
        std::snprintf(cap, sizeof cap, "%s/%d", cap_name(c.state), c.timer);
    } catch (const cambc::error& e) { std::snprintf(cap, sizeof cap, "ERR(%d:%s)", (int)e.code(), e.message().c_str()); }
    const vec2 p = T(me.position());  // own-team coordinates
    std::printf("PROBE r%d %c %s pos=(%d,%d) seeA=%d seeB=%d state=%s capture=%s\n", R(), team_a() ? 'A' : 'B', tag, p.x, p.y,
                (int)vis.is_set(T(TA)), (int)vis.is_set(T(TB)), st, cap);
}

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != T(t) && me.can_move()) me.move_towards(T(t));
}

int phase = 0, walk_x = 12;

void varg() {
    auto& me = cambc::self();
    if (phase == 0) {
        go(KILL_AT);
        if (me.position() != T(KILL_AT)) return;
        for (const auto& c : cambc::vision::camps())
            if ((c.position() == T(TA) || c.position() == T(TB)) && me.can_attack()) me.attack(c);
        log_group("kill");
        bool any_alive = false;
        for (const auto& c : cambc::vision::camps()) any_alive |= c.position() == T(TA) || c.position() == T(TB);
        if (!any_alive) phase = 1;
        return;
    }
    if (phase == 1) {
        if (walk_x > 3) { --walk_x; go({ walk_x, 1 }); }
        log_group("walk");
        if (T(me.position()) == vec2{ 3, 1 }) phase = 2;
        return;
    }
    go({ 4, 1 });
    if (T(me.position()) == vec2{ 4, 1 }) cambc::shared_memory[0] = 1;
    log_group("hold");
}

int vesper_step = 0;
void vesper() {
    auto& me = cambc::self();
    if (cambc::shared_memory[0] != 1) return;
    const vec2 path[] = { { 10, 6 }, { 13, 3 }, TB };
    while (vesper_step < 2 && T(me.position()) == path[vesper_step]) ++vesper_step;
    go(path[vesper_step]);
    const vec2 p = T(me.position());
    std::printf("PROBE r%d %c vesper pos=(%d,%d)\n", R(), team_a() ? 'A' : 'B', p.x, p.y);
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
            else if (cambc::self().is_alive()) {
                const auto t = cambc::self().champion_name();
                if (t == CT::varg) varg();
                else if (t == CT::vesper_vale) vesper();
            }
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %s\n", R(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
