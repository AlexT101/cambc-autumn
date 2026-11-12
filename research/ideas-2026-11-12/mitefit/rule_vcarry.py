"""Rule layer (mitere section 9, rule 1): groups with gold go to Vesper. Her passive pays +33% on her capture
shares, so a gold group she holds alone pays a third more. Mite's Vesper holds 56-58% of its captured base gold by
r100, ours 36%. Our Prism's carry macro (sole holder, allies leave cleared groups for a carrier due in time, the
carrier's 'G'/'L' farm picks, the hold tiles others keep off) generalised to two carriers:
- Vesper: groups with gold.
- Prism: groups with gems and no gold, or every gem group when the team has no Vesper alive.
For c520-ps-based bots (the body or ours).
With `prism`, Prism keeps every gem group and Vesper carries the pure-gold ones, and the mixed ones only when no
Prism of ours is alive.
    py rule_vcarry.py BOT_DIR [prism]"""
import sys
from pathlib import Path
src = Path(sys.argv[1]) / 'src'
PRISM_FIRST = len(sys.argv) > 2 and sys.argv[2] == 'prism'

def sub(path, old, new, count=1):
    f = src / path; s = f.read_text()
    assert s.count(old) == count, (path, old[:80], s.count(old))
    f.write_text(s.replace(old, new))

sub('bot_parts.h', 'const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G);\n',
    'const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G);\n'
    'bool carrier_type(const ChampionBelief& a);\n'
    'bool carrier_of(const World& world, const ChampionBelief& a, const CampGroup& G);\n')

C = 'economy/capture.cc'
CARRIER_OF = 'bool carrier_of(const World& world, const ChampionBelief& a, const CampGroup& G) {\n    if (G.has_monolith) return false;\n    if (a.type == cambc::champion_type::vesper_vale) return G.gold > 0;\n    if (a.facts().passive != Passive::gem_focus || G.gems <= 0) return false;\n    if (G.gold <= 0) return true;\n    for (const auto& v : world.allies)\n        if (v.alive && v.type == cambc::champion_type::vesper_vale) return false;\n    return true;\n}'
CARRIER_PF = 'bool carrier_of(const World& world, const ChampionBelief& a, const CampGroup& G) {\n    if (G.has_monolith) return false;\n    if (a.facts().passive == Passive::gem_focus) return G.gems > 0;\n    if (a.type != cambc::champion_type::vesper_vale || G.gold <= 0) return false;\n    if (G.gems <= 0) return true;\n    for (const auto& p : world.allies)\n        if (p.alive && p.facts().passive == Passive::gem_focus) return false;\n    return true;\n}'
sub(C, '// The ally that should hold G alone, the rest stepping off (yield_capture)',
    '''// Vesper's +33% gold passive makes her the carrier of groups with gold (mitere section 9); Prism, keeping its bag
// for Focus, carries the gem groups: those without gold, or all of them with no Vesper of ours alive.
bool carrier_type(const ChampionBelief& a) {
    return a.facts().passive == Passive::gem_focus || a.type == cambc::champion_type::vesper_vale;
}
bool carrier_of(const World& world, const ChampionBelief& a, const CampGroup& G) {
    if (G.has_monolith) return false;
    if (a.type == cambc::champion_type::vesper_vale) return G.gold > 0;
    if (a.facts().passive != Passive::gem_focus || G.gems <= 0) return false;
    if (G.gold <= 0) return true;
    for (const auto& v : world.allies)
        if (v.alive && v.type == cambc::champion_type::vesper_vale) return false;
    return true;
}

// The ally that should hold G alone, the rest stepping off (yield_capture)''')
# sole_capture_holder: a gold group with Vesper fit on it is hers, enemy seen or not (as Prism's gem holds).
sub(C, '    if (G.gems <= 0) return seen ? nullptr : prospector_gold_holder(world, G);\n',
    '''    bool vesper = false;
    for (const auto& a : world.allies) vesper |= a.alive && a.type == cambc::champion_type::vesper_vale;
    if (G.gems <= 0 && !(vesper && G.gold > 0)) return seen ? nullptr : prospector_gold_holder(world, G);
''')
sub(C, '        if (a.facts().passive != Passive::gem_focus || !fit_on(a, G.tiles())\n',
    '        if (!carrier_of(world, a, G) || !fit_on(a, G.tiles())\n')
# The Stellar/Marcella receiver stays a gem-group rule, and a pure-gold group without Vesper on it falls back to
# the Prospector holder as before.
sub(C, '    if (!seen && economy_three(world) && map_economy(map).stellar_map()',
    '    if (G.gems > 0 && !seen && economy_three(world) && map_economy(map).stellar_map()')
f = src / C; s = f.read_text(); i = s.index('const ChampionBelief* sole_capture_holder(const World& world, const CampGroup& G) {')
j = s.index('\n    return nullptr;\n}', i)
f.write_text(s[:j] + '\n    return G.gems <= 0 && !seen ? prospector_gold_holder(world, G) : nullptr;\n}' + s[j + len('\n    return nullptr;\n}'):])
# leave_for_prism: the carrier of G, not only Prism.
sub(C, '        if (a.is_self || !a.alive || a.facts().passive != Passive::gem_focus) continue;\n        const bool claimed',
    '        if (a.is_self || !a.alive || !carrier_of(world, a, G)) continue;\n        const bool claimed')
sub(C, '    if (g < 0 || world.me().facts().passive == Passive::gem_focus) return false;\n    const auto& G = world.map().groups[g];\n    const auto& c = world.camps[g];\n    if (G.gems <= 0 || G.has_monolith',
    '    if (g < 0) return false;\n    const auto& G = world.map().groups[g];\n    const auto& c = world.camps[g];\n'
    '    if (carrier_of(world, world.me(), G) || (G.gems <= 0 && G.gold <= 0) || G.has_monolith')
sub(C, '    const bool sole_prism = prism && prism->facts().passive == Passive::gem_focus;',
    '    const bool sole_prism = prism && carrier_type(*prism);')
sub(C, 'bool prism_carries(const World& world, Safety& safety, const CampGroup& G, bitboard& goal) {\n    if (G.gems <= 0 || G.has_monolith',
    'bool prism_carries(const World& world, Safety& safety, const CampGroup& G, bitboard& goal) {\n    if (!carrier_of(world, world.me(), G)')
sub(C, '    if (G.gems <= 0 || G.has_monolith || enemy_seen(world) || test(G.tiles(), my_position()) || sole_capture_holder(world, G)) return false;',
    '    if (!carrier_of(world, world.me(), G) || enemy_seen(world) || test(G.tiles(), my_position()) || sole_capture_holder(world, G)) return false;')
sub(C, '    return prism ? !prism->is_self && prism->facts().passive == Passive::gem_focus : left_for_prism(world, pathing, g);',
    '    return prism ? !prism->is_self && carrier_type(*prism) : left_for_prism(world, pathing, g);')
# prism_hold_tiles: every carrier's sole hold, ours included when we are the other carrier.
sub(C, '''    if (world.me().facts().passive == Passive::gem_focus) return nullptr;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || a.facts().passive != Passive::gem_focus) continue;
        const int g = world.map().group_at(a.pos);
        if (g < 0 || world.camps[g].state != CampState::cleared) return nullptr;
        const auto& G = world.map().groups[g];
        if (G.gems <= 0 || (!on_too && test(G.tiles(), my_position())) || sole_capture_holder(world, G) != &a) return nullptr;
        return &G.tiles();
    }''', '''    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !a.visible || !carrier_type(a)) continue;
        const int g = world.map().group_at(a.pos);
        if (g < 0 || world.camps[g].state != CampState::cleared) continue;
        const auto& G = world.map().groups[g];
        if (!carrier_of(world, a, G) || (!on_too && test(G.tiles(), my_position())) || sole_capture_holder(world, G) != &a) continue;
        return &G.tiles();
    }''')
sub(C, '''    if (world.me().facts().passive == Passive::gem_focus || G.gems <= 0 || c.holder != team::ally || c.held_since < 0) return false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || a.facts().passive != Passive::gem_focus || comms::claim_of(world, a.index) != g) continue;''',
    '''    if (carrier_of(world, world.me(), G) || c.holder != team::ally || c.held_since < 0) return false;
    for (const auto& a : world.allies) {
        if (a.is_self || !a.alive || !carrier_of(world, a, G) || comms::claim_of(world, a.index) != g) continue;''')
sub(C, '    if (!wins && ((prism && !prism->is_self && prism->facts().passive == Passive::gem_focus) || prism_coming(world, pathing, G, c, g)))',
    '    if (!wins && ((prism && !prism->is_self && carrier_type(*prism)) || prism_coming(world, pathing, G, c, g)))')

F = 'economy/farm.cc'
sub(F, '    const bool keeps = keeps_gems(world, pathing);\n',
    '    const bool keeps = keeps_gems(world, pathing);\n'
    '    const bool carries = keeps || world.me().type == cambc::champion_type::vesper_vale;\n')
sub(F, '    const bool taking_over = keeps && carried >= 0', '    const bool taking_over = carries && carried >= 0')
sub(F, '''    if (keeps && !banks_bag && !memory.banking) {
        world.each_cleared([&](int g) {
            const auto& G = groups[g];
            const int least = steps_to(G, here); // no walk to its tiles is shorter
            if (G.gems <= 0 || least > reach) return;''', '''    if (carries && !banks_bag && !memory.banking) {
        world.each_cleared([&](int g) {
            const auto& G = groups[g];
            const int least = steps_to(G, here); // no walk to its tiles is shorter
            if (!carrier_of(world, world.me(), G) || least > reach) return;''')

B = 'bot.cc'
sub(B, '''    if (world.me().facts().passive == Passive::gem_focus) {
        switch (decision) {''', '''    if (carrier_type(world.me())) {
        switch (decision) {''')
sub(B, '''        default: break;
        }
    // Posted, our claim on a cleared group we leave for Prism would keep it out of Prism's farm.
    } else if (world.me().alive''', '''        default: break;
        }
    }
    // Posted, our claim on a cleared group we leave for a carrier would keep it out of the carrier's farm.
    if (world.me().alive''')
if PRISM_FIRST: sub(C, CARRIER_OF, CARRIER_PF)
print('patched', src)
