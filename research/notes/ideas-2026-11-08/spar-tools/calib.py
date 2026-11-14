"""Calibration of local setups against live (v86-89, r2 Fish + Mite).
   python3 calib.py SETUP...   where SETUP is label=run[:ver:opp],run[:ver:opp],...  (ver 86-89, opp F/M: paired cells)"""
import sys, os, hashlib, collections, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import live, local
C = live.cells('r2'); L = live.per_map(C); LF = live.per_map(C, 'F'); LM = live.per_map(C, 'M')
maps = sorted(L); half = {m: int(hashlib.md5(m.encode()).hexdigest(), 16) % 2 for m in maps}

def corr(a, b, ms):
    x = np.array([a[m] for m in ms]); y = np.array([b[m] for m in ms])
    return np.corrcoef(x, y)[0, 1]

def boot_ci(a, b, ms, n=2000):
    rng = np.random.default_rng(1); ms = np.array(ms); rs = []
    for _ in range(n):
        s = rng.choice(ms, len(ms)); rs.append(corr(a, b, list(s)))
    return np.nanpercentile(rs, [2.5, 97.5])

def evaluate(label, runs):
    pm = collections.defaultdict(list); pair = []
    for spec in runs:
        name, *vo = spec.split(':')
        for (m, side), w in local.cells(name).items():
            pm[m].append(w)
            if vo:
                k = (int(vo[0]), m, side, vo[1])
                if k in C: pair.append((w, C[k]))
    P = {m: np.mean(pm[m]) for m in maps if m in pm}; ms = [m for m in maps if m in P]
    r = corr(P, L, ms); lo, hi = boot_ci(P, L, ms)
    rh = [corr(P, L, [m for m in ms if half[m] == h]) for h in (0, 1)]
    line = (f'{label:28s} n/map {len(pm[ms[0]]):3d} local {100*np.mean(list(P.values())):5.1f}%  r {r:+.2f} ({lo:+.2f}..{hi:+.2f})'
            f'  halves {rh[0]:+.2f}/{rh[1]:+.2f}  rF {corr(P, LF, ms):+.2f} rM {corr(P, LM, ms):+.2f}')
    if pair:
        p = np.array(pair); agree = np.mean(p[:, 0] == p[:, 1]); phi = np.corrcoef(p[:, 0], p[:, 1])[0, 1]
        line += f'  cells {len(p)} agree {100*agree:.0f}% phi {phi:+.2f} (live {100*p[:,1].mean():.0f}%)'
    print(line); return P

if __name__ == '__main__':
    print(f'live r2 v86-89: {len(C)} cells, {len(maps)} maps, {100*np.mean(list(C.values())):.1f}% won; r(F, M) {corr(LF, LM, maps):+.2f}')
    for a in sys.argv[1:]:
        label, runs = a.split('=', 1); evaluate(label, runs.split(','))
