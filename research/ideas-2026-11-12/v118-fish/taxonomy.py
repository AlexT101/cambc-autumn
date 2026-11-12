"""Loss taxonomy for v118's 345 Fish r8 games: one mechanism per game, from the replay's gem flow and deaths.

    py research/ideas-2026-11-12/v118-fish/taxonomy.py [--tsv OUT] [--list] [--bag 100] [--carried 300] [--deaths 10]

Reads replays/v118/analysis/{games,deaths}.jsonl (features.py). The same conditions are evaluated on our side of
every game, wins included, so each class's count in the losses stands against its count in the wins.

Classes, first match, all about OUR side of the game:
  hoard-killed  we lost a bag of --bag (100) or more gems to an enemy champion. Tag `ahead` when our wealth
                (tributed + carried) was at least Fish's in the round before the first hit of the largest such
                death, else `behind`.
  hoard-camp    a bag of --bag or more lost to a camp.
  unbanked      no such loss, and we ended with --carried (300) or more gems still carried.
  overrun       none of the above, and we died --deaths (10) or more times or captured under 300 gems in the game.
  outfarmed     the rest: few deaths, no big bag lost, nothing left in the bags.
Other columns: the gem-flow split of the final wealth deficit (farm = Fish's capture gems - ours; fight = 2 x (our
bags lost to champions - theirs); camp = bags lost to camps, ours - theirs), which adds up exactly.
"""
import argparse, json, math, statistics as st
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
A = REPO / "replays/v118/analysis"
ORDER = ["hoard-killed", "hoard-camp", "unbanked", "overrun", "outfarmed"]


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


def pct(k, n):
    lo, hi = wilson(k, n)
    return f"{k}/{n} {100 * k / max(1, n):.0f}% [{100 * lo:.0f}-{100 * hi:.0f}]"


def load():
    G = [json.loads(l) for l in open(A / "games.jsonl")]
    D = defaultdict(list)
    for l in open(A / "deaths.jsonl"):
        d = json.loads(l)
        D[d["key"]].append(d)
    return G, D


def classify(g, deaths, bag=100, carried=300, ndeaths=10):
    e = g["cp"]["end"]
    u, o = e["us"], e["op"]
    mine = [d for d in deaths if d["us"]]
    big = [d for d in mine if d["bag"] >= bag and d["kind"] == "death"]
    bigc = [d for d in mine if d["bag"] >= bag and d["kind"] == "camp_death"]
    top = max(big, key=lambda d: d["bag"]) if big else None
    tags = []
    if top:
        cls = "hoard-killed"
        tags.append("ahead" if top["lead_before"] >= 0 else "behind")
    elif bigc:
        cls = "hoard-camp"
        top = max(bigc, key=lambda d: d["bag"])
    elif u["carried"] >= carried:
        cls = "unbanked"
    elif u["deaths"] >= ndeaths or u["cap"] < 300:
        cls = "overrun"
    else:
        cls = "outfarmed"
    num = {"farm": o["cap"] - u["cap"], "fight": 2 * (u["lostc"] - o["lostc"]), "camp": u["lostm"] - o["lostm"],
           "cap_us": u["cap"], "cap_op": o["cap"], "lostc_us": u["lostc"], "lostc_op": o["lostc"], "lostm_us": u["lostm"], "carried_us": u["carried"],
           "deaths_us": u["deaths"], "deaths_op": o["deaths"], "top_bag": top["bag"] if top else 0, "top_r": top["r"] if top else 0,
           "top_victim": top["victim"] if top else "", "top_by": (top["by"] or "camp") if top else "", "lead_before": top["lead_before"] if top else 0}
    return cls, tags, num, top


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tsv")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--bag", type=int, default=100)
    ap.add_argument("--carried", type=int, default=300)
    ap.add_argument("--deaths", type=int, default=10)
    a = ap.parse_args()
    G, D = load()
    rows = [(g, *classify(g, D[g["key"]], a.bag, a.carried, a.deaths)) for g in G]
    n = len(rows)
    L = [r for r in rows if r[0]["result"] == "loss"]
    W = [r for r in rows if r[0]["result"] == "win"]
    print(f"{n} games: {len(W)} wins, {len(L)} losses ({100 * len(W) / n:.1f}%)")
    print("\nclass         in losses               in wins                 our win rate when it holds")
    for c in ORDER:
        kl, kw = sum(1 for r in L if r[1] == c), sum(1 for r in W if r[1] == c)
        print(f"{c:13s} {pct(kl, len(L)):23s} {pct(kw, len(W)):23s} {pct(kw, kl + kw)}")
    hk = [r for r in L if r[1] == "hoard-killed"]
    print(f"\nhoard-killed losses: ahead before the death {sum('ahead' in r[2] for r in hk)}, behind {sum('behind' in r[2] for r in hk)}; "
          f"victim {dict(Counter(r[3]['top_victim'] for r in hk).most_common())}; killer {dict(Counter(r[3]['top_by'] for r in hk).most_common())}; "
          f"bag median {st.median(r[3]['top_bag'] for r in hk)}, round median {st.median(r[3]['top_r'] for r in hk)}")
    hkw = [r for r in W if r[1] == "hoard-killed"]
    if hkw:
        print(f"hoard-killed wins: {len(hkw)}; victim {dict(Counter(r[3]['top_victim'] for r in hkw).most_common())}; bag median {st.median(r[3]['top_bag'] for r in hkw)}")
    print("\nmean gem-flow split of the final deficit (Fish - us), by class, losses: farm / fight / camp; our deaths v theirs; rounds")
    for c in ORDER:
        sel = [r for r in L if r[1] == c]
        if sel:
            print(f"  {c:13s} n={len(sel):3d} farm {st.mean(r[3]['farm'] for r in sel):5.0f} fight {st.mean(r[3]['fight'] for r in sel):5.0f} camp {st.mean(r[3]['camp'] for r in sel):4.0f} | "
                  f"deaths {st.mean(r[3]['deaths_us'] for r in sel):4.1f} v {st.mean(r[3]['deaths_op'] for r in sel):4.1f} | cap {st.mean(r[3]['cap_us'] for r in sel):4.0f} v {st.mean(r[3]['cap_op'] for r in sel):4.0f} | "
                  f"carried at end {st.mean(r[3]['carried_us'] for r in sel):4.0f} | rounds median {st.median(r[0]['rounds'] for r in sel):.0f}")
    print("  wins (all)    " + f"farm {st.mean(r[3]['farm'] for r in W):5.0f} fight {st.mean(r[3]['fight'] for r in W):5.0f} camp {st.mean(r[3]['camp'] for r in W):4.0f} | "
          f"deaths {st.mean(r[3]['deaths_us'] for r in W):4.1f} v {st.mean(r[3]['deaths_op'] for r in W):4.1f}")
    lim = [r for r in rows if r[0]["end_reason"] != "gems"]
    print(f"\nround-limit games: {len(lim)}: " + "; ".join(f"{r[0]['key']} {r[0]['map']} {r[0]['result']} {r[0]['our_gems']:.0f}-{r[0]['opp_gems']:.0f} [{r[1]}] carried {r[3]['carried_us']:.0f}" for r in lim))

    def by(label, keyf, minn=8):
        print(f"\nby {label}: games, win rate [95% Wilson], loss classes")
        groups = defaultdict(list)
        for r in rows:
            groups[keyf(r[0])].append(r)
        for k, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            if len(rs) < minn:
                continue
            w = sum(1 for r in rs if r[0]["result"] == "win")
            cc = Counter(r[1] for r in rs if r[0]["result"] == "loss")
            print(f"  {str(k)[:58]:58s} {pct(w, len(rs)):22s} " + " ".join(f"{c}:{cc[c]}" for c in ORDER if cc[c]))

    by("set", lambda g: f"{g['set']} {g['part']}")
    by("side", lambda g: g["side"])
    by("picks", lambda g: g["npicks"])
    by("our Prism", lambda g: "Prism" in g["our_draft"])
    by("our Prism and Willow", lambda g: ("Prism" in g["our_draft"], "Willow" in g["our_draft"]))
    by("our Vesper", lambda g: "Vesper Vale" in g["our_draft"])
    by("Fish's Vesper", lambda g: "Vesper Vale" in g["opp_draft"])
    by("Fish's draft", lambda g: "/".join(x.split()[0][:5] for x in g["opp_draft"]))
    by("our draft", lambda g: "/".join(x.split()[0][:5] for x in g["our_draft"]))
    by("altars", lambda g: "1 altar" if g["altars"] == 1 else "2-4" if g["altars"] <= 4 else "5+")
    by("map size", lambda g: "<=40" if max(g["W"], g["H"]) <= 40 else "41-60" if max(g["W"], g["H"]) <= 60 else "61+")
    by("rounds", lambda g: "<=600" if g["rounds"] <= 600 else "601-800" if g["rounds"] <= 800 else "801-1000" if g["rounds"] <= 1000 else "1001+")
    if a.tsv:
        cols = ["key", "map", "side", "result", "rounds", "npicks", "class", "tags", "our_gems", "opp_gems", "farm", "fight", "camp", "cap_us", "cap_op", "lostc_us",
                "lostc_op", "lostm_us", "carried_us", "deaths_us", "deaths_op", "top_bag", "top_r", "top_victim", "top_by", "lead_before", "our_draft", "opp_draft"]
        with open(a.tsv, "w") as f:
            f.write("\t".join(cols) + "\n")
            for g, c, t, num, top in sorted(rows, key=lambda r: (r[0]["result"], ORDER.index(r[1]), r[0]["map"])):
                d = {**num, "key": g["key"], "map": g["map"], "side": g["side"], "result": g["result"], "rounds": g["rounds"], "npicks": g["npicks"], "class": c,
                     "tags": ",".join(t), "our_gems": g["our_gems"], "opp_gems": g["opp_gems"], "our_draft": "/".join(g["our_draft"]), "opp_draft": "/".join(g["opp_draft"])}
                f.write("\t".join(f"{d[k]:.0f}" if isinstance(d[k], float) else str(d[k]) for k in cols) + "\n")
        print("\nwrote", a.tsv)
    if a.list:
        for g, c, t, num, top in sorted(L, key=lambda r: (ORDER.index(r[1]), r[0]["map"])):
            print(f"{c:12s} {g['key']} {g['map'][:18]:18s} {g['side']} r{g['rounds']:4d} {g['our_gems']:4.0f}-{g['opp_gems']:4.0f} farm {num['farm']:5.0f} fight {num['fight']:5.0f} "
                  f"deaths {num['deaths_us']:.0f}v{num['deaths_op']:.0f} carried {num['carried_us']:4.0f} top {num['top_victim'][:5]}<{num['top_by'][:5]} {num['top_bag']}@{num['top_r']} lead {num['lead_before']} {','.join(t)}")
    return rows


if __name__ == "__main__":
    main()
