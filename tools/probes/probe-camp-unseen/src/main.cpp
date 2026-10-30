// probe-camp-unseen: what can a champion read about a camp and its group with none of its tiles in vision?
// Map campunseen.map26a (makemap.mjs): group G = gold clusters M1 (20,24), M2 (21,24), absolute coordinates, far from A's spawn.
// Team A's Ryth stays on spawn and logs raw host reads for G every turn (G is never in its vision; no wards are placed).
// Team B's Vesper stands on (21,26) and logs the same reads with G in vision (ground truth). Its schedule:
//   r15, r18, r21 hit M1 (45 each: dead at r21); r30-32 kill M2 (cleared); from r45 stands on M2's tile to capture,
//   steps back to (21,26) once paid (respawning, 50 rounds), and watches the group return.
//   node tools/probes/probe-camp-unseen/makemap.mjs
//   cambc run tools/probes/probe-camp-unseen tools/probes/probe-camp-unseen \
//     --map tools/probes/probe-camp-unseen/campunseen.map26a --rounds 130 --fuel 50000000 -o <dir>
// Result (2026-10-30): A's 130 rows are identical through asleep (r1-14), awake (r15-), one member dead (r21-31), cleared
// (r32-51, B capturing r46-51), respawning (r52-101, B reads cooldown 50..1) and returned asleep (r102-): unseen camps are absent
// from camp/awake/asleep occupancy; camp_state, camp, camp_at, has_camp, camp_buffs and group capture_state raise 97;
// camp_group_state returns 0 ("unknown") with rc 0; camp_group_cooldown raises 106 (not respawning) even while it respawns.
// So no camp liveness is readable out of vision. B's in-vision control: a dead member's camp_state reads 0 (dead), its camp()
// raises 97, camp_at 98, has_camp 0.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
namespace M = cambc::map;
namespace X = cambc::detail;

namespace {

bool team_a() { return M::spawn_region(team::ally).is_set({ 0, 0 }); }
int R() { return (int)cambc::round_number(); }

const vec2 M1{ 20, 24 }, M2{ 21, 24 }, STAND{ 21, 26 };

const M::camp_group& group() {
    static std::vector<M::camp_group> gs = M::camp_groups();
    for (auto& g : gs) for (auto& c : g) if (c.spawn_position() == M1) return g;
    return gs.front();
}

void log_group(const char* tag) {
    auto& me = cambc::self();
    const auto vis = cambc::vision::visible_tiles();
    const auto occ = cambc::vision::camp_tiles();
    const auto awk = cambc::vision::awake_camp_tiles();
    const auto slp = cambc::vision::asleep_camp_tiles();
    const auto& g = group();
    const std::uint32_t gh = static_cast<std::uint32_t>(static_cast<cambc::handle_camp_group_t>(g));
    std::uint32_t gs = 99; std::int32_t gcd = -99;
    X::camp_group_capture_state cap{ -99, -99 };
    const int rgs = X::sdk_camp_group_state(gh, &gs);
    const int rcd = X::sdk_camp_group_cooldown(gh, &gcd);
    const int rcap = X::sdk_camp_group_capture_state(gh, &cap);
    const vec2 p = me.position();
    std::printf("PROBE r%d %c %s pos=(%d,%d) occN=%d | group rc=%d st=%u cd rc=%d v=%d cap rc=%d st=%d t=%d", R(), team_a() ? 'A' : 'B',
                tag, p.x, p.y, (int)occ.count(), rgs, gs, rcd, gcd, rcap, cap.state, cap.timer);
    for (const auto& c : g) {
        const vec2 s = c.spawn_position();
        const std::uint32_t ch = static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(c));
        std::uint32_t st = 99, at = 9999; std::int32_t has = -9;
        X::camp_state info{}; info.health = -1;
        X::camp_buff_data buf[8]{}; std::uint32_t nb = 99;
        const int rst = X::sdk_camp_state(ch, &st);
        const int rinf = X::sdk_camp(ch, &info);
        const int rat = X::sdk_camp_at(s.x, s.y, &at);
        const int rhas = X::sdk_has_camp(s.x, s.y, &has);
        const int rbuf = X::sdk_camp_buffs(ch, buf, 8, &nb);
        std::printf(" || (%d,%d) h=%u vis=%d occ=%d awk=%d slp=%d state rc=%d v=%u info rc=%d hp=%.0f at rc=%d h=%u has rc=%d v=%d buffs rc=%d n=%u",
                    s.x, s.y, ch, (int)vis.is_set(s), (int)occ.is_set(s), (int)awk.is_set(s), (int)slp.is_set(s), rst, st, rinf,
                    info.health, rat, at, rhas, has, rbuf, nb);
    }
    std::printf("\n");
}

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != t && me.can_move()) me.move_towards(t);
}

void hit(vec2 t) {
    auto& me = cambc::self();
    for (const auto& c : cambc::vision::camps())
        if (c.position() == t && me.can_attack()) { me.attack(c); return; }
}

int phase = 0;  // 0 kill schedule, 1 capturing, 2 back to stand
void vesper() {
    const int r = R();
    if (phase == 0) {
        go(STAND);
        if (r == 15 || r == 18 || r == 21) hit(M1);
        if (r >= 30 && r <= 32) hit(M2);
        if (r >= 45) phase = 1;
    }
    if (phase == 1) {
        go(M2);
        std::uint32_t gs = 0;
        X::sdk_camp_group_state(static_cast<std::uint32_t>(static_cast<cambc::handle_camp_group_t>(group())), &gs);
        if (gs == 3) phase = 2;
    }
    if (phase == 2) go(STAND);
    log_group("vesper");
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const D a[] = { D::ryth, D::marcella, D::tavi }, b[] = { D::vesper_vale, D::ryth, D::marcella };
    for (auto d : team_a() ? a : b)
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive()) {
                const auto t = cambc::self().champion_name();
                if (team_a() && t == CT::ryth) log_group("watch");
                else if (!team_a() && t == CT::vesper_vale) vesper();
            }
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %s\n", R(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
