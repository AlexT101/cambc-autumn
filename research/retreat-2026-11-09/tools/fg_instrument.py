#!/usr/bin/env python3
"""Fuel-gate checkpoints for a copy of ocean (debug builds only: all inside debug_block).

usage: instrument.py SRC_DIR
Prints per retreat turn (main.cc end):  FG <round> <handle> v0 .. v39
and per out-of-fuel turn (main loop):   FGO <round> <now> v0 .. v39
Indices: see IDX below."""
import re, sys, pathlib

src = pathlib.Path(sys.argv[1])


def patch(rel, old, new, count=1):
    p = src / rel
    t = p.read_text()
    n = t.count(old)
    if n != count:
        sys.exit(f"{rel}: pattern found {n} times, want {count}: {old[:80]!r}")
    p.write_text(t.replace(old, new))


# util.h: the array and macros, after turn_round().
patch("util.h", "// Set while deciding a turn that follows one that did not finish in its own round",
      """inline std::uint64_t* fgp() { static std::uint64_t a[48]; return a; }
#define FG(i) debug_block({ if (::aph::round_now() == ::aph::turn_round()) { ::aph::fgp()[i] = ::aph::fuel(); ::aph::fgp()[35] = (i); } })
#define FGSET(i, v) debug_block({ if (::aph::round_now() == ::aph::turn_round()) ::aph::fgp()[i] = (v); })
#define FGADD(i, v) debug_block({ if (::aph::round_now() == ::aph::turn_round()) ::aph::fgp()[i] += (v); })
// Set while deciding a turn that follows one that did not finish in its own round""")

# main.cc: reset and turn start; decide start; end print; OOF print.
patch("main.cc", """        const auto start = aph::fuel();
        aph::FuelMeter meter{"turn"};""",
      """        const auto start = aph::fuel();
        debug_block({ for (int i = 0; i < 48; ++i) aph::fgp()[i] = 0; aph::fgp()[0] = start; aph::fgp()[47] = aph::round_now(); });
        aph::FuelMeter meter{"turn"};""")
patch("main.cc", """        run("decide", [&] {
            aph::FuelMeter meter{"decide"};""",
      """        FG(1);
        run("decide", [&] {
            aph::FuelMeter meter{"decide"};""")
patch("main.cc", """        aph::print_fuel_log();
    }""",
      """        FG(14);
        debug_block({
            auto* t = aph::fgp();
            if (t[31] && t[47] == aph::round_now()) {
                std::printf("FG %u %u", aph::round_now(), aph::my_handle());
                for (int i = 0; i < 47; ++i) std::printf(" %llu", (unsigned long long)t[i]);
                std::printf("\\n");
            }
        });
        aph::print_fuel_log();
    }""")
patch("main.cc", """                std::printf("OOF %u %s\\n", round, aph::fuel_phase());""",
      """                std::printf("OOF %u %s\\n", round, aph::fuel_phase());
                auto* t = aph::fgp();
                std::printf("FGO %u %u %u", round, now, aph::my_handle());
                for (int i = 0; i < 47; ++i) std::printf(" %llu", (unsigned long long)t[i]);
                std::printf("\\n");""")

# bot.cc act: after decide, end of act; play_turn end.
patch("bot.cc", """    decide(world, pathing, safety, memory);
    if (decision != Branch::wait_altar) memory.wait_altar = -1;""",
      """    decide(world, pathing, safety, memory);
    FG(11);
    if (decision != Branch::wait_altar) memory.wait_altar = -1;""")
patch("bot.cc", """    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
}""", """    FG(36);
    if (!support_owned) start_recall(world);
    count_use(world, could_attack);
    FG(12);
}""")
patch("bot.cc", """        chase_role = {decision == Branch::retreat, decision == Branch::chase, engaged};
        set_turn_order(world, safety);""", """        chase_role = {decision == Branch::retreat, decision == Branch::chase, engaged};
        FG(37);
        set_turn_order(world, safety);
        FG(38);""")
patch("bot.cc", """    upkeep.camp_turns += camp_hits() != camp_hits_before;""",
      """    upkeep.camp_turns += camp_hits() != camp_hits_before;
    FG(13);""")

# fight.cc: retreat checkpoints.
patch("combat/fight.cc", """void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;""",
      """void retreat_step_(const World& world, Pathing& pathing, Safety& safety, const Field& home);
void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    FG(6);
    retreat_step_(world, pathing, safety, home);
    FG(9);
    FGSET(34, my_can_move() ? 1 : 0);
}
void retreat_step_(const World& world, Pathing& pathing, Safety& safety, const Field& home) {
    if (!my_can_move()) return;""")
patch("combat/fight.cc", """    auto& plan = escape::plan(world, pathing, safety, params::escape::walk_reserve);
    add(false);""", """    FGSET(32, 2);
    FG(39);
    auto& plan = escape::plan(world, pathing, safety, params::escape::walk_reserve);
    FG(7);
    add(false);""")
patch("combat/fight.cc", """    const auto by = [](const Option& a, const Option& b) {
        if (a.home != b.home) return a.home;""", """    FG(8);
    FGSET(40, n);
    FGSET(41, plan.active() ? 1 : 0);
    const auto by = [](const Option& a, const Option& b) {
        if (a.home != b.home) return a.home;""")
patch("combat/fight.cc", """void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();""", """void retreat_(World& world, Pathing& pathing, Safety& safety, Memory& memory);
void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    FGSET(31, 1);
    FG(2);
    retreat_(world, pathing, safety, memory);
    FG(10);
}
void retreat_(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();""")
patch("combat/fight.cc", """    const bool keep_dash = contested && my_health() < params::recall_health_fraction * my_max_health()
                           && my_can_cast() && my_cooldown(escape_slot) == 0;
    if (keep_dash) {""", """    const bool keep_dash = contested && my_health() < params::recall_health_fraction * my_max_health()
                           && my_can_cast() && my_cooldown(escape_slot) == 0;
    FG(3);
    FGSET(33, keep_dash ? 1 : 0);
    if (keep_dash) {""")
patch("combat/fight.cc", """    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    if (reset_and_attack_enemy(world)) see_kills(world, pathing, safety);""", """    FG(4);
    // The escape dash shares the one cast: the reset only after it, from a melee attack or a ranged walk.
    if (reset_and_attack_enemy(world)) see_kills(world, pathing, safety);""")
patch("combat/fight.cc", """    if (!flee_camps(world, pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());""",
      """    FG(5);
    if (!flee_camps(world, pathing, safety, pathing.to_ally_spawn())) retreat_step(world, pathing, safety, pathing.to_ally_spawn());
    FG(42);""")

# self_abilities.cc: asker id for landings.
patch("combat/self_abilities.cc", """        if (auto& p = escape::plan(world, pathing, safety, params::escape::dash_reserve); p.active() && p.dash_now()) {""",
      """        FGSET(32, 1);
        if (auto& p = escape::plan(world, pathing, safety, params::escape::dash_reserve); p.active() && p.dash_now()) {""")

# escape.cc: builds and slack.
patch("model/escape.cc", """        p.round = world.round, p.handle = me, p.at = here, p.observations = world.observations;
        p.build(world, pathing, safety, reserve + cost);""", """        p.round = world.round, p.handle = me, p.at = here, p.observations = world.observations;
        std::uint64_t ask = 0;
        debug_block({ ask = fuel(); });
        p.build(world, pathing, safety, reserve + cost);
        debug_block({
            if (round_now() == turn_round()) {
                auto* t = fgp();
                const int k = static_cast<int>(t[15]);
                if (k < 3) {
                    t[16 + 4 * k] = ask;
                    t[17 + 4 * k] = ask - fuel();
                    t[18 + 4 * k] = p.short_of_fuel() ? 1 : (p.active() ? 2 : 3); // 1 gated, 2 active, 3 inactive
                    t[19 + 4 * k] = t[32];
                }
                t[15] = k + 1;
            }
        });""")
patch("model/escape.cc", """    if (!active_ || pass_[1].ready || fuel() < reserve + slack_cost_) return;
    const auto before = fuel();
    run(slack_goal_, pass_[1]);
    note_cost(slack_cost_, before - fuel());""", """    if (active_ && !pass_[1].ready) FGADD(28, 1);
    if (active_ && !pass_[1].ready && fuel() < reserve + slack_cost_) FGADD(29, 1);
    if (!active_ || pass_[1].ready || fuel() < reserve + slack_cost_) return;
    const auto before = fuel();
    run(slack_goal_, pass_[1]);
    FGADD(30, before - fuel());
    note_cost(slack_cost_, before - fuel());""")
print("ok")
