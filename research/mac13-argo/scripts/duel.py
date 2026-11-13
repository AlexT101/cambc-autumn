"""Near-even Prism duels (victim Focus >= 0.7 x killer's): the first round, within the 15 before the kill, that the two
Prisms stood within 4 (stun range); which one moved to close the gap that round (from >4 to <=4); who struck first.
py duel.py ANALYSIS_DIR"""
import gzip, json, sys
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
        return []
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; team = {c['id']: c['team'] for c in C}
    name = {c['id']: c['name'] for c in meta['champions']}; rid = {r: i for i, r in enumerate(R['round'])}
    out = []
    moves = {}
    for e in ev:
        if e['k'] in ('move',) or (e['k'] == 'cast' and e.get('moved')):
            moves.setdefault((e['a'], e['r']), []).append(e['s'])
    for e in ev:
        if e['k'] != 'death' or name.get(e['v']) != 'Prism' or name.get(e.get('by')) != 'Prism': continue
        v, k = e['v'], e['by']; i = rid.get(e['r'] - 1)
        if i is None: continue
        V, K = C[idx[v]], C[idx[k]]
        if not K['foc'][i] or V['foc'][i] / K['foc'][i] < 0.7: continue
        first_in = None
        for j in range(max(1, i - 15), i + 1):
            if not (V['alive'][j] and K['alive'][j]) or V['x'][j] is None or K['x'][j] is None or V['x'][j-1] is None or K['x'][j-1] is None: continue
            dn = cheb((V['x'][j], V['y'][j]), (K['x'][j], K['y'][j]))
            dp = cheb((V['x'][j-1], V['y'][j-1]), (K['x'][j-1], K['y'][j-1]))
            if dn <= 4 and dp > 4:
                vm = cheb((V['x'][j], V['y'][j]), (V['x'][j-1], V['y'][j-1])) > 0
                km = cheb((K['x'][j], K['y'][j]), (K['x'][j-1], K['y'][j-1])) > 0
                first_in = ('victim' if vm and not km else 'killer' if km and not vm else 'both' if vm and km else 'none')
                break
        # turn order that round: who acts first? the team of odd rounds is A
        out.append(dict(closer=first_in, vbush=None))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8): rows += r
    print('near-even Prism-on-Prism kills', len(rows), 'who closed to within 4 first:', Counter(r['closer'] for r in rows))
