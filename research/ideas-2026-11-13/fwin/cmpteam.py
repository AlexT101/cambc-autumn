"""Our games against other teams' on the same maps (cell = map, Fish side), feature by feature: per-cell means, then
the mean difference (team X minus us) over shared cells; and wins vs losses within each.
    py cmpteam.py OURS.jsonl OTHERS.jsonl TEAM [--keys ...]"""
import json, sys, collections, math
ours, others, team = sys.argv[1:4]
U = [json.loads(l) for l in open(ours)]; X = [g for g in (json.loads(l) for l in open(others)) if g['opp'] == team]
def val(g, k):
    if k.startswith('d_'):
        a, b = g.get('f_' + k[2:]), g.get('o_' + k[2:]); return (a or 0) - (b or 0)
    if k == 'o_win': return 0.0 if g['fish_win'] else 1.0
    v = g.get(k)
    if v is None and any(k.startswith(p) for p in ('f_kills', 'o_kills', 'f_deaths', 'o_deaths', 'f_gemslost', 'o_gemslost', 'f_capgold', 'o_capgold', 'f_capn', 'o_capn', 'f_campdeaths', 'o_campdeaths')): v = 0
    return v
keys = ['o_win', 'rounds']
for c in (100, 200, 300, 500, 800):
    keys += [f'f_earned_{c}', f'v_earned_{c}', f'o_earned_{c}', f'f_gems_{c}', f'o_gems_{c}', f'o_kills_{c}', f'f_kills_{c}', f'v_kills_{c}', f'v_deaths_{c}', f'o_gemslost_{c}', f'f_gemslost_{c}', f'o_capgold_enemy_{c}', f'o_capgold_mid_{c}', f'f_capgold_mid_{c}']
keys += ['o_ntrib', 'o_ntrib100', 'o_trib1', 'f_ntrib', 'f_ntrib100', 'f_trib1', 'v_greed', 'o_locks']
if '--keys' in sys.argv: keys = sys.argv[sys.argv.index('--keys') + 1].split(',')
cell = lambda g: (g['map'], g['fish'])
CU = collections.defaultdict(list); CX = collections.defaultdict(list)
for g in U: CU[cell(g)].append(g)
for g in X: CX[cell(g)].append(g)
shared = [c for c in CX if c in CU]
print(f'{team}: {len(X)} games, {len(shared)} cells shared with ours ({sum(len(CU[c]) for c in shared)} of our games)')
def mean(xs):
    xs = [x for x in xs if x is not None]; return sum(xs) / len(xs) if xs else None
def ms(ds):
    m = sum(ds) / len(ds); se = math.sqrt(sum((d - m) ** 2 for d in ds) / max(1, len(ds) - 1) / len(ds)) if len(ds) > 1 else float('nan'); return m, se
print(f"{'feature':22s} {'us':>8s} {team[:8]:>8s} {'diff':>8s} {'±se':>6s} | {'X win-loss':>10s} {'±se':>6s} {'n':>3s} | {'us win-loss':>11s} {'±se':>6s}")
for k in keys:
    ds = []; a = []; b = []
    for c in shared:
        mu = mean(val(g, k) for g in CU[c]); mx = mean(val(g, k) for g in CX[c])
        if mu is None or mx is None: continue
        ds.append(mx - mu); a.append(mu); b.append(mx)
    if not ds: continue
    m, se = ms(ds)
    wl = []
    for C in (CX, CU):
        d2 = []
        for c in (shared if C is CX else list(CU)):
            W = [val(g, k) for g in C[c] if not g['fish_win']]; L = [val(g, k) for g in C[c] if g['fish_win']]
            mw, ml = mean(W), mean(L)
            if mw is not None and ml is not None: d2.append(mw - ml)
        wl.append(ms(d2) + (len(d2),) if len(d2) > 1 else (float('nan'), float('nan'), len(d2)))
    print(f'{k:22s} {sum(a)/len(a):8.1f} {sum(b)/len(b):8.1f} {m:+8.1f} {se:6.1f} | {wl[0][0]:+10.1f} {wl[0][1]:6.1f} {wl[0][2]:3d} | {wl[1][0]:+11.1f} {wl[1][1]:6.1f}')
