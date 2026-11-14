# Round ends at an altar (within 1) carrying gems: which channel is up, by nearest enemy (opponent fidelity).
#   py atalt.py   (live r2 v86/87/89/95 and local lf-c27, opponent side, rounds <= 1200)
import gzip, json, os, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes as E
def scan(job):
    key, d, T = job; d = Path(d); out = collections.Counter()
    meta = json.load(open(d / 'meta.json')); mp = json.load(open(d / meta['mapFile'])); alt = [tuple(a) for a in mp['altars']]
    rd = json.load(gzip.open(d / 'rounds.json.gz'))
    for c in rd['champions']:
        if c['team'] == T: continue
        for i, r in enumerate(rd['round']):
            if r > 1200: break
            if not c['alive'][i] or c['gems'][i] <= 10 or c['x'][i] is None: continue
            x, y = c['x'][i], c['y'][i]
            if min(max(abs(ax - x), abs(ay - y)) for ax, ay in alt) > 1: continue
            dd = E.near(rd, i, c['team'], x, y); b = min(dd, 9)
            out[(b, c['chan'][i])] += 1
    return key, out
if __name__ == '__main__':
    jobs = [j for j in E.live_jobs() if j[0][1] in (86, 87, 89, 95)] + [j for j in E.local_jobs() if j[0][1] == 'c27']
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = P.map(scan, jobs, chunksize=4)
    for g in (('live', 'mite'), ('live', 'fish'), ('local', 'M'), ('local', 'F')):
        for cls in ('one', 'other'):
            S = collections.Counter(); n = 0
            for key, o in res:
                if key[0] == g[0] and key[2] == g[1] and E.MC.get(key[3]) == cls: S.update(o); n += 1
            print(g, cls, n, 'by nearest d: share of round ends tributing / recalling / none (rounds per game)')
            print('   ', ' '.join(f"{d}:{100*S[(d,2)]/max(1,sum(S[(d,c)] for c in range(4))):.0f}/{100*S[(d,1)]/max(1,sum(S[(d,c)] for c in range(4))):.0f}/{100*S[(d,0)]/max(1,sum(S[(d,c)] for c in range(4))):.0f} ({sum(S[(d,c)] for c in range(4))/n:.1f})" for d in range(1, 10)))
