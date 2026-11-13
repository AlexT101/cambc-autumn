"""Split ab.py results by map features and game length.

    python3 split.py NAME [NAME...] [--sides SIDES.json] [--altars ALTARS.json] [--json OUT]

NAME is an ab.py --name (replays/ab/NAME/summary.json). CAND's win % per bucket, with a 95% CI from map-pair
means (a map's two games are correlated). Game length is post-treatment: suggestive only.
"""
import argparse, json, math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def bucket_altars(n):
    return "1" if n == 1 else "2" if n == 2 else "3-4" if n <= 4 else "5+"


def bucket_rounds(r):
    return "<600" if r < 600 else "600-899" if r < 900 else "900-1499" if r < 1500 else "1500+"


def stat(pairs):
    n = len(pairs)
    if not n: return None
    m = sum(pairs) / n
    v = sum((x - m) ** 2 for x in pairs) / max(1, n - 1)
    return 100 * m, 196 * math.sqrt(v / n), n


def load(name):
    s = json.load(open(ROOT / f"replays/ab/{name}/summary.json"))
    out = []
    for su in s["suites"]:
        r = json.load(open(ROOT / su["batch"] / "results.json"))
        out += [m for m in r["matches"] if "winner" in m]
    return s, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("names", nargs="+")
    ap.add_argument("--sides", default=str(ROOT / "replays/overseer/nyx-sides.json"))
    ap.add_argument("--altars", default=str(ROOT / "replays/overseer/nyxsuite-altars.json"))
    ap.add_argument("--json")
    a = ap.parse_args()
    sides = json.load(open(a.sides)) if Path(a.sides).exists() else {}
    feats = json.load(open(a.altars)) if Path(a.altars).exists() else {}
    report = {}
    for name in a.names:
        s, ms = load(name)
        bymap = defaultdict(list)
        for m in ms:
            bymap[Path(m["map"]).stem].append(m)
        splits = defaultdict(lambda: defaultdict(list))  # split -> bucket -> pair means
        games = defaultdict(lambda: defaultdict(list))   # rounds split is per game
        for mp, g in bymap.items():
            pm = sum(m["winner"] == 0 for m in g) / len(g)
            sd = sides.get(mp, {})
            ft = feats.get(mp, {})
            n = sd.get("altars", ft.get("altars"))
            splits["all"]["all"].append(pm)
            if n is not None: splits["altars"][bucket_altars(n)].append(pm)
            if "eopt" in sd:
                e = sd["eopt"]
                splits["enemy_options"]["0" if e == 0 else "1" if e == 1 else "2" if e == 2 else "3+"].append(pm)
                c = sd["contested"]
                splits["contested"]["0" if c == 0 else "1" if c == 1 else "2+"].append(pm)
                if n is not None and n <= 3: splits["contested<=3alt"]["0" if c == 0 else "1+"].append(pm)
            if "picks" in ft: splits["picks"][str(ft["picks"])].append(pm)
            if "altar_zone" in ft: splits["altar_zone"][str(ft["altar_zone"])].append(pm)
            for m in g:
                games["rounds"][bucket_rounds(m["rounds"])].append(int(m["winner"] == 0))
        rep = {"games": s["games"], "win": s["cand_win_pct"], "ci95": s["ci95"], "oof": s.get("oof"), "splits": {}}
        for k, b in list(splits.items()) + list(games.items()):
            rep["splits"][k] = {bk: stat(v) for bk, v in sorted(b.items())}
        report[name] = rep
        print(f"== {name}: {s['cand_win_pct']}% {s['ci95']} of {s['games']}; oof cand {s['oof']['cand']} ref {s['oof']['ref']}")
        for k, b in rep["splits"].items():
            if k == "all": continue
            print(f"  {k:16s} " + "  ".join(f"{bk}: {v[0]:.1f}±{v[1]:.1f} ({v[2]})" for bk, v in b.items() if v))
    if a.json: json.dump(report, open(a.json, "w"), indent=1)


main()
