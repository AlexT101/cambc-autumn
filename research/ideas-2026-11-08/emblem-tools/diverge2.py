"""First differing event (any team) between paired games: its kind, whose, and the outcome flip."""
import json, gzip, os, sys, collections
H = os.path.expanduser('~/tmp-offload/')
sys.path.insert(0, H + 'emblem/tools'); from live_items import load
A, B = int(sys.argv[1]), int(sys.argv[2]); OPPF = sys.argv[3] if len(sys.argv) > 3 else None
G = {}; L = {}
for gj, ana in ((H + 'bigl/games.json', H + 'bigl/ana'), (H + 'emblem/games9091.json', H + 'emblem/ana')):
    L.update(load(ana)); G.update(json.load(open(gj)))
cells = collections.defaultdict(dict)
for mid, g in G.items():
    if g['version'] in (A, B) and g.get('refset') == 'r2' and mid in L:
        cells[(g['map'], g['side'], g['opp_name'], g.get('position'))][g['version']] = (mid, g)
def evs(d):
    out = []
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l); e.pop('s', None); out.append(e)
        if len(out) > 400000: break
    return out
tab = collections.Counter(); ex = collections.defaultdict(list)
for k, v in cells.items():
    if not (A in v and B in v): continue
    (ma, ga), (mb, gb) = v[A], v[B]
    if OPPF and not ga['opp_name'].startswith(OPPF): continue
    us = 0 if ga['side'] == 'a' else 1
    meta = json.load(open(L[ma] + '/meta.json')); team = {c['id']: c['team'] for c in meta['champions']}; nm = {c['id']: c['name'] for c in meta['champions']}
    ea, eb = evs(L[ma]), evs(L[mb])
    i = next((i for i, (x, y) in enumerate(zip(ea, eb)) if x != y), None)
    if i is None: continue
    x, y = ea[i], eb[i]
    a = x.get('a', y.get('a'))
    who = 'us' if a is not None and team.get(a) == us else ('them' if a is not None else 'env')
    kind = x['k'] if x['k'] == y['k'] else x['k'] + '/' + y['k']
    res = (ga['result'], gb['result'])
    flip = 'A' if res == ('win', 'loss') else 'B' if res == ('loss', 'win') else '='
    key = (who, kind); tab[(key, flip)] += 1
    if who == 'us': ex[kind].append((x['r'], nm.get(a), flip, json.dumps(x)[:150], json.dumps(y)[:150]))
keys = sorted({k for k, _ in tab}, key=lambda k: -sum(tab[(k, f)] for f in 'AB='))
for k in keys: print(k, 'n', sum(tab[(k, f)] for f in 'AB='), 'flips A', tab[(k, 'A')], 'B', tab[(k, 'B')])
for kind, l in ex.items():
    print('==', kind)
    for t in l[:int(os.environ.get("NEX",6))]: print('  ', t)
