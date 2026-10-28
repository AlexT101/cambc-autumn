// probe-prospector-remainder: is the Prospector bonus 25% of the owner's floor share, or of floor + remainder?
// Map prospector.map26a (makemap.mjs), both teams run this mirrored. Picks Stellar, Ryth, Vendetta, so Stellar has the
// lowest id and gets the remainder.
//   Stellar farms gold block F alone (180), buys 5 Prospector health shards in spawn, steps onto T (4,4) and flags.
//   Ryth kills T (5 gem + 4 gold clusters: 35 gems, 80 gold) with ground casts; Ryth and Vendetta join T on the flag.
// 3-way split: gems 11 each + 2 remainder, gold 26 each + 2 remainder. Stellar's bonus reads 2 gems / 6 gold
// (floor only) or 3 gems / 7 gold (with remainder).
// Run: cambc run tools/probes/probe-prospector-remainder tools/probes/probe-prospector-remainder
//        --map tools/probes/probe-prospector-remainder/prospector.map26a --rounds 120 --fuel 50000000 -o DIR
// Result (2026-10-28): owner +35 gold / +16 gems (28+7, 13+3), others +26 / +11: the bonus is 25% of floor + remainder.
// The early "Known occupied destination" errors are step_to bumping into allies in spawn; harmless.
#include <cambc.h>
#include <algorithm>
#include <cstdio>
#include <optional>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
using F = cambc::item_family;

namespace {
bool team_a() { return cambc::map::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 M(vec2 p) { return team_a() ? p : vec2{ 29 - p.x, 29 - p.y }; }
int R() { return (int)cambc::round_number(); }
char T() { return team_a() ? 'A' : 'B'; }

cambc::bitboard& camp_tiles() {
    static cambc::bitboard b = [] {
        cambc::bitboard t; t.clear();
        for (auto& g : cambc::map::camp_groups()) for (auto& c : g) t.set(c.spawn_position());
        return t;
    }();
    return b;
}
std::optional<cambc::camp> camp_at(vec2 p) {
    for (const auto& c : cambc::vision::camps()) if (c.position() == p && c.is_alive()) return c;
    return std::nullopt;
}
bool any_alive(vec2 c) {
    for (int dx = -1; dx <= 1; ++dx) for (int dy = -1; dy <= 1; ++dy) if (camp_at({ c.x + dx, c.y + dy })) return true;
    return false;
}

bool step_to(vec2 t) {
    auto& me = cambc::self();
    if (me.position() == t) return true;
    if (!me.can_move()) return false;
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::map::spawn_region(team::enemy)
        | cambc::vision::champion_tiles() | camp_tiles();
    blocked.set(me.position(), false);
    blocked.set(t, false);
    cambc::bitboard goal; goal.clear(); goal.set(t);
    cambc::bitboard src; src.clear(); src.set(me.position());
    cambc::distance_field field;
    cambc::bitboard visited;
    field.compute_to(blocked, goal, src, visited);
    auto step = me.position();
    for (auto tile : blocked.reachable_tiles(step, 1).positions())
        if (field.get(tile) < field.get(step)) step = tile;
    if (step != me.position()) me.move_absolute(step);
    return me.position() == t;
}

unsigned last_gold = 0, last_gems = 0;
void log_state(const char* tag) {
    auto& me = cambc::self();
    std::printf("PROBE %c %d %s id=%u gold=%u gems=%u pos=(%d,%d) items=", T(), R(), tag, (unsigned)(cambc::handle_champion_t)me, me.gold_count(),
                me.gem_count(), me.position().x, me.position().y);
    int i = 0;
    for (auto n : me.item_count()) { if (n) std::printf("%d:%u ", i, (unsigned)n); ++i; }
    std::printf("\n");
}
void log_change() {
    auto& me = cambc::self();
    if (me.gold_count() != last_gold || me.gem_count() != last_gems) {
        std::printf("PROBE %c %d delta gold %u->%u (+%d) gems %u->%u (+%d)\n", T(), R(), last_gold, me.gold_count(),
                    (int)me.gold_count() - (int)last_gold, last_gems, me.gem_count(), (int)me.gem_count() - (int)last_gems);
        log_state("after");
    }
    last_gold = me.gold_count(); last_gems = me.gem_count();
}

int st_phase = 0;
void stellar() {
    auto& me = cambc::self();
    const vec2 c = M({ 5, 1 });
    if (st_phase == 0) {  // kill F
        if (!any_alive(c)) { st_phase = 1; return; }
        if (me.position().chebyshev_distance(c) > 3) { step_to(M({ 2, 2 })); return; }
        auto ab = me.abilities()[1];
        if (ab.is_ready()) ab.use(c);
        return;
    }
    if (st_phase == 1) {  // hold F alone
        if (me.gold_count() >= 150) { st_phase = 2; return; }
        step_to(M({ 4, 1 }));
        return;
    }
    if (st_phase == 2) {  // buy in spawn
        if (!step_to(M({ 2, 2 }))) return;
        log_state("before_buy");
        me.buy(cambc::get_item_enum(F::prospector, cambc::item_stat::health), 5);
        log_state("after_buy");
        st_phase = 3;
        return;
    }
    if (st_phase == 3) {  // wait for T cleared, step on, flag
        if (any_alive(M({ 5, 5 }))) return;
        if (step_to(M({ 4, 4 }))) { cambc::shared_memory[0] = 1; log_state("on_T"); st_phase = 4; }
    }
}

void ryth() {
    auto& me = cambc::self();
    const vec2 c = M({ 5, 5 });
    if (any_alive(c)) {
        if (me.position().chebyshev_distance(c) > 3) { step_to(M({ 2, 2 })); return; }
        auto ab = me.abilities()[0];
        if (ab.is_ready()) ab.use(c);
        return;
    }
    if ((uint8_t)cambc::shared_memory[0] != 1) { step_to(M({ 7, 3 })); return; }
    if (me.position() != M({ 6, 4 }) && step_to(M({ 6, 4 }))) log_state("on_T");
}

void vendetta() {
    auto& me = cambc::self();
    if ((uint8_t)cambc::shared_memory[0] != 1) { step_to(M({ 3, 7 })); return; }
    if (me.position() != M({ 4, 6 }) && step_to(M({ 4, 6 }))) log_state("on_T");
}

void play_turn() {
    auto& me = cambc::self();
    if (!me.is_alive()) return;
    if (R() == 1) log_state("start");
    if ((uint8_t)cambc::shared_memory[0] == 1) log_change();
    else { last_gold = me.gold_count(); last_gems = me.gem_count(); }
    switch (me.champion_name()) {
    case CT::stellar: stellar(); break;
    case CT::ryth: ryth(); break;
    case CT::vendetta: vendetta(); break;
    default: break;
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const std::vector<D> order{ D::stellar, D::ryth, D::vendetta };
    for (auto d : order) if (std::find(mine.begin(), mine.end(), d) == mine.end()) { cambc::draft::pick(d); return; }
}
} // namespace

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const cambc::error& e) {
            std::printf("PROBE %d err %s\n", (int)cambc::round_number(), e.message().c_str());
        } catch (const std::exception& e) { std::printf("PROBE err %s\n", e.what()); }
        cambc::end_turn();
    }
}
