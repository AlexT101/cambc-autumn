"""Our Prism's max health, unspent gold, bag and time since it last stood on our spawn, by round: python3 shopstate.py EXTROOT/TAG"""
import collections, gzip, json, os, sys, statistics
from multiprocessing import Pool


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json'))); R = json.load(gzip.open(os.path.join(d, 'rounds.json.gz')))
        mp = json.load(open(os.path.join(d, meta['mapFile'])))
    except Exception: return None
    names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; rounds = R['round']
    out = []
    for c in ch:
        C = ch[c]; sp = mp['spawn'][team[c]]; last = 0
        for i, r in enumerate(rounds):
            if not C['alive'][i]: last = r; continue
            if C['x'][i] is not None and sp['minX'] <= C['x'][i] <= sp['maxX'] and sp['minY'] <= C['y'][i] <= sp['maxY']: last = r
            if r in (150, 300, 450, 600, 800, 1000):
                out.append((typ[c], team[c] == us, r, C['maxHp'][i], C['gold'][i], C['gems'][i], r - last, C['foc'][i], C['str'][i], C['earned'][i]))
    return out


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    med = lambda v: statistics.median(v) if v else 0
    for name, sel in [('our Prism', lambda r: r[0] == 'Prism' and r[1]), ('enemy Prism', lambda r: r[0] == 'Prism' and not r[1]), ('our others', lambda r: r[0] != 'Prism' and r[1]), ('enemy others', lambda r: r[0] != 'Prism' and not r[1])]:
        print(name)
        for q in (150, 300, 450, 600, 800, 1000):
            s = [r for r in R if sel(r) and r[2] == q]
            if not s: continue
            print(f'  r{q}: n {len(s):5d}  max health median {med([r[3] for r in s]):6.0f} (p25 {sorted(r[3] for r in s)[len(s) // 4]:.0f})  unspent gold median {med([r[4] for r in s]):5.0f} p75 {sorted(r[4] for r in s)[3 * len(s) // 4]:5.0f}  '
                  f'earned {med([r[9] for r in s]):5.0f}  bag {med([r[5] for r in s]):4.0f}  rounds since on spawn {med([r[6] for r in s]):4.0f} p75 {sorted(r[6] for r in s)[3 * len(s) // 4]:4.0f}  Focus {med([r[7] for r in s]):4.0f}  Strength {med([r[8] for r in s]):4.0f}')
