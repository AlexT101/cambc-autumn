# Old bodies (dgate's spar-*-F/M) against new ones (Fish locks -Fl, Mite habit -Mt3) on the same draws: block 0 and
# noise seeds 1..K, for each calibration arm against oc-base25.   py calib.py [K]
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cmp
K = int(sys.argv[1]) if len(sys.argv) > 1 else 16
B0 = ['o25', 'oc29']
def members(new):
    f, m = ('Fl', 'Mt3') if new else ('F', 'M')
    return [f'spar-{b}-{x}' for b in B0 for x in (f, m)] + [f'spar-dvn{k}-{x}' for k in range(1, K + 1) for x in (f, m)]
for arm in ('lk600', 'nh63', 'sk'):
    for new in (False, True):
        ms = members(new)
        ok = [m for m in ms if all(os.path.exists(f'{cmp.local.R}replays/ab/{cmp.run(t, m)}/summary.json') for t in (arm, 'c25'))]
        print(f'== {arm} vs c25, {"new" if new else "old"} bodies ({len(ok)}/{len(ms)} members)')
        if not ok: continue
        # pooled by site class and by opponent kind
        cmp.table(arm, 'c25', ok) if False else None
        agg = {}
        import collections, math
        d = collections.defaultdict(list)
        for m in ok:
            x, y = cmp.local.cells(cmp.run(arm, m)), cmp.local.cells(cmp.run('c25', m))
            kind = 'F' if m.endswith(('-F', '-Fl')) else 'M'
            for c in x.keys() & y.keys():
                for g in (('all', 'all'), ('all', cmp.cls(c[0])), (kind, 'all'), (kind, cmp.cls(c[0]))):
                    d[g].append((x[c] - y[c], y[c]))
        for g in sorted(d):
            v = [a for a, _ in d[g]]; n = len(v); mu = sum(v) / n; sd = (sum((a - mu) ** 2 for a in v) / n) ** .5
            print(f'   {g[0]:3s} {g[1]:5s} n {n:5d}  base win {100*sum(b for _, b in d[g])/n:5.1f}  arm-base {100*mu:+6.2f} ±{196*sd/math.sqrt(n):.2f}')
