"""Where 'wait_camp' rounds (still within 3 of a live or respawning group's tiles, not hitting) go: the group's state
(alive asleep/awake, respawning) and class, the champion type, run lengths. py waits.py ANALYSIS_DIR [N]"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/wt/mac13-argo/tools/replay')
from analysis import Game, macro
def cheb(a, b): return max(abs(a[0]-b[0]), abs(a[1]-b[1]))
def one(d):
    try:
        g = Game(d.resolve()); cls = macro.classify(g)
        meta = json.loads((d / 'meta.json').read_text())
        mp = json.loads((d / meta['mapFile']).resolve().read_text())
        R = json.load(gzip.open(d / 'rounds.json.gz'))
    except Exception as ex:
        return None
    C = R['champions']; name = {c['id']: c['name'] for c in meta['champions']}
    types = {gg['id']: gg['types'] for gg in mp['groups']}
    tiles = {gg['id']: [tuple(t) for t in gg['tiles']] for gg in mp['groups']}
    out = Counter(); runs = Counter()
    for ci, c in enumerate(C):
        row = cls.get(c['id'])
        if row is None: return None
        run = 0
        for i, rr in enumerate(R['round']):
            k = row.get(rr) if isinstance(row, dict) else (row[rr] if rr < len(row) else None)
            if k == 'wait_camp':
                run += 1
                p = (c['x'][i], c['y'][i])
                gid = min(tiles, key=lambda q: min(cheb(p, t) for t in tiles[q])) if p[0] is not None else None
                ty = types.get(gid, [])
                cl = 'monolith' if 'Monolith' in ty else 'golem' if 'Golem' in ty else 'elk' if 'Elk' in ty else 'wolf' if 'Wolf' in ty else 'cluster'
                out[(name[c['id']], cl)] += 1
            elif run:
                runs[min(run, 20)] += 1; run = 0
    return out, runs
if __name__ == '__main__':
    root = Path(sys.argv[1]); n = int(sys.argv[2]) if len(sys.argv) > 2 else 400
    dirs = [p for p in root.iterdir() if (p / 'meta.json').exists()][:n]
    tot = Counter(); runs = Counter(); ok = 0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(one, dirs, chunksize=4):
            if r: tot.update(r[0]); runs.update(r[1]); ok += 1
    print('games', ok)
    by_type = Counter(); by_cl = Counter()
    for (t, cl), v in tot.items(): by_type[t] += v; by_cl[cl] += v
    print('wait_camp rounds per game by champion', {k: round(v/ok, 1) for k, v in by_type.most_common()})
    print('by group class', {k: round(v/ok, 1) for k, v in by_cl.most_common()})
    print('run lengths', sorted(runs.items()))
