"""Flp2: Fish body fidelity on top of patch_fm (spar-dvnK-Flp -> -Flp2), from Fish's ladder replays since 2026-11-08T16.
- banking: a non-Prism bag is held (farmed on as if empty-handed) while gems < 8 * (altar_walk - 2),
  FISH_MODEL 8.3's tribute rule, in place of the flat 25-gem floor: far carriers grow big bags.
- emblems: each Fish champion's modal emblem order by ordinal (possq.py), the same at every pick count.
Usage: patch_fish2.py BOT_DIR [all|bank|emb]"""
import re, sys, pathlib
d = pathlib.Path(sys.argv[1]) / 'src'
part = sys.argv[2] if len(sys.argv) > 2 else 'all'
F = dict(monster=0, power=1, durability=2, treasure=3, jungle=4, home=5, bruiser=6, tribute=7, capture=8, prospector=9,
         hunter=10, skirmish=11, greed=12, collectors=13)
S = dict(S=0, F=1, H=2)
def seq(s): return [F[x.split('-')[0].lower()] * 3 + S[x.split('-')[1]] for x in s.split()]
ORDER = {
    'vesper_vale': 'Capture-S Treasure-S Jungle-S Prospector-H Monster-S Hunter-H Durability-H Collectors-S Bruiser-S Bruiser-S Bruiser-H Bruiser-S',
    'vendetta': 'Capture-H Jungle-S Monster-S Hunter-H Durability-H Collectors-S Bruiser-S Bruiser-S Bruiser-S Bruiser-S Bruiser-S Bruiser-S',
    'heart_of_ruin': 'Prospector-F Capture-H Jungle-F Monster-F Hunter-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H',
    'cassi': 'Power-F Durability-F Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H',
    'issac': 'Prospector-H Bruiser-H Durability-H Power-S Power-S Power-S Power-S Power-S Power-S Power-S Power-S Power-S',
    'willow': 'Prospector-H Power-S Home-H Durability-H Power-S Power-S Power-S Power-S Power-S Power-S Power-S Power-S',
    'marcella': 'Prospector-F Capture-F Jungle-F Monster-F Treasure-H Durability-H Bruiser-F Bruiser-F Bruiser-H Bruiser-F Bruiser-F Bruiser-H',
    'prism': 'Prospector-H Hunter-H Jungle-H Capture-H Durability-H Greed-H Skirmish-H Treasure-H Bruiser-H Bruiser-H Bruiser-H Bruiser-H',
    'ren': 'Prospector-H Treasure-F Bruiser-H Durability-H Power-F Power-F Jungle-H Power-F Power-F Power-F Power-F Power-F',
}
t = d / 'economy/emblem_table.h'; s = t.read_text(); n = 0
for name, o in ORDER.items():
    v = seq(o); assert len(v) == 12
    s, k = re.subn(r'\{[0-9, ]+\}, // ' + name + r'\n', '{' + ', '.join(map(str, v)) + '}, // ' + name + '\n', s); n += k
assert n == 3 * len(ORDER), n
if part != 'bank': t.write_text(s)
b = d / 'economy/bank.cc'; s = b.read_text()
old = '    if (bag < params::min_bank && !winning_bag(world) && !closing(world, pathing)) return 0;\n'
new = ('    if (!winning_bag(world) && !closing(world, pathing)) {\n'
       '        const int walk = altar_steps(world, pathing, my_position(), -1);\n'
       '        if (walk == unreachable ? bag < params::min_bank : bag < 8 * (walk - 2)) return 0;\n'
       '    }\n')
assert s.count(old) == 1
if part != 'emb': b.write_text(s.replace(old, new))
