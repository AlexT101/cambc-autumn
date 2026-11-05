"""Compare two instrumented runs: python cmp.py BASE.pkl CAND.pkl"""
import sys
import numpy as np
D = __file__.rsplit("/", 1)[0]
exec(open(D + "/common.py").read())
for path in sys.argv[1:]:
    recs = load(path)
    for name, sel in (("all", lambda r: True), ("non-banking", lambda r: not r["banks"]), ("banking", lambda r: r["banks"]),
                      ("opening", lambda r: r["opening"])):
        rs = [r for r in recs if sel(r)]
        cut = [r for r in rs if r["cut"]]
        oof = sum(r["post_oof"] for r in rs)
        order = sum(1 for r in rs if not r["post_oof"] and r["T"] is not None and r["T"] < 10000)
        share = np.mean([r["k"] / max(r["n"], 1) for r in cut]) if cut else 0
        L = np.mean([r["L"] for r in cut]) / 1e3 if cut else 0
        cutorder = sum(1 for r in cut if "turn-order" in r["cuts"])
        walk = sum(1 for r in rs for c in r["cuts"] if c in ("farm-no-route", "crow-flies-farm", "static-descend", "farm-kept-target"))
        print(f"{path.split('/')[-1]:8s} {name:12s} turns {len(rs):8d} cut {len(cut):7d} ({100*len(cut)/max(1,len(rs)):.2f}%) "
              f"weighed-at-cut {share:.3f} L@cut {L:5.1f}k postOOF {oof:5d} T<10k {order:6d} turn-order-cut {cutorder:5d} walk-cuts {walk:5d}")
