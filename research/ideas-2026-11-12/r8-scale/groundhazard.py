"""Our Prism's hazard by ground while it carries 100+ gems off its spawn: deaths to champions per carrying round.

    python3 research/ideas-2026-11-12/r8-scale/groundhazard.py EXTRACT_DIR --team NAME [--min 100]

Ground by the bot's own bands (params.h own_ground_share, mid_low_share) on s = d_enemy / (d_ally + d_enemy), Chebyshev
distances from the Prism's tile to the two spawn centres: own s >= 0.683, enemy s < 0.2545, middle between."""
import argparse, gzip, json
from collections import defaultdict
from pathlib import Path

OWN, LOW = 0.6832753, 0.25452974


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--min", type=int, default=100)
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    seen = set()
    rounds = defaultdict(int)
    deaths = defaultdict(int)
    fine = defaultdict(lambda: [0, 0])
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
        mp = json.load(open(root / "maps" / (meta["map"]["hash"] + ".json")))
        cen = [((s["minX"] + s["maxX"]) / 2, (s["minY"] + s["maxY"]) / 2) for s in mp["spawn"]]
        sp = mp["spawn"][us]
        R = json.load(gzip.open(g / "rounds.json.gz"))
        c = next(x for x in R["champions"] if x["id"] == p)
        rr = R["round"]
        died = {}
        for l in gzip.open(g / "events.jsonl.gz", "rt"):
            e = json.loads(l)
            if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= a.min and e.get("by") is not None:
                died[e["r"]] = 1

        def ground(i):
            x, y = c["x"][i], c["y"][i]
            da = max(abs(x - cen[us][0]), abs(y - cen[us][1]))
            de = max(abs(x - cen[1 - us][0]), abs(y - cen[1 - us][1]))
            s = de / max(1e-6, da + de)
            return ("own" if s >= OWN else "enemy" if s < LOW else "middle"), s

        for i, r in enumerate(rr):
            if not c["alive"][i] or c["x"][i] is None or c["gems"][i] < a.min:
                continue
            if sp["minX"] <= c["x"][i] <= sp["maxX"] and sp["minY"] <= c["y"][i] <= sp["maxY"]:
                continue
            gname, s = ground(i)
            rounds[gname] += 1
            b = min(9, int(s * 10))
            fine[b][0] += 1
            if r + 1 in died:
                deaths[gname] += 1
                fine[b][1] += 1
    T = sum(rounds.values())
    Dd = sum(deaths.values())
    print(f"carrying rounds {T}, deaths {Dd}, hazard {Dd / max(1, T):.2e} a round")
    for k in ("own", "middle", "enemy"):
        h = deaths[k] / max(1, rounds[k])
        print(f"  {k:7s} time {100 * rounds[k] / max(1, T):5.1f}%  deaths {deaths[k]:4d}  hazard {h:.2e} a round  x{h / max(1e-12, Dd / max(1, T)):.2f} of the mean")
    print("  by s (tenths):", " ".join(f"{b / 10:.1f}:{fine[b][1]}/{fine[b][0]}={1e4 * fine[b][1] / max(1, fine[b][0]):.1f}e-4" for b in sorted(fine)))


if __name__ == "__main__":
    main()
