"""The loser while the winner is finishing (a winning bag held, mirror): capture gems a 100 rounds then vs in the 200
rounds before the winner reached 1000 wealth, and the loser's deaths a 100 rounds then. py defender.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    w = meta['result']['winner']
    if w not in (0, 1): return None
    l = 1 - w; C = R['champions']; n = len(R['round']); team = {c['id']: c['team'] for c in C}
    W = [c for c in C if c['team'] == w]
    wealth = lambda i: R['gems'][w][i] + sum(c['gems'][i] for c in W if c['alive'][i])
    t0 = next((i for i in range(n) if wealth(i) >= 1000), None)
    if t0 is None: return None
    t1 = next((i for i in range(t0, n) if any(c['alive'][i] and R['gems'][w][i] + c['gems'][i] >= 1000 for c in W)), n - 1)
    r0, r1, rend = R['round'][t0], R['round'][t1], R['round'][-1]
    if rend - r1 < 50: return None
    cap = lambda a, b: sum(s[1] for e in ev if e['k'] == 'capture' and e['team'] == l and a <= e['r'] < b for s in e['shares'])
    dth = lambda a, b: sum(1 for e in ev if e['k'] == 'death' and team.get(e['v']) == l and a <= e['r'] < b)
    return (cap(max(1, r0 - 200), r0) / (min(200, r0 - 1) / 100), cap(r1, rend) / ((rend - r1) / 100), dth(r1, rend) / ((rend - r1) / 100), dth(max(1, r0 - 200), r0) / (min(200, r0 - 1) / 100), rend - r1)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex: rows = [r for r in ex.map(one, dirs, chunksize=8) if r]
    print('games with 50+ finishing rounds', len(rows))
    for name, k in (('loser capture gems /100r before', 0), ('loser capture gems /100r while finishing', 1), ('loser deaths /100r before', 3), ('loser deaths /100r while finishing', 2)):
        print(f'  {name}: median {st.median(r[k] for r in rows):.1f} mean {st.mean(r[k] for r in rows):.1f}')
