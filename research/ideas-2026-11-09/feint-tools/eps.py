# Our tribute episodes (r<600) by run and map class: starts by bag size, rounds held, nearest enemy at start, outcome.
import json, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools'); import episodes as E
def job(j):
    run, d, T, cls = j; r = E.scan(d, T, until=600); c = collections.Counter()
    for e in r['eps']:
        if e['side'] != 'us' or e['r'] >= 600: continue
        b = '<=10' if e['gems'] <= 10 else '11-20' if e['gems'] <= 20 else '>20'
        dn = '<=4' if e['d0'] <= 4 else '5-8' if e['d0'] <= 8 else '9+'
        c[(b, dn, e['end'])] += 1; c[('held', b)] += e['held'] or 0; c[('gems', b)] += e['gems'] if e['end'] == 'done' else 0
    c['n'] = 1; return (run, cls), c
if __name__ == '__main__':
    ana = Path(__import__('os').path.expanduser('~/tmp-offload/feint/ana')); runs = sys.argv[1:]; jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        for run in runs:
            m = re.search(rf'-ab-{re.escape(run)}-ladder/\d+-(.+)-(12|21)\.repl26a$', g['source'])
            if m: jobs.append((run, str(ana / g['dir']), 0 if m.group(2) == '12' else 1, E.MC.get(m.group(1).replace('-', '_'))))
    with Pool(32) as P: res = P.map(job, jobs, chunksize=8)
    S = collections.defaultdict(collections.Counter)
    for k, c in res: S[k].update(c)
    keys = sorted({k for c in S.values() for k in c if k != 'n'}, key=str)
    print('key'.ljust(30) + ''.join(f'{r[3:]+"/"+cl[:3]:>14s}' for r in runs for cl in ('one',)))
    for k in keys:
        vals = [S[(r, 'one')][k] / max(1, S[(r, 'one')]['n']) for r in runs]
        if max(vals) >= 0.15: print(str(k).ljust(30) + ''.join(f'{v:14.2f}' for v in vals))
