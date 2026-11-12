"""Mite's Vesper late: Strength and max health at r600 and r900, and whether she owns a Greed item (ids 72-77) by r300,
r600 and the end, with the first round she holds one.   py vlate.py EXT [ROWS]  (prints a summary as JSON lines)"""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from mstats import load
GREED = set(range(72, 78))
def game(job):
    ext, d, mite, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    n = len(R['round']); out = dict(extra, rounds=n)
    v = [c for c in meta['champions'] if c['team'] == mite and c['name'] == 'Vesper Vale']
    if not v: return None
    c = next(x for x in R['champions'] if x['id'] == v[0]['id'])
    for r in (300, 600, 900):
        if n >= r: out[f'str{r}'] = c['str'][r - 1]; out[f'hp{r}'] = c['maxHp'][r - 1]; out[f'greed{r}'] = bool(GREED & set(c['items'][r - 1]))
    out['greed_end'] = bool(GREED & set(c['items'][-1]))
    out['greed_first'] = next((i + 1 for i, it in enumerate(c['items']) if GREED & set(it)), None)
    return out
if __name__ == '__main__':
    ext = sys.argv[1]; idx = json.load(open(ext + '/index.json'))['games']; jobs = []
    rows = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
    for g in idx:
        if rows is not None:
            mid = os.path.basename(g['source'])[:-8]
            if mid in rows and rows[mid]['version'] == 116: r = rows[mid]; jobs.append((ext, g['dir'], 1 if r['side'] == 'a' else 0, {}))
        else:
            base = os.path.basename(g['source'])[:-8]; o = base.rsplit('-', 1)[1]; jobs.append((ext, g['dir'], 1 if o == '12' else 0, {}))
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    import statistics as st
    def m(k, f=st.median):
        xs = [x[k] for x in res if x.get(k) is not None]; return round(f(xs), 2) if xs else None
    print(json.dumps({'games': len(res), 'str600': m('str600'), 'str900': m('str900'), 'hp600': m('hp600'), 'hp900': m('hp900'),
                      'greed300': m('greed300', st.mean), 'greed600': m('greed600', st.mean), 'greed_end': m('greed_end', st.mean),
                      'greed_first_med': m('greed_first')}))
