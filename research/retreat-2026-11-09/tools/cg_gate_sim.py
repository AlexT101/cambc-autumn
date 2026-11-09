"""What a chase_aim gate at fuel left after the build >= T would save: the excess OOF of its builds below T and the
builds it drops, from cg_instrument.py traces. usage: cg_gate_sim.py BATCH_DIR"""
import sys, glob, zipfile
from collections import defaultdict
AIM = {4, 5}
B = 2000
ts = []
g = 0
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    order = f.rsplit('-', 1)[1][:2]
    z = zipfile.ZipFile(f)
    team = 'a' if order == '12' else 'b'
    g += 1
    for l in z.read(f'team-{team}.stdout').decode(errors='replace').replace('\x00', '').splitlines():
        if not (l.startswith('CG ') or l.startswith('CGO ')): continue
        p = l.split()
        try:
            n = int(p[10]); b = [tuple(map(int, x.split(':'))) for x in p[11:11 + n]]
            used, esc = int(p[13 + n]), int(p[14 + n])
        except (ValueError, IndexError):
            continue
        ab = [x for x in b if x[0] in AIM]
        if not ab: continue
        X = ab[-1][1] - ab[-1][2]
        ts.append((X, sum(x[2] for x in ab), p[0] == 'CGO' and int(p[3]) >= 3, used, esc))
for sub in ('all', 'used', 'unused'):
    sel = [t for t in ts if sub == 'all' or (t[3] == 1) == (sub == 'used')]
    t, o = defaultdict(int), defaultdict(int)
    for X, c, oof, *_ in sel:
        t[X // B] += 1; o[X // B] += oof
    def P(x):
        k = x // B; lo = hi = k; n, m = t.get(k, 0), o.get(k, 0)
        while n < 200 and (lo > 0 or hi < 60):
            lo -= 1; hi += 1; n += t.get(lo, 0) + t.get(hi, 0); m += o.get(lo, 0) + o.get(hi, 0)
        return m / n if n else 0.0
    for T in (45000, 50000, 53000, 55000, 58000):
        below = [s for s in sel if s[0] < T]
        ex = sum(P(X) - P(X + c) for X, c, *_ in below)
        print(f'{sub:6s} T {T}: builds dropped {len(below) / g:.2f} a team-game ({100 * len(below) / len(sel):.0f}%), '
              f'escaped among them {sum(1 for s in below if s[4]) / g:.2f}; OOF saved {100 * ex / g:.1f} per 100 team-games')
