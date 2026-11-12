"""Builds as shard equivalents (shard 1, emblem 5, Greed emblem 25) per champion type and game; consumables apart."""
import fl, collections, sys
VS = sys.argv[1:] or ['r7']
G = fl.load(lambda g: g['vg'] in VS)
tot = collections.defaultdict(collections.Counter); ngame = collections.Counter(); spent = collections.Counter(); cons = collections.defaultdict(collections.Counter)
r400 = collections.defaultdict(collections.Counter)
for g in G:
    for c, t in g['team'].items():
        if t == g['mite']: ngame[g['name'][c]] += 1
    for r, a, items, gold, isdead in g['shops']:
        if g['team'][a] != g['mite'] or not items: continue
        nm = g['name'][a]
        for it, k in items.items():
            if k <= 0: continue
            if ' Shard of ' in it: fam, stat = it.split(' Shard of '); w = 1
            elif ' Emblem of ' in it: fam, stat = it.split(' Emblem of '); w = 25 if fam == 'Greed' else 5
            else: cons[nm][it] += k; continue
            tot[nm][f'{fam}-{stat}'] += k * w
            if r <= 400: r400[nm][f'{fam}-{stat}'] += k * w
for nm in sorted(ngame, key=lambda k: -ngame[k]):
    n = ngame[nm]; s = sum(tot[nm].values()); s4 = sum(r400[nm].values())
    st = collections.Counter()
    for k, v in tot[nm].items(): st[k.split('-')[1]] += v
    print(f'{nm} (n={n}): {s/n:.0f} shard-eq/game ({s4/n:.0f} by r400); stats ' + ', '.join(f'{k} {v/s:.0%}' for k, v in st.most_common()) +
          '; families: ' + ', '.join(f'{k} {v/n:.1f}' for k, v in tot[nm].most_common(7)) + ('; consumables ' + ', '.join(f'{k} {v/n:.1f}' for k, v in cons[nm].most_common(3)) if cons[nm] else ''))
