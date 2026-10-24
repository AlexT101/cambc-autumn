// probe-stunread (elkring, self-play): what an observer reads for an enemy champion's stun duration
// before and after the victim's lost turn, and whether a stun on a duration-0 buff takes the next turn.
// Side 1's Vesper (priority -5, last of its 5) shuttles. Side 0: Cassi (prio 10, first) stuns at R30;
// Prism (prio 10) stuns at R31 (on the spent buff); Prism at prio -10 from R40 (after the victim) stuns
// at R41. Willow (prio -20, last of side 0's 6 bodies, after the victim) observes.
// Run: cambc run tools/probes/probe-stunread tools/probes/probe-stunread --map 00elkring --rounds 50 --fuel 50000000 -o <dir>
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
    const champion_draft s0[] = {champion_draft::cassi_and_issac, champion_draft::prism, champion_draft::stellar,
                                 champion_draft::willow, champion_draft::varg};
    const champion_draft s1[] = {champion_draft::vesper_vale, champion_draft::vendetta, champion_draft::ryth,
                                 champion_draft::marcella, champion_draft::tavi, champion_draft::ren};
    for (const auto p : side == 0 ? std::vector<champion_draft>(std::begin(s0), std::end(s0))
                                  : std::vector<champion_draft>(std::begin(s1), std::end(s1)))
        if (!taken(p)) { cambc::draft::pick(p); return; }
    for (int i = 0; i < 11; ++i)
        if (!taken(static_cast<champion_draft>(i))) { cambc::draft::pick(static_cast<champion_draft>(i)); return; }
}

const char* name(champion_type t) {
    switch (t) {
    case champion_type::cassi: return "cassi";
    case champion_type::prism: return "prism";
    case champion_type::willow: return "willow";
    default: return "other";
    }
}

int victim_stun(const char* when, const char* who, int r) {
    for (const auto& e : cambc::vision::champions(team::enemy)) {
        if (e.champion_name() != champion_type::vesper_vale) continue;
        const auto b = e.buffs();
        const int d = b.has_stun() ? b.get<cambc::buff_stun>().duration : -1;
        std::printf("PROBE %d obs %s %s victim_stun=%d\n", r, who, when, d);
        return d;
    }
    std::printf("PROBE %d obs %s %s victim unseen\n", r, who, when);
    return -2;
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
        const vec2 a{12, 19}, c{12, 20};
        bool moved = false;
        const vec2 before = me.position();
        if (r < 25) { if (me.position() != a && me.can_move()) moved = me.move_towards(a); }
        else { const vec2 dst = me.position() == a ? c : a; moved = me.move_towards(dst); }
        if (r >= 28 && r <= 46)
            std::printf("PROBE %d victim pos=%d,%d stun_dur=%d moved=%d\n", r, before.x, before.y, stun, moved ? 1 : 0);
        return;
    }
    const bool cassi = side == 0 && who == champion_type::cassi, prism = side == 0 && who == champion_type::prism,
               willow = side == 0 && who == champion_type::willow;
    if (!cassi && !prism && !willow) {
        const int t = static_cast<int>(who);
        const vec2 park = side == 0 ? vec2{t % 3, 4 + t / 3} : vec2{29 - t % 3, 25 - t / 3};
        if (me.position() != park && me.can_move()) me.move_towards(park);
        return;
    }
    const int prio = willow ? -20 : prism && r >= 39 ? -10 : 10;
    if (me.priority() != prio) me.set_priority(prio);
    const vec2 post = cassi ? vec2{9, 16} : prism ? vec2{9, 17} : vec2{10, 16};
    if (me.position() != post && me.can_move()) me.move_towards(post);
    if (r < 28 || r > 46) return;
    if (willow) {
        std::printf("PROBE %d willow pos=%d,%d\n", r, me.position().x, me.position().y);
        victim_stun("turn", "willow", r);
        return;
    }
    victim_stun("before", name(who), r);
    const bool fire = (cassi && r == 30) || (prism && (r == 31 || r == 41));
    if (!fire) return;
    for (const auto& e : cambc::vision::champions(team::enemy)) {
        if (e.champion_name() != champion_type::vesper_vale) continue;
        const auto abs = me.abilities();
        const auto& ab = abs[cassi ? 1 : 0];
        const bool ok = ab.is_ready() && ab.use(e);
        std::printf("PROBE %d %s stun ok=%d\n", r, name(who), ok ? 1 : 0);
    }
    victim_stun("after", name(who), r);
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
