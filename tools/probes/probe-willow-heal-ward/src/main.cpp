// probe-willow-heal-ward: can Willow's heal (slot 0, target ally, range 4) target an ally she does not see from her own
// tile but does see through her own ward?
// Map healward.map26a (makemap.mjs): spawn (0..2,0..2), bush cluster B (7,6) + BW (7,5), wolf (9,8). Both teams run
// this in their own (rotated) coordinates. Draft Willow + Tavi.
//   Tavi walks to C (6,8), hits the wolf once to wake it, and takes its hits; from round 20 it stands on B.
//   Willow stands at W (5,6): 2 from B, BW and C, out of the wolf's range 3.
//   Control: heal Tavi at C (visible) once damaged. Round 24: heal Tavi on B (unseen; expected refused), then ward the
//   empty bush tile BW (its cluster includes B), then heal again. If refused, retry the next round.
//   node tools/probes/probe-willow-heal-ward/makemap.mjs
//   cambc run tools/probes/probe-willow-heal-ward tools/probes/probe-willow-heal-ward \
//     --map tools/probes/probe-willow-heal-ward/healward.map26a --rounds 30 --fuel 50000000 -o <dir>
// Result (2026-10-28, both teams alike): the caster's ward sight counts, in the turn it is placed.
//   Control r10: Tavi visible at C, 880/900: accepted, after=900.
//   r24 pre-ward: B not in Willow's own cast or champion vision; heal_amount throws 97, the cast throws 30.
//   r24 after warding BW: B still not in her own-tile cast but in champion_vision (visible_tiles() includes the ward),
//   Tavi visible at (7,6) 620/900; heal accepted, amount 280 (the missing health), after=900, cd=8. The refused
//   pre-ward cast spent nothing.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <optional>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
namespace M = cambc::map;

namespace {

bool team_a() { return M::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 T(vec2 p) { return team_a() ? p : vec2{ M::width() - 1 - p.x, M::height() - 1 - p.y }; }
int R() { return (int)cambc::round_number(); }
char TM() { return team_a() ? 'A' : 'B'; }

const vec2 W{ 5, 6 }, B{ 7, 6 }, BW{ 7, 5 }, C{ 6, 8 }, WOLF{ 9, 8 };

void go(vec2 t) {
    auto& me = cambc::self();
    if (me.position() != T(t) && me.can_move()) me.move_towards(T(t));
}

bool hit = false;
void tavi() {
    auto& me = cambc::self();
    const vec2 p0 = T(me.position());
    std::printf("PROBE r%d %c TAVI start pos=(%d,%d) hp=%.1f/%.1f\n", R(), TM(), p0.x, p0.y, me.health(), me.max_health());
    if (R() < 20) {
        go(C);
        if (!hit && me.position() == T(C))
            for (const auto& c : cambc::vision::camps())
                if (c.position() == T(WOLF) && me.can_attack()) { me.attack(c); hit = true; }
    } else go(B);
}

// Returns whether the heal was accepted.
bool try_heal(const cambc::champion& ally, const char* tag) {
    auto& me = cambc::self();
    const bool vis = ally.is_visible();
    float before = -1, amt = -1;
    if (vis) before = ally.health();
    try { amt = me.abilities()[0].heal_amount(ally); } catch (const cambc::error& e) {
        std::printf("PROBE r%d %c %s heal_amount ERR %d %s\n", R(), TM(), tag, (int)e.code(), e.message().c_str());
    }
    try {
        const bool ok = me.abilities()[0].use(ally);
        std::printf("PROBE r%d %c %s HEAL vis=%d returned %d before=%.1f amount=%.1f after=%.1f cd=%d\n", R(), TM(), tag, (int)vis,
                    (int)ok, before, amt, vis ? ally.health() : -1.f, me.abilities()[0].cooldown());
        return ok;
    } catch (const cambc::error& e) {
        std::printf("PROBE r%d %c %s HEAL vis=%d REJECTED code=%d %s\n", R(), TM(), tag, (int)vis, (int)e.code(), e.message().c_str());
        return false;
    }
}

// own = B in the cast from Willow's tile alone; champ = B in her champion vision; ward = B in the ward's cast at BW.
void sight(const cambc::champion& ally, const char* tag) {
    auto& me = cambc::self();
    const bool own = me.visible_tiles_from(me.position()).is_set(T(B));
    const bool champ = me.visible_tiles().is_set(T(B));
    const bool ward = cambc::ward::visible_tiles_from(T(BW)).is_set(T(B));
    const auto wards = me.ward_positions();
    const vec2 ap = ally.is_visible() ? T(ally.position()) : vec2{ -1, -1 };
    std::printf("PROBE r%d %c %s own_tile_sees_B=%d champion_vision_B=%d ward_cast_sees_B=%d wards=%d ally_vis=%d ally_pos=(%d,%d) ally_hp=%.1f\n",
                R(), TM(), tag, (int)own, (int)champ, (int)ward, (int)wards.size(), (int)ally.is_visible(), ap.x, ap.y,
                ally.is_visible() ? ally.health() : -1.f);
}

bool control_done = false, ward_done = false, retry_done = false;
void willow() {
    auto& me = cambc::self();
    go(W);
    std::optional<cambc::champion> ally;
    for (const auto& c : cambc::champions(team::ally))
        if (static_cast<cambc::handle_champion_t>(c) != static_cast<cambc::handle_champion_t>(me)) ally = c;
    if (!ally) return;
    const bool vis = ally->is_visible();
    const vec2 p = T(me.position());
    std::printf("PROBE r%d %c WILLOW pos=(%d,%d) ally_vis=%d ally_hp=%.1f cd=%d\n", R(), TM(), p.x, p.y, (int)vis,
                vis ? ally->health() : -1.f, me.abilities()[0].cooldown());
    if (me.position() != T(W) || me.abilities()[0].cooldown() > 0) return;
    if (!control_done && R() < 20 && vis && ally->health() < ally->max_health()) { try_heal(*ally, "control"); control_done = true; }
    else if (!ward_done && R() >= 24) {
        ward_done = true;
        sight(*ally, "preward");
        try_heal(*ally, "preward");
        try {
            const bool ok = me.place_ward(T(BW));
            std::printf("PROBE r%d %c place_ward BW returned %d\n", R(), TM(), (int)ok);
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d %c place_ward BW ERR %d %s\n", R(), TM(), (int)e.code(), e.message().c_str());
        }
        sight(*ally, "postward");
        if (try_heal(*ally, "ward")) retry_done = true;
    } else if (ward_done && !retry_done) {
        retry_done = true;
        sight(*ally, "nextround");
        try_heal(*ally, "nextround");
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    for (auto d : { D::willow, D::tavi })
        if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else if (cambc::self().is_alive()) {
                if (cambc::self().champion_name() == CT::willow) willow();
                else if (cambc::self().champion_name() == CT::tavi) tavi();
            }
        } catch (const cambc::error& e) {
            std::printf("PROBE r%d err %d %s\n", R(), (int)e.code(), e.message().c_str());
        }
        cambc::end_turn();
    }
}
