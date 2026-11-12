"""Our Prism's branch (the bot's D lines, debug builds) in the rounds before its 100+ bag deaths to a champion.

    python3 research/ideas-2026-11-12/r8-scale/dtrace.py EXTRACT_DIR --team NAME --root REPO [--show 10] [--after 300]

Per death: the branch letter per round (bot_parts.h Branch), the distance to the killer, health. Summary: the branch
on the turn before the fatal run's first hit, on the turns the distance to the killer fell while it was within 9,
and how many rounds the killer had been within 9."""
import argparse, gzip, json, zipfile, re
from collections import Counter, defaultdict
from pathlib import Path


def dlines(path, ours_a):
    out = defaultdict(dict)
    with zipfile.ZipFile(path) as z:
        txt = z.read("team-a.stdout" if ours_a else "team-b.stdout").decode("utf8", "replace")
    for m in re.finditer(r"^D (\d+) (\d+) (.) (-?\d+) (-?\d+)$", txt, re.M):
        out[int(m.group(2))][int(m.group(1))] = (m.group(3), int(m.group(4)), int(m.group(5)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--root", default=".")
    ap.add_argument("--show", type=int, default=8)
    ap.add_argument("--after", type=int, default=300)
    ap.add_argument("--back", type=int, default=16)
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    before, closing, seen_for, n = Counter(), Counter(), [], 0
    last8 = Counter()
    shown = 0
    done = set()
    for row in index:
        if row["dir"] in done:
            continue
        done.add(row["dir"])
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
        ds = [e for e in ev if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= 100 and e.get("by") is not None and e["r"] >= a.after]
        if not ds:
            continue
        D = dlines(Path(a.root) / row["source"], us == 0)
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        # the Prism's handle: the D stream whose alive rounds match best
        hd = None
        for h, d in D.items():
            if h == p:
                hd = h
        if hd is None:
            # handles may be per-team indices: pick by order within our team
            ours = sorted(c["id"] for c in champs.values() if c["team"] == us)
            hs = sorted(D)
            if len(hs) == len(ours):
                hd = hs[ours.index(p)]
        if hd is None:
            continue
        for d in ds:
            k = d["by"]
            r = d["r"]
            first = r
            for e in ev:
                if r - 12 <= e["r"] <= r and e["k"] in ("attack", "cast") and e["a"] == k and any(t == p for t, _ in e.get("dmg", [])):
                    first = min(first, e["r"])
            n += 1
            b = D[hd].get(first - 1, ("?",))[0]
            before[b] += 1
            line = []
            near = 0
            prev = None
            for q in range(r - a.back, r + 1):
                if q not in rr:
                    continue
                i = rr.index(q)
                c, kc = rc[p], rc[k]
                if c["x"][i] is None or kc["x"][i] is None:
                    dist = None
                else:
                    dist = max(abs(c["x"][i] - kc["x"][i]), abs(c["y"][i] - kc["y"][i]))
                br = D[hd].get(q, ("?",))[0]
                if q < first and q >= first - 8:
                    last8[br] += 1
                if dist is not None and dist <= 9:
                    near += 1
                    if prev is not None and dist < prev and q <= first:
                        closing[br] += 1
                prev = dist
                line.append(f"{q}:{br}{'' if dist is None else dist}{'*' if q >= first else ''}")
            seen_for.append(near)
            if shown < a.show:
                shown += 1
                i = max(0, rr.index(r) - 1) if r in rr else -1
                print(f"{row['map']} r{r} bag {d['gems']} by {champs[k]['name']} (str {rc[k]['str'][i]:.0f}) Prism {rc[p]['maxHp'][i]:.0f}: " + " ".join(line))
    print(f"\n{n} deaths (100+ bag, to a champion, from r{a.after})")
    print("branch on the turn before the killer's first hit:", before.most_common())
    print("branch over the 8 turns before the first hit:", last8.most_common())
    print("branch on turns the distance to the killer fell (within 9, before the first hit):", closing.most_common())


if __name__ == "__main__":
    main()
