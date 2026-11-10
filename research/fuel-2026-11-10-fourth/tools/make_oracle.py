"""Add the frozen baseline Reach, sharing only the unchanged terrain helpers, as a same-state oracle.
Diagnostic debug builds only; their cache warming is excluded from fuel measurements.
"""
from pathlib import Path
import sys
base=Path('bots/variants/oc-fuel4-base/src/model')
target=Path(sys.argv[1])/'src/model'
h=(base/'safety.h').read_text();a=h.index('class Reach {');b=h.index('\n};',a)+3;h=h[a:b].replace('class Reach {','class OriginalReach {')
a=h.index('    struct Window {');b=h.index('\n    };',a)+7;h=h[:a]+'    using Window = Reach::Window;'+h[b:]
s=(base/'safety.cc').read_text();a=s.index('void Reach::build(');b=s.index('Blow Threat::at(',a);s=s[a:b].replace('Reach::','OriginalReach::')
# Bundle 4 fixes the old uint8 member limit. Keep the reference's independent
# linear lookup, widened to cover every member, so large groups test the intended rule.
helper = ''
if 'const CampTile& camp_tile' not in (target/'safety.cc').read_text():
    source=(base/'safety.cc').read_text()
    a=source.index('struct CampTile {'); b=source.index('bool live_member(',a)
    helper=source[a:b].replace('CampTile','OracleCampTile').replace('camp_tiles','oracle_camp_tiles').replace('camp_tile(', 'oracle_camp_tile(')
    helper=helper.replace('std::uint8_t','std::uint16_t').replace('255','65535').replace(' && i < 65535','')
    s=s.replace('camp_tile(world, p)','oracle_camp_tile(world, p)').replace('c.member == 255','c.member == 65535')
inc=h+'\n'+helper+s+'''
union OriginalReaches {
    constexpr OriginalReaches() {}
    std::array<OriginalReach, 16> at;
};
OriginalReaches originals;
'''
(target/'reach_oracle.inc').write_text(inc)
h=(target/'safety.h').read_text().replace('    Blow at(vec2 p) const;','    Blow at(vec2 p) const;\n    Blow at_optimized(vec2 p) const;',1);(target/'safety.h').write_text(h)
s=(target/'safety.cc').read_text();s=s.replace('void Reach::build(', '#include "reach_oracle.inc"\n\nvoid Reach::build(',1)
s=s.replace('    world_ = &world;\n    origin_ = e.pos;', '''    debug_block({ originals.at[e.index].build(world, e, turn_round, twice); });
    world_ = &world;
    origin_ = e.pos;''',1)
s=s.replace('Blow Reach::at(vec2 p) const {','''Blow Reach::at(vec2 p) const {
    const Blow out = at_optimized(p);
    debug_block({
        static unsigned checks = 0;
        const Blow ref = originals.at[owner_].at(p);
        if (std::bit_cast<std::uint32_t>(out.damage) != std::bit_cast<std::uint32_t>(ref.damage)
            || out.hits != ref.hits || out.stuns != ref.stuns)
            std::printf("REACH-ORACLE-MISMATCH %d e%d p%d,%d actual=%.9g/%d/%d expected=%.9g/%d/%d\\n",
                        world_->round, owner_, p.x, p.y, out.damage, out.hits, out.stuns, ref.damage, ref.hits, ref.stuns);
        if (++checks == 1 || checks % 4096 == 0) std::printf("REACH-ORACLE %d %u %u\\n", world_->round, my_handle(), checks);
    });
    return out;
}

Blow Reach::at_optimized(vec2 p) const {''',1)
(target/'safety.cc').write_text(s)
