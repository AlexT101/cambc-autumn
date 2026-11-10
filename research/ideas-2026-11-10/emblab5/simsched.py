import numpy as np, sys
rng = np.random.default_rng(1)
N, M = 330, 20
def truth():
    t = rng.normal(-0.15, 0.3, N)
    t[:10] = rng.uniform(-3, -0.5, 10)       # anchors
    t[10:18] = 0                              # placebos
    t[18] = 0.5; t[19] = 0.3; t[20] = 1.0; t[21] = 0.4  # probes
    return t
def noisy(t, n):  # estimate from n appearances
    return t + rng.normal(0, 1, t.shape) * 50 / np.sqrt(n)
def plan(t):
    a = noisy(t, 12000); cost = N * 12000
    keep = np.argsort(-a)[:165]
    b = (a[keep] * 12000 + noisy(t[keep], 24000) * 24000) / 36000; cost += 165 * 24000
    keep = keep[np.argsort(-b)[:60]]
    c = noisy(t[keep], 60000); cost += 60 * 60000
    return set(keep[np.argsort(-c)[:M]]), cost
def cont(t, c=2.0, batch=200000, nmax=96000, floor=6000):
    n = np.zeros(N); s = np.zeros(N); alive = np.ones(N, bool); cost = 0
    while True:
        idx = np.flatnonzero(alive & (n < nmax))
        if len(idx) == 0 or alive.sum() <= M: break
        q = min(batch / len(idx), nmax - n[idx].min()) if True else 0
        q = max(q, 1)
        add = np.minimum(q, nmax - n[idx])
        s[idx] += noisy(t[idx], add) * add; n[idx] += add; cost += add.sum()
        est = s / np.maximum(n, 1); se = 50 / np.sqrt(np.maximum(n, 1))
        a = np.flatnonzero(alive)
        if n[a].min() < floor: continue
        lcb = np.sort(est[a] - c * se[a])[::-1]
        thr = lcb[min(M, len(a)) - 1]
        drop = a[est[a] + c * se[a] < thr]
        alive[drop] = False
    a = np.flatnonzero(alive)
    est = s[a] / n[a]
    return set(a[np.argsort(-est)[:M]]), cost
R = 400
for name, f in [("plan", plan)] + [(f"cont c={c} nmax={nm}", (lambda t, c=c, nm=nm: cont(t, c, nmax=nm))) for c in (1.5, 2.0, 2.5) for nm in (72000, 96000)]:
    hit = np.zeros(4); cost = 0; q = 0
    for _ in range(R):
        t = truth(); sel, cst = f(t); cost += cst
        hit += [i in sel for i in (18, 19, 20, 21)]
        q += np.mean(t[list(sel)])
    print(f"{name:26s} cost {cost / R / 1e6:5.2f}M  P(reach D): +0.5 {hit[0] / R:.2f}  +0.3 {hit[1] / R:.2f}  +1.0 {hit[2] / R:.2f}  +0.4 {hit[3] / R:.2f}  mean truth of D set {q / R:+.3f}")
