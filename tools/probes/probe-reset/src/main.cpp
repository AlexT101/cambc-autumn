// probe-reset: does capture progress reset the moment a group's tiles are empty or contested, even mid-round?
// Shared source with probe-reset-b (team B); run.sh copies this file there and sets SIDE=1.
//   bash tools/probes/probe-reset/run.sh <scenario> [rounds]      (map packs)
// Team A drafts Vendetta (id 0, X), Varg (id 1, Y), Ryth (id 2); all three kill packs group (11..12,17..18)
// (2 gold + 2 gem clusters, 70 gold, 48 gems). X steps onto T1 in round H and writes H to shared memory.
// In round H+D (D = 4):
//   1 control: X stays on T1.
//   2 handoff: X walks off; Y, acting later that round, walks onto T2 (tiles empty between the two turns).
//   3 self: X walks off, then dashes back onto T1 in the same turn.
//   4 within: X walks from T1 to T3 (tiles never empty).
//   5 enemy: X stays; B's Vendetta walks onto T2 and dashes off in one turn (contested mid-turn only).
//   6 handoff, Y first: Y (priority 1) walks onto T2, then X walks off later that round (never empty).
// Old rule (reset only by a capture phase finding the tiles empty/contested): every scenario pays at H+6.
// Immediate rule: 1, 4, 6 pay at H+6; 2, 3, 5 pay at (round of the reset)+6.
#include <cambc.h>
#include <iostream>
#include <string>
#include <variant>
#include "scenario.h"
#include "side.h"

using cambc::vec2;
using cambc::team;
using cambc::champion_type;

constexpr int D = 4;
const vec2 T1{11, 17}, T2{12, 18}, T3{12, 17}, T4{11, 18};
const vec2 PARK{8, 13};

static cambc::bitboard tiles(std::initializer_list<vec2> ps) { cambc::bitboard b; b.clear(); for (auto p : ps) b.set(p); return b; }
static cambc::bitboard around(vec2 p, int r) { cambc::bitboard b; b.clear(); b.draw_chebyshev(p, r); return b; }
static const cambc::bitboard& group_tiles() { static const auto g = tiles({T1, T2, T3, T4}); return g; }

static std::string err_str(const std::exception& e) {
    if (auto* ge = dynamic_cast<const cambc::error*>(&e)) return cambc::to_string(ge->code());
    return e.what();
}

static void prefix(const char* what) {
    auto& me = cambc::self();
    std::cout << "PROBE " << cambc::round_number() << " " << cambc::to_string(me.champion_name()) << " " << what;
}

static std::string list(const cambc::bitboard& b) {
    std::string s;
    for (auto p : b.positions()) s += "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")";
    return s.empty() ? "-" : s;
}

static int group_id() { return static_cast<int>(static_cast<cambc::handle_camp_group_t>(cambc::map::camp(T1).camp_group())); }

static std::string group_state() {
    try {
        for (const auto& grp : cambc::map::camp_groups()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(grp)) != group_id()) continue;
            auto st = grp.state();
            if (std::holds_alternative<cambc::map::camp_group_alive>(st)) return "alive";
            if (std::holds_alternative<cambc::map::camp_group_reward_available>(st)) return "reward_available";
            return "respawning:" + std::to_string(std::get<cambc::map::camp_group_respawning>(st).timer);
        }
    } catch (const std::exception&) { return "unseen"; }
    return "?";
}

static bool group_cleared() { const auto s = group_state(); return s == "reward_available" || s.rfind("respawning", 0) == 0; }

static cambc::bitboard blocked_tiles(const cambc::bitboard& allowed) {
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | cambc::vision::teleport_tiles() | (group_tiles() & ~allowed);
    blocked.set(cambc::self().position(), false);
    return blocked;
}

// One step toward the nearest free goal tile; group tiles are avoided unless they are goals.
static bool step_towards(cambc::bitboard goals) {
    auto& me = cambc::self();
    if (!me.can_move() || goals.is_set(me.position())) return false;
    const auto blocked = blocked_tiles(goals);
    goals &= ~blocked;
    if (goals.is_empty()) return false;
    cambc::distance_field field;
    cambc::bitboard visited;
    field.compute_to(blocked & ~goals, goals, around(me.position(), 0), visited);
    auto step = me.position();
    for (auto tile : blocked.reachable_tiles(step, me.base_stats().base_move_speed).positions())
        if (field.get(tile) < field.get(step)) step = tile;
    return step != me.position() && me.move_absolute(step);
}

static void act(const char* what, vec2 to, bool dash) {
    auto& me = cambc::self();
    std::string res;
    try { res = (dash ? me.abilities()[1].use(to) : me.move_absolute(to)) ? "ok" : "false"; }
    catch (const std::exception& e) { res = err_str(e); }
    prefix(what);
    std::cout << " to=(" << to.x << "," << to.y << ") res=" << res << " pos=(" << me.position().x << "," << me.position().y
              << ") on_group_ally=" << list(cambc::vision::champion_tiles(team::ally) & group_tiles())
              << " on_group_enemy=" << list(cambc::vision::champion_tiles(team::enemy) & group_tiles()) << '\n';
}

static vec2 free_next_to(vec2 t) {
    auto c = around(t, 1) & ~group_tiles() & ~blocked_tiles(cambc::bitboard{});
    for (auto p : c.positions()) return p;
    return t;
}

static void attack_group() {
    auto& me = cambc::self();
    cambc::bitboard goals; goals.clear();
    for (const auto& c : cambc::vision::camps()) {
        if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(c.camp_group())) != group_id()) continue;
        if (me.can_attack() && me.attack_tiles().is_set(c.position())) { me.attack(c); return; }
        goals |= around(c.position(), me.attack_range());
    }
    if (goals.is_empty()) goals = around(T1, me.attack_range());
    step_towards(goals & ~group_tiles());
}

static int hold_start() { return static_cast<std::uint8_t>(cambc::shared_memory[0]) | (static_cast<std::uint8_t>(cambc::shared_memory[1]) << 8); }

struct Bot {
    int phase = 0;
    bool init = false;
    std::uint32_t gold0 = 0, gems0 = 0;
    int seen = 0;

    void log_turn() {
        auto& me = cambc::self();
        prefix("turn");
        std::cout << " id=" << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me)) << " pos=(" << me.position().x << ","
                  << me.position().y << ") gold=" << me.gold_count() << " gems=" << me.gem_count() << " phase=" << phase
                  << " H=" << hold_start() << " grp=" << group_state()
                  << " on_group_ally=" << list(cambc::vision::champion_tiles(team::ally) & group_tiles())
                  << " on_group_enemy=" << list(cambc::vision::champion_tiles(team::enemy) & group_tiles()) << '\n';
        if (me.gold_count() != gold0 || me.gem_count() != gems0) {
            prefix("reward");
            std::cout << " dgold=" << static_cast<int>(me.gold_count()) - static_cast<int>(gold0)
                      << " dgems=" << static_cast<int>(me.gem_count()) - static_cast<int>(gems0) << " H=" << hold_start()
                      << " since_H=" << static_cast<int>(cambc::round_number()) - hold_start() << '\n';
            gold0 = me.gold_count(); gems0 = me.gem_count();
        }
    }

    // X: Vendetta. phase 0 kill, 1 go to T1, 2 wait for H+D, 3 done.
    void play_x() {
        auto& me = cambc::self();
        const int r = static_cast<int>(cambc::round_number());
        if (phase == 0) { if (!group_cleared()) { attack_group(); return; } phase = 1; }
        if (phase == 1) {
            if (me.position() != T1) step_towards(tiles({T1}));
            if (me.position() == T1) {
                cambc::shared_memory[0] = static_cast<std::uint8_t>(r & 255);
                cambc::shared_memory[1] = static_cast<std::uint8_t>(r >> 8);
                prefix("on_T1"); std::cout << " H=" << r << " expect_old=" << r + 6 << " expect_reset=" << r + D + 6 << '\n';
                phase = 2;
            }
            return;
        }
        if (phase == 2 && r == hold_start() + D) {
            phase = 3;
            switch (SCENARIO) {
            case 2: case 6: act("x_step_off", free_next_to(T1), false); break;
            case 3: act("x_step_off", free_next_to(T1), false); act("x_dash_back", T1, true); break;
            case 4: act("x_step_within", T3, false); break;
            default: prefix("x_stay"); std::cout << '\n';
            }
        }
    }

    // Y: Varg. phase 0 kill, 1 wait next to T2, 2 done.
    void play_y() {
        auto& me = cambc::self();
        const int r = static_cast<int>(cambc::round_number());
        if (SCENARIO == 6 && !init) { me.set_priority(1); prefix("priority"); std::cout << " 1\n"; }
        if (phase == 0) { if (!group_cleared()) { attack_group(); return; } phase = 1; }
        if (SCENARIO != 2 && SCENARIO != 6) { step_towards(tiles({PARK})); return; }
        if (phase == 1) {
            const auto wait = around(T2, 1) & ~group_tiles();
            if (!wait.is_set(me.position())) step_towards(wait);
            if (hold_start() && r == hold_start() + D) { act("y_step_on", T2, false); phase = 2; }
        }
    }

    void play_other() {
        if (phase == 0) { if (!group_cleared()) { attack_group(); return; } phase = 1; }
        step_towards(tiles({{PARK.x + 1, PARK.y}}));
    }

    // B's Vendetta in scenario 5: wait next to T2; after seeing an enemy on a group tile on 2 own turns, step on and dash off.
    void play_enemy() {
        auto& me = cambc::self();
        if (SCENARIO != 5 || me.champion_name() != champion_type::vendetta) return;
        const auto wait = tiles({{13, 19}});
        if (phase == 0) {
            if (!wait.is_set(me.position())) { step_towards(wait); return; }
            const auto on = cambc::vision::champion_tiles(team::enemy) & group_tiles();
            if (group_cleared() && !on.is_empty()) ++seen;
            if (seen >= 2) {
                act("e_step_on", T2, false);
                act("e_dash_off", {14, 19}, true);
                phase = 1;
            }
        }
    }

    void play_turn() {
        auto& me = cambc::self();
        log_turn();
        if (me.is_alive()) {
            if (SIDE == 1) play_enemy();
            else if (me.champion_name() == champion_type::vendetta) play_x();
            else if (me.champion_name() == champion_type::varg) play_y();
            else play_other();
        }
        init = true;
    }
};

static void play_draft() {
    using cambc::champion_draft;
    const champion_draft order[3] = {champion_draft::vendetta, champion_draft::varg, champion_draft::ryth};
    cambc::draft::pick(order[cambc::round_number()]);
}

int main() {
    Bot bot;
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else bot.play_turn();
        } catch (const std::exception& error) {
            std::cout << "PROBE " << cambc::round_number() << " err " << err_str(error) << '\n';
        } catch (...) {
            std::cout << "PROBE err unknown\n";
        }
        cambc::end_turn();
    }
}
