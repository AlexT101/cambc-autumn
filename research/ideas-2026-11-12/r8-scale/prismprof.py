"""Our Prism's build, gold and deaths from an extract directory (tools/replay/extract.mjs --out DIR).

    python3 research/ideas-2026-11-12/r8-scale/prismprof.py EXTRACT_DIR --team NAME [--rounds 200,400,600,800]

Per Prism game of team NAME: max health, unspent and earned gold, emblems owned by round; shop events; deaths with a
100+ bag by killer; the enemy's strongest champion (Strength, max health); gold share by champion; long channels."""
import argparse, gzip, json, statistics as st, sys
from collections import Counter, defaultdict
from pathlib import Path


def med(v):
    return round(st.median(v)) if v else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--rounds", default="200,400,600,800")
    a = ap.parse_args()
    root = Path(a.dir)
    enums = json.load(open(root / "enums.json"))
    items = enums["items"]
    rounds = [int(x) for x in a.rounds.split(",")]
    index = json.load(open(root / "index.json"))["games"]
    seen = set()
    n = wins = pg = pw = 0
    hp, unspent, earned, emb, topstr, tophp, share = (defaultdict(list) for _ in range(7))
    embl = defaultdict(Counter)
    shops, shop_rounds, deaths_big, killers, lost = [], [], 0, Counter(), 0
    death_gold, death_hp, death_kstr, death_hits = [], [], [], []
    first_emblems = Counter()
    chan = defaultdict(lambda: [0, 0])
    winbag = [0, 0]
    for row in index:
        if row["dir"] in seen or not row.get("ok", True):
            continue
        seen.add(row["dir"])
        names = [t["name"] if isinstance(t, dict) else t for t in row["teams"]]
        if a.team not in names:
            continue
        us = names.index(a.team)
        g = root / row["dir"]
        meta = json.load(open(g / "meta.json"))
        n += 1
        won = meta["result"]["winner"] == us
        wins += won
        champs = meta["champions"]
        prism = [c["id"] for c in champs if c["team"] == us and c["name"] == "Prism"]
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        ours = [c["id"] for c in champs if c["team"] == us]
        theirs = [c["id"] for c in champs if c["team"] != us]
        for r in rounds:
            if r > rr[-1]:
                continue
            i = rr.index(r)
            tot = sum(rc[c]["earned"][i] for c in ours)
            for c in champs:
                if c["team"] == us and tot > 0:
                    share[(r, c["name"])].append(rc[c["id"]]["earned"][i] / tot)
        ev = [json.loads(l) for l in gzip.open(g / "events.jsonl.gz", "rt")]
        # channels of ours by length
        open_ch = {}
        for e in ev:
            if e["k"] == "tribute_start" and e["a"] in ours:
                open_ch[e["a"]] = e["dur"]
                b = "1-10" if e["dur"] <= 10 else "11-20" if e["dur"] <= 20 else "21-40" if e["dur"] <= 40 else "41-70" if e["dur"] <= 70 else "71+"
                chan[b][0] += 1
                open_ch[e["a"]] = b
            elif e["k"] == "tribute_end" and e["a"] in ours and e["a"] in open_ch:
                chan[open_ch.pop(e["a"])][1] += 1
        # a winning bag at some round end
        wb = False
        for i in range(len(rr)):
            s = R["gems"][us][i]
            if any(rc[c]["gems"][i] + s >= 1000 for c in ours):
                wb = True
                break
        if wb:
            winbag[0] += 1
            winbag[1] += won
        if not prism:
            continue
        p = prism[0]
        pg += 1
        pw += won
        c = rc[p]
        for r in rounds:
            if r > rr[-1]:
                continue
            i = rr.index(r)
            hp[r].append(c["maxHp"][i])
            unspent[r].append(c["gold"][i])
            earned[r].append(c["earned"][i])
            it = c["items"][i]
            own = Counter()
            for k in range(0, len(it), 2):
                nm = items[it[k]]
                if "Emblem" in nm:
                    own[nm.replace(" Emblem of ", "-")[: nm.index(" ") + 2]] += it[k + 1]
            emb[r].append(sum(own.values()))
            for k, v in own.items():
                embl[r][k] += v
            es = [(rc[e]["str"][i], rc[e]["maxHp"][i]) for e in theirs if rc[e]["alive"][i]]
            if es:
                s, h = max(es)
                topstr[r].append(s)
                tophp[r].append(h)
        ns = 0
        got_first = False
        for e in ev:
            if e["k"] == "shop" and e["a"] == p:
                ns += 1
                shop_rounds.append(e["r"])
                for nm, dv in e.get("items", {}).items():
                    if "Emblem" in nm and dv > 0 and not got_first:
                        first_emblems[nm] += 1
                        got_first = True
            if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= 100:
                deaths_big += 1
                lost += e["gems"]
                i = min(len(rr) - 1, max(0, e["r"] - 2))
                death_gold.append(c["gold"][i])
                death_hp.append(c["maxHp"][i])
                if "by" in e and e["by"] is not None and e["by"] in rc:
                    k = next(x for x in champs if x["id"] == e["by"])
                    killers[k["name"]] += 1
                    ks = rc[e["by"]]["str"][i]
                    death_kstr.append(ks)
                    if ks > 0:
                        death_hits.append(c["maxHp"][i] / ks)
                else:
                    killers["camp"] += 1
        shops.append(ns)
    print(f"{n} games, {wins} won ({100 * wins / max(1, n):.1f}%); Prism games {pg}, won {100 * pw / max(1, pg):.1f}%")
    print(f"winning bag held in {winbag[0]} games, won {winbag[1]} ({100 * winbag[1] / max(1, winbag[0]):.1f}%)")
    for r in rounds:
        top = ", ".join(f"{k} {v / max(1, len(emb[r])):.2f}" for k, v in embl[r].most_common(9))
        print(f"r{r}: n {len(hp[r])} maxHp {med(hp[r])} unspent {med(unspent[r])} earned {med(earned[r])} emblems {st.mean(emb[r]) if emb[r] else 0:.1f} | enemy top Str {med(topstr[r])} its maxHp {med(tophp[r])} | {top}")
    print(f"shop events per Prism game {st.mean(shops):.2f}; median round of a shop {med(shop_rounds)}")
    print("first emblem:", first_emblems.most_common(6))
    print(f"100+ bag deaths per Prism game {deaths_big / max(1, pg):.3f} ({deaths_big}), gems lost per Prism game {lost / max(1, pg):.1f}; killers {killers.most_common(6)}")
    print(f"  at those deaths: unspent gold {med(death_gold)}, max health {med(death_hp)}, killer Strength {med(death_kstr)}, hits {st.median(death_hits) if death_hits else None}")
    for r in rounds[:2]:
        sh = sorted(((st.mean(v), k[1], len(v)) for k, v in share.items() if k[0] == r), reverse=True)
        print(f"gold share r{r}: " + ", ".join(f"{nm} {100 * m:.0f}% (n {k})" for m, nm, k in sh))
    print("channels (started, completed):", {k: (v[0], v[1], f"{100 * v[1] / max(1, v[0]):.0f}%") for k, v in sorted(chan.items())})


if __name__ == "__main__":
    main()
