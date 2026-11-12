"""Per-map agreement: live win rate per map (all our versions against the pin, both sides) against the body's win
rate on the same map, side and our version. Pearson r over maps, weighted by live games, with a permutation p.
    py permap.py BODY...  [--ref r7]"""
import sys, random, math, collections
sys.argv += [] ; import calread as C
L = C.live()
for body in C.args:
    lw = collections.defaultdict(list); bw = collections.defaultdict(list)
    for v, bot in C.VER.items():
        cell = C.local(bot, body)
        for (vv, m, s), xs in L.items():
            if vv != v or (m, s) not in cell: continue
            p = sum(cell[(m, s)]) / len(cell[(m, s)])
            for x in xs: lw[m].append(x); bw[m].append(p)
    maps = sorted(lw); n = [len(lw[m]) for m in maps]
    a = [sum(lw[m]) / len(lw[m]) for m in maps]; b = [sum(bw[m]) / len(bw[m]) for m in maps]
    def r(a, b):
        W = sum(n); ma = sum(w * x for w, x in zip(n, a)) / W; mb = sum(w * x for w, x in zip(n, b)) / W
        cov = sum(w * (x - ma) * (y - mb) for w, x, y in zip(n, a, b)); va = sum(w * (x - ma) ** 2 for w, x in zip(n, a)); vb = sum(w * (y - mb) ** 2 for w, y in zip(n, b))
        return cov / math.sqrt(va * vb) if va and vb else 0
    r0 = r(a, b); rng = random.Random(1); perm = sum(r(a, rng.sample(b, len(b))) >= r0 for _ in range(2000)) / 2000
    mae = sum(w * abs(x - y) for w, x, y in zip(n, a, b)) / sum(n)
    print(f'{body}: {len(maps)} maps, {sum(n)} live games; per-map r = {r0:.3f} (permutation p {perm:.3f}); weighted mean |live - body| {100*mae:.1f} points')
