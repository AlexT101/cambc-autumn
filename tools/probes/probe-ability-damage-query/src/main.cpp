// probe-ability-damage-query (cambc 5.0.1): does champion::ability::damage_amount() (sdk_champion_ability_damage, the
// target-free raw) include the caster's Skirmish (+10% to champions) and Collectors (+1% per emblem family) bonuses?
// Map: probe-emblems-v2's emblems.map26a. Only the Stellars act (the other picks idle). Each farms its 3x3 gold block,
// then buys 5 Health shards of Skirmish (team A) or Collectors (team B), so Strength and Focus stay base.
// Logs damage_amount() for both slots against Focus x modifier before and after the emblem, then at the meeting tile
// damage_amount(enemy) and the actual health lost by the enemy Stellar to slot 0 (unit, 2x Focus) and slot 1 (ground, 1.4x).
//   tools/probes/probe-ability-damage-query/run.sh
#include <cambc.h>
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

Farm stellar_farm{ { 5, 5 }, { 4, 4 } };
int st_phase = 0, st_step = 0;
std::optional<cambc::champion> enemy_stellar() {
    for (auto& c : cambc::vision::champions())
        if (c.team() == team::enemy && c.champion_name() == CT::stellar) return c;
    return std::nullopt;
}
float modifier(const cambc::ability& ab) {
    if (ab.is(cambc::ability_types::damage)) return ab.get<cambc::ability_damage>().modifier;
    if (ab.is(cambc::ability_types::aoe_damage)) return ab.get<cambc::ability_aoe_damage>().modifier;
    return 0;
}
void query(const char* tag) {
    auto& me = cambc::self();
    for (int s = 0; s < 2; ++s) {
        auto ab = me.abilities()[s];
        const float raw = ab.damage_amount(), mod = modifier(ab);
        std::printf("PROBE %c %d query %s slot=%d raw=%.4f focus=%.3f mod=%.3f raw/(focus*mod)=%.6f str=%.3f\n", T(), R(), tag, s,
                    raw, me.focus(), mod, raw / (me.focus() * mod), me.strength());
    }
}
void stellar() {
    auto& me = cambc::self();
    if (R() <= 2) query("start");
    if (st_phase == 0) {
        if (stellar_farm.run(team_a() ? F::skirmish : F::collectors)) { st_phase = 1; query("after_buy"); }
        return;
    }
    if (!step_to(M({ 18, 18 }))) return;
    auto e = enemy_stellar();
    if (!e || e->position().chebyshev_distance(me.position()) > 3) return;
    auto rep = [&](int s, float raw, float against, float before, float after) {
        std::printf("PROBE %c %d hit slot=%d raw=%.4f against=%.4f dmg=%.4f dmg/raw=%.6f dmg/(focus*mod)=%.6f enemy_hp_before=%.2f\n", T(),
                    R(), s, raw, against, before - after, (before - after) / raw,
                    (before - after) / (me.focus() * modifier(me.abilities()[s])), before);
    };
    if (st_step == 0 && me.abilities()[0].is_ready()) {
        auto ab = me.abilities()[0];
        float raw = ab.damage_amount(), ag = ab.damage_amount(*e), b = e->health();
        ab.use(*e);
        rep(0, raw, ag, b, e->health());
        st_step = 1; return;
    }
    if (st_step == 1 && me.abilities()[1].is_ready()) {
        auto ab = me.abilities()[1];
        float raw = ab.damage_amount(), ag = ab.damage_amount(*e), b = e->health();
        ab.use(e->position());
        rep(1, raw, ag, b, e->health());
        st_step = 2; return;
    }
}

void play_turn() {
    auto& me = cambc::self();
    if (!me.is_alive()) return;
    if (me.champion_name() == CT::stellar) { stellar(); if (R() % 10 == 0) std::printf("PROBE %c %d stellar pos=(%d,%d) gold=%u phase=%d\n", T(), R(), me.position().x, me.position().y, me.gold_count(), st_phase); }
    else step_to(M({ 2 * (int)me.champion_name() % 30, 16 }));  // the others leave the spawn and stand clear
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
