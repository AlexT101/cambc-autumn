# Fidelity table: the opponent's tribute and lock behaviour in local runs, beside live Mite/Fish (one-site maps, r < 600).
#   py fid.py ANA_DIR [RUN_REGEX]     ANA_DIR from extract.mjs over of-* batches; live rows from episodes.py's pickle
import gzip, json, os, pickle, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import episodes as E

def locks(d, T):
    c = collections.Counter()
    for l in gzip.open(Path(d) / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] >= 600: continue
        if e['k'] == 'lock_place': c['lock_us' if e['team'] == T else 'lock_op'] += 1
        elif e['k'] == 'attack' and e.get('lock'): c['lockhit'] += 1
    return c

def job(j):
    key, d, T = j
    try: r = E.scan(d, T, until=600); r['locks'] = locks(d, T); return key, r
    except Exception as ex: return key, {'err': repr(ex)}

def stats(rows):
    S = collections.Counter(); n = 0
    for r in rows:
        if 'err' in r: continue
        n += 1; S['op600'] += r['op600']; S['win'] += r['win']
        for k, v in r.get('locks', {}).items(): S[k] += v
        for e in r['eps']:
            if e['side'] != 'op' or e['r'] > 600: continue
            S['starts'] += 1; S[e['end']] += 1
            if e['end'] == 'manual':
                S['held1'] += e['held'] == 1; S['retry3'] += e['nxt'] is not None and e['nxt'] <= 3
            if e['d0'] <= 3 and e['gems'] > 10: S['near'] += 1; S['near_man'] += e['end'] == 'manual'
    if not n: return None
    m = max(S['manual'], 1)
    return (f"n {n:4d} win {100*S['win']/n:4.1f}  op600 {S['op600']/n:4.0f}  starts {S['starts']/n:5.2f} done {S['done']/n:5.2f} "
            f"manual {S['manual']/n:4.2f} (held1 {100*S['held1']/m:3.0f}% retry<=3 {100*S['retry3']/m:3.0f}%) stun {S['stun']/n:4.2f} "
            f"lock-cancel {S['lock']/n:4.2f}  d0<=3 cancel {100*S['near_man']/max(1,S['near']):3.0f}%  "
            f"locks op {S['lock_op']/n:3.1f} us {S['lock_us']/n:3.1f}")

if __name__ == '__main__':
    ana = Path(sys.argv[1]); pat = sys.argv[2] if len(sys.argv) > 2 else r'of-([^/]+)-ladder'
    jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        m = re.search(pat + r'/\d+-(.+)-(12|21)\.repl26a$', g['source'])
        if m and E.MC.get(m.group(m.lastindex - 1).replace('-', '_')) == 'one':
            jobs.append(((m.group(1),), str(ana / g['dir']), 0 if m.group(m.lastindex) == '12' else 1))
    with Pool(int(os.environ.get('OMP_NUM_THREADS', 8))) as P: res = P.map(job, jobs, chunksize=2)
    by = collections.defaultdict(list)
    for k, r in res: by[k[0]].append(r)
    live = pickle.load(open(os.path.expanduser('~/tmp-offload/oppfidelity/ep1.pkl'), 'rb'))
    for opp in ('mite', 'fish'):
        for grp, vs in (('A', (86, 87, 89, 95)), ('B', (91, 93))):
            rows = [r for k, r in live.items() if k[0] == 'live' and k[2] == opp and k[1] in vs and E.MC.get(k[3]) == 'one']
            print(f'live {opp} {grp:14s}', stats(rows), '(locks n/a)')
    for k in sorted(by): print(f'{k:20s}', stats(by[k]))
