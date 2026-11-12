"""Per-unit follow-through: a unit that struck enemy X (its most-hit) in round r, with X alive and an option for it
(seen, within conv.OPT) at round r+1's start: how often it strikes X again in r+1, strikes another enemy, or no one.
py follow.py live | EXTRACT_DIR..."""
import gzip, json, os, sys
from collections import Counter, defaultdict
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conv import OPT, cheb, live_jobs, batch_jobs

def one(job):
    d, labels = job
    try:
        meta = json.load(open(d + '/meta.json')); R = json.load(gzip.open(d + '/rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d + '/events.jsonl.gz', 'rt')]
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}
    idx = {r: i for i, r in enumerate(R['round'])}; ch = {c['id']: c for c in R['champions']}
    hits = defaultdict(lambda: defaultdict(Counter))
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for v, amt in e['dmg']:
                if v in team and team[v] != team[e['a']] and amt > 0: hits[e['r']][e['a']][v] += amt
    out = {}
    for t in (0, 1):
        if labels[t] is None: continue
        C = Counter()
        for r, by in hits.items():
            for a, tg in by.items():
                if team[a] != t: continue
                X = max(tg, key=tg.get); i = idx.get(r); ri = idx.get(r + 1)
                if i is None or ri is None or not ch[X]['alive'][i] or ch[a]['x'][i] is None or ch[a]['x'][i] < 0 or ch[X]['x'][i] is None: continue
                if X not in (ch[a]['sees'][ri] or []) or cheb((ch[a]['x'][i], ch[a]['y'][i]), (ch[X]['x'][i], ch[X]['y'][i])) > OPT: continue
                nx = hits.get(r + 1, {}).get(a)
                C['n'] += 1
                if not nx: C['none'] += 1
                elif max(nx, key=nx.get) == X: C['same'] += 1
                else: C['other'] += 1
        out[labels[t]] = C
    return out

if __name__ == '__main__':
    jobs = live_jobs() if sys.argv[1:] == ['live'] else [j for ex in sys.argv[1:] for j in batch_jobs(ex)]
    with Pool(int(os.environ.get('NPROC', 8))) as p: res = [x for x in p.map(one, jobs, chunksize=4) if x]
    tot = defaultdict(Counter)
    for o in res:
        for k, C in o.items(): tot[k].update(C)
    for k, C in sorted(tot.items()):
        n = C['n'] or 1
        print(f"{k:18s} n {C['n']}: strikes X again {100*C['same']/n:.1f}%, another {100*C['other']/n:.1f}%, none {100*C['none']/n:.1f}%; "
              f"given it strikes: X {100*C['same']/max(1,C['same']+C['other']):.1f}%")
