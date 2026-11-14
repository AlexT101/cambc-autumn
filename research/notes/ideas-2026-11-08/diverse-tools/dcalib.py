"""Calibrate opponent-panel designs against live (diverse-panel.md): per-map r with live on the 128 ladder maps, and
the paired deltas of the v86 -> v87 -> v88 -> v89 -> v91 chain (and v89 -> v90, soup-k) against live's.
    python3 dcalib.py [DESIGN...]      (designs below; default all)"""
import sys, os, collections, hashlib, numpy as np
T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(T, '..', 'spar-tools')); import live, local, spar_ab
R = local.R
VER = {'base23': 86, 'base25': 87, 'base26': 88, 'base27': 89, 's2-soupk27': 90, 'base29': 91}
CHAIN = [('base23', 'base25'), ('base25', 'base26'), ('base26', 'base27'), ('base27', 'base29'), ('base23', 'base29'),
         ('base27', 's2-soupk27')]
C = live.cells('r2', 86, 91)
LIVE_PM = live.per_map({k: w for k, w in C.items() if k[0] != 90})  # v90 played only 200 cells
OPP = lambda b: b[-1] if b[-1] in 'FM' else None

def spar_members(bodies): return [(b, o) for b in bodies for o in 'FM']
DESIGNS = {
    'cur':   ('current panel: astraeus-td, proteus-td (test drafts)', [('gp', 'astraeus'), ('gp', 'proteus')]),
    'spar':  ('spar: oc-base29 + 12 jitters, live drafts', spar_members(['o29'] + [f'j{i}' for i in range(1, 13)])),
    'tuneL': ('5 tunings/styles, live drafts', spar_members(['dvoc6', 'dvanti6', 'dvagg', 'dvpas', 'dvgreed'])),
    'noiseL': ('4 noise seeds, live drafts', spar_members(['dvn1', 'dvn2', 'dvn3', 'dvn4'])),
    'noise8': ('8 noise seeds, live drafts', spar_members([f'dvn{i}' for i in range(1, 9)])),
    'noise5-8': ('noise seeds 5-8 only (replication)', spar_members([f'dvn{i}' for i in range(5, 9)])),
    'tuneTD': ('5 tunings/styles, ladder-comp drafts', [('td', b) for b in ['oc6', 'anti6', 'agg', 'pas', 'greed']]),
}
DESIGNS['divL'] = ('tunings + noise, live drafts', DESIGNS['tuneL'][1] + DESIGNS['noiseL'][1])
DESIGNS['all-L'] = ('spar + tunings + noise, live drafts', DESIGNS['spar'][1] + DESIGNS['divL'][1])

def run_of(v, m):
    a, b = m
    if a == 'gp': return f'dvp-c{v}td-gp{b}'
    if a == 'td': return f'dvp-c{v}-{b}td'
    return spar_ab.run_name(f'variants/oc-{v}', a, b)

_cache = {}
def cells(name):
    if name not in _cache:
        _cache[name] = local.cells(name) if os.path.exists(f'{R}replays/ab/{name}/summary.json') else None
    return _cache[name]

def corr(a, b, ms): return np.corrcoef([a[m] for m in ms], [b[m] for m in ms])[0, 1]

def evaluate(key):
    label, members = DESIGNS[key]
    pm = collections.defaultdict(list); have = collections.Counter()
    for v in VER:
        if v == 's2-soupk27': continue
        for m in members:
            c = cells(run_of(v, m))
            if not c: continue
            have[v] += 1
            for (mp, s), w in c.items(): pm[mp].append(w)
    ms = sorted(m for m in LIVE_PM if m in pm)
    if len(ms) < 20: print(f'{key}: no data'); return None
    P = {m: np.mean(pm[m]) for m in ms}
    r = corr(P, LIVE_PM, ms); rng = np.random.default_rng(1)
    bs = [corr(P, LIVE_PM, list(rng.choice(ms, len(ms)))) for _ in range(2000)]
    half = {m: int(hashlib.md5(m.encode()).hexdigest(), 16) % 2 for m in ms}
    rh = [corr(P, LIVE_PM, [m for m in ms if half[m] == h]) for h in (0, 1)]
    print(f'\n## {key}: {label}  ({len(members)} members; runs per version {dict(have)})')
    print(f'  per-map r {r:+.2f} ({np.percentile(bs, 2.5):+.2f}..{np.percentile(bs, 97.5):+.2f}), halves {rh[0]:+.2f}/{rh[1]:+.2f}, '
          f'n/map {len(pm[ms[0]])}, local win {100*np.mean(list(P.values())):.1f}% (live {100*np.mean(list(LIVE_PM.values())):.1f}%)')
    out = {'r': r, 'members': len(members)}
    for a, b in CHAIN:
        d, k = [], []
        for m in members:
            x, y = cells(run_of(a, m)), cells(run_of(b, m))
            if not x or not y: continue
            for c in x:
                if c in y: d.append(y[c] - x[c]); k.append((c[0], c[1], OPP(m[1]) or OPP(m[0]) or ''))
        va, vb = VER[a], VER[b]
        e = np.array([C[(vb, m, s, o)] - C[(va, m, s, o)] for (v, m, s, o) in C if v == va and (vb, m, s, o) in C])
        lv = f'live {100*e.mean():+5.1f} ±{196*e.std()/np.sqrt(len(e)):.1f} ({len(e)})'
        if not d: print(f'  {va}->{vb}: no runs   {lv}'); continue
        d = np.array(d); g = collections.defaultdict(list)
        for kk, x in zip(k, d): g[kk].append(x)
        mm = np.array([np.mean(x) for x in g.values()]); sec = mm.std() / np.sqrt(len(mm))
        print(f'  v{va}->v{vb}: panel {100*d.mean():+5.2f} ±{196*sec:.2f} (cell-clustered; ±{196*d.std()/np.sqrt(len(d)):.2f} by game; '
              f'{len(d)} games)   {lv}')
        out[(a, b)] = (100 * d.mean(), 196 * sec, 100 * e.mean())
    return out

if __name__ == '__main__':
    print(f'live r2 v86-91 (v90 excluded from the per-map target): {len(C)} cells')
    res = {k: evaluate(k) for k in (sys.argv[1:] or DESIGNS)}
