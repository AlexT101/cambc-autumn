"""Rule layer (mitere 'Early gold'): Mite's Vesper is the team's gold sink.
- Holds: Vesper takes a single-holder capture whenever it is on or beside the group (holder_value x VALUE, and its
  hold always differs), so it stands on the pack's captures (59% of Mite's capture gold by r100).
- Build: Greed-Strength first, then Bruiser-Health, then Greed-Health, then the bot's own choice; --build sets the
  order (family-stat, stat s/h/f), e.g. --build greed-s,greed-h,bruiser-s.
VALUE 0 leaves the holds alone (the build only, e.g. on top of rule_vcarry.py).
    py rule_vesper.py BODY_DIR [VALUE=4] [--build F-S,...]"""
import sys, pathlib
argv = sys.argv[1:]; order = 'greed-s,bruiser-h,greed-h'
if '--build' in argv: i = argv.index('--build'); order = argv[i + 1]; del argv[i:i + 2]
src = pathlib.Path(argv[0]) / 'src'; k = float(argv[1]) if len(argv) > 1 else 4.0
STAT = {'s': 'strength_stat', 'h': 'health_stat', 'f': 'focus_stat'}
pins = ', '.join('std::pair{%s, (int)%s}' % (f, STAT[t]) for f, t in (x.split('-') for x in order.split(',')))
def sub(f, old, new):
    s = f.read_text(); assert s.count(old) == 1, old; f.write_text(s.replace(old, new))
cap = src / 'economy/capture.cc'
if k:
  sub(cap, '''    return hold_shy(world, a) ? params::pair_hold_share * value : value;
}''', '''    // Mite body (mitefit rule_vesper.py): its Vesper takes the holds.
    if (a.type == cambc::champion_type::vesper_vale) return %.1ff * value;
    return hold_shy(world, a) ? params::pair_hold_share * value : value;
}''' % k)
  sub(cap, '''bool multiplies(const ChampionBelief& a, const CampGroup& G) { return G.gold > 0 || (G.gems > 0 && a.facts().tribute_gold_per_gem() > 0); }''',
    '''bool multiplies(const ChampionBelief& a, const CampGroup& G) {
    return G.gold > 0 || (G.gems > 0 && a.facts().tribute_gold_per_gem() > 0) || a.type == cambc::champion_type::vesper_vale;
}''')
shop = src / 'economy/shop.cc'
sub(shop, '''    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    if (picks < 3 || picks > 5) return current_emblem(world, bought, items);
    const auto& owned = items ? *items : my_items();
    if (begun_emblem(world, owned)) return current_emblem(world, bought, items);
''', '''    const int picks = economy_pick_count(world), type = static_cast<int>(world.me().type);
    const auto& owned = items ? *items : my_items();
    // Mite body (mitefit rule_vesper.py): Vesper's emblem order.
    if (world.me().type == cambc::champion_type::vesper_vale) {
        for (const auto [family, stat] : {%s}) {
            if (owned[emblem_of(family, stat)] > 0) continue;
            struct Pin {
                Pin(int f, int s) { pin_family = f, pin_stat = s; }
                ~Pin() { pin_family = -1; }
            } pin{family, stat};
            return current_emblem(world, bought, items);
        }
    }
    if (picks < 3 || picks > 5) return current_emblem(world, bought, items);
    if (begun_emblem(world, owned)) return current_emblem(world, bought, items);
''' % pins)
print('patched', src)
