"""Was the killer on the home side when our Prism's fatal run began? (100+ bag deaths to a champion.)

    python3 research/ideas-2026-11-12/r8-scale/homeside.py EXTRACT_DIR --team NAME

At the round before the killer's first hit of the fatal run (hits within 12 rounds of the death): the Prism's and the
killer's Chebyshev distance to our spawn's centre, and their distance apart. home-side: the killer is nearer our
spawn than the Prism is. Then, over the run: rounds the Prism ended within the killer's basic reach (3 for ranged),
and how far the Prism got nearer home."""
import argparse, gzip, json, statistics as st
from collections import Counter
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--min", type=int, default=100)
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    seen = set()
    rows = []
    for row in index:
        if row["dir"] in seen:
            continue
        seen.add(row["dir"])
        names = [t["name"] if isinstance(t, dict) else t for t in row["teams"]]
        if a.team not in names:
            continue
        us = names.index(a.team)
        g = root / row["dir"]
        meta = json.load(open(g / "meta.json"))
        champs = {c["id"]: c for c in meta["champions"]}
        prism = [c for c in champs.values() if c["team"] == us and c["name"] == "Prism"]
        if not prism:
            continue
        p = prism[0]["id"]
        ev = [json.loads(l) for l in gzip.open(g / "events.jsonl.gz", "rt")]
        ds = [e for e in ev if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= a.min and e.get("by") is not None]
        if not ds:
            continue
        mp = json.load(open(root / "maps" / (meta["map"]["hash"] + ".json")))
        s = mp["spawn"][us]
        home = ((s["minX"] + s["maxX"]) / 2, (s["minY"] + s["maxY"]) / 2)
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        for d in ds:
            k, r = d["by"], d["r"]
            first = r
            for e in ev:
                if r - 12 <= e["r"] <= r and e["k"] in ("attack", "cast") and e["a"] == k and any(t == p for t, _ in e.get("dmg", [])):
                    first = min(first, e["r"])
            if first - 1 not in rr:
                continue
            i = rr.index(first - 1)
            c, kc = rc[p], rc[k]
            if c["x"][i] is None or kc["x"][i] is None:
                continue
            P, K = (c["x"][i], c["y"][i]), (kc["x"][i], kc["y"][i])
            inreach = 0
            moves = 0
            for q in range(first, r):
                j = rr.index(q)
                if c["x"][j] is None or kc["x"][j] is None:
                    continue
                inreach += cheb((c["x"][j], c["y"][j]), (kc["x"][j], kc["y"][j])) <= 3
            j = rr.index(r - 1) if r - 1 in rr else i
            end = (c["x"][j], c["y"][j]) if c["x"][j] is not None else P
            casts = sum(1 for e in ev if first <= e["r"] <= r and e["k"] == "cast" and e["a"] == p)
            stunned = sum(1 for q in range(first, r) if c["turn"][rr.index(q)] == 5)
            rows.append(dict(ph=cheb(P, home), kh=cheb(K, home), d=cheb(P, K), run=r - first + 1, inreach=inreach, nearer=cheb(P, home) - cheb(end, home),
                             killer=champs[k]["name"], casts=casts, stunned=stunned, moved=cheb(P, end)))
    n = len(rows)
    hs = [x for x in rows if x["kh"] < x["ph"]]
    print(f"{n} deaths; killer on the home side (nearer our spawn than the Prism) at the run's start: {len(hs)} ({100 * len(hs) / max(1, n):.0f}%)")
    for name, sel in (("home-side", hs), ("far-side", [x for x in rows if x["kh"] >= x["ph"]])):
        if not sel:
            continue
        print(f"  {name}: n {len(sel)}, Prism from home {st.median(x['ph'] for x in sel):.0f}, apart {st.median(x['d'] for x in sel):.0f}, run {st.median(x['run'] for x in sel):.0f} rounds, "
              f"rounds ended within 3 of the killer {st.mean(x['inreach'] for x in sel):.1f}, got nearer home by {st.median(x['nearer'] for x in sel):.0f}, net tiles moved {st.median(x['moved'] for x in sel):.0f}, "
              f"own casts in the run {st.mean(x['casts'] for x in sel):.1f}, stunned turns {st.mean(x['stunned'] for x in sel):.1f}")
    v = [x for x in rows if x["killer"] == "Vesper Vale"]
    hv = [x for x in v if x["kh"] < x["ph"]]
    print(f"Vesper kills: {len(v)}, home-side {len(hv)}")
    print("net tiles moved over the run (all):", sorted(Counter(min(8, x["moved"]) for x in rows).items()))
    print("run length:", sorted(Counter(min(12, x["run"]) for x in rows).items()))


if __name__ == "__main__":
    main()
