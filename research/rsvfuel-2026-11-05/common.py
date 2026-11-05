import pickle, collections
import numpy as np


def first(r):
    f = {}
    for k, v in r["marks"]:
        f.setdefault(k, v)
    return f


def derive(r):
    ms = r["marks"]
    f = first(r)
    r["L"] = f.get("L")
    post_oof = any(ms[i][1] > ms[i - 1][1] for i in range(1, len(ms)))
    r["post_oof"] = post_oof
    if post_oof:
        for i in range(1, len(ms)):
            if ms[i][1] > ms[i - 1][1]:
                r["oof_at"] = ms[i - 1][0] + ms[i][0]
                break
    T = f.get("T")
    r["T"] = T
    r["X"] = r["L"] - T if T is not None and not post_oof else None
    r["order"] = T - f["U"] if T is not None and "U" in f and not post_oof else None
    Q = f.get("Q")
    r["XQ"] = r["L"] - Q if Q is not None and not post_oof else None
    r["reserve"] = r["floor"] + r["lr"]
    r.setdefault("cuts", [])
    r.setdefault("chunks", 0)


def load(path, want="rsv"):
    recs = [r for r in pickle.load(open(path, "rb")) if want in r["bot"]]
    for r in recs:
        derive(r)
    return recs


def q(xs, ps=(50, 90, 95, 99, 99.9)):
    xs = np.array([x for x in xs if x is not None])
    if len(xs) == 0:
        return "n=0"
    return f"n={len(xs):7d} mean {xs.mean()/1000:5.1f}k " + " ".join(f"p{p}={np.percentile(xs, p)/1000:5.1f}k" for p in ps) + f" max={xs.max()/1000:5.1f}k"
