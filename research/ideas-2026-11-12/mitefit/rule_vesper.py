"""Rule layer (mitere 'Early gold'): Mite's Vesper is the team's gold sink.
- Holds: Vesper takes a single-holder capture whenever it is on or beside the group (holder_value x VALUE, and its
  hold always differs), so it stands on the pack's captures (59% of Mite's capture gold by r100).
- Build: Greed-Strength first, then Bruiser-Health, then Greed-Health, then the bot's own choice.
    py rule_vesper.py BODY_DIR [VALUE=4]"""
import sys, pathlib
src = pathlib.Path(sys.argv[1]) / 'src'; k = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
def sub(f, old, new):
    s = f.read_text(); assert s.count(old) == 1, old; f.write_text(s.replace(old, new))
cap = src / 'economy/capture.cc'
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
    // Mite body (mitefit rule_vesper.py): Vesper builds Greed-Strength, Bruiser-Health, Greed-Health.
    if (world.me().type == cambc::champion_type::vesper_vale) {
        for (const auto [family, stat] : {std::pair{greed, (int)strength_stat}, std::pair{bruiser, (int)health_stat}, std::pair{greed, (int)health_stat}}) {
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
''')
print('patched', src)
