"""First Prism deaths: killer type, victim vs killer Focus and bag, victim's HP max, the round, what fraction of the
victim's team was alive, and whether the victim was outnumbered near the death (enemies vs allies within 6).
Usage: py prismdeath.py ANALYSIS_DIR"""
import gzip, json, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def game(d):
    try:
        meta = json.loads((d/'meta.json').read_text())
        R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz', 'rt')]
    except Exception:
        return None
    name = {c['id']: c['name'] for c in meta['champions']}; team = {c['id']: c['team'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}
    for e in ev:
        if e['k'] == 'death' and name[e['v']] == 'Prism':
            v, k = e['v'], e.get('by'); i = max(0, e['r'] - 2)
            if k is None or k not in name: return dict(killer='camp/none', w=meta['result']['winner'] == team[v], r=e['r'], bag=e['gems'])
            vf, kf = ch[v]['foc'][i], ch[k]['foc'][i]
            vp = (ch[v]['x'][i], ch[v]['y'][i])
            def near(t):
                return sum(1 for c in R['champions'] if c['team'] == t and c['alive'][i] and c['x'][i] is not None and vp[0] is not None
                           and max(abs(c['x'][i] - vp[0]), abs(c['y'][i] - vp[1])) <= 6)
            return dict(killer=name[k], w=meta['result']['winner'] == team[v], r=e['r'], bag=e['gems'], kbag=ch[k]['gems'][i] or 0,
                        vf=vf, kf=kf, allies=near(team[v]) - 1, enemies=near(1 - team[v]))
    return None


if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex:
        rows = [o for o in ex.map(game, dirs, chunksize=8) if o]
    print(len(rows), 'first Prism deaths; victim team won', f"{sum(r['w'] for r in rows)/len(rows):.0%}")
    print('killer:', Counter(r['killer'] for r in rows).most_common(8))
    P = [r for r in rows if r['killer'] == 'Prism']
    if P:
        print(f"by enemy Prism {len(P)}: victim Focus < killer {sum(1 for r in P if r['vf'] < r['kf'])}, >= {sum(1 for r in P if r['vf'] >= r['kf'])}")
        for lo, hi in ((0, 0.8), (0.8, 1.0), (1.0, 1.25), (1.25, 9)):
            s = [r for r in P if r['kf'] and lo <= r['vf'] / r['kf'] < hi]
            print(f'   victim/killer Focus {lo}-{hi}: {len(s)}')
    print('numbers near the victim (allies, enemies):', Counter((min(r.get('allies', -1), 3), min(r.get('enemies', -1), 3)) for r in rows).most_common(10))
    rs = sorted(r['r'] for r in rows); print('round p25/50/75', [rs[int(q*(len(rs)-1))] for q in (.25, .5, .75)])
    bs = sorted(r['bag'] for r in rows); print('victim bag p25/50/75', [bs[int(q*(len(bs)-1))] for q in (.25, .5, .75)])
