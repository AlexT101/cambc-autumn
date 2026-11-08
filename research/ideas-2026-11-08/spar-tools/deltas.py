"""Spar-predicted A/B deltas against live paired deltas.
   python3 deltas.py BODY[,BODY...]   (runs named spar-c<cand>-<body><F|M>; cands as in PAIRS)"""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__)); import live, local
C = live.cells('r2', 86, 90)
VER = {'23': 86, '25': 87, '26': 88, '27': 89, 's2-soupk27': 90}
PAIRS = [('23', '25'), ('25', '26'), ('26', '27'), ('23', '27'), ('27', 's2-soupk27'), ('25', 's2-soupk27'),
         ('25', 'base29'), ('base28', 'base29'), ('27', 'base29'), ('23', 'base29')]
def name(c, b, o): return f'spar-c{c}-{b}{o}'
def run(c, b, o):
    n = name(c, b, o)
    return local.cells(n) if os.path.exists(f'{local.R}replays/ab/{n}/summary.json') else None
bodies = sys.argv[1].split(',')
print(f'{"pair":22s} {"spar delta":>16s} {"n":>5s}   {"live delta":>16s} {"cells":>5s}')
for a, b in PAIRS:
    d = []
    for body in bodies:
        for o in 'FM':
            x, y = run(a, body, o), run(b, body, o)
            if x and y: d += [y[k] - x[k] for k in x if k in y]
    if not d: continue
    d = np.array(d); s = f'{100*d.mean():+5.1f} ±{196*d.std()/np.sqrt(len(d)):.1f}'
    lv = ''
    if a in VER and b in VER:
        va, vb = VER[a], VER[b]
        e = np.array([C[(vb, m, s_, o)] - C[(va, m, s_, o)] for (v, m, s_, o) in C if v == va and (vb, m, s_, o) in C])
        lv = f'{100*e.mean():+5.1f} ±{196*e.std()/np.sqrt(len(e)):.1f} {len(e):5d}'
    print(f'{a+"->"+b:22s} {s:>16s} {len(d):5d}   {lv}')
