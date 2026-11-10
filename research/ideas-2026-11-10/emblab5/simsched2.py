import numpy as np
rng = np.random.default_rng(2)
N, M = 330, 20
def truth():
    t = rng.normal(-0.15, 0.3, N)
    t[:10] = rng.uniform(-3, -0.5, 10); t[10:18] = 0
    t[18] = 0.5; t[19] = 0.3; t[20] = 1.0; t[21] = 0.4
    return t
def noisy(t, n): return t + rng.normal(0, 1, t.shape) * 50 / np.sqrt(n)
def plan(t):
    a = noisy(t, 12000); cost = N * 12000
    keep = np.argsort(-a)[:165]
    b = (a[keep] * 12000 + noisy(t[keep], 24000) * 24000) / 36000; cost += 165 * 24000
    keep = keep[np.argsort(-b)[:60]]
    c = noisy(t[keep], 60000); cost += 60 * 60000
    return set(keep[np.argsort(-c)[:M]]), cost
def halving(t, sched):
    """sched: [(cumulative n, keep after)], estimates cumulative."""
    keep = np.arange(N); s = np.zeros(N); n0 = 0; cost = 0
    for n, k in sched:
        add = n - n0
        s[keep] += noisy(t[keep], add) * add; cost += len(keep) * add; n0 = n
        keep = keep[np.argsort(-s[keep])[:k]]
    return set(keep), cost
S = {
 "plan, C cumulative": [(12000, 165), (36000, 60), (96000, 20)],
 "3 stages, C to 72k": [(12000, 165), (36000, 60), (72000, 20)],
 "5 stages a": [(6000, 240), (12000, 165), (24000, 100), (40000, 55), (72000, 20)],
 "5 stages b": [(8000, 220), (16000, 140), (28000, 85), (44000, 50), (76000, 20)],
 "6 stages c": [(6000, 250), (12000, 180), (20000, 120), (32000, 75), (48000, 45), (80000, 20)],
 "6 stages d": [(6000, 260), (12000, 190), (20000, 130), (32000, 85), (52000, 50), (88000, 20)],
 "7 stages e": [(4000, 280), (8000, 230), (14000, 170), (22000, 120), (34000, 80), (52000, 48), (84000, 20)],
}
R = 1500
def run(name, f):
    hit = np.zeros(4); cost = 0; q = 0
    for _ in range(R):
        t = truth(); sel, c = f(t); cost += c
        hit += [i in sel for i in (18, 19, 20, 21)]; q += np.mean(t[list(sel)])
    print(f"{name:22s} cost {cost / R / 1e6:5.2f}M  P(reach D): +0.5 {hit[0] / R:.3f}  +0.4 {hit[3] / R:.3f}  +0.3 {hit[1] / R:.3f}  +1.0 {hit[2] / R:.3f}  D-set truth {q / R:+.3f}")
run("plan", plan)
for k, v in S.items(): run(k, lambda t, v=v: halving(t, v))
