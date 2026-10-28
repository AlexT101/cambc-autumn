// probe-stun-spawn-heal (self-play): does a stunned champion on its own spawn still heal to full at the
// end of its lost turn, and do its cooldowns/buffs tick then? Side 0's Varg (prio 10) stands on its spawn
// tile nearest the enemy and casts its shield (slot 1) at R25, so its cooldown still runs through the lost turn. Side 1's Prism (prio -10, after Varg) walks
// to it and, from R20 on, stuns it once (unit stun deals damage) from outside the spawn. Varg logs health,
// stun and shield cooldown at its turn start; Prism logs Varg's health after Varg's turn.
// Run: cambc run tools/probes/probe-stun-spawn-heal tools/probes/probe-stun-spawn-heal --map 00elkring --rounds 60 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <vector>

using cambc::team;
using cambc::vec2;
using cambc::champion_draft;
using cambc::champion_type;

namespace {

int side = -1;
int fired = -1;

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
    const champion_draft want = side == 0 ? champion_draft::varg : champion_draft::prism;
    if (!taken(want)) { cambc::draft::pick(want); return; }
    for (int i = 0; i < 12; ++i)
        if (!taken(static_cast<champion_draft>(i)) && static_cast<champion_draft>(i) != champion_draft::varg &&
            static_cast<champion_draft>(i) != champion_draft::prism) { cambc::draft::pick(static_cast<champion_draft>(i)); return; }
}

vec2 centre(team t) {
    const auto p = cambc::map::spawn_region(t).positions();
    int x = 0, y = 0;
    for (const auto& v : p) { x += v.x; y += v.y; }
    return {x / static_cast<int>(p.size()), y / static_cast<int>(p.size())};
}

vec2 victim_tile() {  // side 0's spawn tile nearest side 1's spawn centre
    const vec2 ec = side == 0 ? centre(team::enemy) : centre(team::ally);
    const auto p = cambc::map::spawn_region(side == 0 ? team::ally : team::enemy).positions();
    vec2 best = p.front();
    int bd = 1 << 30;
    for (const auto& v : p) {
        const int d = (v.x - ec.x) * (v.x - ec.x) + (v.y - ec.y) * (v.y - ec.y);
        if (d < bd) { bd = d; best = v; }
    }
    return best;
}

void play_turn() {
    auto& me = cambc::self();
    const int r = static_cast<int>(cambc::round_number());
    if (side < 0) side = my_side();
    if (!me.is_alive()) return;
    const auto who = me.champion_name();
    const vec2 vt = victim_tile();
    if (r == 1) {
        const auto a = cambc::map::spawn_region(team::ally).positions();
        const auto e = cambc::map::spawn_region(team::enemy).positions();
        std::printf("PROBE 1 %d side=%d pos=%d,%d ally0=%d,%d n=%d enemy0=%d,%d n=%d vt=%d,%d\n",static_cast<int>(who), side,
                    me.position().x, me.position().y, a.front().x, a.front().y, static_cast<int>(a.size()), e.front().x,
                    e.front().y, static_cast<int>(e.size()), vt.x, vt.y);
    }
    if (side == 0 && who == champion_type::varg) {
        if (me.priority() != 10) me.set_priority(10);
        const auto b = me.buffs();
        const auto abs = me.abilities();
        std::printf("PROBE %d varg start pos=%d,%d hp=%.2f/%.2f stun=%d shield=%d cd1=%d\n", r, me.position().x,
                    me.position().y, me.health(), me.max_health(), b.has_stun() ? b.get<cambc::buff_stun>().duration : -1,
                    b.has_shield() ? b.get<cambc::buff_shield>().duration : -1, abs[1].cooldown());
        if (me.position() != vt && me.can_move()) me.move_towards(vt);
        if (r == 25) {
            bool ok = false;
            try { ok = abs[1].use(); } catch (const std::exception& e) { std::printf("PROBE %d shield err %s\n", r, e.what()); }
            std::printf("PROBE %d varg shield ok=%d cd1=%d\n", r, ok ? 1 : 0, abs[1].cooldown());
        }
        return;
    }
    if (side == 1 && who == champion_type::prism) {
        if (me.priority() != -10) me.set_priority(-10);
        const cambc::champion* victim = nullptr;
        const auto es = cambc::vision::champions(team::enemy);
        for (const auto& e : es)
            if (e.champion_name() == champion_type::varg) victim = &e;
        if (victim) {
            const auto b = victim->buffs();
            std::printf("PROBE %d prism sees varg pos=%d,%d hp=%.2f/%.2f stun=%d\n", r, victim->position().x,
                        victim->position().y, victim->health(), victim->max_health(),
                        b.has_stun() ? b.get<cambc::buff_stun>().duration : -1);
        }
        if (fired < 0 && r >= 20 && victim) {
            bool ok = false;
            try { ok = me.abilities()[0].use(*victim); } catch (const std::exception& e) { std::printf("PROBE %d stun err %s\n", r, e.what()); }
            if (ok) {
                fired = r;
                const auto b = victim->buffs();
                std::printf("PROBE %d prism STUN from %d,%d varg hp=%.2f stun=%d\n", r, me.position().x, me.position().y,
                            victim->health(), b.has_stun() ? b.get<cambc::buff_stun>().duration : -1);
            }
        }
        if (fired < 0 && me.can_move()) me.move_towards(vec2{vt.x + 2, vt.y + 2});  // just outside the spawn
        if (r % 5 == 0) std::printf("PROBE %d prism pos=%d,%d\n", r, me.position().x, me.position().y);
        return;
    }
    if (me.can_move()) try { me.move_towards(side == 0 ? vec2{0, 12} : vec2{29, 17}); } catch (...) {}  // clear the spawns
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
