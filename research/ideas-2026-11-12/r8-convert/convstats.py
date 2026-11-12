"""Conversion and hoard statistics of our bot in a local batch's extract (our bot is bot 1 of the batch, index 0).

    node tools/replay/extract.mjs replays/batch-...-p0 --out EXT --threads 24
    py research/ideas-2026-11-12/r8-convert/convstats.py EXT [EXT2 ...]

Per extract: the winning bag (our score + one champion's bag >= 1000: first round, size, whether the game was won,
rounds from first holding it to the win), our tribute channels by length and how they ended, the Tribute emblem at
the first winning bag, Prism deaths with 100+ gems, our tributes that are not the Prism's, game length."""
import gzip, json, statistics as st, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

TRIBUTE_EMBLEMS = {7 * 6 + 1, 7 * 6 + 3, 7 * 6 + 5}
BUCKETS = [(1, 10), (11, 20), (21, 40), (41, 70), (71, 999)]


def one(args):
    ext, row = args
    d = Path(ext) / row["dir"]
    us = 0 if row["teams"][0].startswith("rc-") or "fr8" in row["teams"][1] or "rt-" in row["teams"][1] else 1
    meta = json.loads((d / "meta.json").read_text())
    R = json.loads(gzip.open(d / "rounds.json.gz").read())
    ours = [i for i, c in enumerate(meta["champions"]) if c["team"] == us]
    name = {c["id"]: c["name"] for c in meta["champions"]}
    team = {c["id"]: c["team"] for c in meta["champions"]}
    ch = R["champions"]
    n = len(R["round"])
    out = {"win": row["winner"] == us, "rounds": n, "prism": any(meta["champions"][i]["name"] == "Prism" for i in ours),
           "first": None, "chan": [], "pdeaths": 0, "pdeath_gems": 0, "cdeaths": 0, "ally_trib": 0, "prism_trib": 0, "end_bag": 0,
           "score": R["gems"][us][-1], "opp": R["gems"][1 - us][-1]}
    for i in range(n):
        s = R["gems"][us][i]
        if s >= 1000:
            break
        bag, k = max((ch[k]["gems"][i], k) for k in ours)
        if s + bag >= 1000:
            items = ch[k]["items"][i]
            out.update(first=i + 1, bag0=bag, score0=s, who=meta["champions"][k]["name"], opp0=R["gems"][1 - us][i],
                       emblem=any(items[j] in TRIBUTE_EMBLEMS and items[j + 1] > 0 for j in range(0, len(items), 2)),
                       gold0=ch[k]["gold"][i])
            break
    out["end_bag"] = max(ch[k]["gems"][-1] for k in ours)
    open_ = {}
    with gzip.open(d / "events.jsonl.gz", "rt") as f:
        for line in f:
            e = json.loads(line)
            k = e["k"]
            if k == "tribute_start" and team[e["a"]] == us:
                open_[e["a"]] = e
            elif k in ("tribute_end", "tribute_cancel") and e["a"] in open_:
                s = open_.pop(e["a"])
                out["chan"].append((s["dur"], s["gems"], "done" if k == "tribute_end" else str(e.get("cause")), e["r"] - s["r"], name[e["a"]]))
                if k == "tribute_end":
                    out["prism_trib" if name[e["a"]] == "Prism" else "ally_trib"] += e.get("gems", 0)
            elif k == "death" and team[e["v"]] == us:
                if e["v"] in open_:
                    s = open_.pop(e["v"])
                    out["chan"].append((s["dur"], s["gems"], "died", e["r"] - s["r"], name[e["v"]]))
                if e["gems"] >= 100:
                    if "camp" in e and "by" not in e:
                        out["cdeaths"] += 1
                    elif name[e["v"]] == "Prism":
                        out["pdeaths"] += 1
                        out["pdeath_gems"] += e["gems"]
    return out


def report(ext):
    idx = [r for r in json.loads((Path(ext) / "index.json").read_text())["games"] if r["ok"]]
    with ProcessPoolExecutor(24) as ex:
        G = list(ex.map(one, [(ext, r) for r in idx], chunksize=8))
    n = len(G)
    W = [g for g in G if g["win"]]
    print(f"== {ext}: {n} games, won {len(W)} ({100 * len(W) / n:.1f}%); median length {st.median(g['rounds'] for g in G):.0f} "
          f"(wins {st.median(g['rounds'] for g in W):.0f}); round-limit games {sum(g['rounds'] >= 2000 for g in G)}")
    H = [g for g in G if g["first"]]
    HW = [g for g in H if g["win"]]
    print(f"winning bag held in {len(H)} games: converted {len(HW)} ({100 * len(HW) / max(1, len(H)):.1f}%); never held: won {sum(g['win'] for g in G if not g['first'])} of {n - len(H)}")
    for lo, hi in ((0, 100), (100, 300), (300, 500), (500, 700), (700, 99999)):
        b = [g for g in H if lo <= g["bag0"] < hi]
        if b:
            bw = [g for g in b if g["win"]]
            lag = [g["rounds"] - g["first"] for g in bw]
            print(f"  bag {lo:>3}-{hi:<5}: {len(b):4d} games, converted {100 * len(bw) / len(b):5.1f}%, rounds to the win median {st.median(lag) if lag else 0:.0f} "
                  f"mean {st.mean(lag) if lag else 0:.0f}; Tribute emblem then {100 * sum(g['emblem'] for g in b) / len(b):.0f}%; Prism's {100 * sum(g['who'] == 'Prism' for g in b) / len(b):.0f}%")
    big = [g for g in H if g["bag0"] >= 300]
    if big:
        print(f"  bags of 300+: {len(big)} games ({100 * len(big) / n:.1f}% of all), converted {100 * sum(g['win'] for g in big) / len(big):.1f}%, "
              f"mean rounds held-to-end {st.mean(g['rounds'] - g['first'] for g in big):.0f}; carrier's unspent gold then median {st.median(g['gold0'] for g in big):.0f}")
    print("our channels (one-round manual feints left out):")
    print("  turn ends      n   done   manual  stun  lock  died  other")
    for lo, hi in BUCKETS:
        c = [x for g in G for x in g["chan"] if lo <= x[0] <= hi and not (x[2] == "manual" and x[3] <= 1)]
        if not c:
            continue
        k = Counter(x[2] for x in c)
        other = len(c) - sum(k[z] for z in ("done", "manual", "stun", "lock", "died"))
        print(f"  {lo:>3}-{hi:<4} {len(c):6d}  {100 * k['done'] / len(c):5.1f}%  {k['manual']:5d} {k['stun']:5d} {k['lock']:5d} {k['died']:5d} {other:5d}")
    P = [g for g in G if g["prism"]]
    if P:
        print(f"Prism games {len(P)} (won {100 * sum(g['win'] for g in P) / len(P):.1f}%): Prism deaths with 100+ gems {sum(g['pdeaths'] for g in P) / len(P):.3f} a game, "
              f"{sum(g['pdeath_gems'] for g in P) / len(P):.0f} gems a game; games with one {sum(g['pdeaths'] > 0 for g in P)} "
              f"(won {100 * sum(g['win'] for g in P if g['pdeaths'] > 0) / max(1, sum(g['pdeaths'] > 0 for g in P)):.0f}%); "
              f"camp deaths with 100+ {sum(g['cdeaths'] for g in P)}")
        print(f"  gems tributed a Prism game: Prism {st.mean(g['prism_trib'] for g in P):.0f}, allies {st.mean(g['ally_trib'] for g in P):.0f}; "
              f"lost with 300+ unbanked in one bag: {sum((not g['win']) and g['end_bag'] >= 300 for g in P)}")
    L = [g for g in G if not g["win"]]
    print(f"losses {len(L)}: held a winning bag {sum(1 for g in L if g['first'])}, ended with 300+ in one bag {sum(g['end_bag'] >= 300 for g in L)}, "
          f"Prism lost a 100+ bag {sum(g['pdeaths'] > 0 for g in L)}, our score median {st.median(g['score'] for g in L) if L else 0:.0f}")


if __name__ == "__main__":
    for ext in sys.argv[1:]:
        report(ext)
