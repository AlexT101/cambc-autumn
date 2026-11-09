# Per channel turn of every tribute: keep or manual cancel, against what the channeller saw at that turn's start.
#   py chanturns.py OUT.pkl   (live r2 + liveforensic local, as episodes.py; rounds <= 1200)
# Row: (key, side, who, gems, turn_in_channel, left, dmin_seen, dmin_any, n_seen<=5, hp_frac, approached, cancelled)
# dmin_seen: nearest enemy in the channeller's `sees` at its turn start (positions of the previous round's end).
import gzip, json, os, pickle, sys
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes as E

def scan(job):
    key, d, T = job; d = Path(d)
    try:
        meta = json.load(open(d / 'meta.json')); team = {c['id']: c['team'] for c in meta['champions']}
        name = {c['id']: c['name'] for c in meta['champions']}
        rd = json.load(gzip.open(d / 'rounds.json.gz')); R = rd['round']; ri = {r: i for i, r in enumerate(R)}
        ch = {c['id']: c for c in rd['champions']}
        ev = [json.loads(l) for l in gzip.open(d / 'events.jsonl.gz', 'rt')]
    except Exception as ex: return []
    starts, rows = {}, []
    cancel_r = {}
    for e in ev:
        if e['k'] == 'tribute_start': starts.setdefault(e['a'], []).append([e['r'], None, None, e['gems']])
        elif e['k'] in ('tribute_end', 'tribute_cancel', 'death'):
            a = e.get('a', e.get('v'))
            if a in starts and starts[a][-1][1] is None:
                starts[a][-1][1] = e['r']; starts[a][-1][2] = 'manual' if e['k'] == 'tribute_cancel' and e.get('cause') == 'manual' else e['k']
    for a, eps in starts.items():
        c = ch[a]; side = 'us' if team[a] == T else 'op'
        for r0, r1, how, gems in eps:
            if r1 is None or r0 > 1200: continue
            prev = None
            for t in range(r0 + 1, r1 + 1):
                i, j = ri.get(t - 1), ri.get(t)
                if i is None or j is None or c['x'][i] is None: break
                x, y = c['x'][i], c['y'][i]
                seen = set(c['sees'][j]) if c['sees'][j] is not None else set()
                ds_seen, ds_any = [], []
                for o in rd['champions']:
                    if o['team'] == team[a] or not o['alive'][i] or o['x'][i] is None: continue
                    dd = max(abs(o['x'][i] - x), abs(o['y'][i] - y)); ds_any.append(dd)
                    if o['id'] in seen: ds_seen.append(dd)
                dmin_s = min(ds_seen) if ds_seen else 99; dmin_a = min(ds_any) if ds_any else 99
                lab = (t == r1 and how == 'manual')
                rows.append((key, side, name[a], gems, t - r0, c['chanT'][i], dmin_s, dmin_a, sum(v <= 5 for v in ds_seen),
                             c['hp'][i] / c['maxHp'][i] if c['maxHp'][i] else 1, prev is not None and dmin_s < prev, lab))
                prev = dmin_s
                if t == r1: break
    return rows

if __name__ == '__main__':
    jobs = E.live_jobs() + E.local_jobs()
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = P.map(scan, jobs, chunksize=4)
    rows = [r for o in res for r in o]; print(len(rows))
    pickle.dump(rows, open(sys.argv[1], 'wb'))
