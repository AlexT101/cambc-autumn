"""Champion kills before r300: victim and killer types, what the victim was doing (macro.py class of its death round
and the round before), local numbers (allies+self vs enemies within 8), side of the map. py early.py ANALYSIS_DIR"""
import gzip, json, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/wt/mac13-argo/tools/replay')
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return []
    w = meta['result']['winner']
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; team = {c['id']: c['team'] for c in C}
    name = {c['id']: c['name'] for c in meta['champions']}; rid = {r: i for i, r in enumerate(R['round'])}
    sp = mp['spawn']
    def spc(t): s = sp[t]; return ((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2)
    out = []; first = True
    for e in ev:
        if e['k'] != 'death' or e['r'] > 300 or e.get('linked') or e.get('by') is None or team.get(e['by']) == team.get(e['v']): continue
        i = rid.get(e['r'] - 1)
        if i is None: continue
        v = C[idx[e['v']]]
        if not v['alive'][i] or v['x'][i] is None: continue
        p = (v['x'][i], v['y'][i]); t = v['team']
        al = sum(1 for c in C if c['team'] == t and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), p) <= 8)
        en = sum(1 for c in C if c['team'] != t and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), p) <= 8)
        own = cheb(p, spc(t)) < cheb(p, spc(1 - t))
        out.append(dict(v=name[e['v']], k=name[e['by']], al=al, en=en, own=own, first=first, vwon=(t == w), gems=e.get('gems', 0)))
        first = False
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=16): rows += r
    n = len(rows); print('kills before r300', n, 'first kills', sum(r['first'] for r in rows))
    print('victims', Counter(r['v'] for r in rows).most_common(8))
    print('killers', Counter(r['k'] for r in rows).most_common(8))
    print('local numbers (allies incl. self - enemies) within 8', sorted(Counter(max(-3, min(3, r['al'] - r['en'])) for r in rows).items()))
    print('on own half', sum(r['own'] for r in rows), 'of', n)
    f = [r for r in rows if r['first']]
    print('first kill victim team won', sum(r['vwon'] for r in f), 'of', len(f))
    print('first-kill victims', Counter(r['v'] for r in f).most_common(6), 'numbers', sorted(Counter(max(-3, min(3, r['al'] - r['en'])) for r in f).items()))
