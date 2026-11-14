"""Mite's emblem orders (possq_mite.py on real Mite since 11-09 12:00): each champion's modal emblem by ordinal, no
family twice but Bruiser and Power, the same at every pick count. mite-re: the body's Marcella ends with 220 Focus
against real 318, HoR 117 against 195; real Mite buys ~4 Bruiser Health emblems on its bruisers.
Usage: patch_mite_emb.py BOT_DIR"""
import re, sys, pathlib
d = pathlib.Path(sys.argv[1]) / 'src'
F = dict(monster=0, power=1, durability=2, treasure=3, jungle=4, home=5, bruiser=6, tribute=7, capture=8, prospector=9,
         hunter=10, skirmish=11, greed=12, collectors=13)
S = dict(S=0, F=1, H=2)
def seq(s): return [F[x.split('-')[0].lower()] * 3 + S[x.split('-')[1]] for x in s.split()]
ORDER = {
    'vesper_vale': 'Jungle-S Monster-S Prospector-S Capture-S Durability-H Collectors-S Tribute-S Treasure-S Home-S Greed-S Bruiser-H Bruiser-H',
    'vendetta': 'Jungle-S Durability-H Prospector-S Bruiser-H Capture-S Bruiser-H Collectors-S Bruiser-H Tribute-S Bruiser-H Home-S Bruiser-H',
    'heart_of_ruin': 'Jungle-F Durability-H Prospector-F Bruiser-H Bruiser-H Capture-F Collectors-F Bruiser-H Tribute-F Bruiser-H Home-F Bruiser-H',
    'cassi': 'Jungle-F Durability-H Prospector-F Bruiser-H Monster-F Bruiser-H Collectors-F Bruiser-H Capture-F Bruiser-H Tribute-F Bruiser-H',
    'issac': 'Prospector-H Durability-H Monster-S Bruiser-H Capture-S Bruiser-H Collectors-S Bruiser-H Jungle-S Bruiser-H Tribute-S Bruiser-H',
    'tavi': 'Monster-S Durability-H Prospector-S Bruiser-H Treasure-S Bruiser-H Bruiser-S Bruiser-H Capture-S Bruiser-H Collectors-S Bruiser-H',
    'marcella': 'Prospector-F Durability-H Monster-F Bruiser-H Bruiser-H Collectors-F Capture-F Bruiser-H Tribute-F Skirmish-F Bruiser-H Power-F',
    'willow': 'Durability-H Power-F Power-F Power-F Power-F Power-F Power-F Power-F Power-F Power-F Power-F Power-F',
    'prism': 'Prospector-F Durability-H Monster-F Bruiser-H Capture-F Collectors-F Tribute-F Bruiser-H Home-F Bruiser-H Greed-H Bruiser-H',
}
t = d / 'economy/emblem_table.h'; s = t.read_text(); n = 0
for name, o in ORDER.items():
    v = seq(o); assert len(v) == 12
    s, k = re.subn(r'\{[0-9, ]+\}, // ' + name + r'\n', '{' + ', '.join(map(str, v)) + '}, // ' + name + '\n', s); n += k
assert n == 3 * len(ORDER), n
t.write_text(s)
