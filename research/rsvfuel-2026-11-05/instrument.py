#!/usr/bin/env python3
"""Instrument a copy of astraeus with RSV trace lines: on farm-loop turns, fuel at marks after the loop
and the post-loop cost of each part, plus the state known at the loop's exit. Debug builds only."""
import sys
from pathlib import Path

src = Path(sys.argv[1])

HEADER = r'''
// ---- RSV instrumentation (measurement copies only) ----
struct RsvTrace {
    bool on = false;
    int n = 0;
    char ids[24];
    std::uint64_t marks[24];
    std::uint64_t acc[24] = {};
    int calls[24] = {};
    int oofacc = 0;
    char state[200];
    char cuts[200] = {};
    int ncuts = 0;
};
inline RsvTrace& rsv() { static RsvTrace t; return t; }
inline void rsv_mark(char id) {
    debug_block({
        auto& t = rsv();
        if (t.on && t.n < 24) t.ids[t.n] = id, t.marks[t.n++] = cambc::fuel_remaining();
    });
}
struct RsvScope {
    int k;
    std::uint64_t start = 0;
    explicit RsvScope(int kind) : k(kind) { debug_block({ if (rsv().on) start = cambc::fuel_remaining(); }); }
    ~RsvScope() {
        debug_block({
            if (rsv().on && start) {
                const auto now = cambc::fuel_remaining();
                if (now <= start) rsv().acc[k] += start - now, ++rsv().calls[k];
                else ++rsv().oofacc;
            }
        });
    }
};
'''

def patch(rel, old, new, count=1):
    p = src / rel
    s = p.read_text()
    if s.count(old) != count:
        sys.exit(f"{rel}: anchor found {s.count(old)} times, want {count}: {old[:60]!r}")
    p.write_text(s.replace(old, new))

# util.h: the header before the namespace's end.
p = src / "util.h"
s = p.read_text()
i = s.index("inline void note_shortcut(const char* what) {")
p.write_text(s[:i] + HEADER + "\n" + s[i:])
patch("util.h", "            std::printf(\"SHORTCUT %d %u %s\\n\", cambc::round_number(),\n",
"""            if (auto& t = rsv(); t.on && t.ncuts < 190) t.ncuts += std::snprintf(t.cuts + t.ncuts, sizeof t.cuts - t.ncuts, "%s,", what);
            std::printf("SHORTCUT %d %u %s\\n", cambc::round_number(),
""")

# farm.cc: the loop's exit, with its state.
patch("economy/farm.cc", '    if (k < evaluated) note_shortcut("farm-partial-evaluation");\n',
'''    if (k < evaluated) note_shortcut("farm-partial-evaluation");
    debug_block({
        auto& t = rsv();
        t = RsvTrace{};
        t.on = true;
        const int g = best >= 0 ? best : memory.farm_group;
        const auto lr = loop_reserve();
        const auto wr = walk_reserve(g);
        const int gsteps = g < 0 ? -1 : (g == best ? best_steps : dist(here, groups[g].centre));
        const auto se = g >= 0 ? search_cost_estimate(gsteps + max_detour) : 0;
        int near = 99, foes6 = 0, foes10 = 0;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) {
                const int d = dist(e.pos, here);
                near = std::min(near, d), foes6 += d <= 6, foes10 += d <= 10;
            }
        const int apr = g >= 0 ? pathing.approach_ready(g, walk_range(world, g)) : -1;
        const int cen = g >= 0 ? pathing.from_centre(g) != nullptr : -1;
        const int gstate = g >= 0 ? static_cast<int>(world.camps[g].state) : -1;
        std::snprintf(t.state, sizeof t.state, "%d %d %d %d %d %llu %llu %llu %llu %llu %llu %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",
                      banks_bag ? 1 : 0, opening ? 1 : 0, k < evaluated ? 1 : 0, k, n_groups,
                      (unsigned long long)loop_floor, (unsigned long long)lr, (unsigned long long)wr, (unsigned long long)se,
                      (unsigned long long)travel, (unsigned long long)(opening ? decode : 0), zoned ? 1 : 0, g, best >= 0 ? 1 : 0, apr, cen, gstate, gsteps,
                      near, foes6, foes10, my_can_move() ? 1 : 0, my_can_attack() ? 1 : 0, my_can_cast() ? 1 : 0,
                      map.width * map.height, shared >= 0 ? 1 : 0, help_group >= 0 ? 1 : 0, static_cast<int>(search_chunks()));
    });
    rsv_mark('L');
''')
patch("economy/farm.cc", "    const int cap = best_steps + max_detour;\n    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);\n",
      "    rsv_mark('P');\n    const int cap = best_steps + max_detour;\n    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);\n")
patch("economy/farm.cc", '''bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return farm_turn<false, true>(world, pathing, safety, memory);
}''', '''bool farm_banking(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const bool r = farm_turn<false, true>(world, pathing, safety, memory);
    rsv_mark(r ? 'b' : 'B');
    return r;
}''')
patch("economy/farm.cc", '''bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    return world.round == world.first_round ? farm_turn<true>(world, pathing, safety, memory) : farm_turn<false>(world, pathing, safety, memory);
}''', '''bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    const bool r = world.round == world.first_round ? farm_turn<true>(world, pathing, safety, memory) : farm_turn<false>(world, pathing, safety, memory);
    rsv_mark(r ? 'f' : 'F');
    return r;
}''')
patch("economy/farm.cc", "[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor) {\n",
      "[[gnu::noinline]] const bitboard* farm_attack_tiles(const World& world, Pathing& pathing, int group, int range, Floor floor) {\n    RsvScope rsv_scope{8};\n")

# Scoped costs.
patch("model/pathing.cc", "[[gnu::flatten]] const Field* Pathing::prepare_approach(int group, int range, std::uint64_t fuel_floor) {\n",
      "[[gnu::flatten]] const Field* Pathing::prepare_approach(int group, int range, std::uint64_t fuel_floor) {\n    RsvScope rsv_scope{1};\n")
patch("model/pathing.cc", "Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {\n",
      "Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {\n    RsvScope rsv_scope{3};\n")
patch("model/pathing.cc", "                                std::optional<vec2> aim) {\n    // An enemy a refused move revealed makes the dash the fight's",
      "                                std::optional<vec2> aim) {\n    RsvScope rsv_scope{0};\n    // An enemy a refused move revealed makes the dash the fight's")
patch("combat/guard.cc", "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {\n",
      "const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {\n    RsvScope rsv_scope{2};\n")
patch("combat/guard.cc", "const bitboard* pack_zone(const World& world, Safety& safety) {\n",
      "const bitboard* pack_zone(const World& world, Safety& safety) {\n    RsvScope rsv_scope{4};\n")
patch("model/turn_order.cc", "void set_turn_order(const World& world, Safety& safety) {\n",
      "void set_turn_order(const World& world, Safety& safety) {\n    RsvScope rsv_scope{5};\n")
patch("model/comms.cc", "void send(World& world, bool moved, bool refresh) {\n",
      "void send(World& world, bool moved, bool refresh) {\n    RsvScope rsv_scope{6};\n")

# bot.cc: act's end, the turn order, play_turn's end.
patch("bot.cc", "    if (!support_owned) start_recall(world);\n    count_use(world, could_attack);\n}",
      "    if (!support_owned) start_recall(world);\n    count_use(world, could_attack);\n    rsv_mark('A');\n}")
patch("bot.cc", "        if (!world.is_stale()) see_stuns(world, safety);\n        set_turn_order(world, safety);\n",
      "        if (!world.is_stale()) see_stuns(world, safety);\n        rsv_mark('T');\n        set_turn_order(world, safety);\n        rsv_mark('U');\n")

# main.cc: reset at the turn's start, marks at the turn end, the queue, and the line.
patch("main.cc", "        const auto start = aph::fuel();\n        aph::FuelMeter meter{\"turn\"};\n",
      "        const auto start = aph::fuel();\n        debug_block({ aph::rsv() = aph::RsvTrace{}; });\n        aph::FuelMeter meter{\"turn\"};\n")
patch("main.cc", "        aph::finish_late() = late && world->resumed();\n",
      "        aph::finish_late() = late && world->resumed();\n        aph::rsv_mark('D');\n")
patch("main.cc", "        if (!world->is_stale())\n            run(\"queue\", [&] { queue.run(*world, *pathing, memory, start); });\n        aph::print_fuel_log();\n",
      '''        aph::rsv_mark('Q');
        if (!world->is_stale())
            run("queue", [&] {
                aph::RsvScope rsv_scope{7};
                queue.run(*world, *pathing, memory, start);
            });
        aph::rsv_mark('Z');
        aph::print_fuel_log();
''')
patch("main.cc", "        const auto now = aph::round_now();\n        late = now != round;\n",
"""        const auto now = aph::round_now();
        late = now != round;
        debug_block({
            auto& t = aph::rsv();
            if (t.on) {
                std::printf("RSV %u %u %d %s |", round, aph::my_handle(), late ? 1 : 0, t.state);
                for (int i = 0; i < t.n; ++i) std::printf(" %c%llu", t.ids[i], (unsigned long long)t.marks[i]);
                std::printf(" |");
                for (int i = 0; i < 24; ++i) std::printf(" %llu/%d", (unsigned long long)t.acc[i], t.calls[i]);
                std::printf(" %d | %s\\n", t.oofacc, t.ncuts ? t.cuts : "-");
                t.on = false;
            }
        });
""")

def scope(rel, head, k, count=1):
    patch(rel, head, head + "    RsvScope rsv_scope{%d};\n" % k, count)
scope("model/pathing.cc", "                                          std::optional<vec2> aim) {\n", 9)
scope("bot.cc", "bool see_revealed(World& world, Pathing& pathing, Safety& safety) {\n", 10)
scope("combat/plan.cc", "[[gnu::flatten]] bool strike_enemy(const World& world) {\n", 11)
scope("economy/camps.cc", "template <class Allowed> int attack_camp(const World& world, Allowed allowed) {\n", 12)
scope("combat/abilities.cc", "bool cast_at_camp(const World& world, int group, bool attackers_only, bool any_value) {\n", 13)
scope("combat/self_abilities.cc", "bool reset_and_attack_camp(const World& world, int group) {\n", 14)
scope("economy/home.cc", "bool home_stands(const World& world, Pathing& pathing, Safety& safety, const bitboard& tiles, int wake, bitboard& out) {\n", 15)
scope("model/pathing.cc", "Pathing::Ahead Pathing::ahead(const cambc::distance_field& d, const bitboard& goals, int here, int horizon) {\n", 16)
scope("model/pathing.cc", "Pathing::TravelDash Pathing::travel_dash() {\n", 17)
scope("combat/self_abilities.cc", "bool heal_ally(const World& world, Safety& safety) {\n", 18)
scope("combat/self_abilities.cc", "bool shield_if_needed(const World& world, Safety& safety, int farmed) {\n", 19)
scope("bot.cc", "bool place_ward(const World& world, Memory& memory, bool bushes) {\n", 20)
scope("economy/bank.cc", "[[gnu::flatten]] void place_lock(const World& world) {\n", 21)
scope("combat/plan.cc", "Planned strike_after(const World& world, Pathing& pathing, Safety& safety) {\n", 22)
scope("combat/abilities.cc", "bool cast_at_camp_on_approach(const World& world, int group) {\n", 23)
print("instrumented", src)
