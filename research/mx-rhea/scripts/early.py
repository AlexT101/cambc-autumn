"""Early game: at rounds 100/150/200/300, each team's gems in hand (carried + tributed), Prism Focus, deaths and kills;
how often the team ahead wins, and what the first events (first death, first Prism death) predict.
Usage: py early.py ANALYSIS_DIR"""
import gzip, json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    w = meta['result']['winner']
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    out = dict(w=w)
    for r in (100, 150, 200, 300):
        i = r - 1
        if i >= len(R['round']): continue
        g = [R['gems'][t][i] + sum((c['gems'][i] or 0) for c in R['champions'] if c['team'] == t) for t in (0, 1)]
        out[r] = g
    deaths = [e for e in ev if e['k'] == 'death']
    if deaths:
        out['first_death'] = (deaths[0]['r'], team[deaths[0]['v']], name[deaths[0]['v']])
    pd = [e for e in deaths if name[e['v']] == 'Prism']
    if pd: out['first_prism_death'] = (pd[0]['r'], team[pd[0]['v']])
    caps = [e for e in ev if e['k'] == 'capture']
    if caps: out['first_cap'] = (caps[0]['r'], caps[0]['team'])
    return out


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        rows = [o for o in ex.map(game, dirs, chunksize=8) if o]
    for r in (100, 150, 200, 300):
        S = [x for x in rows if r in x and x[r][0] != x[r][1]]
        for lo, hi in ((0, 10), (10, 30), (30, 60), (60, 10**6)):
            s = [x for x in S if lo <= abs(x[r][0] - x[r][1]) < hi]
            if s:
                ahead_won = sum(1 for x in s if (x[r][0] > x[r][1]) == (x['w'] == 0))
                print(f'r{r} lead {lo}-{hi}: {len(s)} games, ahead won {ahead_won/len(s):.0%}')
    fd = [x for x in rows if 'first_death' in x]
    print(f"first death (median r{sorted(x['first_death'][0] for x in fd)[len(fd)//2]}): its team won {sum(1 for x in fd if x['first_death'][1]==x['w'])/len(fd):.0%} of {len(fd)}")
    fp = [x for x in rows if 'first_prism_death' in x]
    print(f"first Prism death (median r{sorted(x['first_prism_death'][0] for x in fp)[len(fp)//2]}): its team won {sum(1 for x in fp if x['first_prism_death'][1]==x['w'])/len(fp):.0%} of {len(fp)}")
    fpe = [x for x in fp if x['first_prism_death'][0] <= 200]
    print(f"  ... by r200: {len(fpe)} games, its team won {sum(1 for x in fpe if x['first_prism_death'][1]==x['w'])/max(1,len(fpe)):.0%}")
    fc = [x for x in rows if 'first_cap' in x]
    print(f"first capture: its team won {sum(1 for x in fc if x['first_cap'][1]==x['w'])/len(fc):.0%}")
