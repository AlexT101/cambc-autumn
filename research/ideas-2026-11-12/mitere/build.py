"""Shop builds by champion type: shards per game by family/stat, first purchases, consumables."""
import fl, collections, sys
VS = sys.argv[1:] or ['r7', 'v2']
G = fl.load(lambda g: g['vg'] in VS)
tot = collections.defaultdict(collections.Counter); ngame = collections.Counter(); order = collections.defaultdict(collections.Counter)
cons = collections.defaultdict(collections.Counter); when = collections.defaultdict(list); dead = collections.Counter(); nshop = collections.Counter()
for g in G:
    seen = set()
    for c, t in g['team'].items():
        if t == g['mite']: ngame[g['name'][c]] += 1
    first = collections.defaultdict(list)
    for r, a, items, gold, isdead in g['shops']:
        if g['team'][a] != g['mite'] or not items: continue
        nm = g['name'][a]; nshop[nm] += 1; dead[nm] += isdead
        for it, k in items.items():
            if k <= 0: continue
            if 'Shard' in it:
                tot[nm][it] += k
                if len(first[a]) < 3 and it not in first[a]: first[a].append(it)
                when[nm].append(r)
            else: cons[nm][it] += k
    for a, f in first.items(): order[g['name'][a]][' > '.join(x.replace('Shard of ', '') for x in f)] += 1
for nm in sorted(ngame, key=lambda k: -ngame[k]):
    n = ngame[nm]
    fam = collections.Counter()
    for it, k in tot[nm].items(): fam[it] += k
    s = sum(fam.values())
    print(f'{nm} (n={n}): {s/n:.0f} shards/game, shops while dead {dead[nm]/max(1,nshop[nm]):.0%}; ' + ', '.join(f'{it.replace(" Shard of ", "-")} {k/n:.1f}' for it, k in fam.most_common(8)))
    print('    first three: ' + '; '.join(f'{k} ({c})' for k, c in order[nm].most_common(3)) + ' | consumables/game: ' + ', '.join(f'{k} {c/n:.1f}' for k, c in cons[nm].most_common()))
