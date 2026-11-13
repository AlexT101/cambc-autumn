"""lastdec.py EXT: for each of our deaths (whole game), the victim's branch on its last 3 turns, by killer class and phase."""
import sys, collections
sys.path.insert(0, '/home/ubuntu/cambc-autumn/research/ideas-2026-11-12/vfish/surv')
from tracelib import *
ext = sys.argv[1]
C = collections.defaultdict(collections.Counter); N = collections.Counter(); ng = 0
for gm in games(ext):
    ng += 1; typ = gm.typ; team = gm.team; cand = gm.cand
    for d in gm.deaths(5000):
        v = d['v']; r = d['r']; by = d.get('by')
        cls = 'Prism' if by in typ and typ[by] == 'Prism' and team[by] != cand else 'camp' if (by not in typ or team.get(by) == cand) else 'other'
        ph = 'r<=300' if r <= 300 else 'r301-600' if r <= 600 else 'r601+'
        seq = ''.join(gm.dec(v, rr) for rr in (r - 2, r - 1, r))
        last = [x for x in seq if x not in '-?']
        key = 'E' if 'E' in seq else 'U' if 'U' in seq else 'G' if 'G' in seq else (last[-1] if last else '?')
        C[(cls, ph)][key] += 1; N[(cls, ph)] += 1
print(ng, 'games')
for k in sorted(N):
    tot = N[k]; print(f"  {k[0]:6} {k[1]:9} {tot:5d} ({tot/ng:.2f} a game): " + ' '.join(f"{a}:{b/tot:.2f}" for a, b in C[k].most_common(8)))
