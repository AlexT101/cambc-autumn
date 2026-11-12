"""Our Prism's deaths with a 100+ bag in an extract: when, to whom, from what health, with whom near.

    python3 research/ideas-2026-11-12/r8-scale/hoarddeaths.py EXTRACT_DIR --team NAME [--min 100]"""
import argparse, gzip, json, statistics as st
from collections import Counter, defaultdict
from pathlib import Path


def q(v):
    v = sorted(v)
    return "-" if not v else f"{v[len(v) // 4]:.0f}/{v[len(v) // 2]:.0f}/{v[3 * len(v) // 4]:.0f}"


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
        deaths = [e for e in ev if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= a.min and e.get("by") is not None]
        if not deaths:
            continue
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        won = meta["result"]["winner"] == us
        for d in deaths:
            r = d["r"]
            i = max(0, min(len(rr) - 1, r - 2))  # state at the end of the round before
            dmg = defaultdict(float)
            first = r
            for e in ev:
                if e["r"] < r - 12 or e["r"] > r or e["k"] not in ("attack", "cast"):
                    continue
                for tid, amt in e.get("dmg", []):
                    if tid == p and e["a"] in champs and champs[e["a"]]["team"] != us:
                        dmg[e["a"]] += amt
                        first = min(first, e["r"])
            j = max(0, min(len(rr) - 1, first - 2))
            c = rc[p]
            hpfrac = c["hp"][j] / max(1, c["maxHp"][j])
            px, py = c["x"][i], c["y"][i]
            allies = 0
            for cid, cc in rc.items():
                if cid != p and champs[cid]["team"] == us and cc["alive"][i] and px is not None and cc["x"][i] is not None:
                    allies += max(abs(cc["x"][i] - px), abs(cc["y"][i] - py)) <= 8
            enemies = 0
            for cid, cc in rc.items():
                if champs[cid]["team"] != us and cc["alive"][i] and px is not None and cc["x"][i] is not None:
                    enemies += max(abs(cc["x"][i] - px), abs(cc["y"][i] - py)) <= 8
            k = champs[d["by"]]
            top = max(dmg.items(), key=lambda kv: kv[1])[0] if dmg else d["by"]
            rows.append(dict(r=r, bag=d["gems"], killer=k["name"], n_att=len(dmg), run=r - first + 1, hpfrac=hpfrac, maxhp=c["maxHp"][i], allies=allies, enemies=enemies,
                             kstr=rc[d["by"]]["str"][i], khp=rc[d["by"]]["maxHp"][i], won=won, gold=c["gold"][i], topshare=(max(dmg.values()) / sum(dmg.values())) if dmg else 1,
                             chan=c["chan"][i], foc=c["foc"][i]))
    n = len(rows)
    print(f"{n} Prism deaths with {a.min}+ gems to champions; in wins {sum(x['won'] for x in rows)}")
    print("round q:", q([x["r"] for x in rows]), " bag q:", q([x["bag"] for x in rows]), " Prism max health q:", q([x["maxhp"] for x in rows]), " Focus q:", q([x["foc"] for x in rows]))
    print("killer:", Counter(x["killer"] for x in rows).most_common(8))
    print("attackers in the last 12 rounds:", sorted(Counter(x["n_att"] for x in rows).items()))
    print("fatal run length (rounds) q:", q([x["run"] for x in rows]), " health fraction before its first hit q:", " ".join(f"{v:.2f}" for v in sorted(x["hpfrac"] for x in rows)[n // 4::max(1, n // 4)][:3]))
    print("allies within 8 at the end of the round before:", sorted(Counter(x["allies"] for x in rows).items()), " enemies within 8:", sorted(Counter(x["enemies"] for x in rows).items()))
    print("killer Strength q:", q([x["kstr"] for x in rows]), " killer max health q:", q([x["khp"] for x in rows]), " hits (max health / killer Strength) q:", " ".join(f"{v:.1f}" for v in sorted(x['maxhp'] / max(1, x['kstr']) for x in rows)[n // 4::max(1, n // 4)][:3]))
    print("unspent gold q:", q([x["gold"] for x in rows]), " channelling a tribute the round before:", sum(x["chan"] == 2 for x in rows), " recall:", sum(x["chan"] == 1 for x in rows))
    print("top attacker's share of the damage q:", " ".join(f"{v:.2f}" for v in sorted(x["topshare"] for x in rows)[n // 4::max(1, n // 4)][:3]))
    for lo, hi in ((0, 300), (300, 500), (500, 700), (700, 3000)):
        s = [x for x in rows if lo <= x["r"] < hi]
        if s:
            print(f"  r{lo}-{hi}: {len(s)} deaths, bag {st.median(x['bag'] for x in s):.0f}, attackers {st.mean(x['n_att'] for x in s):.1f}, allies near {st.mean(x['allies'] for x in s):.1f}, enemies near {st.mean(x['enemies'] for x in s):.1f}, hits {st.median(x['maxhp'] / max(1, x['kstr']) for x in s):.1f}, killers {Counter(x['killer'] for x in s).most_common(3)}")


if __name__ == "__main__":
    main()
