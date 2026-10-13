// probe-order-b: team-B counterpart of probe-order; identical source compiled with VARIANT 1 (regenerate by prepending these lines to rules-verification/probes/probe-order/src/main.cpp; add "#define B_YIELD_DRAFT 1" for the yield-draft test).
#define VARIANT 1
// probe-order: verifies turn order, round numbering, priority, shared/draft memory and draft rules.
// VARIANT 0 = this bot (rules-verification/probes/probe-order, team A); VARIANT 1 = rules-verification/probes/probe-order-b (same file + "#define VARIANT 1").
// Every value logged as "PROBE <round> <who> ..." is read from the engine.
// Run with a large --fuel (e.g. --fuel 100000000): the logging otherwise exhausts the default fuel and the turn
// is suspended into the next round (which is itself one of the findings).
#ifndef VARIANT
#define VARIANT 0
#endif
#ifndef B_YIELD_DRAFT
#define B_YIELD_DRAFT 0  // B only: 1 = write draft memory, then yield draft turn 0 without picking (run r1)
#endif
#ifndef MOVE_PLAN
#define MOVE_PLAN 1      // 1 (default) = walk every champion toward the enemy spawn (cross-team visibility runs)
#endif
#include <cambc.h>
#include <climits>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

using cambc::champion_draft;
using cambc::team;

static std::string err(const std::exception& e) {
    if (auto* ce = dynamic_cast<const cambc::error*>(&e))
        return "ERR(" + std::to_string(static_cast<int>(ce->code())) + ":" + ce->message() + ")";
    return std::string("EXC(") + e.what() + ")";
}

static std::string picks(team side) {
    std::string s = "[";
    try {
        for (auto p : cambc::draft::current_draft(side)) s += cambc::to_string(p) + ",";
    } catch (const std::exception& e) { s += err(e); }
    return s + "]";
}

static std::string round_str() {
    try { return std::to_string(cambc::round_number()); } catch (const std::exception& e) { return err(e); }
}

static void log_pick(const char* what, champion_draft p) {
    try {
        cambc::draft::pick(p);
        std::cout << "PROBE " << round_str() << " draft " << what << "=" << cambc::to_string(p) << " ok\n";
    } catch (const std::exception& e) {
        std::cout << "PROBE " << round_str() << " draft " << what << "=" << cambc::to_string(p) << " " << err(e) << '\n';
    }
}

static int draft_turn = 0;

static void play_draft() {
    std::ostringstream o;
    o << "PROBE " << round_str() << " draft turn=" << draft_turn << " abs_team=" << cambc::detail::sdk_my_team()
      << " team_size=";
    try { o << cambc::draft::team_size(); } catch (const std::exception& e) { o << err(e); }
    o << " fuel=" << cambc::fuel_remaining() << " ally=" << picks(team::ally) << " enemy=" << picks(team::enemy)
      << " dmem_snapshot0=" << (cambc::draft_memory.size() ? int(cambc::draft_memory[0]) : -1)
      << " dmem_size=" << cambc::draft_memory.size();
    if (draft_turn == 0) {
        auto a = cambc::map::spawn_region(team::ally).positions(), e = cambc::map::spawn_region(team::enemy).positions();
        o << " map=" << cambc::map::width() << "x" << cambc::map::height() << " ally_spawn=" << cambc::to_string(a.front())
          << ".." << cambc::to_string(a.back()) << " enemy_spawn=" << cambc::to_string(e.front()) << ".."
          << cambc::to_string(e.back());
    }
    std::cout << o.str() << '\n';

#if VARIANT == 1 && !B_YIELD_DRAFT
    // B (normal): never writes draft memory (shows its initial contents); picks without Cassi & Issac.
    const champion_draft b_order[] = {champion_draft::ryth, champion_draft::vendetta, champion_draft::stellar,
                                      champion_draft::prism, champion_draft::willow};
    log_pick("pick", b_order[draft_turn % 5]);
    std::cout << "PROBE " << round_str() << " draft after ally=" << picks(team::ally) << " enemy=" << picks(team::enemy) << '\n';
    ++draft_turn;
    return;
#endif

    // Draft memory: turn k writes (5-k) copies of char 'a'+k at offset 0 (persist/overwrite test).
    try {
        std::string w(5 - draft_turn, char('a' + draft_turn));
        cambc::draft_memory = std::string_view(w);
        std::cout << "PROBE " << round_str() << " draft dmem_write=" << w << " ok\n";
    } catch (const std::exception& e) { std::cout << "PROBE " << round_str() << " draft dmem_write " << err(e) << '\n'; }

#if VARIANT == 0
    // A: turn0 cassi_and_issac; later turns first retry cassi_and_issac (duplicate), then the list; then a 2nd pick.
    const champion_draft order[] = {champion_draft::cassi_and_issac, champion_draft::ryth, champion_draft::vendetta,
                                    champion_draft::stellar, champion_draft::prism};
    if (draft_turn >= 1) log_pick("dup_pick", champion_draft::cassi_and_issac);
    log_pick("pick", order[draft_turn % 5]);
    log_pick("second_pick", champion_draft::tavi);
#endif
    // B with B_YIELD_DRAFT=1 picks nothing here.
    std::cout << "PROBE " << round_str() << " draft after ally=" << picks(team::ally) << " enemy=" << picks(team::enemy) << '\n';
    ++draft_turn;
}

static int play_turns = 0;

static void play_turn() {
    auto& me = cambc::self();
    const auto name = cambc::to_string(me.champion_name());
    const auto r = round_str();
    const unsigned id = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me));

    std::ostringstream o;
    o << "PROBE " << r << " " << name << " START id=" << id << " abs_team=" << cambc::detail::sdk_my_team()
      << " prio=" << me.priority() << " prev_prio=" << me.prev_priority() << " alive=" << me.is_alive()
      << " hp=" << me.health() << " pos=" << cambc::to_string(me.position()) << " fuel=" << cambc::fuel_remaining();
    std::uint8_t mem[8];
    cambc::shared_memory.read(0, std::span{mem, 8});
    o << " smem=";
    for (int i = 0; i < 8; ++i) o << int(mem[i]) << (i < 7 ? "," : "");
    if (play_turns == 0) {
        o << " dmem=";
        for (int i = 0; i < 8; ++i) o << int(cambc::draft_memory[i]) << ",";
        o << " dmem_size=" << cambc::draft_memory.size();
    }
    std::cout << o.str() << '\n';

    // Everyone's state (allies and enemies; hidden ones report an error).
    for (auto& c : cambc::champions()) {
        std::ostringstream l;
        l << "PROBE " << r << " " << name << " SEE id=" << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(c));
        try {
            l << " team=" << (c.is_ally() ? "ally" : "enemy") << " name=" << cambc::to_string(c.champion_name())
              << " pos=" << cambc::to_string(c.position()) << " done=" << c.has_completed_turn()
              << " alive=" << c.is_alive() << " prio=" << c.priority() << " prev=" << c.prev_priority();
        } catch (const std::exception& e) { l << " " << err(e); }
        std::cout << l.str() << '\n';
    }

    // Shared memory: byte0 = writer's round (low byte), byte1 = team turn counter, byte2 = writer id.
    cambc::shared_memory[0] = static_cast<std::uint8_t>(cambc::round_number());
    cambc::shared_memory[1] = static_cast<std::uint8_t>(mem[1] + 1);
    cambc::shared_memory[2] = static_cast<std::uint8_t>(id);

    const auto rn = cambc::round_number();
    // Priority schedule (both teams cluster at the map midpoint first, so the full order is visible to everyone).
#if VARIANT == 0
    if (rn == 20) {  // A: priority = id*10 -> expect reversed (higher id first) from round 21
        me.set_priority(int(id) * 10);
        std::cout << "PROBE " << r << " " << name << " set_priority=" << id * 10 << " now prio=" << me.priority()
                  << " prev=" << me.prev_priority() << '\n';
    }
    if (rn == 25) {  // range tests; the last successful value is kept -> all equal from round 26
        for (int v : {-7, INT_MAX, INT_MIN}) {
            try {
                me.set_priority(v);
                std::cout << "PROBE " << r << " " << name << " set_priority(" << v << ") ok prio=" << me.priority()
                          << " prev=" << me.prev_priority() << '\n';
            } catch (const std::exception& e) {
                std::cout << "PROBE " << r << " " << name << " set_priority(" << v << ") " << err(e) << '\n';
            }
        }
    }
    if (rn == 30 && name == "prism") me.set_priority(INT_MAX);  // one champion jumps to the front from round 31
    // Draft memory write during play.
    if (play_turns == 0) {
        try {
            cambc::draft_memory = std::string_view("zz");
            std::cout << "PROBE " << r << " " << name << " play_dmem_write ok\n";
        } catch (const std::exception& e) { std::cout << "PROBE " << r << " " << name << " play_dmem_write " << err(e) << '\n'; }
        // Bypass the SDK's is_draft() guard to see the engine's own answer.
        const std::byte zz[2] = {std::byte{'z'}, std::byte{'z'}};
        std::cout << "PROBE " << r << " " << name << " raw_play_dmem_write code="
                  << static_cast<int>(cambc::detail::sdk_bc_submit_draft_memory(zz, 2)) << '\n';
    }
#else
    if (rn == 20 && name == "stellar") me.set_priority(-3);  // B: stellar to the back from round 21 (persists)
    if (rn == 20 && name == "willow") me.set_priority(3);    // B: willow to the front from round 21
    if (rn >= 41) {  // B: from round 41 basic-attack any enemy champion in range (to get A champions killed)
        for (const auto& c : cambc::vision::champions(team::enemy)) {
            if (!me.can_attack() || !c.is_visible() || c.health() <= 0 || !me.attack_tiles().is_set(c.position())) continue;
            const auto hp = c.health();
            try {
                me.attack(c);
                std::cout << "PROBE " << rn << " " << name << " attack " << cambc::to_string(c.champion_name())
                          << " hp_before=" << hp << " hp_after=" << c.health() << " alive=" << c.is_alive() << '\n';
            } catch (const std::exception& e) { std::cout << "PROBE " << rn << " " << name << " attack " << err(e) << '\n'; }
            break;
        }
    }
#endif
#if MOVE_PLAN
    try {  // walk toward free tiles within 3 of the midpoint of the two spawns (distance field, as in starter-cpp)
        auto e = cambc::map::spawn_region(team::enemy).positions();
        auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
            | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles() | cambc::vision::camp_tiles();
        blocked.set(me.position(), false);
        cambc::bitboard goals;
        goals.clear();
        auto a = cambc::map::spawn_region(team::ally).positions();
        goals.draw_chebyshev((a[a.size() / 2] + e[e.size() / 2]) / 2, 3);
        goals &= ~blocked;
        bool moved = false;
        if (me.can_move() && !goals.is_empty() && !goals.is_set(me.position())) {
            cambc::distance_field field;
            cambc::bitboard visited, from;
            from.clear();
            from.set(me.position(), true);
            field.compute_to(blocked & ~goals, goals, from, visited);
            auto step = me.position();
            for (auto t : blocked.reachable_tiles(step, me.base_stats().base_move_speed).positions())
                if (field.get(t) < field.get(step)) step = t;
            moved = step != me.position() && me.move_absolute(step);
        }
        std::cout << "PROBE " << rn << " " << name << " moved=" << moved << " pos=" << cambc::to_string(me.position()) << '\n';
    } catch (const std::exception& ex) { std::cout << "PROBE " << rn << " " << name << " move " << err(ex) << '\n'; }
#endif
    std::cout << "PROBE " << cambc::round_number() << " " << name << " END fuel=" << cambc::fuel_remaining() << '\n';
    ++play_turns;
}

int main() {
    while (true) {
        try {
            if (cambc::is_draft()) play_draft();
            else play_turn();
        } catch (const std::exception& e) {
            std::cout << "PROBE bot_error " << err(e) << '\n';
        }
        cambc::end_turn();
    }
}
