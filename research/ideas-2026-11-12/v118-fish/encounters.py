"""Hoard encounters: our Prism carrying a bag with an enemy in sight that out-kills it, and what followed.

    py research/ideas-2026-11-12/v118-fish/encounters.py [--bag 100] [--near 9]

From the traced re-runs (trusted rounds): Prism's turns with a bag of --bag or more, off spawn, and a visible enemy
within --near tiles (as our belief has it at the turn's end) that kills Prism before Prism kills it:
  its turns to kill us   = our health / its Strength (one basic attack a turn; resets, spells and emblems left out)
  our turns to kill it   = its health / (0.3125 x our Focus + our Strength), Focus = 90 + 1.5 x bag (two spells an
                           8-round cooldown, 2.5 x Focus together, and a basic attack; shards left out)
An episode is a run of such turns (gaps up to 3 rounds). Counted per game by result, with what followed within 30
rounds of its start: Prism died (and the bag), or not; and whether want_home already said yes on its first turn."""
import argparse, json, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tracelib as T  # noqa: E402

A = T.V / "analysis"


def cheb(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", type=int, default=100)
    ap.add_argument("--near", type=int, default=9)
    a = ap.parse_args()
    games = [json.loads(l) for l in open(A / "games.jsonl")]
    deaths = defaultdict(list)
    for l in open(A / "deaths.jsonl"):
        d = json.loads(l)
        if d["us"]:
            deaths[(d["key"], d["vid"])].append(d)
    eps = []
    ngames = Counter()
    for g in games:
        pr = next((c for c in g["champs"] if c["us"] and c["type"] == "Prism"), None)
        if not pr:
            continue
        ngames[g["result"]] += 1
        types = {c["id"]: c["type"] for c in g["champs"]}
        tr = T.load(g["key"])
        cur = None
        for r in range(1, min(tr.trusted, g["rounds"]) + 1):
            t = tr.turn(r, pr["id"])
            if not t or "TT" not in t or not t["TT"]["alive"]:
                continue
            tt = t["TT"]
            if tt["gems"] < a.bag or tt["hp"] <= 0:
                continue
            focus = 90 + 1.5 * tt["gems"]
            ours = 0.3125 * focus + 35
            best = None
            for e in t.get("EB", []):
                if not e["visible"] or e["str"] <= 0:
                    continue
                d = cheb((tt["ex"], tt["ey"]), (e["x"], e["y"]))
                if d > a.near:
                    continue
                t_us, t_them = tt["hp"] / e["str"], e["hp"] / ours
                if t_us < t_them and (best is None or t_us < best[0]):
                    best = (t_us, t_them, e["e"], d, e["str"], e["maxhp"])
            if not best:
                continue
            home = any(w["code"] > 0 for w in t.get("WH", []))
            if cur and r - cur["last"] <= 3:
                cur["last"] = r
                cur["turns"] += 1
                cur["home_turns"] += home
                cur["dmin"] = min(cur["dmin"], best[3])
            else:
                cur = {"key": g["key"], "result": g["result"], "r0": r, "last": r, "turns": 1, "bag": tt["gems"], "t_us": best[0], "t_them": best[1], "enemy": types[best[2]],
                       "d0": best[3], "dmin": best[3], "home0": home, "home_turns": int(home), "str": best[4], "ehp": best[5], "maxhp": tt["maxhp"], "branch0": tt["branch"]}
                eps.append(cur)
        for e in [x for x in eps if x["key"] == g["key"]]:
            dd = [d for d in deaths[(g["key"], pr["id"])] if e["r0"] <= d["r"] <= e["last"] + 30]
            e["died"] = bool(dd)
            e["lost"] = dd[0]["bag"] if dd else 0
            e["killer_same"] = bool(dd) and dd[0]["by"] == e["enemy"]
    print(f"games with our Prism: {dict(ngames)}; episodes: {len(eps)} (bag >= {a.bag}, an out-killing enemy seen within {a.near})")
    for res in ("win", "loss"):
        S = [e for e in eps if e["result"] == res]
        n = ngames[res]
        if not S:
            continue
        d = [e for e in S if e["died"]]
        print(f"  our {res}s: {len(S)} episodes ({len(S) / n:.2f} a game, {sum(e['turns'] for e in S) / n:.1f} turns a game); Prism died within 30 rounds in {len(d)} ({100 * len(d) / len(S):.0f}%), "
              f"{sum(e['lost'] for e in d)} gems; want_home on the first turn {100 * sum(e['home0'] for e in S) / len(S):.0f}%; enemy {dict(Counter(e['enemy'] for e in S).most_common(4))}")
    print("  death rate by the enemy's turns to kill us at the first turn (all games):")
    for lo, hi in ((0, 2), (2, 4), (4, 7), (7, 12), (12, 999)):
        S = [e for e in eps if lo <= e["t_us"] < hi]
        if S:
            print(f"    {lo:3d}-{hi:<3d} turns: {len(S):4d} episodes, died {sum(e['died'] for e in S):3d} ({100 * sum(e['died'] for e in S) / len(S):3.0f}%), gems lost {sum(e['lost'] for e in S)}")
    print("  death rate by first distance (all games):")
    for lo, hi in ((0, 3), (4, 5), (6, 7), (8, 9)):
        S = [e for e in eps if lo <= e["d0"] <= hi]
        if S:
            print(f"    d {lo}-{hi}: {len(S):4d} episodes, died {sum(e['died'] for e in S):3d} ({100 * sum(e['died'] for e in S) / len(S):3.0f}%); want_home on the first turn {100 * sum(e['home0'] for e in S) / len(S):.0f}%")
    S = [e for e in eps if e["enemy"] == "Vesper Vale"]
    print(f"  against Vesper: {len(S)} episodes, died {sum(e['died'] for e in S)} ({100 * sum(e['died'] for e in S) / max(1, len(S)):.0f}%), gems {sum(e['lost'] for e in S)}; "
          f"episode length median {st.median(e['turns'] for e in S) if S else 0} turns")
    json.dump(eps, open(A / "encounters.json", "w"))


if __name__ == "__main__":
    main()
