"""Rule layer (mitere 'Packing'): Mite clears groups with the team pack in the opening (2.47 bodies a clear before
r200). In farm's group choice before round PACK_UNTIL, a group with no visible off-spawn ally nearer to it than we are
is worth LONE x its value (as fishfid/patch_coh.py's Fish cohesion; scaling values down keeps every prune's upper
bound an upper bound). With LEAD=vesper, a team with Vesper alive packs on her: only a visible Vesper nearer to the
group than we are lifts the discount (Vesper herself chooses freely), so the pack clears where she captures.
    py rule_pack.py BODY_DIR [LONE=0.5] [PACK_UNTIL=200] [LEAD=any|vesper]"""
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'src/economy/farm.cc'; s = p.read_text()
lone = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5; until = int(sys.argv[3]) if len(sys.argv) > 3 else 200
lead = sys.argv[4] if len(sys.argv) > 4 else 'any'
def sub(old, new):
    global s; assert s.count(old) == 1, old; s = s.replace(old, new)
sub('''    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
''', '''    const auto is_claimed = [&](int g) __attribute__((always_inline)) { return g < 256 && (claimed_bits[g >> 6] >> (g & 63) & 1); };
    // Mite body (mitefit rule_pack.py): in the opening, a group no visible off-spawn ally is nearer to is worth less.
    const auto lone = [&](int g) {
        if (world.round >= %d) return 1.0f;
        const vec2 c = map.groups[g].centre;
        const int mine = dist(here, c);
        bool lead = false;
        for (const auto& a : world.allies)
            if (a.alive && a.type == cambc::champion_type::vesper_vale) lead = %s;
        if (lead && world.me().type == cambc::champion_type::vesper_vale) return 1.0f;
        for (const auto& a : world.allies)
            if (!a.is_self && a.alive && a.visible && !test(map.ally_spawn, a.pos) && dist(a.pos, c) < mine
                && (!lead || a.type == cambc::champion_type::vesper_vale)) return 1.0f;
        return %ff;
    };
''' % (until, 'true' if lead == 'vesper' else 'false', lone))
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
p.write_text(s); print('patched', p)
