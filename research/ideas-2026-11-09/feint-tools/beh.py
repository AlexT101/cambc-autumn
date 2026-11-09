# Behaviour of our side per run (one-site / multi): tribute starts, manual cancels, completions (r<600), our and their
# tributed gems at 600, win%. Paired runs: base spar-cbase25-<m> vs spar-cv87-ft-<v>-<m>.
#   py beh.py ANA_DIR RUN...
import json, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools'); import episodes as E
def job(j):
    run, d, T, cls = j
    r = E.scan(d, T, until=600); c = collections.Counter()
    for e in r['eps']:
        if e['side'] == 'us' and e['r'] < 600: c['start'] += 1; c[e['end']] += 1
    c['us600'] = r['us600']; c['op600'] = r['op600']; c['win'] = int(r['win']); c['n'] = 1
    return (run, cls), c
if __name__ == '__main__':
    ana = Path(sys.argv[1]); runs = sys.argv[2:]; jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        for run in runs:
            m = re.search(rf'-ab-{re.escape(run)}-ladder/\d+-(.+)-(12|21)\.repl26a$', g['source'])
            if m: jobs.append((run, str(ana / g['dir']), 0 if m.group(2) == '12' else 1, E.MC.get(m.group(1).replace('-', '_'))))
    with Pool(32) as P: res = P.map(job, jobs, chunksize=8)
    S = collections.defaultdict(collections.Counter)
    for k, c in res: S[k].update(c)
    for k in sorted(S):
        c = S[k]; n = c['n']
        print(f'{k[0]:28s} {k[1]:6s} n={n:4d} ' + ' '.join(f'{x} {c[x]/n:6.2f}' for x in ('start', 'done', 'manual', 'stun', 'lock', 'death', 'us600', 'op600')) + f' win {100*c["win"]/n:.1f}')
