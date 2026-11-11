#!/usr/bin/env python3
"""Mechanism read of an arm against the base on decoded local replays (extract.mjs --out), paired by map and side.
    mech.py EXT_BASE EXT_ARM      # e.g. ~/tmp-offload/biggroups/ext/r2-oc-dfuel-506-Mt3q  .../r2-bg-rich-Mt3q
'Rich' groups: a Golem (no Monolith) whose gem clusters pay at least its strikers' gems."""
import json, gzip, os, sys, collections, math
def games(ext):
    out = {}
    for g in json.load(open(ext + '/index.json'))['games']:
        base = os.path.basename(g['source']).replace('.repl26a', '')
        us = 0 if base.endswith('-12') else 1
        d = ext + '/' + g['dir']
        meta = json.load(open(d + '/meta.json'))
        mf = os.path.join(d, meta['mapFile'])
        if not os.path.exists(mf): mf = os.path.join(ext, meta['mapFile'])
        mp = json.load(open(mf))
        team = {c['id']: c['team'] for c in meta['champions']}
        rich = set()
        for q in mp['groups']:
            t = collections.Counter(q['types'])
            if t.get('Golem') and not t.get('Monolith') and 7 * t.get('Gem cluster', 0) >= q['gems'] - 7 * t.get('Gem cluster', 0): rich.add(q['id'])
        cg = {c['id']: c['group'] for c in mp['camps']}
        s = collections.Counter(); first = None; first_wake = None
        for l in gzip.open(d + '/events.jsonl.gz', 'rt'):
            e = json.loads(l); k = e['k']; r = e['r']
            if k == 'capture':
                mine = e['team'] == us; gems = sum(x[1] for x in e['shares']); gold = sum(x[2] for x in e['shares'])
                w = 'us' if mine else 'th'
                for h in (150, 300, 600):
                    if r <= h:
                        s[f'{w}_gems_{h}'] += gems; s[f'{w}_gold_{h}'] += gold
                        if e['g'] in rich: s[f'{w}_richcaps_{h}'] += 1; s[f'{w}_richgems_{h}'] += gems
                        else: s[f'{w}_othercaps_{h}'] += 1
                if mine and e['g'] in rich and first is None: first = r
            elif k == 'death':
                w = 'us' if team[e['v']] == us else 'th'
                for h in (150, 300, 600):
                    if r <= h:
                        s[f'{w}_deaths_{h}'] += 1
                        if 'camp' in e: s[f'{w}_campdeaths_{h}'] += 1
                        if 'camp' in e and cg.get(e['camp']) in rich: s[f'{w}_richdeaths_{h}'] += 1
                        s[f'{w}_diedgems_{h}'] += e.get('gems', 0) or 0
            elif k == 'group_wake' and e['g'] in rich and e.get('by') is not None and team[e['by']] == us and first_wake is None: first_wake = r
            elif k == 'recall_end' and team[e['a']] == us:
                for h in (150, 300):
                    if r <= h: s[f'us_recalls_{h}'] += 1
        s['win'] = 1 if g['winner'] == us else 0
        s['rounds'] = g['rounds']
        s['first_rich'] = first if first is not None else float('nan')
        s['first_wake'] = first_wake if first_wake is not None else float('nan')
        s['took_300'] = 1 if first is not None and first <= 300 else 0
        out[base] = s
    return out
A, B = games(sys.argv[1]), games(sys.argv[2])
keys = sorted(set(A) & set(B))
print(f'paired games {len(keys)} (base {len(A)}, arm {len(B)})')
cols = ['win', 'took_300', 'first_wake', 'first_rich'] + [f'{w}_{m}_{h}' for h in (150, 300, 600) for w in ('us', 'th') for m in ('richcaps', 'richgems', 'othercaps', 'gems', 'gold', 'deaths', 'campdeaths', 'richdeaths', 'diedgems')] + ['us_recalls_150', 'us_recalls_300']
print(f"{'metric':22s} {'base':>8s} {'arm':>8s} {'delta':>8s} {'±se':>6s}")
for c in cols:
    xs = [(A[k][c], B[k][c]) for k in keys if not (isinstance(A[k][c], float) and math.isnan(A[k][c])) and not (isinstance(B[k][c], float) and math.isnan(B[k][c]))]
    if len(xs) < 5: continue
    a = sum(x[0] for x in xs) / len(xs); b = sum(x[1] for x in xs) / len(xs)
    d = [x[1] - x[0] for x in xs]; m = sum(d) / len(d); se = math.sqrt(sum((v - m) ** 2 for v in d) / max(1, len(d) - 1) / len(d))
    if a == 0 and b == 0: continue
    print(f"{c:22s} {a:8.2f} {b:8.2f} {m:+8.2f} {se:6.2f}" + (f"   (n={len(xs)})" if len(xs) != len(keys) else ''))
