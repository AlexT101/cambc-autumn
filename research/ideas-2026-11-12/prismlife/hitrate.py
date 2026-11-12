"""How much of the worst case the Prism actually takes: python3 hitrate.py EXTROOT/TAG   (variants/pl-trace)
For every Prism turn that ended on a tile with worst damage above 0 (PLE): the health it lost before its next turn
start (PLS; all of it if it died first), over that worst damage. hit_given_reach prices this share at 0.234."""
import collections, gzip, json, os, sys, zipfile
from multiprocessing import Pool
import trace as T
ROOT = '/home/ubuntu/cambc-autumn'


def one(d):
    try:
        meta = json.load(open(os.path.join(d, 'meta.json')))
        ev = [json.loads(l) for l in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt')]
        names = [t['name'] for t in meta['teams']]; us = 0 if not names[0].startswith('rt-') else 1
        out = zipfile.ZipFile(os.path.join(ROOT, meta['source'])).read(f"team-{'ab'[us]}.stdout").decode('utf-8', 'replace')
    except Exception: return None
    team = {c['id']: c['team'] for c in meta['champions']}; typ = {c['id']: c['name'] for c in meta['champions']}
    pr = [c for c in team if typ[c] == 'Prism' and team[c] == us]
    if not pr: return None
    p = pr[0]; S = {}; E = {}; D = {}
    for line in out.replace('\x00', '').splitlines():
        try: T.parse(line.strip(), p, S, E, D)
        except (ValueError, IndexError): pass
    deaths = {x['r'] for x in ev if x['k'] == 'death' and x['v'] == p}
    rows = []
    for q, e in E.items():
        if e['worst'] <= 0: continue
        if q + 1 in S: lost = max(0, e['hp'] - S[q + 1]['hp'])
        elif q + 1 in deaths or q in deaths: lost = e['hp']
        else: continue
        rows.append((e['dec'], e['worst'], lost, e['worst'] / max(1, e['hp']), e['hp']))
    return rows


if __name__ == '__main__':
    root = sys.argv[1]
    dirs = [os.path.join(root, x) for x in os.listdir(root) if os.path.isfile(os.path.join(root, x, 'meta.json'))]
    with Pool(24) as pool: R = [r for g in pool.map(one, dirs, chunksize=8) if g for r in g]
    print(len(R), 'turn ends in reach of an enemy')

    def line(name, S):
        if not S: return
        w = sum(r[1] for r in S); l = sum(min(r[2], r[1]) for r in S)
        hit = sum(1 for r in S if r[2] > 0)
        print(f'  {name:22s} {len(S):6d} turns  damage taken / worst {l / w:.3f}  any damage {100 * hit / len(S):5.1f}%  mean share of worst when hit {sum(min(r[2], r[1]) / r[1] for r in S if r[2] > 0) / max(1, hit):.2f}')
    line('all', R)
    for dec in ('F', 'C', 'R', 'B', 'T', 'P', 'W', 'E', 'G', 'U'):
        line('decision ' + dec, [r for r in R if r[0] == dec])
    for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0), (1.0, 99)):
        line(f'worst/health {lo}-{hi}', [r for r in R if lo <= r[3] < hi])
    for lo, hi in ((0, 0.25), (0.25, 0.5), (0.5, 1.0), (1.0, 99)):
        line(f'not R, worst/health {lo}-{hi}', [r for r in R if lo <= r[3] < hi and r[0] != 'R'])
