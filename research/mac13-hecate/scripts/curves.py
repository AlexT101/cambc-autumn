import sys, json, gzip, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
CK = [100,200,300,400,500,600,700,800,1000,1200]
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
    except Exception: return None
    n = len(R['round']); win = meta.get('winner')
    sc = R['gems']  # per team list over rounds?
    out = {'n': n, 'meta_keys': list(meta.keys())}
    g0 = sc[0]; g1 = sc[1]
    ws = 0 if g0[-1] >= g1[-1] else 1
    res = {}
    for t in (0,1):
        tag = 'W' if t == ws else 'L'
        champs = [c for c in R['champions'] if c['team']==t]
        for r in CK:
            i = min(r, n) - 1
            if r > n: continue
            res.setdefault(tag, {})[r] = dict(score=sc[t][i], bag=sum(c['gems'][i] for c in champs),
                prismbag=max([c['gems'][i] for c in champs if c['foc'][0]==90] or [0]),
                gold=sum(c['earned'][i] for c in champs), alive=sum(c['alive'][i] for c in champs)/len(champs))
    return n, res
if __name__ == '__main__':
    dirs = [p for a in sys.argv[1:] for p in Path(a).iterdir() if (p/'meta.json').exists()]
    agg = collections.defaultdict(lambda: collections.defaultdict(list)); lens = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if not o: continue
            n, res = o; lens.append(n)
            for tag, d in res.items():
                for r, v in d.items():
                    for k, x in v.items(): agg[(tag, r)][k].append(x)
    print('games', len(lens), 'len median', statistics.median(lens), 'mean', sum(lens)/len(lens))
    for r in CK:
        for tag in 'WL':
            v = agg[(tag, r)]
            if not v: continue
            print(r, tag, len(v['score']), ' '.join(f"{k}={sum(x)/len(x):.0f}" for k, x in v.items()))
