import sys, collections, re
sys.path.insert(0, '/home/ubuntu/tmp-offload/fishre/tools')
from fl import games
pos = collections.defaultdict(lambda: collections.defaultdict(collections.Counter)); n = collections.Counter()
for g in games(lambda g: g['created'] >= '2026-11-08T16', rounds=False):
    F = g['fish']; names = {c['id']: c['name'] for c in g['meta']['champions'] if c['team'] == F}
    order = collections.defaultdict(list)
    for e in g['ev']:
        if e['k'] == 'shop' and e['a'] in names and 'items' in e:
            for it, k in e['items'].items():
                m = re.match(r'(\w+) (Shard|Emblem) of (\w+)', it)
                if m and k > 0 and m.group(2) == 'Emblem': order[e['a']] += [m.group(1) + '-' + m.group(3)[0]] * k
    for a, nm in names.items():
        n[nm] += 1
        for i, f in enumerate(order[a][:14]): pos[nm][i][f] += 1
for nm in n:
    print(f"\n{nm} ({n[nm]})")
    for i in sorted(pos[nm]):
        t = sum(pos[nm][i].values())
        print(f"  {i:2d} n={t:4d} " + '  '.join(f"{k} {v/t:.2f}" for k, v in pos[nm][i].most_common(4)))
