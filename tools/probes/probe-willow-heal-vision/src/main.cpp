// probe-willow-heal-vision: does Willow's heal (slot 0, target ally, range 4) need the ally in Willow's own vision?
// Map healvis.map26a (makemap.mjs): spawn (0..2,0..2), one-tile bush B (7,6), wolf (9,8). Both teams run this in their
// own (rotated) coordinates. Draft Willow + Tavi.
//   Tavi walks to C (6,8), hits the wolf once to wake it, and takes its hits; from round 20 it stands in the bush B.
//   Willow stands at W (4,6), 3 from B and 2 from C, out of the wolf's range 3.
//   Control: heal Tavi at C (visible) once damaged. Hidden: from round 24, heal Tavi on B (a bush tile, unseen).
//   node tools/probes/probe-willow-heal-vision/makemap.mjs
//   cambc run tools/probes/probe-willow-heal-vision tools/probes/probe-willow-heal-vision \
//     --map tools/probes/probe-willow-heal-vision/healvis.map26a --rounds 40 --fuel 50000000 -o <dir>
// Result (2026-10-28, both teams alike): vision is required.
//   Control r10: Tavi visible at C, 880/900: accepted, after=900 (heal_amount read 20, capped at the missing health).
//   Hidden r24: Tavi on B, unseen, 620/900: heal_amount throws 97 "Unit is not in vision"; the cast throws
//   30 (invalid_action_spell_cast_bad_target) "Target must be a visible unit"; Tavi's health keeps falling 20/round.
//   An ally seen only through Willow's ward is accepted: probe-willow-heal-ward.
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

const vec2 W{ 4, 6 }, B{ 7, 6 }, C{ 6, 8 }, WOLF{ 9, 8 };

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

bool control_done = false, hidden_done = false;
void try_heal(const cambc::champion& ally, const char* tag) {
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
    } catch (const cambc::error& e) {
        std::printf("PROBE r%d %c %s HEAL vis=%d REJECTED code=%d %s\n", R(), TM(), tag, (int)vis, (int)e.code(), e.message().c_str());
    }
}

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
    else if (!hidden_done && R() >= 24) { try_heal(*ally, "hidden"); hidden_done = true; }
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
