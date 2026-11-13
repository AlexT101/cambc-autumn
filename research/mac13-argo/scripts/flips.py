"""Flipped games (mirror): the first team to 1000 wealth loses. Was its Prism killed after t0 (and with what bag),
and by whom; vs games it won. py flips.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception: return None
    w = meta['result']['winner']; C = R['champions']; n = len(R['round']); name = {c['id']: c['name'] for c in meta['champions']}
    team = {c['id']: c['team'] for c in C}
    wealth = lambda t, i: R['gems'][t][i] + sum(c['gems'][i] for c in C if c['team'] == t and c['alive'][i])
    first = None
    for i in range(n):
        a, b = wealth(0, i) >= 1000, wealth(1, i) >= 1000
        if a or b: first = (0 if a else 1, R['round'][i]); break
    if first is None: return None
    t, r0 = first
    pd = [(e['r'], e.get('gems', 0), name.get(e.get('by'), 'camp')) for e in ev if e['k'] == 'death' and team.get(e['v']) == t and name[e['v']] == 'Prism' and e['r'] >= r0]
    return (t != w, pd, R['round'][-1] - r0)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex: rows = [r for r in ex.map(one, dirs, chunksize=8) if r]
    for flip in (True, False):
        s = [r for r in rows if r[0] == flip]
        died = [r for r in s if r[1]]
        print(f"{'flipped' if flip else 'held'}: {len(s)} games; the first team's Prism died after t0 in {100*len(died)/max(1,len(s)):.0f}%; "
              f"first such death bag median {st.median(r[1][0][1] for r in died) if died else '-'}; killers {Counter(r[1][0][2] for r in died).most_common(4)}; rounds t0->end median {st.median(r[2] for r in s)}")
