// probe-denial: respawn denial (a champion on a respawning group's camp tile) and tribute timing (a capture paying
// into a bag mid-tribute). Shared source with probe-denial-b (team B); run.sh copies it there and sets SIDE=1.
//   bash rules-verification/probes/probe-denial/run.sh <scenario> [rounds]     (map probe-denial/denial.map26a)
// Both teams draft Vendetta (A id 0 = X, B id 3 = E), Varg (Y), Stellar (Z). Team A coordinates (see makemap.mjs).
// Respawn: A kills R = wolf T1 (8,5) + gold cluster T2 (9,5) (respawn 50); X captures alone on T1 (payout P).
//   1  X stays on T1 until P+90, then steps off to (8,4) and stays there.
//   2  X steps off at P; B's E (non-capturing team) walks onto T2 from P+1, stays until P+90, steps off to (10,6).
//   3  X stays until P+20 (occupied only before the group is due).
//   4  X stays until P+49 (leaves in the last round before it is due).
//   5  X stays until the first odd round L >= P+70 (A acts first), then steps off; E, waiting on (10,6),
//      steps onto T2 later in round L (the tiles are empty between two turns, never at a round start);
//      E leaves at L+20.
// Tribute (altar (14,8), Q = gem cluster (15,8) next to it): A kills a prep group, then Q; X steps onto Q in round H
// (payout at H+6) and starts a tribute at the altar:
//   11 bag 8 (PSMALL split three ways), tribute started at H+5: channel 1, completes at H+6 turn start.
//   12 bag 72 (PBIG alone), tribute started at H in the same turn as the step-on: channel 8, payout mid-channel.
//   13 bag 8, tribute started at H+4: completes at H+5, one round before the payout (control).
// Camp target tie-break:
//   6  A's Varg (id 1, priority 1: acts before id 0) waits on (6,7), B's Vendetta (id 3; B acts first in even rounds)
//      on (10,7); then A's Vendetta (id 0) hits wolf T1 once from (7,4) and moves to (6,3). All three are diagonal
//      Chebyshev 2 from the wolf. Lowest id: id 0 hit every round; turn order: id 1 in odd rounds, id 3 in even.
#include <cambc.h>
#include <iostream>
#include <string>
#include <variant>
#include "scenario.h"
#include "side.h"

using cambc::vec2;
using cambc::team;
using cambc::champion_type;
using cambc::champion_state;

const vec2 T1{8, 5}, T2{9, 5};
const vec2 X_OFF{8, 4}, E_WAIT{13, 7}, E_NEXT{10, 6};
const vec2 ALTAR{14, 8}, Q{15, 8};
const vec2 PSMALL[3] = {{4, 9}, {5, 9}, {6, 9}};
const vec2 PBIG[3] = {{4, 13}, {5, 13}, {6, 13}};
const vec2 PARK_Y{3, 5}, PARK_Z{3, 4}, PARK_Y2{17, 6}, PARK_Z2{17, 4};
constexpr bool TRIBUTE = SCENARIO >= 11;

static cambc::bitboard tiles(std::initializer_list<vec2> ps) { cambc::bitboard b; b.clear(); for (auto p : ps) b.set(p); return b; }
static cambc::bitboard around(vec2 p, int r) { cambc::bitboard b; b.clear(); b.draw_chebyshev(p, r); return b; }

static std::string err_str(const std::exception& e) {
    if (auto* ge = dynamic_cast<const cambc::error*>(&e)) return cambc::to_string(ge->code());
    return e.what();
}

static int rnd() { return static_cast<int>(cambc::round_number()); }

static void prefix(const char* what) {
    std::cout << "PROBE " << rnd() << " " << cambc::to_string(cambc::self().champion_name()) << " " << what;
}

static std::string pos_str(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }

static std::string list(const cambc::bitboard& b) {
    std::string s;
    for (auto p : b.positions()) s += pos_str(p);
    return s.empty() ? "-" : s;
}

static const cambc::bitboard& all_group_tiles() {
    static cambc::bitboard g = [] {
        cambc::bitboard b; b.clear();
        for (const auto& grp : cambc::map::camp_groups()) b |= grp.spawn_tiles();
        return b;
    }();
    return g;
}

static int group_of(vec2 p) { return static_cast<int>(static_cast<cambc::handle_camp_group_t>(cambc::map::camp(p).camp_group())); }

static std::string group_state(vec2 member) {
    try {
        for (const auto& grp : cambc::map::camp_groups()) {
            if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(grp)) != group_of(member)) continue;
            auto st = grp.state();
            if (std::holds_alternative<cambc::map::camp_group_alive>(st)) return "alive";
            if (std::holds_alternative<cambc::map::camp_group_reward_available>(st)) return "reward_available";
            return "respawning:" + std::to_string(std::get<cambc::map::camp_group_respawning>(st).timer);
        }
    } catch (const std::exception&) { return "unseen"; }
    return "?";
}

static int respawn_timer(vec2 member) {
    const auto s = group_state(member);
    return s.rfind("respawning:", 0) == 0 ? std::stoi(s.substr(11)) : -1;
}

static bool cleared(vec2 member) { const auto s = group_state(member); return s == "reward_available" || s.rfind("respawning", 0) == 0; }

static std::string camp_on(vec2 p) {
    try {
        if (!cambc::vision::has_camp(p)) return "none";
        auto c = cambc::vision::camp_at(p);
        auto st = c.state();
        return std::string(st.is_awake() ? "awake" : st.is_alive() ? "asleep" : "dead") + ":" + std::to_string(static_cast<int>(c.health()));
    } catch (const std::exception& e) { return err_str(e); }
}

static cambc::bitboard blocked_tiles(const cambc::bitboard& allowed) {
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles()
        | cambc::vision::camp_tiles() | (all_group_tiles() & ~allowed);
    blocked.set(cambc::self().position(), false);
    return blocked;
}

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

static void go(vec2 to) { step_towards(tiles({to})); }

static void act_move(const char* what, vec2 to) {
    auto& me = cambc::self();
    std::string res;
    try { res = me.move_absolute(to) ? "ok" : "false"; } catch (const std::exception& e) { res = err_str(e); }
    prefix(what);
    std::cout << " to=" << pos_str(to) << " res=" << res << " pos=" << pos_str(me.position()) << '\n';
}

// Attack the group containing `member`; approach within attack range without stepping on group tiles.
static void attack_group(vec2 member) {
    auto& me = cambc::self();
    const int gid = group_of(member);
    cambc::bitboard goals; goals.clear();
    for (const auto& c : cambc::vision::camps()) {
        if (static_cast<int>(static_cast<cambc::handle_camp_group_t>(c.camp_group())) != gid) continue;
        if (me.can_attack() && me.attack_tiles().is_set(c.position())) { me.attack(c); return; }
        goals |= around(c.position(), me.attack_range());
    }
    if (goals.is_empty()) goals = around(member, me.attack_range());
    step_towards(goals & ~all_group_tiles());
}

static void store(int slot, int v) {
    cambc::shared_memory[2 * slot] = static_cast<std::uint8_t>(v & 255);
    cambc::shared_memory[2 * slot + 1] = static_cast<std::uint8_t>(v >> 8);
}
static int load(int slot) {
    return static_cast<std::uint8_t>(cambc::shared_memory[2 * slot]) | (static_cast<std::uint8_t>(cambc::shared_memory[2 * slot + 1]) << 8);
}
// slots: 0 H (step-on round), 1 P (payout round), 2 prep paid, 3 Q cleared

struct Bot {
    int phase = 0;
    std::uint32_t gold0 = 0, gems0 = 0;
    float hp0 = -1;
    int left = 0, e_on = 0, e_off = 0, p_seen = 0;

    void log_turn() {
        auto& me = cambc::self();
        prefix("turn");
        std::cout << " pos=" << pos_str(me.position()) << " hp=" << me.health() << " gold=" << me.gold_count() << " gems=" << me.gem_count();
        const auto st = me.state();
        if (st.contains(champion_state::submitting_gems)) {
            std::cout << " tribute_ch=";
            try { std::cout << me.remaining_channel_time(); } catch (const std::exception& e) { std::cout << err_str(e); }
        }
        std::cout << " subA=" << cambc::global_submitted_gems(SIDE == 0 ? team::ally : team::enemy)
                  << " H=" << load(0) << " P=" << load(1);
        if (TRIBUTE) std::cout << " Q=" << group_state(Q) << " Qcamp=" << camp_on(Q);
        else std::cout << " R=" << group_state(T1) << " T1=" << camp_on(T1) << " T2=" << camp_on(T2);
        std::cout << " on_ally=" << list(cambc::vision::champion_tiles(team::ally) & all_group_tiles())
                  << " on_enemy=" << list(cambc::vision::champion_tiles(team::enemy) & all_group_tiles()) << '\n';
        if (me.gold_count() != gold0 || me.gem_count() != gems0) {
            prefix("delta");
            std::cout << " dgold=" << static_cast<int>(me.gold_count()) - static_cast<int>(gold0)
                      << " dgems=" << static_cast<int>(me.gem_count()) - static_cast<int>(gems0) << '\n';
        }
        if (hp0 >= 0 && me.health() != hp0) { prefix("hp_change"); std::cout << " from=" << hp0 << " to=" << me.health() << '\n'; }
        gold0 = me.gold_count(); gems0 = me.gem_count(); hp0 = me.health();
    }

    void submit(const char* what) {
        auto& me = cambc::self();
        std::string res = "ok";
        try { me.submit_gems(ALTAR); } catch (const std::exception& e) { res = err_str(e); }
        prefix(what);
        std::cout << " gems=" << me.gem_count() << " res=" << res;
        try { std::cout << " ch=" << me.remaining_channel_time(); } catch (const std::exception& e) { std::cout << " ch=" << err_str(e); }
        std::cout << '\n';
    }

    // ---- respawn scenarios, team A
    void respawn_x() {
        auto& me = cambc::self();
        const int r = rnd();
        if (phase == 0) { if (!cleared(T1)) { attack_group(T1); return; } phase = 1; }
        if (phase == 1) {
            if (me.position() != T1) go(T1);
            if (me.position() == T1) { store(0, r); prefix("on_T1"); std::cout << " H=" << r << '\n'; phase = 2; }
            return;
        }
        if (phase == 2) {
            if (me.gold_count() > 0) { store(1, r); prefix("paid"); std::cout << " P=" << r << " due=" << r + 50 << '\n'; phase = 3; }
            else return;
        }
        if (phase == 3) {
            const int P = load(1);
            int leave = SCENARIO == 1 ? P + 90 : SCENARIO == 2 ? P : SCENARIO == 3 ? P + 20 : SCENARIO == 4 ? P + 49 : P + 70;
            if (SCENARIO == 5 && (leave & 1) == 0) ++leave;
            if (r == leave) { act_move("x_step_off", X_OFF); left = r; phase = 4; }
        }
    }

    void respawn_other(vec2 park) {
        if (phase == 0) { if (!cleared(T1)) { attack_group(T1); return; } phase = 1; }
        go(park);
    }

    // ---- respawn scenarios, team B's Vendetta (E)
    void respawn_e() {
        auto& me = cambc::self();
        const int r = rnd();
        if (SCENARIO != 2 && SCENARIO != 5) return;
        const int t = respawn_timer(T1);
        if (!p_seen && t > 0) { p_seen = r - (50 - t); prefix("e_sees_respawning"); std::cout << " timer=" << t << " P=" << p_seen << '\n'; }
        if (!p_seen) { go(E_WAIT); return; }
        const int P = p_seen;
        if (SCENARIO == 2) {
            if (!e_on) {
                if (r >= P + 1) {
                    if (me.position() == T2) { e_on = r; prefix("e_on_T2"); std::cout << " round=" << r << '\n'; }
                    else go(T2);
                    if (me.position() == T2 && !e_on) { e_on = r; prefix("e_on_T2"); std::cout << " round=" << r << '\n'; }
                }
                return;
            }
            if (!e_off && r == P + 90) { act_move("e_step_off", E_NEXT); e_off = r; }
            return;
        }
        // scenario 5
        if (!e_on) {
            if (me.position() != E_NEXT) { go(E_NEXT); return; }
            const bool x_on = (cambc::vision::champion_tiles(team::enemy) & tiles({T1, T2})).is_empty() == false;
            if (r >= P + 70 && !x_on) { act_move("e_step_on_T2", T2); if (me.position() == T2) e_on = r; }
            else if (r >= P + 70) { prefix("e_waits_x_on"); std::cout << '\n'; }
            return;
        }
        if (!e_off && r == e_on + 20) { act_move("e_step_off", E_NEXT); e_off = r; }
    }

    // ---- tribute scenarios, team A
    void tribute_x() {
        auto& me = cambc::self();
        const int r = rnd();
        const vec2* prep = SCENARIO == 12 ? PBIG : PSMALL;
        if (phase == 0) { if (!cleared(prep[0])) { attack_group(prep[0]); return; } phase = 1; }
        if (phase == 1) {
            if (me.gem_count() > 0) { store(2, 1); phase = 2; }
            else { go(prep[0]); return; }
        }
        if (phase == 2) { if (!cleared(Q)) { attack_group(Q); return; } phase = 3; }
        if (phase == 3) {
            if (me.position() != Q) go(Q);
            if (me.position() == Q) {
                store(0, r);
                prefix("on_Q"); std::cout << " H=" << r << " payout_expected=" << r + 6 << '\n';
                phase = 4;
                if (SCENARIO == 12) submit("tribute_start_same_turn");
            }
            return;
        }
        if (phase == 4) {
            const int H = load(0);
            if ((SCENARIO == 11 && r == H + 5) || (SCENARIO == 13 && r == H + 4)) submit("tribute_start");
        }
    }

    void tribute_other(int idx, vec2 park) {
        auto& me = cambc::self();
        const vec2* prep = SCENARIO == 12 ? PBIG : PSMALL;
        if (phase == 0) { if (!cleared(prep[0])) { attack_group(prep[0]); return; } phase = 1; }
        if (phase == 1) {
            if (SCENARIO == 12) { if (load(2)) phase = 2; else { go(PARK_Y); return; } }
            else if (me.gem_count() > 0) phase = 2;
            else { go(prep[idx]); return; }
        }
        if (phase == 2) { if (!cleared(Q)) { attack_group(Q); return; } phase = 3; }
        go(park);
    }

    void tie_break() {
        auto& me = cambc::self();
        const auto n = me.champion_name();
        if (SIDE == 1) { if (n == champion_type::vendetta) go({10, 7}); return; }
        if (n == champion_type::varg) {
            if (phase == 0) { me.set_priority(1); phase = 1; prefix("priority"); std::cout << " 1\n"; }
            go({6, 7});
            return;
        }
        if (n != champion_type::vendetta) return;
        const bool ready = cambc::vision::has_champion({6, 7}) && cambc::vision::has_champion({10, 7});
        if (phase == 0) { if (ready && me.position() == vec2{4, 2}) phase = 1; else { go({4, 2}); return; } }
        if (phase == 1) {
            if (me.position() != vec2{7, 4}) { go({7, 4}); return; }
            me.attack(cambc::vision::camp_at(T1)); prefix("woke_wolf"); std::cout << '\n'; phase = 2; return;
        }
        if (phase == 2) { act_move("x_to_post", {6, 3}); phase = 3; }
    }

    void play_turn() {
        auto& me = cambc::self();
        log_turn();
        if (!me.is_alive()) return;
        if (SCENARIO == 6) { tie_break(); return; }
        const auto n = me.champion_name();
        if (SIDE == 1) { if (!TRIBUTE && n == champion_type::vendetta) respawn_e(); return; }
        if (TRIBUTE) {
            if (n == champion_type::vendetta) tribute_x();
            else if (n == champion_type::varg) tribute_other(1, PARK_Y2);
            else tribute_other(2, PARK_Z2);
        } else {
            if (n == champion_type::vendetta) respawn_x();
            else respawn_other(n == champion_type::varg ? PARK_Y : PARK_Z);
        }
    }
};

static void play_draft() {
    using cambc::champion_draft;
    const champion_draft order[3] = {champion_draft::vendetta, champion_draft::varg, champion_draft::stellar};
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
