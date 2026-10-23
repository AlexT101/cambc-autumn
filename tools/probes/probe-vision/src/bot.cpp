// probe-vision: rules probes for vision, wards, information hiding and teleport crystals.
// Select the scenario with SCEN below, rebuild, then run against probe-vision-b (passive unless noted):
//   SCEN 0 any map      : dump constants + ASCII map (# wall, " bush, o hole, A altar, S/E spawns, c camp).
//   SCEN 1 map corners  : vision shape, ward placement legality/range/cooldown/lifetime, sharing, death.
//   SCEN 2 map corners  : farm gold clusters, buy teleport crystals, test destinations/channel/occupancy.
//   SCEN 3 map corners  : hidden-blocker reveal (tile_reveal_rounds) and attacking from a bush; needs probe-vision-b BSCEN 1.
//   SCEN 4 map corners  : ward on own/ally-ward/enemy-spawn/enemy-ward tiles, double place, ward while dead,
//                         crystal onto ally / hidden enemy / tile an enemy then tries to enter; needs BSCEN 2.
// SCEN 1 and 2 were run with probe-vision-b BSCEN 0 (passive).
// Commands (all with --fuel 20000000 so long logging turns are never suspended):
//   cambc run probe-vision probe-vision-b --map corners --rounds 250 --fuel 20000000 -o <dir>   (SCEN 1, BSCEN 0)
//   rounds: SCEN 2 -> 200, SCEN 3 -> 50, SCEN 4 -> 130.  Logs: unzip <dir>/*.repl26a, grep PROBE/GRID team-a.stdout.
// Every logged value is read from the engine. Line format: PROBE <round> <champion> key=value ...
#include <cambc.h>
#include "bot.h"
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#ifndef SCEN
#define SCEN 4
#endif

using cambc::vec2; using cambc::team; using cambc::bitboard;
namespace m = cambc::map; namespace v = cambc::vision;

static std::string P(vec2 p) { return "(" + std::to_string(p.x) + "," + std::to_string(p.y) + ")"; }
static std::string name() { return cambc::to_string(cambc::self().champion_name()); }
static int R() { return (int)cambc::round_number(); }
static void L(const std::string& s) { std::cout << "PROBE " << R() << " " << name() << " " << s << '\n'; }

// Run an engine call and describe its outcome: value, or err:<code>, or exc:<what>.
static std::string T(const std::function<std::string()>& f) {
    try { return f(); }
    catch (const cambc::error& e) { return "err:" + cambc::to_string(e.code()); }
    catch (const std::exception& e) { return std::string("exc:") + e.what(); }
}
static std::string B(bool b) { return b ? "true" : "false"; }

// ASCII grid around c. Visible: v open, W wall, B bush, O hole, A altar. Hidden: lowercase / '.'.
// '@' = self, 'X' = a tile in `mark`.
static void grid(const std::string& tag, vec2 c, int r, const bitboard& vis, const bitboard* mark = nullptr) {
    for (int dy = -r; dy <= r; ++dy) {
        std::string row;
        for (int dx = -r; dx <= r; ++dx) {
            vec2 p{c.x + dx, c.y + dy};
            if (!m::is_in_bounds(p)) { row += ' '; continue; }
            bool s = vis.is_set(p); char ch;
            if (m::walls().is_set(p)) ch = s ? 'W' : 'w';
            else if (m::bushes().is_set(p)) ch = s ? 'B' : 'b';
            else if (m::holes().is_set(p)) ch = s ? 'O' : 'o';
            else if (m::altars().is_set(p)) ch = s ? 'A' : 'a';
            else ch = s ? 'v' : '.';
            if (mark && mark->is_set(p)) ch = 'X';
            if (p == cambc::self().position()) ch = '@';
            row += ch;
        }
        std::cout << "GRID " << R() << " " << name() << " " << tag << " " << (dy >= 0 ? "+" : "") << dy << " " << row << '\n';
    }
}

static void dump_map() {
    namespace k = cambc::constants; const auto& gs = cambc::detail::cached_game_settings;
    std::cout << "PROBE 0 const w=" << m::width() << " h=" << m::height() << " team=" << cambc::champions(team::ally).size()
      << " active_wards=" << k::active_wards << " ward_charges=" << gs.ward_charges
      << " tile_reveal_rounds=" << k::tile_reveal_rounds << " ward_cooldown=" << k::ward_cooldown
      << " ward_lifetime=" << k::ward_lifetime << " ward_vision_radius=" << k::ward_vision_radius
      << " ward_placement_radius=" << k::ward_placement_radius
      << " cw_vis=" << gs.control_ward_vision_radius << " cw_place=" << gs.control_ward_placement_radius
      << " tp_crystal_time=" << k::tp_crystal_time << " passive_gold=" << k::passive_gold
      << " tp_cost=" << cambc::consumable_type::tp_crystal.cost()
      << " tp_limit=" << cambc::consumable_type::tp_crystal.carry_limit() << '\n';
    bitboard camps; camps.clear();
    for (auto& g : m::camp_groups()) for (auto& c : g) {
        camps.set(c.spawn_position());
        std::cout << "PROBE 0 camp pos=" << P(c.spawn_position()) << " kind=" << (int)static_cast<cambc::camp_type>(c.kind()) << '\n';
    }
    std::vector<std::string> g(m::height(), std::string(m::width(), '.'));
    auto put = [&](const bitboard& b, char ch) { for (auto p : b.positions()) g[p.y][p.x] = ch; };
    put(m::spawn_region(team::ally), 'S'); put(m::spawn_region(team::enemy), 'E');
    put(m::altars(), 'A'); put(m::holes(), 'o'); put(m::bushes(), '"'); put(m::walls(), '#'); put(camps, 'c');
    for (int y = 0; y < m::height(); ++y)
        std::cout << "MAP " << (y < 10 ? "0" : "") << y << " " << g[y] << '\n';
}

// ---- shared helpers ------------------------------------------------------------------------
static bool at(vec2 p) { return cambc::self().position() == p; }
static void go(vec2 p) {
    auto& me = cambc::self();
    if (!at(p) && me.can_move()) { auto r = T([&] { return B(me.move_towards(p)); }); if (r != "true") L("move_to=" + P(p) + " r=" + r); }
}
static std::string wardinfo() {
    auto& me = cambc::self(); std::ostringstream o;
    o << "cd=" << T([&] { return std::to_string(me.ward_cooldown()); }) << " mine=[";
    for (auto p : me.ward_positions()) o << P(p);
    o << "] visible_wards=[";
    for (auto& w : v::wards()) o << P(w.position()) << (w.is_ally() ? "a" : "e") << ":" << (w.remaining_time() ? std::to_string(*w.remaining_time()) : "inf");
    o << "] myvis=" << me.visible_tiles().count() << " teamvis=" << v::visible_tiles().count();
    return o.str();
}
// Try a ward at `t`, logging terrain/visibility of the tile and the result.
static std::string place(vec2 t) {
    auto& me = cambc::self();
    const bool vb = me.visible_tiles().is_set(t), ob = me.visible_tiles_from(me.position()).is_set(t);
    std::string r = T([&] { return B(me.place_ward(t)); });
    L("place_ward t=" + P(t) + " off=" + P(t - me.position()) + " visible_before=" + B(vb) + " own_vis_before=" + B(ob)
      + " wall=" + B(m::walls().is_set(t)) + " bush=" + B(m::bushes().is_set(t)) + " hole=" + B(m::holes().is_set(t))
      + " altar=" + B(m::altars().is_set(t)) + " r=" + r + " " + wardinfo());
    return r;
}

struct Task { vec2 stand; std::vector<vec2> targets; };

// ---- SCEN 1 (corners) ------------------------------------------------------------------------
static vec2 last_ward{-1, -1};
static int stage = 0, stage_round = 0;
static size_t task_i = 0;

// idx0 vesper: vision shape, placement range, cooldown cadence, ward vision shape, lifetime.
static void s1_vesper() {
    auto& me = cambc::self(); const vec2 A{20, 40};
    if (R() == 1) { grid("spawn", me.position(), 9, me.visible_tiles()); L("myvis=" + std::to_string(me.visible_tiles().count()) + " " + wardinfo()); }
    if (stage == 0) { go(A); if (at(A)) { stage = 1; } else return; }
    if (stage == 1) {
        bitboard ch; ch.clear(); ch.draw_chebyshev(A, 8); bitboard ci; ci.clear(); ci.draw_circle(A, 8);
        L("open_vision count=" + std::to_string(me.visible_tiles().count()) + " cheb8=" + std::to_string(ch.count())
          + " circle8=" + std::to_string(ci.count()) + " eq_cheb=" + B(me.visible_tiles() == ch) + " eq_circle=" + B(me.visible_tiles() == ci));
        grid("open", A, 9, me.visible_tiles());
        for (vec2 o : {vec2{3, 0}, vec2{0, 3}, vec2{3, 3}, vec2{-3, 1}}) place(A + o);
        if (place(A + vec2{2, 2}) == "true") last_ward = A + vec2{2, 2};
        stage = 2; stage_round = R(); return;
    }
    if (stage == 2) { // try every round at a new tile for 6 rounds
        static const vec2 offs[] = {{-2, -2}, {2, -2}, {-2, 2}, {2, 0}, {0, 2}, {-1, 1}};
        int k = R() - stage_round - 1;
        L("round_start " + wardinfo());
        vec2 t = A + offs[k];
        if (place(t) == "true") last_ward = t;
        if (k == 5) { stage = 3; }
        return;
    }
    if (stage == 3) { // walk far away, then isolate the ward's contribution
        const vec2 F{5, 27};
        go(F); if (!at(F)) return;
        auto team_vis = v::visible_tiles(), mine = me.visible_tiles_from(me.position());
        auto ward_only = team_vis & ~mine;
        auto hyp = cambc::ward::visible_tiles_from(last_ward);
        bitboard ch; ch.clear(); ch.draw_chebyshev(last_ward, 6); bitboard ci; ci.clear(); ci.draw_circle(last_ward, 6);
        L("ward_vision ward=" + P(last_ward) + " team_vis=" + std::to_string(team_vis.count()) + " mine=" + std::to_string(mine.count())
          + " ward_only=" + std::to_string(ward_only.count()) + " hyp=" + std::to_string(hyp.count())
          + " team_minus_mine_eq_hyp_minus_mine=" + B(ward_only == (hyp & ~mine)) + " cheb6=" + std::to_string(ch.count())
          + " circle6=" + std::to_string(ci.count()) + " hyp_eq_cheb6=" + B(hyp == ch) + " hyp_eq_circle6=" + B(hyp == ci)
          + " " + wardinfo());
        bitboard wm; wm.clear(); wm.set(last_ward);
        grid("wardview", last_ward, 7, team_vis, &wm);
        stage = 4; return;
    }
    if (stage == 4 && R() % 25 == 0) L("persist " + wardinfo());
}

// idx1 ren: stays on spawn; what can it see/read of out-of-vision allies, enemies, camps and wards?
static void s1_ren() {
    auto& me = cambc::self();
    if (R() != 1 && R() != 20 && R() != 40 && R() != 80) return;
    std::ostringstream o;
    o << "share myvis=" << me.visible_tiles().count() << " teamvis=" << v::visible_tiles().count()
      << " vis_allies=" << v::champions(team::ally).size() << " vis_enemies=" << v::champions(team::enemy).size()
      << " ally_ward_tiles=" << v::ward_tiles(team::ally).count() << " wards=" << v::wards().size();
    L(o.str());
    for (auto side : {team::ally, team::enemy}) {
        for (auto& c : cambc::champions(side)) {
            if (c == me) continue;
            L(std::string(side == team::ally ? "ally" : "enemy") + " is_visible=" + T([&] { return B(c.is_visible()); })
              + " name=" + T([&] { return cambc::to_string(c.champion_name()); })
              + " pos=" + T([&] { return P(c.position()); }) + " hp=" + T([&] { return std::to_string(c.health()); })
              + " alive=" + T([&] { return B(c.is_alive()); }) + " gems=" + T([&] { return std::to_string(c.gem_count()); })
              + " state=" + T([&] { return std::to_string(c.state().bits()); })
              + " vis_tiles=" + T([&] { return std::to_string(c.visible_tiles().count()); })
              + " wardpos=" + T([&] { return std::to_string(c.ward_positions().size()); }));
            if (side == team::enemy) break; // one enemy is enough
        }
    }
    auto camp = m::camp({60, 41});
    L("far_camp spawn=(60,41) is_visible=" + T([&] { return B(camp.is_visible()); }) + " hp=" + T([&] { return std::to_string(camp.health()); })
      + " pos=" + T([&] { return P(camp.position()); }) + " group_state=" + T([&] { return std::to_string(camp.camp_group().state().index()); })
      + " has_camp=" + T([&] { return B(v::has_camp({60, 41})); }));
}

// idx2 varg / idx3 marcella / idx4 willow: placement on special tiles, then ward vision from those tiles.
static void run_tasks(const std::vector<Task>& tasks, vec2 away) {
    auto& me = cambc::self();
    if (task_i < tasks.size()) {
        const auto& t = tasks[task_i];
        go(t.stand); if (!at(t.stand)) return;
        if (stage_round == 0) { grid("task" + std::to_string(task_i) + "_own", t.stand, 9, me.visible_tiles_from(t.stand)); grid("task" + std::to_string(task_i) + "_eff", t.stand, 9, me.visible_tiles()); stage_round = R(); }
        if (me.ward_cooldown() != 0) { L("waiting " + wardinfo()); return; }
        for (auto p : t.targets) if (place(p) == "true") { last_ward = p; break; }
        ++task_i; stage_round = 0; return;
    }
    if (stage == 0) {
        go(away); if (!at(away)) return;
        auto team_vis = v::visible_tiles(), ward_only = team_vis & ~me.visible_tiles_from(me.position());
        auto hyp = last_ward.x >= 0 ? cambc::ward::visible_tiles_from(last_ward) : bitboard{};
        L("ward_vision ward=" + P(last_ward) + " ward_only=" + std::to_string(ward_only.count()) + " hyp=" + std::to_string(hyp.count())
          + " " + wardinfo());
        bitboard wm; wm.clear(); if (last_ward.x >= 0) wm.set(last_ward);
        grid("wardview", last_ward, 7, team_vis, &wm);
        stage = 1;
    }
}

static void s1_varg() {
    run_tasks({{{15, 33}, {{14, 33}, {15, 33}}},             // ally-occupied tile (ren), own tile
               {{33, 34}, {{35, 34}, {34, 32}, {33, 36}}},    // altar, gem-camp tile, open
               {{33, 27}, {{35, 27}, {35, 28}, {34, 27}}},    // bush tile from outside
               {{35, 25}, {}}},                               // stand inside the bush: grid only
              {25, 27});
}
static void s1_marcella() {
    auto& me = cambc::self();
    if (task_i < 1 || stage == 0) {
        run_tasks({{{12, 50}, {{13, 50}, {14, 50}, {14, 49}, {11, 50}}}}, {12, 44}); // wall, tiles behind wall
        if (at({12, 50}) && R() % 50 == 0) grid("wall", me.position(), 9, me.visible_tiles());
        return;
    }
    // then die to the elk at (10,53) and watch the ward
    if (stage == 1) { go({10, 52}); if (at({10, 52})) stage = 2; return; }
    if (stage >= 2) {
        bool alive = me.is_alive();
        if (alive && stage == 2) {
            for (auto& c : v::camps()) if (c.spawn_position() == vec2{10, 53} && me.can_attack()) L("attack_elk r=" + T([&] { me.attack(c); return std::string("ok"); }));
            if (R() % 5 == 0) L("fighting hp=" + std::to_string(me.health()) + " " + wardinfo());
            return;
        }
        if (!alive) stage = 3;
        if (stage == 3 && (R() % 5 == 0 || !alive))
            L("dead_or_respawned alive=" + B(alive) + " pos=" + T([&] { return P(me.position()); }) + " " + T([&] { return wardinfo(); }));
        if (alive) { stage = 4; L("respawned " + wardinfo()); }
    }
}
static void s1_willow() {
    auto& me = cambc::self();
    run_tasks({{{22, 15}, {{22, 13}, {23, 13}, {22, 14}}}}, {22, 25}); // hole tiles, then open
    if (at({22, 15}) && stage_round != 0) grid("hole", me.position(), 9, me.visible_tiles());
}

// ---- SCEN 2 (corners): earn gold at the gold clusters, buy a teleport crystal, test destinations ----
struct Tp { vec2 farm, capture, home, stand; std::vector<vec2> targets; };
static int tp_round = -1;     // round the channel started
static vec2 tp_dest{-1, -1};

static std::string tpstate() {
    auto& me = cambc::self(); std::ostringstream o;
    o << "pos=" << P(me.position()) << " teleporting=" << B(me.is_teleporting())
      << " chan=" << T([&] { return std::to_string(me.remaining_channel_time()); })
      << " crystals=" << me.consumables()[cambc::consumable_type::tp_crystal].count() << " gold=" << me.gold_count()
      << " can_move=" << B(me.can_move()) << " can_attack=" << B(me.can_attack()) << " can_cast=" << B(me.can_cast())
      << " state=" << me.state().bits() << " tps=[";
    for (auto& t : v::teleports()) o << P(t.position()) << (t.is_ally() ? "a" : "e") << ":" << t.remaining_time();
    o << "] tp_tiles=" << v::teleport_tiles().count();
    return o.str();
}

static void s2_run(const Tp& c) {
    auto& me = cambc::self();
    if (stage == 0) { // farm the gold-cluster group next to `farm`
        go(c.farm); if (!at(c.farm)) return;
        bool any = false;
        for (auto& camp : v::camps()) {
            if (!camp.is_gold_cluster() || camp.health() <= 0) continue;
            any = true;
            if (me.can_attack() && me.attack_tiles().is_set(camp.position())) { T([&] { me.attack(camp); return std::string(); }); break; }
        }
        if (!any) { stage = 1; L("clusters_dead " + tpstate()); }
        return;
    }
    if (stage == 1) { go(c.capture); if (me.gold_count() > 0) { stage = 2; L("captured " + tpstate()); } return; }
    if (stage == 2) {
        go(c.home); if (!m::spawn_region(team::ally).is_set(me.position())) return;
        L("buy r=" + T([&] { me.buy(cambc::consumable_type::tp_crystal); return std::string("ok"); }) + " " + tpstate());
        L("buy_again r=" + T([&] { me.buy(cambc::consumable_type::tp_crystal); return std::string("ok"); }) + " " + tpstate());
        stage = 3; return;
    }
    if (stage == 3) {
        go(c.stand); if (!at(c.stand)) return;
        grid("tp_own", c.stand, 4, me.visible_tiles_from(c.stand));
        for (auto t : c.targets) {
            const bool vb = me.visible_tiles().is_set(t);
            auto r = T([&] { return B(me.consumables()[cambc::consumable_type::tp_crystal].use(t)); });
            L("tp_use t=" + P(t) + " off=" + P(t - me.position()) + " visible_before=" + B(vb) + " wall=" + B(m::walls().is_set(t))
              + " bush=" + B(m::bushes().is_set(t)) + " hole=" + B(m::holes().is_set(t)) + " altar=" + B(m::altars().is_set(t))
              + " espawn=" + B(m::spawn_region(team::enemy).is_set(t)) + " camp=" + B(v::has_camp(t)) + " champ=" + B(v::has_champion(t))
              + " r=" + r + " " + tpstate());
            if (r == "true") { tp_round = R(); tp_dest = t; stage = 4; break; }
        }
        if (stage == 3) stage = 9;
        return;
    }
    if (stage == 4) { // channelling: log state; try other actions on a few rounds
        L("chan_start " + tpstate());
        const int k = R() - tp_round;
        if (k == 1) L("try_move r=" + T([&] { return B(me.move(vec2{0, -1})); }) + " " + tpstate());
        if (k == 1) L("try_ward r=" + T([&] { return B(me.place_ward(me.position())); }));
        if (k == 2) L("try_cancel r=" + T([&] { cambc::detail::check(cambc::detail::sdk_cancel_channel()); return std::string("ok"); }) + " " + tpstate());
        if (k == 2) L("try_attack_any r=" + T([&] { for (auto& cc : v::camps()) { me.attack(cc); return std::string("ok"); } return std::string("nocamp"); }));
        if (me.position() == tp_dest || k > 6) { L("chan_end " + tpstate()); stage = 5; }
        return;
    }
    if (stage == 5 && R() <= tp_round + 8) L("after " + tpstate());
}

static void s2_ren() { // stand next to vesper's destination and try to step onto the reserved tile
    auto& me = cambc::self(); const vec2 D{15, 50}, S{16, 50};
    go(S); if (!at(S)) return;
    if (v::teleport_tiles().count() > 0 || v::has_champion(D)) {
        L("reserve_seen has_tp=" + B(v::has_teleport(D)) + " champ_on_D=" + B(v::has_champion(D)) + " " + tpstate());
        if (stage < 3 && v::has_teleport(D)) { ++stage; L("ren_move_onto_reserved r=" + T([&] { return B(me.move_absolute(D)); }) + " pos=" + P(me.position())); }
    }
}

// ---- SCEN 3 (corners, vs probe-vision-b BSCEN 1): hidden blocker reveal + attacking from a bush ----
static std::string obs(vec2 t) {
    auto& me = cambc::self(); std::ostringstream o;
    o << "obs tile=" << P(t) << " tile_vis=" << B(me.visible_tiles().is_set(t)) << " has_champ=" << T([&] { return B(v::has_champion(t)); })
      << " enemies=[";
    for (auto& e : v::champions(team::enemy)) o << P(e.position());
    o << "] myhp=" << me.health();
    for (auto& e : cambc::champions(team::enemy)) {
        if (!e.is_visible()) continue;
        o << " | enemy " << T([&] { return cambc::to_string(e.champion_name()); }) << " pos=" << T([&] { return P(e.position()); })
          << " hp=" << T([&] { return std::to_string(e.health()); }) << " gems=" << T([&] { return std::to_string(e.gem_count()); })
          << " state=" << T([&] { return std::to_string(e.state().bits()); })
          << " its_vis=" << T([&] { return std::to_string(e.visible_tiles().count()); })
          << " items=" << T([&] { return std::to_string(e.item_count()[cambc::item_type::power_shard_of_health]); })
          << " gold=" << T([&] { return std::to_string(e.gold_count()); });
    }
    return o.str();
}
static void s3_vesper() {
    auto& me = cambc::self(); const vec2 Bt{35, 25};
    if (R() < 30) { go({33, 25}); if (R() >= 26) L(obs(Bt)); return; }
    if (R() == 30) { go({34, 25}); L(obs(Bt)); return; }
    if (R() == 44) { place(Bt); L(obs(Bt)); return; }  // ward onto the unseen enemy (after the reveal tests)
    if (R() == 34 || R() == 36) {
        L("move_into_hidden r=" + T([&] { return B(me.move_absolute(Bt)); }) + " pos=" + P(me.position()));
        L(obs(Bt)); return;
    }
    if (R() == 47) { L("step_into_bush r=" + T([&] { return B(me.move_absolute({35, 24})); })); }
    if (R() <= 50) L(obs(Bt));
}
static void s3_ren() {
    const vec2 Bt{35, 25};
    go({30, 25});
    if (R() >= 33 && R() <= 42) L(obs(Bt));
}

// ---- SCEN 4 (corners, vs probe-vision-b BSCEN 2): leftover ward + crystal edge cases ----
static void s4_varg() { // own tile, ally-ward tile, double placement in one round
    auto& me = cambc::self();
    if (R() == 2) place(me.position());
    if (R() == 3) { place({14, 32}); place({16, 32}); place({16, 34}); }
}
static void s4_ren() { // R1: ward at (14,32) for varg's test; then stand at (33,23) as an ally-occupied crystal target
    if (R() == 1) place({14, 32});
    if (R() == 2) { // raw engine camp-group state for an out-of-vision group (the SDK wrapper throws before asking)
        auto g = m::camp({60, 41}).camp_group(); std::uint32_t st = 99;
        auto code = cambc::detail::sdk_camp_group_state(static_cast<std::uint32_t>(static_cast<cambc::handle_camp_group_t>(g)), &st);
        cambc::detail::camp_state cs{}; auto code2 = cambc::detail::sdk_camp(static_cast<std::uint32_t>(static_cast<cambc::handle_camp_t>(m::camp({60, 41}))), &cs);
        L("raw_far_group_state code=" + std::to_string(code) + " state=" + std::to_string(st) + " raw_camp code=" + std::to_string(code2)
          + " vis_groups=" + std::to_string(v::camp_groups().size()) + " all_groups=" + std::to_string(m::camp_groups().size()));
    }
    go({33, 23});
}
static void s4_willow() { // enemy spawn tile and enemy-ward tile
    const vec2 S{53, 34};
    go(S); if (!at(S)) return;
    if (stage == 0) { L("enemy_wards " + wardinfo()); place({55, 34}); place({54, 33}); place({54, 35}); stage = 1; }
}
static void s4_marcella() { // die to the elk at (10,53), then try a ward while dead
    auto& me = cambc::self();
    if (stage == 0) { go({10, 52}); if (at({10, 52})) stage = 1; return; }
    if (me.is_alive()) {
        for (auto& c : v::camps()) if (c.spawn_position() == vec2{10, 53} && me.can_attack()) T([&] { me.attack(c); return std::string(); });
        return;
    }
    if (stage == 1) { stage = 2; L("dead ward_r=" + T([&] { return B(me.place_ward({10, 50})); }) + " cd=" + T([&] { return std::to_string(me.ward_cooldown()); })); L("dead_buy r=" + T([&] { me.buy(cambc::consumable_type::tp_crystal); return std::string("ok"); })); }
}

void Bot::play_turn() {
    auto& me = cambc::self();
    if (idx < 0) {
        auto allies = cambc::champions(team::ally);
        for (size_t i = 0; i < allies.size(); ++i) if (allies[i] == me) idx = (int)i;
        if (SCEN == 0 && idx == 0) dump_map();
        L("idx=" + std::to_string(idx) + " pos=" + P(me.position()) + " vis=" + std::to_string(me.visible_tiles().count())
          + " gold=" + std::to_string(me.gold_count()));
    }
    if (SCEN == 1) {
        switch (idx) { case 0: s1_vesper(); break; case 1: s1_ren(); break; case 2: s1_varg(); break;
                       case 3: s1_marcella(); break; case 4: s1_willow(); break; }
    }
    if (SCEN == 3) { if (idx == 0) s3_vesper(); if (idx == 1) s3_ren(); }
    if (SCEN == 4) {
        switch (idx) {
        case 0: s2_run({{33, 15}, {34, 15}, {13, 33}, {33, 25}, {{33, 23}, {35, 25}, {36, 25}}}); break; // ally tile, hidden enemy, open
        case 1: s4_ren(); break; case 2: s4_varg(); break; case 3: s4_marcella(); break; case 4: s4_willow(); break;
        }
    }
    if (SCEN == 2) {
        switch (idx) {
        case 0: s2_run({{33, 15}, {34, 15}, {13, 33}, {12, 50}, {{13, 50}, {16, 50}, {15, 50}, {11, 47}}}); break; // wall, out-of-range, out-of-vision
        case 1: s2_ren(); break;
        case 2: s2_run({{33, 16}, {34, 16}, {14, 33}, {22, 14}, {{22, 13}, {26, 14}, {22, 10}, {19, 11}}}); break; // hole, range 4 x2, (-3,-3) over holes
        case 3: s2_run({{37, 15}, {36, 15}, {15, 33}, {33, 31}, {{35, 34}, {34, 32}, {37, 31}, {35, 28}}}); break; // altar, camp, range, bush
        case 4: s2_run({{37, 16}, {36, 16}, {13, 34}, {52, 34}, {{55, 34}, {55, 33}, {53, 33}, {50, 31}}}); break; // enemy spawn(+enemy), adj, open
        }
    }
}
