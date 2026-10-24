from pathlib import Path
import difflib
root=Path('/Users/yufan/Desktop/Development/CambridgeBattlecode2026/willow-upstream-development')
prep=root/'provenance/khaos-v34-ladder-intake-20261024-v1/gem-fields-action-trace-prep'
src=root/'provenance/willow-astraeus-clock-recovery-20261024-v1/workspace/bots/service-base-f7/src'
orig=prep/'source-original'; inst=prep/'source-instrumented'
orig.mkdir(parents=True,exist_ok=True); inst.mkdir(parents=True,exist_ok=True)
for name in ('bot.cpp','abilities.cpp'):
    data=(src/name).read_text()
    (orig/name).write_text(data)
    (inst/name).write_text(data)

def sub(name, old, new, n=1):
    p=inst/name; s=p.read_text(); c=s.count(old)
    if c!=n: raise SystemExit(f'{name}: expected {n} occurrence(s), found {c}: {old[:100]!r}')
    p.write_text(s.replace(old,new,n))

sub('bot.cpp',
'''[[gnu::flatten]] bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();''',
'''[[gnu::flatten]] bool farm(World& world, Pathing& pathing, Safety& safety, Memory& memory) {
    world.throw_if_stale();
    const bool trace_ar = my_handle() == 0 && world.round >= 6 && world.round <= 7;''')
sub('bot.cpp',
'''        const auto walk = [&](const Field& field, int target) __attribute__((always_inline)) {
            return dash_across(world, pathing, field) || pathing.descend(field, zone, groups[target].centre)
                   || pathing.step_towards(field, zone, groups[target].centre);
        };''',
'''        const auto walk = [&](const Field& field, int target) __attribute__((always_inline)) {
            const bool dashed = dash_across(world, pathing, field);
            if (dashed) {
                debug_block({ if (trace_ar && target == 4) std::printf("AR_WALK r%d g%d route=dash\\n", world.round, target); });
                return true;
            }
            const bool descended = pathing.descend(field, zone, groups[target].centre);
            if (descended) {
                debug_block({ if (trace_ar && target == 4) std::printf("AR_WALK r%d g%d route=descend\\n", world.round, target); });
                return true;
            }
            const bool stepped = pathing.step_towards(field, zone, groups[target].centre);
            debug_block({ if (trace_ar && target == 4) std::printf("AR_WALK r%d g%d route=step moved%d\\n", world.round, target, static_cast<int>(stepped)); });
            return stepped;
        };''')
sub('bot.cpp',
'''        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field, g);
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.''',
'''        if (const auto* field = pathing.prepare_approach(g, walk_range(world, g), end_reserve)) return walk(*field, g);
        debug_block({ if (trace_ar && g == 4) std::printf("AR_WALK r%d g%d field=unavailable previous%d\\n", world.round, g, previous); });
        // Too short of fuel to search the way to a new choice: last turn's, whose way is known.''')
sub('bot.cpp',
'''            memory.farm_group = memory.claim = previous;
            memory.crew = false;
            return walk(*pathing.approach(previous, walk_range(world, previous)), previous);''',
'''            memory.farm_group = memory.claim = previous;
            memory.crew = false;
            debug_block({ if (trace_ar && g == 4) std::printf("AR_WALK r%d intended%d route=previous target%d\\n", world.round, g, previous); });
            return walk(*pathing.approach(previous, walk_range(world, previous)), previous);''')
sub('bot.cpp',
'''        if (const auto* centre = pathing.from_centre(g)) return pathing.descend(*centre, zone, groups[g].centre);
        note_shortcut("crow-flies-farm");
        return pathing.step_closer(groups[g].centre, zone, groups[g].centre);''',
'''        if (const auto* centre = pathing.from_centre(g)) {
            const bool moved = pathing.descend(*centre, zone, groups[g].centre);
            debug_block({ if (trace_ar && g == 4) std::printf("AR_WALK r%d g%d route=centre moved%d\\n", world.round, g, static_cast<int>(moved)); });
            return moved;
        }
        note_shortcut("crow-flies-farm");
        const bool moved = pathing.step_closer(groups[g].centre, zone, groups[g].centre);
        debug_block({ if (trace_ar && g == 4) std::printf("AR_WALK r%d g%d route=centre-fallback moved%d\\n", world.round, g, static_cast<int>(moved)); });
        return moved;''')
sub('bot.cpp',
'''    memory.farm_group = best;
    // Our fields price a dash over a hole line; live routes walk round it.''',
'''    debug_block({ if (trace_ar && best == 4) std::printf("AR_PICK r%d actor%u group%d steps%d spell%d claim%d crew%d here%d,%d\\n",
        world.round, my_handle(), best, best_steps, static_cast<int>(spell), memory.claim, static_cast<int>(memory.crew), here.x, here.y); });
    memory.farm_group = best;
    // Our fields price a dash over a hole line; live routes walk round it.''')
sub('bot.cpp',
'''    if (spell && dist(here, groups[best].centre) <= vision_radius + ability_range
        && spell_clear(world, pathing, best, zone, cap))
        return true;
    if (cast_at_camp_on_approach(world, best)) return true;
    const auto* tiles = farm_attack_tiles(world, pathing, best, range, [&] { return end_reserve + walk_reserve(best); });
    if (!tiles) {
        note_shortcut("farm-no-attack-tiles");
        walk_on(best);
        return true;
    }''',
'''    if (spell && dist(here, groups[best].centre) <= vision_radius + ability_range
        && spell_clear(world, pathing, best, zone, cap)) {
        debug_block({ if (trace_ar && best == 4) std::printf("AR_SPELL_CLEAR r%d group%d result=handled\\n", world.round, best); });
        return true;
    }
    const bool approach_cast = cast_at_camp_on_approach(world, best);
    debug_block({ if (trace_ar && best == 4) std::printf("AR_APPROACH r%d actor%u group%d spell%d returned%d\\n",
        world.round, my_handle(), best, static_cast<int>(spell), static_cast<int>(approach_cast)); });
    if (approach_cast) return true;
    const auto* tiles = farm_attack_tiles(world, pathing, best, range, [&] { return end_reserve + walk_reserve(best); });
    debug_block({ if (trace_ar && best == 4) std::printf("AR_ATTACK_TILES r%d group%d ready%d\\n", world.round, best, static_cast<int>(tiles != nullptr)); });
    if (!tiles) {
        note_shortcut("farm-no-attack-tiles");
        const bool moved = walk_on(best);
        debug_block({ if (trace_ar && best == 4) std::printf("AR_ROUTE r%d group%d route=walk-on-no-attack-tiles moved%d\\n", world.round, best, static_cast<int>(moved)); });
        return true;
    }''')
sub('bot.cpp',
'''    if (!walked)
        walked = fuel_ok(search_cost_estimate(cap) + end_reserve)
                     ? pathing.step_towards(off_zone(goals), zone, cap, groups[best].centre)
                           || pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap, groups[best].centre)
                     : (note_shortcut("farm-no-route"), walk_on(best));
    if (!walked && dasher) walk_on(best);''',
'''    if (!walked) {
        const bool enough_for_search = fuel_ok(search_cost_estimate(cap) + end_reserve);
        if (enough_for_search) {
            const bool main_route = pathing.step_towards(off_zone(goals), zone, cap, groups[best].centre);
            const bool adjacent_route = !main_route
                && pathing.step_towards(off_zone(groups[best].adjacent()), zone, cap, groups[best].centre);
            walked = main_route || adjacent_route;
            debug_block({ if (trace_ar && best == 4) std::printf("AR_ROUTE r%d group%d route=%s moved%d\\n", world.round, best,
                main_route ? "attack-tiles" : adjacent_route ? "adjacent" : "none", static_cast<int>(walked)); });
        } else {
            note_shortcut("farm-no-route");
            walked = walk_on(best);
            debug_block({ if (trace_ar && best == 4) std::printf("AR_ROUTE r%d group%d route=walk-on-fuel-short moved%d\\n", world.round, best, static_cast<int>(walked)); });
        }
    }
    if (!walked && dasher) {
        const bool fallback = walk_on(best);
        debug_block({ if (trace_ar && best == 4) std::printf("AR_ROUTE r%d group%d route=walk-on-dash-fallback moved%d\\n", world.round, best, static_cast<int>(fallback)); });
    }''')
# best_ground optional diagnostic context and count only under debug
sub('abilities.cpp',
'''Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip, const std::vector<vec2>* harmful = nullptr) {''',
'''Cast best_ground(int slot, float min_weight_value, const std::vector<Target>& targets, vec2 here, int range,
                 const bitboard& skip, const std::vector<vec2>* harmful = nullptr,
                 bool trace_ar = false, int trace_round = -1, int trace_group = -1) {''')
sub('abilities.cpp',
'''    static bitboard centres{cambc::uninitialized};
    clear_board(centres);''',
'''    int trace_rejected = 0, trace_max_hits = -1;
    float trace_max_rejected_value = 0;
    vec2 trace_max_rejected_centre{-1, -1};
    static bitboard centres{cambc::uninitialized};
    clear_board(centres);''', n=1)
sub('abilities.cpp',
'''            if (hits < 2) continue;
        }
        best.slot = slot, best.value = v, best.tile = c;
    }
    return best;''',
'''            if (hits < 2) {
                debug_block({
                    if (trace_ar) {
                        ++trace_rejected;
                        if (v > trace_max_rejected_value) {
                            trace_max_rejected_value = v;
                            trace_max_rejected_centre = c;
                            trace_max_hits = hits;
                        }
                    }
                });
                continue;
            }
        }
        best.slot = slot, best.value = v, best.tile = c;
    }
    debug_block({ if (trace_ar) std::printf("AR_GROUND r%d g%d slot%d targets%zu harmful%zu rejected_lt2%d maxRejected%.3f hits%d centre%d,%d selected%.3f tile%d,%d\\n",
        trace_round, trace_group, slot, targets.size(), harmful ? harmful->size() : 0, trace_rejected,
        static_cast<double>(trace_max_rejected_value), trace_max_hits, trace_max_rejected_centre.x, trace_max_rejected_centre.y,
        static_cast<double>(best.value), best.tile.x, best.tile.y); });
    return best;''')
# scope camp_cast, preserve native query call sequence
sub('abilities.cpp',
'''Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value, bool approach = false) {
    if (!my_can_cast()) return {};
    const auto& f = world.me().facts();''',
'''Cast camp_cast(const World& world, int group, bool attackers_only, bool any_value, bool approach = false) {
    const bool trace_ar = approach && group == 4 && my_handle() == 0 && world.round >= 6 && world.round <= 7;
    if (!my_can_cast()) {
        debug_block({ if (trace_ar) std::printf("AR_CAMP r%d g%d reject=my-can-cast\\n", world.round, group); });
        return {};
    }
    const auto& f = world.me().facts();''')
sub('abilities.cpp',
'''    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];''',
'''    const bool stuns = (ready[0] && f.abilities[0].stuns) || (ready[1] && f.abilities[1].stuns);
    const vec2 here = my_position();
    const auto& g = world.map().groups[group];''')
sub('abilities.cpp',
'''    if (enemy_within(world, here, hold_range)) return {};
    // A ranged walk also spends the basic: require our native position to be unchanged.''',
'''    const bool enemy_hold = enemy_within(world, here, hold_range);
    if (enemy_hold) {
        debug_block({ if (trace_ar) std::printf("AR_CAMP r%d g%d reject=enemy-within-hold-range\\n", world.round, group); });
        return {};
    }
    // A ranged walk also spends the basic: require our native position to be unchanged.''')
sub('abilities.cpp',
'''    if (members.empty()) return {};
    // A spell clear has no basic attack to finish an attacker under the usual floor:''',
'''    if (members.empty()) {
        debug_block({ if (trace_ar) std::printf("AR_CAMP r%d g%d members0 harmful%zu\\n", world.round, group, harmful.size()); });
        return {};
    }
    debug_block({ if (trace_ar) std::printf("AR_CAMP_MEMBERS r%d g%d ready%d,%d members%zu harmful%zu allVisible%d\\n",
        world.round, group, static_cast<int>(ready[0]), static_cast<int>(ready[1]), members.size(), harmful.size(), static_cast<int>(all_visible)); });
    // A spell clear has no basic attack to finish an attacker under the usual floor:''')
sub('abilities.cpp',
'''            best.offer(best_ground(s, finishes ? 0.0f : any_value ? 1.0f : floor_value, targets, here, a.range(), skip,
                                   approach && !harmless_approach ? &harmful : nullptr));''',
'''            best.offer(best_ground(s, finishes ? 0.0f : any_value ? 1.0f : floor_value, targets, here, a.range(), skip,
                                   approach && !harmless_approach ? &harmful : nullptr,
                                   trace_ar, world.round, group));''')
sub('abilities.cpp',
'''    return best;
}

} // namespace

bool enemy_tribute_wins''',
'''    debug_block({ if (trace_ar) std::printf("AR_CAMP_CHOICE r%d g%d slot%d value%.3f tile%d,%d\\n",
        world.round, group, best.slot, static_cast<double>(best.value), best.tile.x, best.tile.y); });
    return best;
}

} // namespace

bool enemy_tribute_wins''')
# rewrite approach gates so each original expression is evaluated once in the same short-circuit order.
sub('abilities.cpp',
'''bool cast_at_camp_on_approach(const World& world, int group) {
    world.throw_if_stale();
    if (world.me().type != cambc::champion_type::prism
        || (!world.me().ability_ready(0, world.round) && !world.me().ability_ready(1, world.round))
        || !my_can_cast() || walked(world))
        return false;
    const auto& c = world.camps[group];
    if (c.state != CampState::alive) return false;
    const auto& map = world.map();
    const auto& g = map.groups[group];
    const bool harmless = g.strength <= 0;
    if (harmless ? g.members.size() <= 1 : c.awake != Awake::awake) return false;
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    for (std::size_t i = 0; i < g.members.size(); ++i)
        if ((harmless || c.health[i] > 0) && dist(here, g.members[i].pos) <= range && cambc::vision::has_camp(g.members[i].pos))
            return false;
    for (int other : map.groups_near(here, map.max_camp_reach)) {
        if (world.camps[other].state != CampState::alive) continue;
        const auto& members = map.groups[other].members;
        for (std::size_t i = 0; i < members.size(); ++i)
            if (world.camps[other].health[i] > 0 && members[i].strength > 0 && dist(here, members[i].pos) <= members[i].reach)
                return false;
    }
    try {
        const auto selected = camp_cast(world, group, false, false, true);
        world.throw_if_stale();
        const bool cast = selected.execute();
        world.throw_if_stale();
        camp_hits() += cast;
        return cast;
    } catch (const cambc::error&) {
        return false;
    }
}''',
'''bool cast_at_camp_on_approach(const World& world, int group) {
    world.throw_if_stale();
    const bool trace_ar = group == 4 && my_handle() == 0 && world.round >= 6 && world.round <= 7;
    if (world.me().type != cambc::champion_type::prism) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=not-prism\\n", world.round, group); });
        return false;
    }
    const bool ready0 = world.me().ability_ready(0, world.round);
    const bool ready = ready0 || world.me().ability_ready(1, world.round);
    if (!ready) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=no-slot-ready\\n", world.round, group); });
        return false;
    }
    if (!my_can_cast()) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=my-can-cast\\n", world.round, group); });
        return false;
    }
    if (walked(world)) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=already-walked\\n", world.round, group); });
        return false;
    }
    const auto& c = world.camps[group];
    if (c.state != CampState::alive) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=group-state state%d\\n", world.round, group, static_cast<int>(c.state)); });
        return false;
    }
    const auto& map = world.map();
    const auto& g = map.groups[group];
    const bool harmless = g.strength <= 0;
    if (harmless ? g.members.size() <= 1 : c.awake != Awake::awake) {
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=group-awake harmless%d awake%d\\n",
            world.round, group, static_cast<int>(harmless), static_cast<int>(c.awake)); });
        return false;
    }
    const vec2 here = my_position();
    const int range = world.me().facts().attack_range();
    for (std::size_t i = 0; i < g.members.size(); ++i) {
        if (!(harmless || c.health[i] > 0)) continue;
        const int d = dist(here, g.members[i].pos);
        if (d > range) continue;
        if (!cambc::vision::has_camp(g.members[i].pos)) continue;
        debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=basic-range member%zu distance%d range%d\\n", world.round, group, i, d, range); });
        return false;
    }
    for (int other : map.groups_near(here, map.max_camp_reach)) {
        if (world.camps[other].state != CampState::alive) continue;
        const auto& members = map.groups[other].members;
        for (std::size_t i = 0; i < members.size(); ++i) {
            if (world.camps[other].health[i] <= 0) continue;
            if (members[i].strength <= 0) continue;
            const int d = dist(here, members[i].pos);
            if (d > members[i].reach) continue;
            debug_block({ if (trace_ar) std::printf("AR_GATE r%d g%d reject=damaging-camp-exposure other%d member%zu distance%d reach%d\\n",
                world.round, group, other, i, d, members[i].reach); });
            return false;
        }
    }
    try {
        const auto selected = camp_cast(world, group, false, false, true);
        debug_block({ if (trace_ar) std::printf("AR_SELECTED r%d g%d slot%d value%.3f tile%d,%d\\n",
            world.round, group, selected.slot, static_cast<double>(selected.value), selected.tile.x, selected.tile.y); });
        world.throw_if_stale();
        const bool cast = selected.execute();
        world.throw_if_stale();
        camp_hits() += cast;
        debug_block({ if (trace_ar) std::printf("AR_EXECUTE r%d g%d slot%d result%d\\n", world.round, group, selected.slot, static_cast<int>(cast)); });
        return cast;
    } catch (const cambc::error&) {
        debug_block({ if (trace_ar) std::printf("AR_EXECUTE r%d g%d error\\n", world.round, group); });
        return false;
    }
}''')
# Emit unified review patch from exact source before to generated instrumented result.
diff=[]
for name in ('bot.cpp','abilities.cpp'):
    a=(orig/name).read_text().splitlines(True); b=(inst/name).read_text().splitlines(True)
    diff.extend(difflib.unified_diff(a,b,fromfile=f'a/{name}',tofile=f'b/{name}'))
(prep/'action-realization-instrumentation-v2.patch').write_text(''.join(diff))
print('instrumented',[(name,(inst/name).stat().st_size) for name in ('bot.cpp','abilities.cpp')])
