"""Lethal and summed danger per decision (PLAN2.md): the held-out danger rows grouped by (opponent run, frame, round,
victim), so each group is one of our turns with every visible enemy that could hit our end tile.

    python3 research/reply-model/lethal.py [GAM.pkl ...]

For each group: the damage actually taken before our next turn from those enemies (sum of labels; a victim killed
by the first enemy keeps only that row, build.py), our health and shield (my_hp), and three predictions:
  worst  sum of blows (ocean's lethal/damage_bound, without camps and unseen enemies),
  flat   0.234 x the sum (plan_strikes' danger), model: the full model's expected damage summed,
  pk     P(killed) with independent hits: enemy i deals k_i x blow_i with probability p_i (a Poisson-binomial over
         the group's enemies, exact by enumeration up to 6 enemies).
Reports the sum's R2 for each, and for lethal: how many groups each flags, and recall/precision against groups
whose taken damage reached our health.
"""
import pickle
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import compress  # noqa: E402,F401  (pickled Gam classes)
import train  # noqa: E402

C = "replays/combatlab/reply/compress"


def main():
    va = np.load(f"{C}/val.npy")
    cfg = np.load(f"{C}/val_cfg.npy")
    X, y = va[:, 4:-1], va[:, -1]
    m = pickle.load(open("replays/combatlab/reply/m1.pkl", "rb"))
    ph = m["danger"][0].predict_proba(X)[:, 1]
    dmg = np.maximum(m["danger"][1].predict(X), 0)
    ed = ph * dmg
    blow = X[:, 1]
    key = ((cfg.astype(np.int64) * (1 << 24) + va[:, 0].astype(np.int64)) * 4096 + va[:, 1].astype(np.int64)) * 64 + va[:, 2].astype(np.int64)
    u, inv = np.unique(key, return_inverse=True)
    n = np.bincount(inv)
    taken = np.bincount(inv, y)
    hp = np.zeros(len(u))
    hp[inv] = X[:, 12]
    worst = np.bincount(inv, blow)
    flat = train.HGR * worst
    model = np.bincount(inv, ed)
    print(f"groups {len(u)}, enemies per group: " + ", ".join(f"{k}: {(n == k).mean():.3f}" for k in range(1, 5)) + f", 5+: {(n >= 5).mean():.3f}")
    var = np.var(taken)
    for name, p in (("worst (sum of blows)", worst), ("flat 0.234 x sum", flat), ("model sum", model)):
        print(f"  summed danger {name:22s} R2 {1 - np.mean((p - taken) ** 2) / var:.3f}  mean {p.mean():.1f} / {taken.mean():.1f}")
    killed = taken >= hp - 0.5
    print(f"killed (taken >= health): {killed.mean():.4f} of groups ({killed.sum()})")
    # P(killed) by enumeration of hit subsets, damage given a hit = the regressor's (dmg / k-scaled blow).
    order = np.argsort(inv, kind="stable")
    starts = np.r_[0, np.cumsum(n)]
    pk = np.zeros(len(u))
    pkb = np.zeros(len(u))
    for g in range(len(u)):
        rows = order[starts[g]:starts[g + 1]]
        if len(rows) > 6:
            rows = rows[np.argsort(-ed[rows])[:6]]
        p, d, b = ph[rows], dmg[rows], blow[rows]
        if b.sum() < hp[g]:
            continue  # no subset reaches it either way (dmg is at most about blow)
        tot = totb = 0.0
        for mask in range(1, 1 << len(rows)):
            bits = np.array([(mask >> i) & 1 for i in range(len(rows))], bool)
            pr = np.prod(np.where(bits, p, 1 - p))
            if d[bits].sum() >= hp[g]:
                tot += pr
            if b[bits].sum() >= hp[g]:
                totb += pr
        pk[g], pkb[g] = tot, totb
    print(f"  Pblow(killed) log loss {train.logloss(pkb, killed.astype(float)):.4f}")
    ll = train.logloss(pk, killed.astype(float))
    print(f"  P(killed) log loss {ll:.4f} (constant rate {train.logloss(np.full(len(u), killed.mean()), killed.astype(float)):.4f}), "
          f"mean {pk.mean():.4f}")
    for name, flag in (("worst >= health", worst >= hp), ("model sum >= health", model >= hp),
                       ("P(killed) >= 0.05", pk >= 0.05), ("P(killed) >= 0.10", pk >= 0.10), ("P(killed) >= 0.25", pk >= 0.25),
                       ("P(killed) >= 0.5", pk >= 0.5), ("Pblow(killed) >= 0.05", pkb >= 0.05),
                       ("Pblow(killed) >= 0.10", pkb >= 0.10), ("Pblow(killed) >= 0.20", pkb >= 0.20), ("Pblow(killed) >= 0.35", pkb >= 0.35),
                       ("Pblow(killed) >= 0.5", pkb >= 0.5)):
        tp = (flag & killed).sum()
        print(f"  lethal {name:22s} flags {flag.mean():.4f}  recall {tp / max(1, killed.sum()):.3f}  precision {tp / max(1, flag.sum()):.3f}")
    # calibration of P(killed)
    for a, b in ((0, .02), (.02, .05), (.05, .1), (.1, .25), (.25, .5), (.5, 1.01)):
        mk = (pk >= a) & (pk < b)
        if mk.sum() >= 50:
            print(f"    P(killed) in [{a:.2f},{b:.2f}): n {mk.sum()}, observed {killed[mk].mean():.3f}, predicted {pk[mk].mean():.3f}")


if __name__ == "__main__":
    main()
