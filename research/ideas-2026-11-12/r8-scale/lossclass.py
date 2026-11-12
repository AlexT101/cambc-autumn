"""Study A's loss classes (v118-fish/taxonomy.py's rules) on an extract of local games.

    python3 research/ideas-2026-11-12/r8-scale/lossclass.py EXTRACT_DIR --team NAME

hoard-killed: a 100+ bag lost to an enemy champion; hoard-camp: to a camp; unbanked: 300+ carried at the end;
overrun: 10+ deaths or under 300 gems captured; outfarmed: the rest. First match, on our side of wins and losses."""
import argparse, gzip, json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    seen = set()
    cls = defaultdict(lambda: [0, 0])
    early = defaultdict(list)
    lens = defaultdict(list)
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
        won = meta["result"]["winner"] == us
        ours = {c["id"] for c in meta["champions"] if c["team"] == us}
        deaths = big = camp = cap = 0
        d300 = 0
        for l in gzip.open(g / "events.jsonl.gz", "rt"):
            e = json.loads(l)
            if e["k"] == "death" and e["v"] in ours:
                deaths += 1
                d300 += e["r"] <= 300
                if e.get("gems", 0) >= 100:
                    if e.get("by") is not None:
                        big += 1
                    else:
                        camp += 1
            elif e["k"] == "capture" and e["team"] == us:
                cap += sum(s[1] for s in e["shares"])
        R = json.load(gzip.open(g / "rounds.json.gz"))
        carried = sum(c["gems"][-1] for c in R["champions"] if c["id"] in ours)
        c = "hoard-killed" if big else "hoard-camp" if camp else "unbanked" if carried >= 300 else "overrun" if deaths >= 10 or cap < 300 else "outfarmed"
        cls[c][0 if won else 1] += 1
        early[(c, won)].append(d300)
        lens[(c, won)].append(meta["result"]["rounds"])
    W = sum(v[0] for v in cls.values())
    L = sum(v[1] for v in cls.values())
    print(f"{W + L} games, {W} won, {L} lost")
    for c in ("hoard-killed", "hoard-camp", "unbanked", "overrun", "outfarmed"):
        w, l = cls[c]
        el = early[(c, False)]
        ll = sorted(lens[(c, False)])
        print(f"{c:13s} losses {l:4d} ({100 * l / max(1, L):4.1f}%)  wins {w:4d}  won when it holds {100 * w / max(1, w + l):5.1f}%  deaths by r300 in losses {sum(el) / max(1, len(el)):.2f}  median loss length {ll[len(ll) // 2] if ll else None}")


if __name__ == "__main__":
    main()
