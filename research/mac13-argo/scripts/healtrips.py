"""Heal trips: completed recalls started below 60% health, and walks onto own spawn below 60% (by champion type),
per 100 alive rounds, rounds from trip start to the next camp hit; split by whether the team has a Willow.
py healtrips.py ANALYSIS_DIR [N]"""
import gzip, json, sys, statistics as st
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
def one(d):
    try:
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    C = R['champions']; idx = {c['id']: i for i, c in enumerate(C)}; name = {c['id']: c['name'] for c in meta['champions']}
    rid = {r: i for i, r in enumerate(R['round'])}; n = min(len(R['round']), 600)
    willow = {t: any(c['name'] == 'Willow' and c['team'] == t for c in meta['champions']) for t in (0, 1)}
    hits = defaultdict(list)
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg') and e['r'] <= 700: hits[e['a']].append(e['r'])
    out = []
    for c in C:
        alive = sum(c['alive'][:n]); trips = []
        rs = None
        for e in ev:
            if e.get('a') != c['id'] or e['r'] > 600: continue
            if e['k'] == 'recall_start':
                i = rid.get(e['r'] - 1, 0); rs = (e['r'], c['hp'][i] / c['maxHp'][i] if c['maxHp'][i] else 1)
            elif e['k'] == 'recall_end' and rs:
                if rs[1] < 0.6:
                    nxt = next((h for h in hits[c['id']] if h > e['r']), None)
                    trips.append((nxt - rs[0]) if nxt else None)
                rs = None
            elif e['k'] == 'recall_cancel': rs = None
        out.append((name[c['id']], willow[c['team']], alive, trips))
    return out
if __name__ == '__main__':
    root = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()][:n]
    agg = defaultdict(lambda: [0, 0, []])
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=8):
            if not r: continue
            for nm, w, alive, trips in r:
                a = agg[(nm, w)]; a[0] += alive; a[1] += len(trips); a[2] += [t for t in trips if t is not None]
    for (nm, w), (alive, k, ts) in sorted(agg.items()):
        if alive < 20000: continue
        print(f"{nm:12s} willow={int(w)} heal recalls /100 alive r1-600 {100*k/alive:.2f}; start->next hit median {st.median(ts) if ts else '-'}; share of alive time ~{(k*(st.mean(ts) if ts else 0))/alive*100:.1f}%")
