"""Base rate for prism_mech.py: Prism-rounds (r <= 300, both teams drafted Prism, every 5th round, alive) bucketed by
exposure (rounds of the previous 20 with an enemy in sight while on a farm/hold branch) and by outnumbering within 8,
with the share that die within the next 15 rounds.  py prism_hazard.py ANALYSIS_ROOT BATCH_NAME"""
import gzip, json, sys, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import prism_mech as pm

FARM = set('FPQCBWUSXGThHr')


def one(dd):
    try:
        m = json.loads((dd / 'meta.json').read_text())
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        z = zipfile.ZipFile(pm.WT / m['source'])
    except Exception:
        return []
    names = {c['id']: c['name'] for c in m['champions']}; team = {c['id']: c['team'] for c in m['champions']}
    prisms = [i for i in names if names[i] == 'Prism']
    if len(prisms) != 2: return []
    br = {}
    for nm in ('team-a.stdout', 'team-b.stdout'):
        for r, cid, b, g, cl in pm.D_RE.findall(z.read(nm)): br[(int(r), int(cid))] = b.decode()
    deaths = {}
    for e in ev:
        if e['k'] == 'death' and e['v'] in prisms: deaths.setdefault(e['v'], []).append(e['r'])
    rix = {r: i for i, r in enumerate(R['round'])}; C = {c['id']: c for c in R['champions']}
    ev_by = {}
    for e in ev:
        if e['k'] in ('cast', 'attack'): ev_by.setdefault(e['r'], []).append(e)
    out = []
    for v in prisms:
        t = team[v]
        for r in range(25, 301, 5):
            i = rix.get(r)
            if i is None or not C[v]['alive'][i]: continue
            if any(d <= r for d in deaths.get(v, [])): break  # first life only
            vp = (C[v]['x'][i], C[v]['y'][i])
            expo = 0
            for rr in range(r - 20, r):
                j = rix.get(rr)
                if j is None or not C[v]['alive'][j]: continue
                if any(team.get(x) != t for x in C[v]['sees'][j] or []) and br.get((rr, v), '?') in FARM: expo += 1
            al8 = en8 = 0
            for c in C:
                if c == v or not C[c]['alive'][i] or C[c]['x'][i] is None: continue
                if pm.cheb(vp, (C[c]['x'][i], C[c]['y'][i])) <= 8:
                    if team[c] == t: al8 += 1
                    else: en8 += 1
            die = any(r < d <= r + 15 for d in deaths.get(v, []))
            hpf = C[v]['hp'][i] / max(1, C[v]['maxHp'][i])
            b2 = ''.join(br.get((rr, v), '?') for rr in (r, r + 1, r + 2))
            hit = any(e['r'] in (r - 1, r) and team.get(e.get('a')) not in (None, t) and any(tid == v for tid, _ in e.get('dmg') or []) for e in ev_by.get(r, []) + ev_by.get(r - 1, []))
            ed = [pm.cheb(vp, (C[c]['x'][i], C[c]['y'][i])) for c in C if team[c] != t and C[c]['alive'][i] and C[c]['x'][i] is not None]
            j5 = rix.get(r + 5)
            ed5 = None
            if j5 is not None and C[v]['alive'][j5]:
                vp5 = (C[v]['x'][j5], C[v]['y'][j5])
                ed5 = min([pm.cheb(vp5, (C[c]['x'][j5], C[c]['y'][j5])) for c in C if team[c] != t and C[c]['alive'][j5] and C[c]['x'][j5] is not None] or [99])
            out.append((expo, al8, en8, die, b2, hpf, hit, min(ed or [99]), ed5))
    return out


def main():
    root = Path(sys.argv[1]); bname = sys.argv[2]
    dirs = [dd for dd in sorted(root.iterdir()) if (dd / 'meta.json').exists() and bname in (json.loads((dd / 'meta.json').read_text()).get('source') or '')]
    allr = []
    with ProcessPoolExecutor(24) as ex:
        for x in ex.map(one, dirs, chunksize=4): allr += x
    print('prism-rounds', len(allr), 'die within 15:', sum(x[3] for x in allr))
    def rate(pred, label):
        S = [x for x in allr if pred(x)]
        print(f'{label}: n={len(S)} share of samples {len(S) / len(allr) * 100:.1f}%  die-within-15 {sum(x[3] for x in S) / max(1, len(S)) * 100:.1f}%')
    rate(lambda x: x[0] == 0, 'exposure 0')
    rate(lambda x: 1 <= x[0] < 8, 'exposure 1-7')
    rate(lambda x: x[0] >= 8, 'exposure >=8')
    rate(lambda x: x[0] >= 8 and x[2] > x[1], 'exposure >=8 and outnumbered within 8 now')
    rate(lambda x: x[0] >= 8 and x[2] <= x[1], 'exposure >=8 and not outnumbered')
    rate(lambda x: x[2] >= 2 and x[2] > x[1], '>=2 enemies within 8, outnumbered')
    rate(lambda x: x[2] >= 2 and x[2] <= x[1], '>=2 enemies within 8, not outnumbered')
    rate(lambda x: x[2] == 0, 'no enemy within 8')
    base = lambda x: x[2] >= 2 and x[2] > x[1] and not x[6] and x[5] > 0.7
    for lo, hi in ((5, 6), (7, 8)):
        b = lambda x: base(x) and lo <= x[7] <= hi
        for lab, p in (('retreats (R in next 3)', lambda x: 'R' in x[4]), ('keeps farming', lambda x: 'R' not in x[4] and x[4][0] in FARM)):
            S = [x for x in allr if b(x) and p(x)]
            g = [x for x in S if x[8] is not None]
            print(f'nearest enemy {lo}-{hi}, outnumbered, unhit, hp>70%, {lab}: n={len(S)} die15 {sum(x[3] for x in S) / max(1, len(S)) * 100:.1f}%'
                  f'  nearest enemy 5 rounds later mean {sum(x[8] for x in g) / max(1, len(g)):.1f}')


if __name__ == '__main__':
    main()
