from pathlib import Path
import sys
p=Path(sys.argv[1])/'src'
s=(p/'model/safety.cc').read_text();a=s.index('// By tile, once looked up: its camp group');b=s.index('bool live_member(',a);s=s[:a]+s[b:]
s=s.replace('''                const auto& c = camp_tile(world, p);
                if (c.group < 0 || c.member == 255 || !live_member(world, c.group, c.member)) continue;''','''                const int group = world.map().group_at(p), member = world.map().camp_member_at(p);
                if (group < 0 || member < 0 || !live_member(world, group, member)) continue;''')
s=s.replace('pointblank_range','from_here_range').replace('pointblank','from_here')
s=s.replace('        // Every movement set contains the origin; all attacks reach a neighbour that is outside bushes.', '        // Every movement set contains the origin. Seeing the target from there settles every way within this range.')
s=s.replace('        // Strike must bound Reach: blow() cuts at Strike\'s reach.', '        // Do not build deferred geometry under the debug fuel refund. Strike must bound any geometry already built.')
s=s.replace('''    if ((sets_reusable_ || (!splash_ && sets_built_ && sets_camps_version_ == world.camp_geometry_version)) && sets_origin_ == origin_ && sets_kind_ == kind && sets_occupied_.lo == occupied.lo
        && sets_occupied_.hi == occupied.hi && sets_fixed_.lo == fixed.lo && sets_fixed_.hi == fixed.hi) {''','''    if ((sets_reusable_ || (!splash_ && sets_built_ && sets_camps_version_ == world.camp_geometry_version))
        && sets_origin_ == origin_ && sets_kind_ == kind && sets_occupied_.lo == occupied.lo && sets_occupied_.hi == occupied.hi
        && sets_fixed_.lo == fixed.lo && sets_fixed_.hi == fixed.hi) {''')
(p/'model/safety.cc').write_text(s)
h=(p/'model/safety.h').read_text().replace('pointblank_range','from_here_range').replace('pointblank','from_here')
h=h.replace('#include <span>', '#include <span>\n#include <type_traits>')
h=h.replace('    // and no camp lies in its window.', '    // and camp occupancy is unchanged (Varg still rebuilds its splash units near camps).')
(p/'model/safety.h').write_text(h)
h=(p/'model/world.h').read_text().replace('    int camp_member_at(vec2 p) const {', '    // Member on a camp tile, or -1; the first lookup indexes its whole group.\n    int camp_member_at(vec2 p) const {');(p/'model/world.h').write_text(h)
s=(p/'combat/plan.cc').read_text().replace('#include <wasm_simd128.h>', '#if defined(__wasm_simd128__)\n#include <wasm_simd128.h>\n#endif')
s=s.replace('''[[gnu::always_inline]] inline Node copy_node(const Node& from) {
    static_assert''','''// A bulk copy charges per byte; fixed vector loads and stores copy the same representation.
[[gnu::always_inline]] inline Node copy_node(const Node& from) {
#if defined(__wasm_simd128__)
    static_assert''').replace('''    return to;
}

// A sequence''','''    return to;
#else
    return from;
#endif
}

// A sequence''')
(p/'combat/plan.cc').write_text(s)
