// probe-emblems-v2 (engine 2.0.0): the Capture, Tribute, Skirmish and Collectors emblems.
// Map emblems.map26a (makemap.mjs). Both teams run this code in mirrored halves; team B buys no Capture/Tribute emblem
// (the control) and Collectors instead of Skirmish.
//   Ryth: farms its gold block, buys Capture (A), holds X alone, then joins Vendetta's capture of Y 2 rounds in.
//   Prism: farms its gold block, buys Tribute (A), captures gem groups of 14/21/28/56 next to the altar, tributing each.
//   Stellar: farms its gold block, buys Skirmish (A) / Collectors (B), then at the meeting tile hits the enemy Stellar
//   and its wolf with basic attacks, slot 0 (2x Focus, unit) and slot 1 (1.4x Focus, ground).
//   Varg kills the gem groups; Vendetta kills X and Y, then starts Y's capture when Ryth is ready.
// All emblems are 5 Health shards, so Strength and Focus are base. Logs PROBE lines.
//   tools/probes/probe-emblems-v2/run.sh <join_delay>   (rounds after Vendetta starts Y that Ryth joins; 1-4 tested)
// Results (2026-10-25, engine 2.0.0):
//   Capture: held from R pays at R+4 (R+6 without); capture_state reads available/5 the turn R steps on, then ally 3,2,1
//   (5,4,3,2,1 without). An emblem holder joining mid-capture sets timer = min(timer, 3) at once: 5->3, 4->3, 3->3, 2->2.
//   Tribute: bags 14/21/28/56 channel 2/3/3/5 turn ends (6 without at 56): ceil(ceil(g/10) * 0.67).
//   Skirmish: x1.05 on basic, unit and ground damage to champions, x1.00 to camps. Collectors alone: x1.01 to both.
#include <cambc.h>
#if __has_include("scenario.h")
#include "scenario.h"
#endif
#include <algorithm>
#include <cstdio>
#include <optional>
#include <string_view>
#include <variant>
#include <vector>

using cambc::vec2;
using cambc::team;
using D = cambc::champion_draft;
using CT = cambc::champion_type;
using F = cambc::item_family;

#ifndef JOIN_DELAY
#define JOIN_DELAY 2  // rounds after Vendetta starts Y that Ryth joins (scenario.h overrides)
#endif

namespace {

bool team_a() { return cambc::map::spawn_region(team::ally).is_set({ 0, 0 }); }
vec2 M(vec2 p) { return team_a() ? p : vec2{ 39 - p.x, 39 - p.y }; }
int R() { return (int)cambc::round_number(); }
char T() { return team_a() ? 'A' : 'B'; }

std::vector<cambc::map::camp_group>& groups() {
    static std::vector<cambc::map::camp_group> g = cambc::map::camp_groups();
    return g;
}
cambc::bitboard& camp_tiles() {
    static cambc::bitboard b = [] {
        cambc::bitboard t; t.clear();
        for (auto& g : groups()) for (auto& c : g) t.set(c.spawn_position());
        return t;
    }();
    return b;
}
cambc::map::camp_group* group_at(vec2 p) {
    for (auto& g : groups()) for (auto& c : g) if (c.spawn_position() == p) return &g;
    return nullptr;
}
const char* cap_name(cambc::map::camp_group_capture_type t) {
    switch (t) {
    case cambc::map::camp_group_capture_type::no_capture_available: return "none";
    case cambc::map::camp_group_capture_type::ally_capturing: return "ally";
    case cambc::map::camp_group_capture_type::contested: return "contested";
    case cambc::map::camp_group_capture_type::enemy_capturing: return "enemy";
    case cambc::map::camp_group_capture_type::capture_available: return "available";
    }
    return "?";
}
const char* life_name(const cambc::map::camp_group& g) {
    try {
        auto s = g.state();
        if (std::holds_alternative<cambc::map::camp_group_alive>(s)) return "alive";
        if (std::holds_alternative<cambc::map::camp_group_reward_available>(s)) return "cleared";
        return "respawning";
    } catch (...) { return "unseen"; }
}
bool cleared(const cambc::map::camp_group& g) { return std::string_view(life_name(g)) == "cleared"; }

void log_group(const char* tag, vec2 tile) {
    auto* g = group_at(tile);
    if (!g) return;
    auto cs = g->capture_state();
    auto& me = cambc::self();
    std::printf("PROBE %c %d %s group@(%d,%d) life=%s cap=%s timer=%d my_gold=%u my_gems=%u pos=(%d,%d)\n", T(), R(), tag,
                tile.x, tile.y, life_name(*g), cap_name(cs.state), cs.timer, me.gold_count(), me.gem_count(), me.position().x,
                me.position().y);
}

bool step_to(vec2 t) {
    auto& me = cambc::self();
    if (me.position() == t) return true;
    if (!me.can_move()) return false;
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars() | cambc::map::spawn_region(team::enemy)
        | cambc::vision::champion_tiles() | camp_tiles();
    for (const auto& c : cambc::vision::camps()) if (c.is_alive()) blocked.set(c.position());
    blocked.set(me.position(), false);
    cambc::bitboard goal; goal.clear(); goal.set(t);
    if (camp_tiles().is_set(t)) blocked.set(t, false);
    for (const auto& c : cambc::vision::camps()) if (c.is_alive() && c.position() == t) return false;
    goal &= ~blocked;
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

std::optional<cambc::camp> camp_at(vec2 p) {
    for (const auto& c : cambc::vision::camps()) if (c.position() == p && c.is_alive()) return c;
    return std::nullopt;
}

// ---- shared: farm own 3x3 gold block with ground casts, hold it, buy an emblem ----
struct Farm {
    vec2 center, hold;
    int phase = 0;  // 0 cast, 1 hold, 2 buy, 3 done
    int cap_from = -1;
    bool run(std::optional<F> fam) {
        auto& me = cambc::self();
        const vec2 c = M(center), h = M(hold);
        if (phase == 0) {
            bool alive = false;
            for (int dx = -1; dx <= 1; ++dx) for (int dy = -1; dy <= 1; ++dy) if (camp_at({ c.x + dx, c.y + dy })) alive = true;
            if (!alive) { phase = 1; std::printf("PROBE %c %d block_dead\n", T(), R()); }
            else {
                if (me.position().chebyshev_distance(c) > 4) { step_to(M({ 2, 2 })); return false; }
                auto ab = me.abilities()[me.champion_name() == CT::ryth ? 0 : (me.champion_name() == CT::prism ? 1 : 1)];
                if (ab.is_ready()) { ab.use(c); std::printf("PROBE %c %d ground_cast\n", T(), R()); }
                return false;
            }
        }
        if (phase == 1) {
            log_group("hold_start", h);
            if (me.gold_count() >= 150) { phase = 2; std::printf("PROBE %c %d paid gold=%u (held from %d)\n", T(), R(), me.gold_count(), cap_from); }
            else {
                bool was = me.position() == h;
                if (step_to(h) && !was) { cap_from = R(); log_group("hold_after_step", h); }
                return false;
            }
        }
        if (phase == 2) {
            if (!cambc::map::spawn_region(team::ally).is_set(me.position())) step_to(M({ 2, 2 }));
            if (!cambc::map::spawn_region(team::ally).is_set(me.position())) return false;
            if (fam) {
                me.buy(cambc::get_item_enum(*fam, cambc::item_stat::health), 5);
                std::printf("PROBE %c %d bought family=%d gold=%u maxhp=%.1f str=%.2f focus=%.2f\n", T(), R(), (int)*fam,
                            me.gold_count(), me.max_health(), me.strength(), me.focus());
            }
            phase = 3;
            return true;
        }
        return phase == 3;
    }
};

// ---- Ryth: Capture emblem ----
Farm ryth_farm{ { 5, 1 }, { 4, 1 } };
int ryth_phase = 0, ryth_from = -1;
unsigned ryth_gold0 = 0;
void ryth() {
    auto& me = cambc::self();
    if (ryth_phase == 0) { if (ryth_farm.run(team_a() ? std::optional<F>(F::capture) : std::nullopt)) { ryth_phase = 1; ryth_gold0 = me.gold_count(); } return; }
    const vec2 X = M({ 8, 1 }), Y2 = M({ 8, 4 }), STAGE = M({ 7, 4 });
    if (ryth_phase == 1) {  // hold X alone
        auto* gx = group_at(X);
        if (!cleared(*gx) && me.position() != X) { step_to(M({ 7, 1 })); return; }
        log_group("X_start", X);
        if (me.gold_count() > ryth_gold0) {
            std::printf("PROBE %c %d X_paid gold=%u held_from=%d\n", T(), R(), me.gold_count(), ryth_from);
            ryth_phase = 2; ryth_gold0 = me.gold_count();
        } else {
            bool was = me.position() == X;
            if (step_to(X) && !was) { ryth_from = R(); log_group("X_after_step", X); }
            return;
        }
    }
    if (ryth_phase == 2) {  // stage next to Y
        if (step_to(STAGE)) { cambc::shared_memory[0] = 1; ryth_phase = 3; std::printf("PROBE %c %d staged\n", T(), R()); }
        return;
    }
    if (ryth_phase == 3) {  // join Vendetta's capture two rounds after it started
        log_group("Y_ryth_start", Y2);
        if ((uint8_t)cambc::shared_memory[0] != 2) return;
        const int vr = (uint8_t)cambc::shared_memory[1];
        if (((R() - vr) & 255) >= JOIN_DELAY) {
            if (step_to(Y2)) { ryth_phase = 4; ryth_from = R(); log_group("Y_ryth_joined", Y2); }
        }
        return;
    }
    if (ryth_phase == 4) {
        log_group("Y_ryth_start", Y2);
        if (me.gold_count() > ryth_gold0) { std::printf("PROBE %c %d Y_paid_ryth gold=%u joined=%d\n", T(), R(), me.gold_count(), ryth_from); ryth_phase = 5; }
    }
}

// ---- Vendetta: kill X and Y, then start Y's capture ----
int ven_phase = 0, ven_from = -1;
unsigned ven_gold0 = 0;
void hit(vec2 target) {
    auto& me = cambc::self();
    auto c = camp_at(target);
    if (!c && me.position().chebyshev_distance(target) <= 1) return;
    if (me.position().chebyshev_distance(target) > 1) {
        vec2 best = me.position(); int bd = 1 << 20;
        cambc::bitboard adj; adj.clear(); adj.draw_chebyshev(target, 1);
        adj &= ~camp_tiles();
        adj &= ~(cambc::map::walls() | cambc::map::altars() | cambc::vision::champion_tiles());
        for (auto p : adj.positions()) { int d = p.chebyshev_distance(me.position()); if (d < bd) { bd = d; best = p; } }
        step_to(best);
    }
    if (!c || me.position().chebyshev_distance(target) > 1) return;
    if (me.can_attack()) me.attack(*c);
    if (!me.can_attack() && c->is_alive() && me.abilities()[0].is_ready()) {
        me.abilities()[0].use();
        if (me.can_attack()) me.attack(*c);
    }
}
void vendetta() {
    auto& me = cambc::self();
    const vec2 targets[] = { M({ 8, 1 }), M({ 8, 3 }), M({ 8, 4 }) };
    if (ven_phase == 0) {
        for (auto t : targets) if (camp_at(t) || me.position().chebyshev_distance(t) > 8) { hit(t); return; }
        ven_phase = 1;
    }
    const vec2 Y1 = M({ 8, 3 });
    if (ven_phase == 1) {
        if (!step_to(M({ 9, 3 }))) return;
        if ((uint8_t)cambc::shared_memory[0] != 1) return;
        ven_gold0 = me.gold_count();
        if (step_to(Y1)) {
            ven_from = R();
            cambc::shared_memory[0] = 2; cambc::shared_memory[1] = (uint8_t)(R() & 255);
            log_group("Y_ven_after_step", Y1);
            ven_phase = 2;
        }
        return;
    }
    if (ven_phase == 2) {
        log_group("Y_ven_start", Y1);
        if (me.gold_count() > ven_gold0) { std::printf("PROBE %c %d Y_paid_ven gold=%u from=%d\n", T(), R(), me.gold_count(), ven_from); ven_phase = 3; }
    }
}

// ---- Varg: kill the gem groups ----
void varg() {
    std::vector<vec2> tiles;
    for (vec2 p : { vec2{ 9, 11 }, vec2{ 8, 11 }, vec2{ 11, 11 }, vec2{ 11, 12 }, vec2{ 11, 13 }, vec2{ 11, 9 }, vec2{ 12, 9 },
                    vec2{ 11, 8 }, vec2{ 12, 8 } })
        tiles.push_back(M(p));
    for (int y = 9; y >= 6; --y) for (int x = 9; x >= 8; --x) tiles.push_back(M({ x, y }));
    auto& me = cambc::self();
    if (R() % 10 == 0) std::printf("PROBE %c %d varg pos=(%d,%d)\n", T(), R(), me.position().x, me.position().y);
    for (auto t : tiles) if (camp_at(t) || me.position().chebyshev_distance(t) > 7) { hit(t); return; }
}

// ---- Prism: Tribute emblem ----
Farm prism_farm{ { 1, 5 }, { 1, 4 } };
int prism_phase = 0, prism_k = 0;
const vec2 PRISM_HOLD[] = { { 9, 11 }, { 11, 11 }, { 11, 9 }, { 9, 9 } };
void prism() {
    auto& me = cambc::self();
    if (prism_phase == 0) { if (prism_farm.run(team_a() ? std::optional<F>(F::tribute) : std::nullopt)) prism_phase = 1; return; }
    if (prism_k >= 4) return;
    const vec2 h = M(PRISM_HOLD[prism_k]), altar = M({ 10, 10 });
    const bool chan = me.state().contains(cambc::champion_state::submitting_gems);
    if (prism_phase == 1) {  // hold group k
        auto* g = group_at(h);
        if (R() % 10 == 0) std::printf("PROBE %c %d prism_wait k=%d life=%s pos=(%d,%d)\n", T(), R(), prism_k, life_name(*g), me.position().x, me.position().y);
        if (!cleared(*g) && me.position() != h) { step_to(M({ 10, 12 })); return; }
        if (me.gem_count() > 0) {
            std::printf("PROBE %c %d bag=%u submitted_before=%u\n", T(), R(), me.gem_count(), cambc::global_submitted_gems(team::ally));
            me.submit_gems(altar);
            std::printf("PROBE %c %d tribute_start bag=%u channel=%d\n", T(), R(), me.gem_count(), me.remaining_channel_time());
            prism_phase = 2;
            return;
        }
        step_to(h);
        return;
    }
    if (prism_phase == 2) {
        std::printf("PROBE %c %d tribute_tick chan=%d channel=%d bag=%u submitted=%u\n", T(), R(), (int)chan,
                    chan ? me.remaining_channel_time() : -1, me.gem_count(), cambc::global_submitted_gems(team::ally));
        if (!chan) { prism_phase = 1; ++prism_k; }
    }
}

// ---- Stellar: Skirmish (A) / Collectors (B) ----
Farm stellar_farm{ { 5, 5 }, { 4, 4 } };
int st_phase = 0, st_step = 0;
std::optional<cambc::champion> enemy_stellar() {
    for (auto& c : cambc::vision::champions())
        if (c.team() == team::enemy && c.champion_name() == CT::stellar) return c;
    return std::nullopt;
}
void stellar() {
    auto& me = cambc::self();
    if (st_phase == 0) { if (stellar_farm.run(team_a() ? F::skirmish : F::collectors)) st_phase = 1; return; }
    if (!step_to(M({ 18, 18 }))) return;
    auto e = enemy_stellar();
    auto w = camp_at(M({ 18, 15 }));
    if (!e || !w || e->position().chebyshev_distance(me.position()) > 3) return;
    auto rep = [&](const char* what, float before, float after, float base) {
        std::printf("PROBE %c %d %s before=%.4f after=%.4f dmg=%.4f base=%.4f ratio=%.6f str=%.3f focus=%.3f\n", T(), R(), what,
                    before, after, before - after, base, (before - after) / base, me.strength(), me.focus());
    };
    if (st_step == 0 && me.can_attack() && me.abilities()[0].is_ready()) {
        float b = e->health(); me.attack(*e); float a = e->health(); rep("basic_champ", b, a, me.strength());
        b = a; me.abilities()[0].use(*e); a = e->health(); rep("spell0_champ", b, a, 2 * me.focus());
        st_step = 1; return;
    }
    if (st_step == 1 && me.can_attack() && me.abilities()[1].is_ready()) {
        float b = w->health(); me.attack(*w); float a = w->health(); rep("basic_camp", b, a, me.strength());
        b = a; me.abilities()[1].use(w->position()); a = w->health(); rep("spell1_camp", b, a, 1.4f * me.focus());
        st_step = 2; return;
    }
    if (st_step == 2 && me.abilities()[0].is_ready()) {
        float b = w->health(); me.abilities()[0].use(*w); float a = w->health(); rep("spell0_camp", b, a, 2 * me.focus());
        st_step = 3; return;
    }
    if (st_step == 3 && me.abilities()[1].is_ready()) {
        float b = e->health(); me.abilities()[1].use(e->position()); float a = e->health(); rep("spell1_champ", b, a, 1.4f * me.focus());
        st_step = 4; return;
    }
}

void play_turn() {
    auto& me = cambc::self();
    if (!me.is_alive()) return;
    if (R() == 1 && me.champion_name() == CT::stellar && team_a()) {
        for (auto f : { F::tribute, F::capture, F::skirmish, F::collectors, F::prospector, F::hunter, F::greed })
            std::printf("PROBE settings family=%d emblem_passive_magnitude=%.6f\n", (int)f,
                        cambc::get_item_enum(f, cambc::item_stat::health, false).passive_magnitude());
        std::printf("PROBE settings capture_time=%d submit_mult=%.6f submit_base=%d submit_min=%d\n", cambc::constants::capture_time,
                    cambc::detail::cached_game_settings.submit_gem_duration_multiplier, cambc::constants::submit_gem_base_duration,
                    cambc::constants::submit_gem_minimum_duration);
    }
    switch (me.champion_name()) {
    case CT::ryth: ryth(); break;
    case CT::vendetta: vendetta(); break;
    case CT::varg: varg(); break;
    case CT::prism: prism(); break;
    case CT::stellar: stellar(); break;
    default: break;
    }
}

void play_draft() {
    const auto mine = cambc::draft::current_draft(team::ally);
    const std::vector<D> order{ D::stellar, D::ryth, D::prism, D::varg, D::vendetta };
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
