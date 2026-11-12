"""Adds the fightfuel profile (fz.h) to a copy of charybdis: python3 instr.py bots/variants/NAME/src

Debug builds only. One `FZ` stdout line a turn of the Prism, and of any champion with an enemy in sight or out of fuel:
FZ round handle type decision seen near allies hp% gems hit start left_after_decide left_before_queue OOFSTACK id:fuel:calls...
(type: bit 8 set for the Prism; near: the nearest visible enemy's distance, 99 if none; allies: visible within 6; hit:
health lost since our last turn, %; OOFSTACK: the scopes open when the fuel ran out, '-' if it did not). Scope ids: IDS
below; fuel is inclusive. Silent fuel tests get SHORTCUT lines too (NOTES below). parse with fzread.py.
"""
import re, sys
from pathlib import Path

SRC = Path(sys.argv[1])

# id: name. Function-top scopes: (file, text starting the definition line, id).
IDS = {
    0: 'world', 1: 'recv', 2: 'decide', 3: 'turn_end', 4: 'send', 5: 'queue', 7: 'approach', 8: 'wards_shop', 9: 'want_home',
    10: 'local_support', 11: 'retreat', 12: 'guard_steps', 13: 'capture_pre', 14: 'search_strikes', 16: 'hold_capture', 17: 'guard_work',
    18: 'carry_bag', 19: 'shop_guard_contest', 20: 'siege', 21: 'farm', 22: 'strike_after', 23: 'turn_order', 24: 'habit', 25: 'step_guard',
    26: 'guard_cover', 27: 'new_fight', 28: 'stand_trade', 29: 'esc_build', 30: 'esc_chase', 31: 'chase', 33: 'plan_strikes', 35: 'retreat_step',
    36: 'stand_lost_at', 37: 'drawn_home', 38: 'prey', 39: 'route', 40: 'lethal', 41: 'observe', 42: 'see_again', 43: 'refresh',
    44: 'farm_loop', 45: 'farm_picks', 46: 'channel', 47: 'heal_shield', 48: 'harm_idle', 49: 'pack_zone', 50: 'camp_trapped', 51: 'escape_walk',
    52: 'cast_enemies', 53: 'dash_away', 54: 'farm_walk', 55: 'upkeep', 56: 'chase_trade', 57: 'keep_bid', 58: 'may_reach', 59: 'stand_reach',
    60: 'safety_ctor', 61: 'threats_at', 62: 'act_tail', 63: 'other',
    64: 'rs_avoid', 65: 'rs_add', 66: 'rs_homewalk', 67: 'rs_price', 68: 'rs_move', 69: 'stand_walks', 70: 'stand_roster', 71: 'keeps_us',
    # fuel left on entry (the "fuel" field is the fuel left, not a cost)
    72: 'guard_sims',
    80: '@retreat_step', 81: '@prey', 82: '@farm', 83: '@want_home', 84: '@search', 85: '@turn_order', 86: '@retreat', 87: '@farm_loop',
    88: '@guard_exit', 89: '@guard_entry',
    79: 'last_mark', 90: '@goal', 91: '@sealed', 92: '@wants_shop', 93: '@guard_turn', 94: '@chase', 95: '@contest', 73: '@siege', 74: '@after_goal', 75: '@turn_tail', 76: '@posts',
}
TOPS = [
    ('bot.cc', 'bool place_ward(const World& world, Memory& memory, bool bushes) {', 8),
    ('bot.cc', 'bool reveal_ward(const World& world, Memory& memory) {', 8),
    ('bot.cc', 'bool shop(const World& world, const Memory& memory, bool consumables, bool shards) {', 8),
    ('combat/fight.cc', 'bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {', 9),
    ('combat/support.cc', 'bool local_support(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool leave, bool& mate_eligible) {', 10),
    ('combat/fight.cc', 'void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 11),
    ('combat/guard.cc', 'void guard_steps(const World& world, Pathing& pathing, Safety& safety) {', 12),
    ('bot.cc', 'bool search_strikes(World& world, Pathing& pathing, Safety& safety, const Memory& memory, bool holding, bool contested) {', 14),
    ('combat/plan.cc', '[[gnu::flatten]] Planned plan_strikes(const World& world, Pathing& pathing, Safety& safety, const Intent& intent) {', 33),
    ('combat/plan.cc', 'Planned strike_after(const World& world, Pathing& pathing, Safety& safety) {', 22),
    ('combat/plan.cc', 'Planned keep_bid(const World& world, Pathing& pathing, Safety& safety) {', 57),
    ('economy/capture.cc', 'void hold_capture(const World& world, Memory& memory, bool attacked) {', 16),
    ('combat/guard.cc', 'void guard_work(const World& world, Pathing& pathing, Safety& safety, float damage, const bitboard* avoid) {', 17),
    ('economy/bank.cc', 'void carry_bag(World& world, Pathing& pathing, Safety& safety, Memory& memory, bool attacked, const Pathing::GuardState& chase_guard) {', 18),
    ('economy/shop.cc', '[[gnu::flatten]] bool wants_shop(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {', 19),
    ('economy/altar_guard.cc', 'bool guard_turn(const World& world, Pathing& pathing, Safety& safety, Memory& memory, const Pathing::GuardState& strike_guard) {', 19),
    ('combat/fight.cc', 'bool chase(const World& world, Pathing& pathing, Safety& safety) {', 31),
    ('economy/capture.cc', 'bool contest_capture(const World& world, Pathing& pathing, Memory& memory) {', 19),
    ('economy/siege.cc', 'bool siege(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 20),
    ('economy/siege.cc', 'bool kite(const World& world, Pathing& pathing, Memory& memory) {', 20),
    ('economy/farm.cc', 'bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 21),
    ('model/turn_order.cc', 'void set_turn_order(const World& world, Safety& safety) {', 23),
    ('economy/bank.cc', 'bool mite_tribute_habit(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {', 24),
    ('combat/guard.cc', 'const bitboard* step_guard(const World& world, Safety& safety, vec2 here, int radius) {', 25),
    ('combat/guard.cc', 'const bitboard* step_guard_cover(const World& world, Safety& safety, vec2 here, int radius) {', 26),
    ('model/safety.cc', 'Trade Safety::new_fight(std::uint32_t key, bool falls, std::uint32_t late, bool settle) {', 27),
    ('model/safety.cc', 'Trade Safety::chase_trade(std::uint32_t key, std::uint32_t delayed, const std::array<int, 2>& self_cooldowns, bool can_cast, bool falls,', 56),
    ('model/safety.cc', 'Trade Safety::stand_trade(const StandRoster& r, bool falls) {', 28),
    ('model/escape.cc', 'void Plan::build(const World& world, Pathing& pathing, Safety& safety) {', 29),
    ('model/escape.cc', 'void Plan::build_chase(const World& world, Pathing& pathing, const ChampionBelief& target, bool measured) {', 30),
    ('combat/fight.cc', 'void retreat_step(const World& world, Pathing& pathing, Safety& safety, const Field& home) {', 35),
    ('combat/fight.cc', 'bool stand_lost_at(const World& world, Safety& safety, HoldAt& hold) {', 36),
    ('combat/fight.cc', 'bool drawn_home(const World& world, Safety& safety, HoldAt& hold) {', 37),
    ('combat/fight.cc', 'const ChampionBelief* prey(const World& world, Pathing& pathing, Safety& safety) {', 38),
    ('model/pathing.cc', 'Pathing::Route Pathing::route(const bitboard& goals, const bitboard* avoid, int max_steps, std::optional<vec2> aim) {', 39),
    ('model/safety.cc', 'bool Safety::lethal(vec2 p) {', 40),
    ('model/world.cc', '[[gnu::flatten]] void World::observe() {', 41),
    ('bot.cc', '[[gnu::noinline]] void see_again(World& world, Pathing& pathing, Safety& safety) {', 42),
    ('model/safety.cc', 'void Safety::refresh() {', 43),
    ('economy/bank.cc', 'bool continue_tribute(const World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home) {', 46),
    ('economy/bank.cc', 'bool continue_recall(World& world, Pathing& pathing, Safety& safety, Memory& memory, std::optional<bool>& home, int recall_farm) {', 46),
    ('economy/capture.cc', 'bool yield_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory, bool after_farm) {', 13),
    ('economy/capture.cc', 'bool take_capture_handoff(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 13),
    ('economy/capture.cc', 'bool join_marcella_capture(const World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 13),
    ('combat/self_abilities.cc', 'bool heal_ally(const World& world, Safety& safety) {', 47),
    ('combat/self_abilities.cc', 'bool shield_if_needed(const World& world, Safety& safety, int farmed) {', 47),
    ('model/safety.cc', 'int Safety::turns_to_harm_idle(const ChampionBelief& c, vec2 p, int horizon, float keep, bool unseen) {', 48),
    ('combat/guard.cc', 'bool in_pack_zone(const World& world, Safety& safety, vec2 p) {', 49),
    ('combat/fight.cc', 'bool camp_trapped(const World& world, Pathing& pathing, Safety& safety, vec2 here, float health, bool sieging) {', 50),
    ('combat/fight.cc', 'bool escape_walk(World& world, Pathing& pathing, Safety& safety, bool& kept, bool* looked = nullptr) {', 51),
    ('combat/abilities.cc', 'bool cast_at_enemies(const World& world, float walk, bool lethal_only, bool* attempted) {', 52),
    ('combat/self_abilities.cc', 'bool dash_away(const World& world, Pathing& pathing, Safety& safety, const Field& home, vec2 dead, bool plan) {', 53),
    ('economy/shop.cc', 'void note_upkeep(const World& world, Safety& safety, float damage) {', 55),
    ('model/pathing.cc', 'const Field* Pathing::approach(int group, int range) {', 7),
    ('model/safety.cc', 'bool Safety::may_reach_within(vec2 p, int turns) {', 58),
    ('model/safety.cc', 'Safety::StandReach Safety::stand_reach(vec2 p, int farthest) {', 59),
    ('model/safety.cc', 'int Safety::threats_at(vec2 p, std::array<ThreatAt, 16>& out, bool unseen_only) {', 61),
    ('model/safety.cc', 'void Safety::stand_walks(vec2 p, int farthest, StandReach& r) {', 69),
    ('model/safety.cc', 'Safety::StandRoster Safety::stand_roster(vec2 p, const StandReach& reach, int approach, bool unseen) {', 70),
]
# The fuel left on entry: (file, definition line, id), after the function's scope line.
ATS = [
    ('combat/fight.cc', 'const ChampionBelief* prey(const World& world, Pathing& pathing, Safety& safety) {', 81),
    ('economy/farm.cc', 'bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 82),
    ('combat/fight.cc', 'bool want_home(const World& world, Pathing& pathing, Safety& safety, const Memory& memory) {', 83),
    ('bot.cc', 'bool search_strikes(World& world, Pathing& pathing, Safety& safety, const Memory& memory, bool holding, bool contested) {', 84),
    ('model/turn_order.cc', 'void set_turn_order(const World& world, Safety& safety) {', 85),
    ('combat/fight.cc', 'void retreat(World& world, Pathing& pathing, Safety& safety, Memory& memory) {', 86),
]
# Exact replacements: (file, old, new).
SUBS = [
    ('util.h', '#include <vector>\n', '#include <vector>\n#include "fz.h"\n'),
    ('main.cc', '''template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
''', '''template <class F> bool run(const char* phase, F&& f) {
    debug_block({ aph::fuel_phase() = phase; });
    // world, map conditioning, comms receive, decide, turn end, comms send, debug, queue, draft
    FZ(phase[0] == 'w' ? 0 : phase[0] == 'm' || (phase[0] == 'c' && phase[6] == 'r') ? 1 : phase[0] == 'd' && phase[1] == 'e' && phase[2] == 'c' ? 2
       : phase[0] == 't' ? 3 : phase[0] == 'c' ? 4 : phase[0] == 'q' ? 5 : 63);
'''),
    ('main.cc', '''            instance.play_turn(late);
''', '''        {
            debug_block({ aph::fz::begin(); });
            instance.play_turn(late);
            debug_block({ aph::fz::end(); });
        }
'''),
    ('main.cc', '''        if (!world->is_stale())
            run("queue", [&] { queue.run(*world, *pathing, memory, start); });
''', '''        debug_block({ aph::fz::st().left_queue = aph::fz::now(); });
        if (!world->is_stale())
            run("queue", [&] { queue.run(*world, *pathing, memory, start); });
'''),
    ('main.cc', '''        // Decided in its own round, the turn end is abandoned as usual if it runs out.
''', '''        debug_block({ aph::fz::st().left_decide = aph::fz::now(); });
        // Decided in its own round, the turn end is abandoned as usual if it runs out.
'''),
    # context, at the start of the champion's turn; the decision at its end
    ('bot.cc', '''void play_turn(World& world, Pathing& pathing, Memory& memory) {
    Safety safety{world};
''', '''void play_turn(World& world, Pathing& pathing, Memory& memory) {
    debug_block({
        auto& s = fz::st();
        const auto& me = world.me();
        s.ctx = true;
        s.type = static_cast<int>(me.type) | (me.facts().passive == Passive::gem_focus ? 256 : 0);
        s.handle = static_cast<int>(static_cast<std::uint32_t>(me.handle));
        s.seen = 0, s.near = 99, s.allies = 0;
        for (const auto& e : world.enemies)
            if (e.alive && e.visible) ++s.seen, s.near = std::min(s.near, me.alive && me.pos.x >= 0 ? dist(me.pos, e.pos) : 99);
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && me.alive && dist(me.pos, a.pos) <= 6) ++s.allies;
        s.hp = me.alive && me.max_health > 0 ? static_cast<int>(100 * me.health / me.max_health) : -1;
        s.gems = me.alive ? static_cast<int>(my_gems()) : 0;
        s.hit = memory.round == world.round - 1 && me.alive && me.max_health > 0 ? static_cast<int>(100 * std::max(0.0f, memory.health - me.health) / me.max_health) : 0;
    });
    Safety safety{world};
'''),
    ('bot.cc', '''    debug_block({ std::printf("D %d %u %c %d %d\\n", world.round,''', '''    debug_block({ fz::st().decision = static_cast<char>(decision); });
    debug_block({ std::printf("D %d %u %c %d %d\\n", world.round,'''),
    ('bot.cc', '''    const bool tight = end_tight = !fuel_ok(turn_end_tight);
''', '''    const bool tight = end_tight = !fuel_ok(turn_end_tight);
    FZ(62);
'''),
    # the farm loop and the picks after it
    ('economy/farm.cc', '''    int k = 0;
    for (; k < evaluated && room(); ++k) {
''', '''    int k = 0;
    debug_block({ fz::enter(44); });
    for (; k < evaluated && room(); ++k) {
'''),
    ('economy/farm.cc', '''    read_g = -1;
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
''', '''    read_g = -1;
    debug_block({ fz::exit(); });
    if (k < evaluated) note_shortcut("farm-partial-evaluation");
'''),
    ('economy/farm.cc', '''    const int cap = best_steps + max_detour;
    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);
''', '''    const int cap = best_steps + max_detour;
    FZ(54);
    const bool search = fuel_ok(search_cost_estimate(cap) + end_reserve);
'''),
    # inside retreat_step
    ('combat/fight.cc', '''    if (!safety.avoid_within(here, vision_radius)) {
        if (!beside_held || !pathing.descend(home, held)) pathing.step_towards(home);
        return;
    }
    // A walk the dash was put off for is the plan's to choose.
    const bool walk_dash = walk_dash_deferred(world) && my_can_cast();
    const auto& avoid = safety.avoid();''', '''    debug_block({ fz::at(80); fz::enter(64); });
    const bool fz_avoid = safety.avoid_within(here, vision_radius);
    debug_block({ fz::exit(); });
    if (!fz_avoid) {
        if (!beside_held || !pathing.descend(home, held)) pathing.step_towards(home);
        return;
    }
    // A walk the dash was put off for is the plan's to choose.
    const bool walk_dash = walk_dash_deferred(world) && my_can_cast();
    debug_block({ fz::enter(64); });
    const auto& avoid = safety.avoid();
    debug_block({ fz::exit(); });'''),
    ('combat/fight.cc', '''    auto& plan = escape::plan(world, pathing, safety);
    add(false);
    if (!clear) {
        // Worth it only if the spawn leaves us healthier than the clear step away would.
        HomeWalk w(world, pathing, safety, home);
        for (int i = 0; i < n; ++i) options[i].home = w.walk_from(options[i].p, w.now());
        add(true);
    } else if (plan.active()) {''', '''    auto& plan = escape::plan(world, pathing, safety);
    debug_block({ fz::enter(65); });
    add(false);
    debug_block({ fz::exit(); });
    if (!clear) {
        // Worth it only if the spawn leaves us healthier than the clear step away would.
        debug_block({ fz::enter(66); });
        HomeWalk w(world, pathing, safety, home);
        for (int i = 0; i < n; ++i) options[i].home = w.walk_from(options[i].p, w.now());
        debug_block({ fz::exit(); fz::enter(65); });
        add(true);
        debug_block({ fz::exit(); });
    } else if (plan.active()) {'''),
    ('combat/fight.cc', '''    if (plan.active()) {
        life = my_health_and_shield(world);
        for (int i = 0; i < n; ++i)
            if (options[i].t.left) price(options[i]);
    }''', '''    if (plan.active()) {
        FZ(67);
        life = my_health_and_shield(world);
        for (int i = 0; i < n; ++i)
            if (options[i].t.left) price(options[i]);
    }'''),
    ('combat/fight.cc', '''    std::array<std::uint8_t, 8> order, group, last;
    for (int i = 0; i < n; ++i) order[i] = static_cast<std::uint8_t>(i);''', '''    std::array<std::uint8_t, 8> order, group, last;
    FZ(68);
    for (int i = 0; i < n; ++i) order[i] = static_cast<std::uint8_t>(i);'''),
    ('combat/fight.cc', '''    if (hold.keeps_us(safety)) return false;
    // Either pursuit horizon reads as far as the joiners'.''', '''    debug_block({ fz::enter(71); });
    const bool fz_keeps = hold.keeps_us(safety);
    debug_block({ fz::exit(); });
    if (fz_keeps) return false;
    // Either pursuit horizon reads as far as the joiners'.'''),
    ('economy/farm.cc', '''    int k = 0;
    debug_block({ fz::enter(44); });''', '''    int k = 0;
    debug_block({ fz::at(87); fz::enter(44); });'''),
    # the step guard: the fuel on its first entry and its last exit, and its new sims
    ('combat/guard.cc', '''        } else {
            const auto t = safety.new_fight(key);
            lost = t.lost;
            falls = t.self_falls;
        }
        if (s < static_cast<int>(settled.size())) settled[s++] = {key, !lost && !falls, lost};''', '''        } else {
            debug_block({ fz::enter(72); });
            const auto t = safety.new_fight(key);
            debug_block({ fz::exit(); });
            lost = t.lost;
            falls = t.self_falls;
        }
        if (s < static_cast<int>(settled.size())) settled[s++] = {key, !lost && !falls, lost};'''),
    ('combat/guard.cc', '''    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    static bitboard guard{cambc::uninitialized};''', '''    world.throw_if_stale();
    if (!enemy_seen(world)) return nullptr;
    debug_block({ fz::at(89); });
    struct FzExit {
        ~FzExit() { debug_block({ fz::set(88); }); }
    } fz_exit;
    static bitboard guard{cambc::uninitialized};'''),
    # marks along decide's goal steps
    ('bot.cc', '''    if (banks_bag(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked, strike_guard);
        return;
    }
    // Banked inside a camp ring: the turn-end recall is the way out (continue_recall keeps it).
    if (sealed_in(world, pathing, my_position())) return;
    if (wake_ring(world, pathing, safety)) return;''', '''    debug_block({ fz::at(90); });
    if (banks_bag(world, pathing)) {
        carry_bag(world, pathing, safety, memory, attacked, strike_guard);
        return;
    }
    debug_block({ fz::at(91); });
    // Banked inside a camp ring: the turn-end recall is the way out (continue_recall keeps it).
    if (sealed_in(world, pathing, my_position())) return;
    if (wake_ring(world, pathing, safety)) return;
    debug_block({ fz::at(92); });'''),
    ('bot.cc', '''    if (guard_turn(world, pathing, safety, memory, strike_guard)) return;
    if (chase_with_guard(world, pathing, safety, strike_guard)) return;
    if (contest_capture(world, pathing, memory)) {''', '''    debug_block({ fz::at(93); });
    if (guard_turn(world, pathing, safety, memory, strike_guard)) return;
    debug_block({ fz::at(94); });
    if (chase_with_guard(world, pathing, safety, strike_guard)) return;
    debug_block({ fz::at(95); });
    if (contest_capture(world, pathing, memory)) {'''),
    ('bot.cc', '''    decision = Branch::farm;
    if ((world.map().shared_gems && kite(world, pathing, memory)) || siege(world, pathing, safety, memory)) {''', '''    decision = Branch::farm;
    debug_block({ fz::at(73); });
    if ((world.map().shared_gems && kite(world, pathing, memory)) || siege(world, pathing, safety, memory)) {'''),
    ('bot.cc', '''    decide(world, pathing, safety, memory);
    if (decision != Branch::wait_altar) memory.wait_altar = -1;''', '''    decide(world, pathing, safety, memory);
    debug_block({ fz::at(74); });
    if (decision != Branch::wait_altar) memory.wait_altar = -1;'''),
    ('bot.cc', '''        // Only the turn order reads this turn's stuns, and this short it keeps its last rank.''', '''        debug_block({ fz::at(75); });
        // Only the turn order reads this turn's stuns, and this short it keeps its last rank.'''),
    ('bot.cc', '''    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);''', '''    debug_block({ fz::at(76); });
    comms::claim(memory.claim);
    comms::bag(world.me().alive ? static_cast<int>(my_gems()) : 0);'''),
    # silent fuel tests
    ('model/escape.cc', '''    if (!self.alive || fuel() < params::escape::min_fuel || !ready_statics(world)) return;
    const std::uint64_t start_fuel = fuel();''', '''    if (self.alive && fuel() < params::escape::min_fuel) note_shortcut("esc-min-fuel");
    if (!self.alive || fuel() < params::escape::min_fuel || !ready_statics(world)) return;
    const std::uint64_t start_fuel = fuel();'''),
    ('model/escape.cc', '''    if (active_ && !pass_[1].ready && fuel() >= params::escape::slack_fuel) run(slack_goal_, pass_[1]);''',
     '''    if (active_ && !pass_[1].ready && fuel() < params::escape::slack_fuel) note_shortcut("esc-no-slack");
    if (active_ && !pass_[1].ready && fuel() >= params::escape::slack_fuel) run(slack_goal_, pass_[1]);'''),
    ('model/escape.cc', '''    if (!fuel_ok(need)) return nullptr;
    auto& p = plans[next];''', '''    if (!fuel_ok(need)) {
        note_shortcut("chase-plan-fuel");
        return nullptr;
    }
    auto& p = plans[next];'''),
    ('economy/capture.cc', '''    if (!fuel_ok(hold_safety->fight_cost_estimate() + end_reserve)) return''', '''    if (!fuel_ok(hold_safety->fight_cost_estimate() + end_reserve)) note_shortcut("hold-threat-fuel");
    if (!fuel_ok(hold_safety->fight_cost_estimate() + end_reserve)) return'''),
    ('economy/farm.cc', '''                    if (!fuel_ok(full_field_cost_estimate() + loop_reserve())) break;''',
     '''                    if (!fuel_ok(full_field_cost_estimate() + loop_reserve())) {
                        note_shortcut("farm-field-fuel");
                        break;
                    }'''),
    ('economy/farm.cc', '''                if (!pathing.hop_ready(h) && !fuel_ok(2 * full_field_cost_estimate() + loop_reserve())) break;''',
     '''                if (!pathing.hop_ready(h) && !fuel_ok(2 * full_field_cost_estimate() + loop_reserve())) {
                    note_shortcut("farm-hop-fuel");
                    break;
                }'''),
    ('economy/farm.cc', '''            if (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve())) return;''',
     '''            if (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve())) {
                note_shortcut("carry-pick-fuel");
                return;
            }'''),
    ('model/pathing.cc', '''        if (!bumped) return r.steps == unreachable && fuel() >= fuel_floor + last_reserve && make_way(goals, nullptr, cap);''',
     '''        if (!bumped && r.steps == unreachable && fuel() < fuel_floor + last_reserve) note_shortcut("make-way-fuel");
        if (!bumped) return r.steps == unreachable && fuel() >= fuel_floor + last_reserve && make_way(goals, nullptr, cap);'''),
]


def read(name):
    return (SRC / name).read_text()


def main():
    files = {}
    def get(name):
        if name not in files: files[name] = read(name)
        return files[name]
    for name, old, new in SUBS:
        s = get(name)
        assert s.count(old) == 1, (name, old[:80], s.count(old))
        files[name] = s.replace(old, new)
    for name, sig, ident in TOPS:
        s = get(name)
        assert s.count(sig) == 1, (name, sig, s.count(sig))
        i = s.index(sig)
        j = s.index('{\n', i) + 2 if not sig.endswith('{') else i + len(sig) + 1
        files[name] = s[:j] + f'    FZ({ident});\n' + s[j:]
    for name, sig, ident in ATS:
        s = get(name)
        assert s.count(sig) == 1, (name, sig, s.count(sig))
        j = s.index(sig) + len(sig) + 1
        files[name] = s[:j] + f'    debug_block({{ fz::at({ident}); }});\n' + s[j:]
    for name, s in files.items(): (SRC / name).write_text(s)
    (SRC / 'fz.h').write_text((Path(__file__).parent / 'fz.h').read_text())
    print('instrumented', len(SUBS), 'subs,', len(TOPS), 'tops')


if __name__ == '__main__':
    main()
