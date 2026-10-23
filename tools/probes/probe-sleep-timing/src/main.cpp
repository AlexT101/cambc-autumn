// probe-sleep-timing: how many empty camp phases does a monster need before it sleeps, freshly woken vs long awake?
// Self-play on 00interlock; team B runs the same scenarios rotated 180 degrees. Coordinates below are team A's.
//   Vesper  lone wolf (5,8): S1 basic attack from (5,5) (d3) and dash to (5,3) (d5) in the same turn;
//           S2 re-wake from (5,5), stay in range 4 phases, walk to (5,4) (d4) without attacking;
//           S2b re-wake from (5,5), stay 4 phases, then attack and dash to (5,3) in the leaving turn.
//   Stellar wolf (5,14) + gem (4,14): unit spell from (9,14) (d4 / d5), nobody ever in range. Twice.
//   Prism   gold clusters (19,2),(19,3): ground spell at (19,2) from (15,2) (d4 both), nobody ever in range.
//   Marcella wolf (5,21) + gold (4,21): spell from (8,21) (wolf d3, gold d4), stays 5 phases, walks to (9,21).
//   Vendetta idles at spawn.
// On 00elkring (group elk (9,2), gold (10,2), gem (9,3)): Vesper wakes the elk from (6,2) and holds (5,2) (elk d4, clusters
// d4/d5); once both clusters read asleep, Stellar at (13,6) (d4 from all three) spells the awake elk; once the clusters are
// asleep again, Prism steps from (14,6) to (13,5) (gold d3, gem d4, elk d4) and next turn basic-attacks the asleep gold cluster.
//   cambc run ... --map 00elkring --rounds 40 --fuel 50000000 -o <dir>
//   cambc run tools/probes/probe-sleep-timing tools/probes/probe-sleep-timing \
//     --map 00interlock --rounds 90 --fuel 50000000 -o <dir>
#include <cambc.h>
#include <cstdio>
#include <vector>
using cambc::team;
using cambc::vec2;
using CT = cambc::champion_type;
using D = cambc::champion_draft;

namespace {
bool g_b = false;
vec2 T(vec2 p) { return g_b ? vec2{ cambc::map::width() - 1 - p.x, cambc::map::height() - 1 - p.y } : p; }

const char* who() {
    switch (cambc::self().champion_name()) {
    case CT::vesper_vale: return "vesper";
    case CT::stellar: return "stellar";
    case CT::prism: return "prism";
    case CT::marcella: return "marcella";
    default: return "other";
    }
}

std::vector<cambc::camp> group_of(vec2 member) {
    for (const auto& g : cambc::map::camp_groups())
        for (const auto& c : g.camps())
            if (c.spawn_position() == T(member)) return { g.camps().begin(), g.camps().end() };
    return {};
}

bool all_asleep(const std::vector<cambc::camp>& g) {
    for (const auto& c : g) if (!c.is_asleep()) return false;
    return true;
}

void log(const char* tag, const std::vector<cambc::camp>& g, int stage) {
    auto& me = cambc::self();
    const vec2 p = me.position();
    std::printf("PROBE r=%d %s st=%d %s pos=(%d,%d) hp=%.0f", (int)cambc::round_number(), who(), stage, tag, p.x, p.y, (double)me.health());
    for (const auto& c : g) {
        const vec2 s = c.spawn_position();
        std::printf(" %s(%d,%d):", cambc::to_string(c.kind()).c_str(), s.x, s.y);
        try { std::printf("%s/%.0f", c.is_awake() ? "AWAKE" : c.is_asleep() ? "asleep" : "dead", (double)c.health()); }
        catch (const cambc::error&) { std::printf("unseen"); }
        std::printf("/d%d", (int)s.chebyshev_distance(p));
    }
    std::printf("\n");
}

void step_to(vec2 t) {
    auto& me = cambc::self();
    const vec2 p = me.position();
    auto sg = [](int v) { return v > 0 ? 1 : v < 0 ? -1 : 0; };
    me.move_towards(vec2{ p.x + sg(t.x - p.x), p.y + sg(t.y - p.y) });
}

struct Walker {
    std::vector<vec2> pts;
    size_t i = 0;
    bool step() {
        auto& me = cambc::self();
        while (i < pts.size() && me.position() == T(pts[i])) ++i;
        if (i >= pts.size()) return true;
        if (me.can_move()) step_to(T(pts[i]));
        return false;
    }
};

int st = 0, w = -1;
Walker walker;

void vesper() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 5, 8 });
    const auto& wolf = g.front();
    if (st == 0 || st == 2 || st == 5) {
        if (me.position() != T({ 5, 5 })) { if (me.can_move()) step_to(T({ 5, 5 })); return; }
        log("start", g, st);
        if (!wolf.is_asleep() || !me.can_attack()) return;
        me.attack(wolf);
        w = r;
        if (st == 0) { me.abilities()[1].use(T({ 5, 3 })); st = 1; std::printf("PROBE r=%d vesper WAKE S1 attack+dash\n", r); }
        else if (st == 2) { st = 3; std::printf("PROBE r=%d vesper WAKE S2\n", r); }
        else { st = 6; std::printf("PROBE r=%d vesper WAKE S2b\n", r); }
        log("after", g, st);
        return;
    }
    log("start", g, st);
    if (st == 1 || st == 4 || st == 7) {
        if (wolf.is_asleep()) { std::printf("PROBE r=%d vesper ASLEEP st=%d wake=%d\n", r, st, w); st = st == 1 ? 2 : st == 4 ? 5 : 8; }
        return;
    }
    if (st == 3 || st == 6) {
        if (r < w + 4) return;
        if (st == 3) { step_to(T({ 5, 4 })); std::printf("PROBE r=%d vesper LEAVE S2 walk\n", r); st = 4; }
        else { me.attack(wolf); me.abilities()[1].use(T({ 5, 3 })); std::printf("PROBE r=%d vesper LEAVE S2b attack+dash\n", r); st = 7; }
        w = r;
        log("after", g, st);
    }
}

void stellar() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 5, 14 });
    if (st == 0) {
        walker.pts = { { 13, 1 }, { 13, 14 }, { 9, 14 } };
        st = 1;
    }
    if (st == 1) { if (!walker.step()) return; st = 2; return; }
    log("start", g, st);
    if (st == 2 || st == 4) {
        if (!all_asleep(g) || !me.abilities()[0].is_ready()) return;
        me.abilities()[0].use(g.front().kind() == cambc::camp_type::wolf ? g.front() : g.back());
        w = r;
        std::printf("PROBE r=%d stellar WAKE spell st=%d\n", r, st);
        ++st;
        log("after", g, st);
        return;
    }
    if (st == 3 || st == 5) {
        bool any = false;
        for (const auto& c : g) if (c.is_awake()) any = true;
        if (!any) { std::printf("PROBE r=%d stellar ALLASLEEP st=%d wake=%d\n", r, st, w); ++st; }
    }
}

void prism() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 19, 2 });
    if (st == 0) {
        if (me.position() != T({ 15, 2 })) { if (me.can_move()) step_to(T({ 15, 2 })); return; }
        st = 1;
        return;
    }
    log("start", g, st);
    if (st == 1 || st == 3) {
        if (!all_asleep(g) || !me.abilities()[1].is_ready()) return;
        me.abilities()[1].use(T({ 19, 2 }));
        w = r;
        std::printf("PROBE r=%d prism WAKE ground st=%d\n", r, st);
        ++st;
        log("after", g, st);
        return;
    }
    if (st == 2 || st == 4) {
        if (all_asleep(g)) { std::printf("PROBE r=%d prism ALLASLEEP st=%d wake=%d\n", r, st, w); ++st; }
    }
}

void marcella() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 5, 21 });
    if (st == 0) { walker.pts = { { 14, 1 }, { 14, 21 }, { 8, 21 } }; st = 1; }
    if (st == 1) { if (!walker.step()) return; st = 2; return; }
    log("start", g, st);
    const cambc::camp* wolf = nullptr;
    for (const auto& c : g) if (c.kind() == cambc::camp_type::wolf) wolf = &c;
    if (st == 2) {
        if (!all_asleep(g) || !me.abilities()[1].is_ready()) return;
        me.abilities()[1].use(*wolf);
        w = r;
        std::printf("PROBE r=%d marcella WAKE spell\n", r);
        st = 3;
        log("after", g, st);
        return;
    }
    if (st == 3 && r >= w + 5) {
        step_to(T({ 9, 21 }));
        std::printf("PROBE r=%d marcella LEAVE walk wake=%d\n", r, w);
        st = 4;
        log("after", g, st);
        return;
    }
    if (st == 4 && all_asleep(g)) { std::printf("PROBE r=%d marcella ALLASLEEP\n", r); st = 5; }
}

void elk_vesper() {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 9, 2 });
    if (st == 0 && r < 14) return;
    if (st == 0) {
        if (me.position() != T({ 6, 2 })) { if (me.can_move()) step_to(T({ 6, 2 })); return; }
        log("start", g, st);
        if (!g.front().is_asleep() || !me.can_attack()) return;
        for (const auto& c : g) if (c.kind() == cambc::camp_type::elk) me.attack(c);
        std::printf("PROBE r=%d vesper WAKE elk\n", r);
        st = 1;
        log("after", g, st);
        return;
    }
    log("start", g, st);
    if (me.position() != T({ 5, 2 }) && me.can_move()) step_to(T({ 5, 2 }));
}

void elk_hitter(bool stellar) {
    auto& me = cambc::self();
    const int r = (int)cambc::round_number();
    auto g = group_of({ 9, 2 });
    const vec2 home = stellar ? vec2{ 13, 6 } : vec2{ 14, 6 };
    if (st == 0 && me.position() != T(home)) { if (me.can_move()) step_to(T(home)); return; }
    log("start", g, st);
    const cambc::camp *elk = nullptr, *gold = nullptr;
    bool clusters_asleep = true;
    for (const auto& c : g) {
        if (c.kind() == cambc::camp_type::elk) elk = &c;
        else if (!c.is_asleep()) clusters_asleep = false;
        if (c.kind() == cambc::camp_type::gold_cluster) gold = &c;
    }
    if (st != 0 && !(st == 1 && !stellar)) return;
    if (!elk->is_awake() || !clusters_asleep) return;
    if (stellar) {
        if (!me.abilities()[0].is_ready()) return;
        me.abilities()[0].use(*elk);
        cambc::shared_memory[0] = 1;
        std::printf("PROBE r=%d stellar HIT awake elk (clusters asleep)\n", r);
        st = 1;
    } else if (st == 0) {
        if (cambc::shared_memory[0] != 1) return;
        step_to(T({ 13, 5 }));
        std::printf("PROBE r=%d prism STEP to (13,5)\n", r);
        st = 1;
    } else {
        if (!me.can_attack()) return;
        me.attack(*gold);
        std::printf("PROBE r=%d prism HIT asleep gold cluster (elk awake)\n", r);
        st = 2;
    }
    log("after", g, st);
}

void play_turn() {
    auto& me = cambc::self();
    if (cambc::round_number() == 1) {
        g_b = cambc::map::spawn_region(team::ally).positions().front().y > cambc::map::height() / 2;
        std::printf("PROBE r=1 init %s team=%c\n", who(), g_b ? 'B' : 'A');
    }
    std::printf("POS r=%d %s (%d,%d) hp=%.0f\n", (int)cambc::round_number(), who(), me.position().x, me.position().y, (double)me.health());
    if (cambc::map::width() == 30) {
        switch (me.champion_name()) {
        case CT::vesper_vale: elk_vesper(); break;
        case CT::stellar: elk_hitter(true); break;
        case CT::prism: elk_hitter(false); break;
        default: {
            const vec2 park = T(me.champion_name() == CT::marcella ? vec2{ 0, 2 } : vec2{ 2, 0 });
            if (me.position() != park && me.can_move()) step_to(park);
            break;
        }
        }
        return;
    }
    switch (me.champion_name()) {
    case CT::vesper_vale: vesper(); break;
    case CT::stellar: stellar(); break;
    case CT::prism: prism(); break;
    case CT::marcella: marcella(); break;
    default: break;
    }
}

void play_draft() {
    for (auto d : { D::vesper_vale, D::stellar, D::prism, D::marcella, D::vendetta, D::ryth, D::varg })
        try { cambc::draft::pick(d); return; } catch (const cambc::error&) {}
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) { std::printf("PROBE r=%d %s err %s\n", (int)cambc::round_number(), who(), e.message().c_str()); }
        cambc::end_turn();
    }
}
