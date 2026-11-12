"""What our Prism did with each turn of a fatal run (100+ bag, killed by a champion): by turn, relative to the killer's
tile at the end of the round before.

    python3 research/ideas-2026-11-12/r8-scale/runmoves.py EXTRACT_DIR --team NAME [--killer "Vesper Vale"]"""
import argparse, gzip, json
from collections import Counter
from pathlib import Path


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--killer")
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    seen = set()
    kinds = Counter()
    runs = 0
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
        ds = [e for e in ev if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= 100 and e.get("by") is not None
              and (not a.killer or champs[e["by"]]["name"] == a.killer)]
        if not ds:
            continue
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        mp = json.load(open(root / "maps" / (meta["map"]["hash"] + ".json")))
        s = mp["spawn"][us]
        home = ((s["minX"] + s["maxX"]) // 2, (s["minY"] + s["maxY"]) // 2)
        for d in ds:
            k, r = d["by"], d["r"]
            first = r
            for e in ev:
                if r - 12 <= e["r"] <= r and e["k"] in ("attack", "cast") and e["a"] == k and any(t == p for t, _ in e.get("dmg", [])):
                    first = min(first, e["r"])
            runs += 1
            c, kc = rc[p], rc[k]
            for q in range(first, r):
                if q not in rr or q - 1 not in rr:
                    continue
                i, j = rr.index(q - 1), rr.index(q)
                if c["x"][i] is None or c["x"][j] is None or kc["x"][i] is None:
                    continue
                P0, P1, K0 = (c["x"][i], c["y"][i]), (c["x"][j], c["y"][j]), (kc["x"][i], kc["y"][i])
                mine = [e for e in ev if e["r"] == q and e.get("a") == p]
                cast = [e for e in mine if e["k"] == "cast"]
                if c["turn"][j] == 5:
                    kinds["stunned"] += 1
                elif c["turn"][j] == 3:
                    kinds["channelling"] += 1
                elif c["turn"][j] == 6:
                    kinds["out of fuel"] += 1
                elif P1 == P0:
                    if cast:
                        tg = cast[0].get("tgt")
                        stun = any(e.get("stun") for e in cast)
                        kinds["stood: cast " + ("stun" if stun else "no stun") + (" at the killer" if tg == k or any(t == k for e in cast for t, _ in e.get("dmg", [])) else " at another")] += 1
                    elif any(e["k"] == "attack" for e in mine):
                        kinds["stood: basic attack"] += 1
                    else:
                        kinds["stood: nothing"] += 1
                else:
                    dd = cheb(P1, K0) - cheb(P0, K0)
                    dh = cheb(P1, home) - cheb(P0, home)
                    kinds[f"moved: {'away from' if dd > 0 else 'level with' if dd == 0 else 'toward'} the killer, {'nearer home' if dh < 0 else 'not nearer home'}"] += 1
    n = sum(kinds.values())
    print(f"{runs} fatal runs, {n} Prism turns in them (first hit to the round before the death)")
    for k, v in kinds.most_common():
        print(f"  {100 * v / max(1, n):5.1f}%  {v:4d}  {k}")


if __name__ == "__main__":
    main()
