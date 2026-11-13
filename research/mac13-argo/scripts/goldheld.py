"""Unspent gold by champion type at r300 / r600 (mirror, alive or dead), median and mean, and earned.
py goldheld.py ANALYSIS_DIR"""
import gzip, json, sys, statistics as st
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text()); R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception: return []
    name = {c['id']: c['name'] for c in meta['champions']}; rid = {r: i for i, r in enumerate(R['round'])}
    out = []
    for r in (150, 300, 600):
        i = rid.get(r)
        if i is None: continue
        for c in R['champions']: out.append((name[c['id']], r, c['gold'][i], c['earned'][i]))
    return out
if __name__ == '__main__':
    agg = defaultdict(list)
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p / 'meta.json').exists()]
    with ProcessPoolExecutor(24) as ex:
        for rows in ex.map(one, dirs, chunksize=8):
            for n, r, g, e in rows: agg[(n, r)].append((g, e))
    for n in sorted({k[0] for k in agg}):
        print(n, ' | '.join(f"r{r}: held {st.median(x[0] for x in agg[(n,r)]):.0f}/{st.mean(x[0] for x in agg[(n,r)]):.0f} earned {st.mean(x[1] for x in agg[(n,r)]):.0f}" for r in (150, 300, 600) if agg[(n, r)]))
