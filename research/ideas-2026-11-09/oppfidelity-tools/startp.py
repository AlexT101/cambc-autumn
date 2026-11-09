# P(opponent starts a tribute in round r | it ends round r within 1 of an altar with > 10 gems), by nearest enemy at
# round end, rounds <= 600, one-site maps. Live Mite/Fish (v86/87/89/95) and local runs of an analysis dir.
#   py startp.py [ANA_DIR RUN_REGEX]
import gzip, json, os, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes as E
def scan(job):
    key, d, T = job; d = Path(d); out = collections.Counter()
    meta = json.load(open(d / 'meta.json')); mp = json.load(open(d / meta['mapFile'])); alt = [tuple(a) for a in mp['altars']]
    team = {c['id']: c['team'] for c in meta['champions']}
    st = set()
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'tribute_start' and team[e['a']] != T: st.add((e['a'], e['r']))
    rd = json.load(gzip.open(d / 'rounds.json.gz'))
    for c in rd['champions']:
        if c['team'] == T: continue
        for i, r in enumerate(rd['round']):
            if r > 600: break
            if not c['alive'][i] or c['gems'][i] <= 10 or c['x'][i] is None: continue
            x, y = c['x'][i], c['y'][i]
            if min(max(abs(ax - x), abs(ay - y)) for ax, ay in alt) > 1: continue
            if i and c['chan'][i - 1] == 2 and (c['id'], r) not in st: continue  # still in last turn's channel
            b = min(E.near(rd, i, c['team'], x, y), 9)
            out[(b, 'n')] += 1; out[(b, 's')] += (c['id'], r) in st
    return key, out
if __name__ == '__main__':
    jobs = [j for j in E.live_jobs() if j[0][1] in (86, 87, 89, 95) and E.MC.get(j[0][3]) == 'one']
    if len(sys.argv) > 2:
        ana = Path(sys.argv[1])
        for g in json.load(open(ana / 'index.json'))['games']:
            m = re.search(sys.argv[2] + r'/\d+-(.+)-(12|21)\.repl26a$', g['source'])
            if m and E.MC.get(m.group(m.lastindex - 1).replace('-', '_')) == 'one':
                jobs.append((('local', m.group(1)), str(ana / g['dir']), 0 if m.group(m.lastindex) == '12' else 1))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = P.map(scan, jobs, chunksize=2)
    S = collections.defaultdict(collections.Counter); N = collections.Counter()
    for k, o in res:
        g = (k[0], k[2]) if k[0] == 'live' else k; S[g].update(o); N[g] += 1
    for g in sorted(S, key=str):
        s = S[g]; print(f'{str(g):32s} n {N[g]:4d} ', ' '.join(f"{d}:{100*s[(d,'s')]/max(1,s[(d,'n')]):.0f}%/{s[(d,'n')]/N[g]:.1f}" for d in range(1, 10)))
