"""In flipped games, the leader Prism's first death after t0: was it channelling a tribute in the 3 rounds before,
its health fraction 5 rounds before, Focus ratio to the killer if a Prism, and allies within 6.
py flipdeath.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import flips
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    r = flips.one(d)
    if not r or not r[0] or not r[1]: return None
    meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
    ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    name = {c['id']: c['name'] for c in meta['champions']}; C = R['champions']; rid = {x: i for i, x in enumerate(R['round'])}
    dr = r[1][0][0]
    e = next(e for e in ev if e['k'] == 'death' and e['r'] == dr and name[e['v']] == 'Prism')
    V = next(c for c in C if c['id'] == e['v']); i = rid[dr - 1]; j = rid.get(dr - 5, i)
    K = next((c for c in C if c['id'] == e.get('by')), None)
    chan = any(V['chan'][k] == 2 for k in range(max(0, i - 3), i + 1))
    ratio = V['foc'][i] / K['foc'][i] if K is not None and name[K['id']] == 'Prism' and K['foc'][i] else None
    allies = sum(1 for c in C if c['team'] == V['team'] and c['id'] != V['id'] and c['alive'][i] and c['x'][i] is not None and cheb((c['x'][i], c['y'][i]), (V['x'][i], V['y'][i])) <= 6)
    return (chan, V['hp'][j] / V['maxHp'][j], ratio, allies)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex: rows = [r for r in ex.map(one, dirs, chunksize=8) if r]
    print('leader Prism deaths in flips', len(rows), '; channelling in the 3 rounds before', sum(r[0] for r in rows),
          '; health 5 rounds before median %.2f' % st.median(r[1] for r in rows),
          '; Focus ratio to a Prism killer quartiles', [round(x, 2) for x in st.quantiles([r[2] for r in rows if r[2]], n=4)],
          '; allies within 6 median', st.median(r[3] for r in rows))
