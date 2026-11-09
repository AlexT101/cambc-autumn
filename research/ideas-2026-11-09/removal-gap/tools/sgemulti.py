import json, sys, os, re, zipfile, collections, statistics as st
from multiprocessing import Pool
import beh
ROOT = '/home/ubuntu/cambc-autumn/.claude/worktrees/ocean-removals/'
def run(job):
    d, src = job
    try: meta, rd, ev = beh.load(d); z = zipfile.ZipFile(os.path.join(ROOT, src))
    except Exception: return []
    cid = {(c['team'], c['type']): c['id'] for c in meta['champions']}
    out = []
    for t, fn in ((0, 'team-a.stdout'), (1, 'team-b.stdout')):
        s = z.read(fn).decode(errors='replace')
        byr = collections.defaultdict(set)
        for m in re.finditer(r'^SGE (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$', s, re.M):
            r, ty, trib, gems, dist, locks, hp, ety = map(int, m.groups()); byr[(r, trib, ety)].add((ty, locks))
        deaths = collections.defaultdict(list)
        for e in ev:
            if e['k'] == 'death': deaths[e['v']].append(e['r'])
        for (r, trib, ety), bodies in byr.items():
            for ty, locks in bodies:
                me = cid.get((t, ty))
                out.append((trib, len(bodies), sum(1 for b in bodies if b[1] > 0), locks, any(r <= x <= r + 15 for x in deaths[me])))
    return out
if __name__ == '__main__':
    A = sys.argv[1]; idx = json.load(open(A + '/index.json'))['games']
    with Pool(32) as p: res = [x for r in p.map(run, [(A + '/' + g['dir'], g['source']) for g in idx], chunksize=4) for x in r]
    for trib in (1, 0):
        X = [x for x in res if x[0] == trib]
        c = collections.Counter(min(x[1], 4) for x in X)
        print('tributing' if trib else 'walking', 'body-rounds', len(X), 'bodies in SGE together:', {k: round(v / len(X), 2) for k, v in sorted(c.items())},
              'with >=1 lock among them', round(st.mean(x[2] > 0 for x in X), 2), 'die15 by self-holds-lock', round(st.mean(x[4] for x in X if x[3] > 0), 2), 'no lock', round(st.mean(x[4] for x in X if x[3] == 0), 2))
