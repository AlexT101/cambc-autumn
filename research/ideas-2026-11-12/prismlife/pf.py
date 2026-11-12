"""Where the Prism's fuel goes within a turn (variants/pl-prof's PF lines): python3 pf.py BATCHGLOB
PF round handle decision nearest-visible-enemy f0 f1 f2 f3 f4 f5: the fuel left at decide's start, after want_home,
after the strike search, after the work guard, after decide, and at the turn's end (0: not reached)."""
import collections, glob, sys, zipfile
rows = []
for f in glob.glob(sys.argv[1] + '/*.repl26a'):
    side = 'b' if f.rsplit('.', 1)[0].endswith('-21') else 'a'
    for line in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8', 'replace').replace('\x00', '').splitlines():
        v = line.split()
        if len(v) == 11 and v[0] == 'PF':
            try: rows.append((v[3], int(v[4]), [int(x) for x in v[5:]]))
            except ValueError: pass
print(len(rows), 'Prism turns')


def show(name, S):
    if not S: return
    n = len(S)
    def med(xs):
        xs = sorted(xs); return xs[len(xs) // 2] if xs else 0
    def p90(xs):
        xs = sorted(xs); return xs[int(.9 * len(xs))] if xs else 0
    seg = [('before decide', lambda f: 100000 - f[0]), ('want_home', lambda f: f[0] - f[1] if f[1] else None), ('strike search', lambda f: f[1] - f[2] if f[1] and f[2] else None),
           ('guards', lambda f: f[2] - f[3] if f[2] and f[3] else None), ('goal (farm, bank...)', lambda f: (f[3] or f[2] or f[1] or f[0]) - f[4] if f[4] else None), ('turn end', lambda f: f[4] - f[5] if f[4] else None)]
    print(f'{name}: {n} turns; fuel left at the end: median {med([r[2][5] for r in S])}, under 5k in {100 * sum(1 for r in S if r[2][5] < 5000) / n:.1f}%')
    for nm, fn in seg:
        xs = [fn(r[2]) for r in S]; xs = [x for x in xs if x is not None]
        if xs: print(f'    {nm:22s} reached {100 * len(xs) / n:5.1f}%  median {med(xs):6d}  p90 {p90(xs):6d}  mean {sum(xs) / len(xs):7.0f}')


show('all', rows)
show('enemy in sight within 8', [r for r in rows if r[1] <= 8])
for d in 'FRCBT':
    show(f'enemy within 8, decision {d}', [r for r in rows if r[1] <= 8 and r[0] == d])
show('no enemy in sight', [r for r in rows if r[1] > 8])
