"""Mite's Vesper, per game: Strength, earned gold and items at rounds 150/300/500, for live and local exts.
    py vstats.py live EXT ROWS OUT | local EXT OUT"""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__))
from mstats import load
def game(job):
    ext, d, mite, extra = job
    try: meta, R, ev, mp = load(ext, d)
    except Exception: return None
    n = len(R['round']); out = dict(extra)
    for side, t in (('m', mite), ('o', 1 - mite)):
        v = [c for c in meta['champions'] if c['team'] == t and c['name'] == 'Vesper Vale']
        if not v: continue
        c = next(x for x in R['champions'] if x['id'] == v[0]['id'])
        for r in (150, 300, 500):
            if n >= r: out[f'{side}_str{r}'] = c['str'][r - 1]; out[f'{side}_earn{r}'] = c['earned'][r - 1]; out[f'{side}_items{r}'] = c['items'][r - 1]
        out[f'{side}_vkills'] = v[0]['stats']['kills']; out[f'{side}_vdeaths'] = v[0]['stats']['deaths']
        out[f'{side}_vdmg'] = v[0]['stats']['championDamageDone']
    return out
def main():
    mode = sys.argv[1]; ext = sys.argv[2]; idx = json.load(open(ext + '/index.json'))['games']; jobs = []
    if mode == 'live':
        rows = json.load(open(sys.argv[3])); out = sys.argv[4]
        for g in idx:
            mid = os.path.basename(g['source'])[:-8]
            if mid in rows: r = rows[mid]; jobs.append((ext, g['dir'], 1 if r['side'] == 'a' else 0, {'map': r['map'].replace('_', '-'), 'side': r['side'], 'version': r['version']}))
    else:
        out = sys.argv[3]
        for g in idx:
            base = os.path.basename(g['source'])[:-8]; num, rest = base.split('-', 1); mname, o = rest.rsplit('-', 1)
            side = 'a' if o == '12' else 'b'; jobs.append((ext, g['dir'], 1 if side == 'a' else 0, {'map': mname.replace('_', '-'), 'side': side}))
    with Pool(8) as p: res = [x for x in p.map(game, jobs, chunksize=4) if x]
    with open(out, 'w') as fh:
        for x in res: fh.write(json.dumps(x) + '\n')
    print(len(res), '->', out)
if __name__ == '__main__': main()
