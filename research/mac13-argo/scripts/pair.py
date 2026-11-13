"""Cassi & Issac: their distance apart (alive rounds), deaths (which body was killed, distance apart, enemies near), and
camp damage when apart vs together. py pair.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    w = meta['result']['winner']; C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in C}
    rid = {r: i for i, r in enumerate(R['round'])}
    out = {'dist': Counter(), 'deaths': [], 'dmg': Counter(), 'rounds': Counter()}
    pairs = {}
    for c in meta['champions']:
        if c['name'] in ('Cassi', 'Issac'): pairs.setdefault(c['team'], {})[c['name']] = c['id']
    campdmg = Counter()
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'):
            v = e['cdmg']; s = sum(x[1] for x in v) if isinstance(v, list) else v
            campdmg[(e['a'], e['r'])] += s
    for t, p in pairs.items():
        if len(p) < 2: continue
        a, b = C[idx[p['Cassi']]], C[idx[p['Issac']]]
        for i in range(min(len(R['round']), 800)):
            if a['alive'][i] and b['alive'][i] and a['x'][i] is not None and b['x'][i] is not None:
                dd = cheb((a['x'][i], a['y'][i]), (b['x'][i], b['y'][i]))
                k = '0-2' if dd <= 2 else '3-5' if dd <= 5 else '6-10' if dd <= 10 else '11+'
                out['dist'][k] += 1
                r = R['round'][i]
                out['dmg'][k] += campdmg[(p['Cassi'], r)] + campdmg[(p['Issac'], r)]
        for e in ev:
            if e['k'] == 'death' and e['v'] in (p['Cassi'], p['Issac']) and not e.get('linked'):
                i = rid.get(e['r'] - 1, 0)
                other = p['Issac'] if e['v'] == p['Cassi'] else p['Cassi']
                o = C[idx[other]]; v = C[idx[e['v']]]
                dd = cheb((o['x'][i], o['y'][i]), (v['x'][i], v['y'][i])) if o['alive'][i] and v['alive'][i] and o['x'][i] is not None and v['x'][i] is not None else None
                en = sum(1 for c in C if c['team'] != t and c['alive'][i] and c['x'][i] is not None and v['x'][i] is not None and cheb((c['x'][i], c['y'][i]), (v['x'][i], v['y'][i])) <= 8)
                out['deaths'].append(dict(won=(t == w), body=name[e['v']], apart=dd, enemies=en, camp=('camp' in e), r=e['r']))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    D = Counter(); M = Counter(); deaths = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=16):
            if not o: continue
            D.update(o['dist']); M.update(o['dmg']); deaths += o['deaths']
    tot = sum(D.values())
    print('pair distance share (r1-800, both alive):', {k: f"{100*D[k]/tot:.0f}% dmg/rd {M[k]/max(1,D[k]):.1f}" for k in ('0-2','3-5','6-10','11+')})
    print('pair deaths', len(deaths), 'by camp', sum(d['camp'] for d in deaths), Counter(d['body'] for d in deaths))
    ch = [d for d in deaths if not d['camp'] and d['apart'] is not None]
    print('  champion kills: apart', Counter('0-2' if d['apart']<=2 else '3-5' if d['apart']<=5 else '6-10' if d['apart']<=10 else '11+' for d in ch))
    print('  enemies within 8 of victim', Counter(min(d['enemies'],3) for d in ch))
    print('  W/L pair deaths', sum(d['won'] for d in deaths), sum(not d['won'] for d in deaths))
