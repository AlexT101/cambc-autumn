"""mktrace.py SRC: add the fuelaware debug trace to a copy of chy-525f (or a candidate built on it). Debug builds only:
every line is inside debug_block, so a release build of the copy plays as its source does.

  FLD round champion kind cost left where   a static field built (where: q = the turn-end queue, d = the turn)
  FG  round champion site made              a fuel test before a field read: made 1 = the field is there (free),
                                            2 = not made but the fuel passes (built now), 0 = cut
  TE  round champion start decided end stage  fuel at the turn's start, after decide, at its end; the queue's last stage
plus util.h's debug_fuel lines (fuel r.. c.. label=used ..).
"""
import re, sys
from pathlib import Path

src = Path(sys.argv[1])


def sub(path, old, new, count=1):
    p = src / path
    s = p.read_text()
    if s.count(old) < 1:
        raise SystemExit(f'{path}: not found: {old[:70]!r}')
    if count and s.count(old) != count:
        raise SystemExit(f'{path}: {s.count(old)} matches, wanted {count}: {old[:70]!r}')
    p.write_text(s.replace(old, new))


sub('util.h', 'inline constexpr bool debug_fuel = false;', 'inline constexpr bool debug_fuel = true;')
sub('util.h', '''inline void note_shortcut(const char* what) {''', '''inline bool& fa_in_queue() {
    static bool q = false;
    return q;
}
inline int& fa_stage() {
    static int s = 0;
    return s;
}
inline void fa_field(const char* kind, unsigned long long cost) {
    debug_block({
        if (!cambc::is_draft())
            std::printf("FLD %d %u %s %llu %llu %c\\n", cambc::round_number(),
                        static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), kind, cost,
                        static_cast<unsigned long long>(cambc::fuel_remaining()), fa_in_queue() ? 'q' : 'd');
    });
}
inline void fa_gate(const char* site, int made) {
    debug_block({
        std::printf("FG %d %u %s %d\\n", cambc::round_number(),
                    static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())), site, made);
    });
}

inline void note_shortcut(const char* what) {''')

# pathing: a kind for every cached field
sub('model/pathing.h', 'const Field& cached(Slot& slot, const bitboard& goals);',
    'const Field& cached(Slot& slot, const bitboard& goals, const char* kind = "other");')
sub('model/pathing.cc', '''const Field& Pathing::cached(Slot& slot, const bitboard& goals) {
    if (!slot) {
        FuelMeter meter{"field"};
        // Fill the slot only once computed, so a failure leaves it empty to retry.
        slot = make_field(static_walls(), goals);
    }''', '''const Field& Pathing::cached(Slot& slot, const bitboard& goals, const char* kind) {
    if (!slot) {
        FuelMeter meter{"field"};
        const auto fa_before = cambc::fuel_remaining();
        // Fill the slot only once computed, so a failure leaves it empty to retry.
        slot = make_field(static_walls(), goals);
        fa_field(kind, fa_before - cambc::fuel_remaining());
    }''')
sub('model/pathing.cc', 'cached(ally_spawn_, map().ally_spawn)', 'cached(ally_spawn_, map().ally_spawn, "ally_spawn")')
sub('model/pathing.cc', 'cached(altar_slot(altar), map().altars[altar].tribute_tiles())',
    'cached(altar_slot(altar), map().altars[altar].tribute_tiles(), "altar")')
sub('model/pathing.cc', 'return cached(any_altar_, goals);', 'return cached(any_altar_, goals, "any_altar");')
sub('model/pathing.cc', 'cached(entry(hop_fields_, map().hops().size(), hop), map().hops()[hop].sources)',
    'cached(entry(hop_fields_, map().hops().size(), hop), map().hops()[hop].sources, "hop")')
sub('model/pathing.cc', 'cached(entry(landing_fields_, map().hops().size(), hop), map().hops()[hop].landings)',
    'cached(entry(landing_fields_, map().hops().size(), hop), map().hops()[hop].landings, "landing")')
sub('model/pathing.cc', 'cached(entry(group_fields_, map().groups.size(), group), map().groups[group].tiles())',
    'cached(entry(group_fields_, map().groups.size(), group), map().groups[group].tiles(), "group")')
sub('model/pathing.cc', 'cached(spawn_centre_, single(tile))', 'cached(spawn_centre_, single(tile), "spawn_centre")')
sub('model/pathing.cc', 'cached(slot, single(map().groups[group].centre));', 'cached(slot, single(map().groups[group].centre), "centre_whole");')
sub('model/pathing.cc', 'cached(slot, single(map().groups[g].centre));', 'cached(slot, single(map().groups[g].centre), "centre_whole");', 2)
sub('model/pathing.cc', '''        FuelMeter meter{"field"};
        slot = make_field(map().blocked_for_us, map().groups[group].tiles());''', '''        FuelMeter meter{"field"};
        const auto fa_before = cambc::fuel_remaining();
        slot = make_field(map().blocked_for_us, map().groups[group].tiles());
        fa_field("group_walk", fa_before - cambc::fuel_remaining());''')
sub('model/pathing.cc', '''    slot = make_field(static_walls(), single(map().groups[group].centre), unreachable, &layers);
    while (cap <= layers) cap *= 2;''', '''    const auto fa_before = cambc::fuel_remaining();
    slot = make_field(static_walls(), single(map().groups[group].centre), unreachable, &layers);
    fa_field("centre", fa_before - cambc::fuel_remaining());
    while (cap <= layers) cap *= 2;''')
sub('model/pathing.cc', '''    slot = make_field(static_walls(), single(map().groups[group].centre), try_cap, &layers);
    if (!slot) cap = 2 * try_cap;''', '''    const auto fa_before = cambc::fuel_remaining();
    slot = make_field(static_walls(), single(map().groups[group].centre), try_cap, &layers);
    fa_field(slot ? "centre" : "centre_cut", fa_before - cambc::fuel_remaining());
    if (!slot) cap = 2 * try_cap;''')

# the fuel tests before a group field's read
sub('economy/farm.cc', '''            if (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve())) return;''',
    '''            fa_gate("carry", pathing.group_ready(g) ? 1 : fuel_ok(full_field_cost_estimate() + loop_reserve()) ? 2 : 0);
            if (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve())) return;''')
sub('economy/farm.cc', '''            if (seen || (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve()))) continue;''',
    '''            if (!seen) fa_gate("crewq", pathing.group_ready(g) ? 1 : fuel_ok(full_field_cost_estimate() + loop_reserve()) ? 2 : 0);
            if (seen || (!pathing.group_ready(g) && !fuel_ok(full_field_cost_estimate() + loop_reserve()))) continue;''')
sub('economy/capture.cc', '''        if (!pathing.group_walking_ready(g) && !fuel_ok(full_field_cost_estimate() + end_reserve)) return e.eta = -1;''',
    '''        fa_gate("eta1", pathing.group_walking_ready(g) ? 1 : fuel_ok(full_field_cost_estimate() + end_reserve) ? 2 : 0);
        if (!pathing.group_walking_ready(g) && !fuel_ok(full_field_cost_estimate() + end_reserve)) return e.eta = -1;''')
sub('economy/capture.cc', '''    if (unmade > 0 && !fuel_ok(static_cast<std::uint64_t>(unmade) * full_field_cost_estimate() + end_reserve)) return e.eta = -1;''',
    '''    fa_gate("eta2", unmade == 0 ? 1 : fuel_ok(static_cast<std::uint64_t>(unmade) * full_field_cost_estimate() + end_reserve) ? 2 : 0);
    if (unmade > 0 && !fuel_ok(static_cast<std::uint64_t>(unmade) * full_field_cost_estimate() + end_reserve)) return e.eta = -1;''')
sub('economy/capture.cc', '''    const bool walks = pathing.group_walking_ready(g) || fuel_ok(full_field_cost_estimate() + end_reserve);''',
    '''    const bool walks = pathing.group_walking_ready(g) || fuel_ok(full_field_cost_estimate() + end_reserve);
    fa_gate("leave", pathing.group_walking_ready(g) ? 1 : walks ? 2 : 0);''')

# main: the queue's stages and the turn's fuel
m = src / 'main.cc'
s = m.read_text()


def rep(old, new):
    global s
    if s.count(old) != 1:
        raise SystemExit(f'main.cc: {s.count(old)} matches: {old[:70]!r}')
    s = s.replace(old, new)


rep('''        const auto room = [&] { return aph::fuel_ok(floor + tile_reserve); };
        if (!room()) return;''', '''        const auto room = [&] { return aph::fuel_ok(floor + tile_reserve); };
        if (!room()) return;
        debug_block({ aph::fa_stage() = 1; });''')
rep('''        aph::prepare_next_turn(world, pathing, memory, floor);
        if (world.is_stale()) return;''', '''        debug_block({ aph::fa_stage() = 2; });
        aph::prepare_next_turn(world, pathing, memory, floor);
        if (world.is_stale()) return;
        debug_block({ aph::fa_stage() = 3; });''')
rep('''        if (!map_warmed_up) return;''', '''        if (!map_warmed_up) return;
        debug_block({ aph::fa_stage() = 4; });''')
rep('''            (void)pathing.foot();
            foot_warmed = true;
        }''', '''            (void)pathing.foot();
            foot_warmed = true;
        }
        debug_block({ aph::fa_stage() = 5; });''')
rep('''            const bool centres = pathing.warm_centres(reserve, memory.farm_group);''', '''            const bool centres = pathing.warm_centres(reserve, memory.farm_group);
            debug_block({ if (centres) aph::fa_stage() = 6; });''')
rep('''            if (!warmed_up) return;
        }''', '''            if (!warmed_up) return;
        }
        debug_block({ aph::fa_stage() = 7; });''')
rep('''        if (!clears_warmed && !(clears_warmed = aph::warm_clears(world, floor))) return;''',
    '''        if (!clears_warmed && !(clears_warmed = aph::warm_clears(world, floor))) return;
        debug_block({ aph::fa_stage() = 8; });''')
rep('''        if (!warm_drafted_tiles(map, pathing, me.facts().attack_range(), memory.farm_group, floor)) return;
        if (me.pos.x >= 0) around(me.pos, me.alive ? own_radius : 2 * own_radius);''',
    '''        if (!warm_drafted_tiles(map, pathing, me.facts().attack_range(), memory.farm_group, floor)) return;
        debug_block({ aph::fa_stage() = 9; });
        if (me.pos.x >= 0 && around(me.pos, me.alive ? own_radius : 2 * own_radius)) {
            debug_block({ aph::fa_stage() = 10; });
        }''')
rep('''        const auto start = aph::fuel();
        aph::FuelMeter meter{"turn"};''', '''        const auto start = aph::fuel();
        std::uint64_t fa_decided = 0;
        debug_block({ aph::fa_stage() = 0, aph::fa_in_queue() = false; });
        struct FaEnd {
            std::uint64_t start;
            const std::uint64_t& decided;
            std::uint32_t round;
            ~FaEnd() {
                debug_block({
                    if (cambc::round_number() == round)
                        std::printf("TE %u %u %llu %llu %llu %d\\n", round, static_cast<unsigned>(static_cast<cambc::handle_champion_t>(cambc::self())),
                                    static_cast<unsigned long long>(start), static_cast<unsigned long long>(decided),
                                    static_cast<unsigned long long>(cambc::fuel_remaining()), aph::fa_stage());
                });
            }
        } fa_end{start, fa_decided, cambc::round_number()};
        aph::FuelMeter meter{"turn"};''')
rep('''        // Decided in its own round, the turn end is abandoned as usual if it runs out.''',
    '''        debug_block({ fa_decided = aph::fuel(); });
        // Decided in its own round, the turn end is abandoned as usual if it runs out.''')
rep('''            run("queue", [&] { queue.run(*world, *pathing, memory, start); });''',
    '''            run("queue", [&] {
                debug_block({ aph::fa_in_queue() = true; });
                queue.run(*world, *pathing, memory, start);
                debug_block({ aph::fa_in_queue() = false; });
            });''')
m.write_text(s)
print('traced', src)
