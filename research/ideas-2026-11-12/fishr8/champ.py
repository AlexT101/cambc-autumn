"""Per Fish champion type: games, earned gold r100/300/600, kills, deaths, gems tributed, champion damage, Strength,
max bag and the main items (shard-equivalents a game), for fishx.py outputs side by side.  py champ.py X1.jsonl X2.jsonl"""
import json, sys, collections
for f in sys.argv[1:]:
    D = [json.loads(l) for l in open(f)]
    print(f'== {f} ({len(D)} games)')
    by = collections.defaultdict(list)
    for g in D:
        for c in g['champs']: by[c['type']].append(c)
    for t, L in sorted(by.items(), key=lambda x: -len(x[1])):
        n = len(L); m = lambda k, i=None: sum((c[k][i] if i is not None else c[k]) or 0 for c in L) / n
        it = collections.Counter()
        for c in L: it.update(c['items'])
        top = ', '.join(f'{k} {v / n:.1f}' for k, v in it.most_common(6))
        print(f'{t:14s} n {n:4d} gold {m("earned",0):5.0f} {m("earned",1):5.0f} {m("earned",2):5.0f} k {m("kills"):.2f} d {m("deaths"):.2f} '
              f'trib {m("trib"):5.0f} dmg {m("dmg_champ"):6.0f} str300/600 {m("str",0):4.0f} {m("str",1):4.0f} bag {m("maxbag"):4.0f} | {top}')
