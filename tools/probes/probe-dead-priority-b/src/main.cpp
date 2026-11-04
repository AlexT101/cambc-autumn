// probe-dead-priority-b: team-B counterpart of probe-dead-priority; identical source compiled with VARIANT 1 (regenerate by prepending these lines to tools/probes/probe-dead-priority/src/main.cpp).
#define VARIANT 1
// probe-dead-priority: can a dead champion set its priority, does it reorder turns while dead, and does it persist
// through respawn? VARIANT 0 = this bot (team A); VARIANT 1 = tools/probes/probe-dead-priority-b (this file with
// "#define VARIANT 1" prepended).
//   cambc run tools/probes/probe-dead-priority tools/probes/probe-dead-priority-b --map 00packs --rounds 150 \
//     --fuel 50000000 -o <dir>
// A picks Willow (lowest id: first in A's order at priority 0), Prism, Ren; B picks Varg, Vendetta, Tavi.
// Everyone walks to the map midpoint; until round 70 B basic-attacks only A's Willow, until it dies (round D, logged as dead_since).
// Dead Willow sets priority -100 on its 5th dead turn (last in A from the next round), 100 on its 15th (first),
// -100 on its 25th; then it respawns.
// Every turn logs:
//   slot=k   its index in its own team's order this round (shared memory: byte0 = round, byte1 = turns so far;
//            a dead bot that cannot write leaves the count unchanged, so the next one's k repeats);
//   done=... every champion's has_completed_turn (or the error for an unseen one): a living B champion's view of
//            A's living champions shows whether dead Willow, first in A's order, took an alternation slot.
#ifndef VARIANT
#define VARIANT 0
#endif
#include <cambc.h>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

using cambc::champion_draft;
using cambc::champion_type;
using cambc::team;

static std::string err(const std::exception& e) {
    if (auto* ce = dynamic_cast<const cambc::error*>(&e))
        return "ERR(" + std::to_string(static_cast<int>(ce->code())) + ":" + ce->message() + ")";
    return std::string("EXC(") + e.what() + ")";
}

template <class F> static std::string q(F f) {
    try { return std::to_string(f()); } catch (const std::exception& e) { return err(e); }
}

static void play_draft() {
#if VARIANT == 0
    const champion_draft order[] = {champion_draft::willow, champion_draft::prism, champion_draft::ren,
                                    champion_draft::stellar, champion_draft::vendetta};
#else
    const champion_draft order[] = {champion_draft::varg, champion_draft::vendetta, champion_draft::tavi,
                                    champion_draft::ryth, champion_draft::stellar};
#endif
    cambc::draft::pick(order[cambc::draft::current_draft(team::ally).size()]);
}

// Walk one step toward free tiles within `radius` of `center` (distance field, as in probe-order).
static void walk(cambc::vec2 center, int radius) {
    auto& me = cambc::self();
    if (!me.is_alive() || !me.can_move()) return;
    auto blocked = cambc::map::walls() | cambc::map::holes() | cambc::map::altars()
        | cambc::map::spawn_region(team::enemy) | cambc::vision::champion_tiles() | cambc::vision::camp_tiles();
    blocked.set(me.position(), false);
    cambc::bitboard goals;
    goals.clear();
    goals.draw_chebyshev(center, radius);
    goals &= ~blocked;
    if (goals.is_empty() || goals.is_set(me.position())) return;
    cambc::distance_field field;
    cambc::bitboard visited, from;
    from.clear();
    from.set(me.position(), true);
    field.compute_to(blocked & ~goals, goals, from, visited);
    auto step = me.position();
    for (auto t : blocked.reachable_tiles(step, me.base_stats().base_move_speed).positions())
        if (field.get(t) < field.get(step)) step = t;
    if (step != me.position()) me.move_absolute(step);
}

static int dead_since = -1, dead_turns = 0;

static void play_turn() {
    auto& me = cambc::self();
    const auto name = cambc::to_string(me.champion_name());
    const int rn = static_cast<int>(cambc::round_number());
    const unsigned id = static_cast<unsigned>(static_cast<cambc::handle_champion_t>(me));
    const bool alive = me.is_alive();

    std::uint8_t mem[8];
    cambc::shared_memory.read(0, std::span{mem, 8});
    const int slot = mem[0] == std::uint8_t(rn) ? mem[1] : 0;
    std::string wrote = "ok";
    try {
        cambc::shared_memory[0] = std::uint8_t(rn);
        cambc::shared_memory[1] = std::uint8_t(slot + 1);
    } catch (const std::exception& e) { wrote = err(e); }

    if (!alive) {
        if (dead_since < 0) dead_since = rn;
        ++dead_turns;
    } else dead_since = -1, dead_turns = 0;

    if (rn >= 15) {
        std::ostringstream o;
        o << "PROBE " << rn << " " << name << " id=" << id << " alive=" << alive << " slot=" << slot
          << " smem_write=" << wrote << " prio=" << q([&] { return me.priority(); })
          << " prev=" << q([&] { return me.prev_priority(); });
        if (!alive) o << " dead_since=" << dead_since << " dead_turn=" << dead_turns;
        o << " done=";
        for (auto& c : cambc::champions())
            o << static_cast<unsigned>(static_cast<cambc::handle_champion_t>(c)) << ":"
              << q([&] { return int(c.has_completed_turn()); }) << ",";
        std::cout << o.str() << '\n';
    }

#if VARIANT == 0
    if (me.champion_name() == champion_type::willow && !alive && (dead_turns == 5 || dead_turns == 15 || dead_turns == 25)) {
        const int v = dead_turns == 15 ? 100 : -100;
        std::string r = "ok";
        try { me.set_priority(v); } catch (const std::exception& e) { r = err(e); }
        std::cout << "PROBE " << rn << " " << name << " DEAD set_priority(" << v << ")=" << r
                  << " prio=" << q([&] { return me.priority(); }) << " prev=" << q([&] { return me.prev_priority(); })
                  << '\n';
    }
#else
    if (alive && rn <= 70)  // one kill only: the respawned Willow is left alone
        for (const auto& c : cambc::vision::champions(team::enemy)) {
            if (c.champion_name() != champion_type::willow || !c.is_visible() || !c.is_alive()) continue;
            if (me.can_attack() && me.attack_tiles().is_set(c.position())) {
                try {
                    me.attack(c);
                    std::cout << "PROBE " << rn << " " << name << " attack willow hp_after=" << q([&] { return c.health(); })
                              << " alive=" << c.is_alive() << '\n';
                } catch (const std::exception& e) { std::cout << "PROBE " << rn << " " << name << " attack " << err(e) << '\n'; }
            }
            try { walk(c.position(), 1); } catch (const std::exception&) {}
            return;
        }
#endif
    if (!alive) return;
    try {
        auto a = cambc::map::spawn_region(team::ally).positions(), e = cambc::map::spawn_region(team::enemy).positions();
        walk((a[a.size() / 2] + e[e.size() / 2]) / 2, 3);
    } catch (const std::exception& ex) { std::cout << "PROBE " << rn << " " << name << " move " << err(ex) << '\n'; }
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
