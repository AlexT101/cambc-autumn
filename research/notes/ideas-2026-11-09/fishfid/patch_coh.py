"""Cohesion (Flp4 / Mt3r): Fish joins, never partitions (FISH_MODEL 11, 7.2's ally_closer). In farm's group choice, a
group with no visible off-spawn ally nearer to it than we are is worth `lone` x its value, so bodies go where their
teammates are. Scaling values down keeps every prune's upper bound an upper bound.
Usage: patch_coh.py BOT_DIR LONE"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/economy/farm.cc'; lone = float(sys.argv[2]); s = p.read_text()
def sub(old, new):
    global s; assert s.count(old) == 1, old; s = s.replace(old, new)
sub('''    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
''', '''    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
    // Cohesion (body): a group no visible off-spawn ally is nearer to than we are is worth less.
    const auto lone = [&](int g) {
        const vec2 c = map.groups[g].centre;
        const int mine = dist(here, c);
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && !test(map.ally_spawn, a.pos) && dist(a.pos, c) < mine) return 1.0f;
        return %ff;
    };
''' % lone)
sub('''                                * (op && memory.claim == g ? crew_hold(g) : 1.0f);
''', '''                                * (op && memory.claim == g ? crew_hold(g) : 1.0f) * lone(g);
''')
sub('''            if (damage > spare_health && !ally_engaged(world, g)) {
''', '''            value *= lone(g);
            if (damage > spare_health && !ally_engaged(world, g)) {
''')
sub('''        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;
''', '''        value *= lone(g);
        if (g == memory.mono_group) mono_seen = value;
        if (late) continue;
''')
p.write_text(s)
