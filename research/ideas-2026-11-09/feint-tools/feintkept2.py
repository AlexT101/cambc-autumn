# Base: recall starts by our non-Prism champions within 1 of an altar with gems (r<600): how each ended.
import json, gzip, re, sys, collections
from pathlib import Path
from multiprocessing import Pool
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-09/oppfidelity-tools'); import episodes as E
def job(j):
    d, T, cls = j; d = Path(d); c = collections.Counter()
    meta = json.load(open(d / 'meta.json')); mp = json.load(open(d / meta['mapFile'])); alt = [tuple(a) for a in mp['altars']]
    name = {x['id']: x['name'] for x in meta['champions']}; team = {x['id']: x['team'] for x in meta['champions']}
    rd = json.load(gzip.open(d / 'rounds.json.gz')); ri = {r: i for i, r in enumerate(rd['round'])}; ch = {x['id']: x for x in rd['champions']}
    open_ = {}
    for l in gzip.open(d / 'events.jsonl.gz', 'rt'):
        e = json.loads(l); a = e.get('a')
        if e['r'] >= 600: break
        if e['k'] == 'recall_start' and team.get(a) == T and name[a] != 'Prism':
            i = ri.get(e['r']); x = ch[a]
            if i is None or not x['gems'][i] or x['x'][i] is None: continue
            if min(max(abs(ax - x['x'][i]), abs(ay - x['y'][i])) for ax, ay in alt) > 1: continue
            open_[a] = (e['r'], '<=10' if x['gems'][i] <= 10 else '>10')
        elif e['k'] in ('recall_cancel', 'recall_end') and a in open_:
            r0, b = open_.pop(a); held = e['r'] - r0
            c[(cls, b, 'end' if e['k'] == 'recall_end' else 'cancel1' if held <= 1 else 'cancel_later')] += 1
    c[(cls, 'n')] = 1; return c
if __name__ == '__main__':
    ana = Path(__import__('os').path.expanduser('~/tmp-offload/feint/ana')); jobs = []
    for g in json.load(open(ana / 'index.json'))['games']:
        m = re.search(r'-ab-fb-oc-base25-(Fl|Mt3)-ladder/\d+-(.+)-(12|21)\.repl26a$', g['source'])
        if m: jobs.append((str(ana / g['dir']), 0 if m.group(3) == '12' else 1, E.MC.get(m.group(2).replace('-', '_'))))
    with Pool(32) as P: res = P.map(job, jobs, chunksize=8)
    S = collections.Counter()
    for c in res: S.update(c)
    for cls in ('one', 'other'):
        n = S[(cls, 'n')]; print(cls, n, {k[1:]: round(v / n, 2) for k, v in sorted(S.items()) if k[0] == cls and k[1] != 'n'})
