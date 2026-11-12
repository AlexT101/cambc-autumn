"""Print the rounds before our Prism's 100+ bag deaths to a champion: positions, health, what each did.

    python3 research/ideas-2026-11-12/r8-scale/episode.py EXTRACT_DIR --team NAME [--n 8] [--after 500] [--killer "Vesper Vale"] [--back 12]"""
import argparse, gzip, json, random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--team", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--after", type=int, default=450)
    ap.add_argument("--killer", default="Vesper Vale")
    ap.add_argument("--back", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    root = Path(a.dir)
    index = json.load(open(root / "index.json"))["games"]
    rows = []
    seen = set()
    for row in index:
        if row["dir"] in seen:
            continue
        seen.add(row["dir"])
        names = [t["name"] if isinstance(t, dict) else t for t in row["teams"]]
        if a.team in names:
            rows.append((row, names.index(a.team)))
    random.Random(a.seed).shuffle(rows)
    shown = 0
    for row, us in rows:
        if shown >= a.n:
            break
        g = root / row["dir"]
        meta = json.load(open(g / "meta.json"))
        champs = {c["id"]: c for c in meta["champions"]}
        prism = [c for c in champs.values() if c["team"] == us and c["name"] == "Prism"]
        if not prism:
            continue
        p = prism[0]["id"]
        ev = [json.loads(l) for l in gzip.open(g / "events.jsonl.gz", "rt")]
        ds = [e for e in ev if e["k"] == "death" and e["v"] == p and e.get("gems", 0) >= 100 and e.get("by") is not None and e["r"] >= a.after
              and champs[e["by"]]["name"] == a.killer]
        if not ds:
            continue
        d = ds[0]
        R = json.load(gzip.open(g / "rounds.json.gz"))
        rc = {c["id"]: c for c in R["champions"]}
        rr = R["round"]
        k = d["by"]
        sp = None
        print(f"\n=== {row['map']} us={'AB'[us]} death r{d['r']} bag {d['gems']} by {champs[k]['name']}; result {row['gems']} winner {'AB'[row['winner']]}; source {row['source']}")
        for r in range(d["r"] - a.back, d["r"] + 1):
            if r < 1:
                continue
            i = rr.index(r) if r in rr else None
            acts = {}
            for e in ev:
                if e["r"] != r or "a" not in e:
                    continue
                s = e["k"]
                if s == "move":
                    s = f"mv{e['to']}"
                elif s in ("attack", "cast"):
                    tg = e.get("tgt")
                    dm = sum(x[1] for x in e.get("dmg", []))
                    s = f"{'A' if s == 'attack' else 'C' + str(e.get('slot'))}>{champs[tg]['name'][:4] if tg in champs else ('camp' if 'camp' in e or e.get('cdmg') else '-')}:{dm:.0f}" + ("*stun" if e.get("stun") else "")
                acts.setdefault(e["a"], []).append((e["t"], s))
            if i is None:
                continue
            c = rc[p]
            kc = rc[k]
            px, py = c["x"][i], c["y"][i]
            kx, ky = kc["x"][i], kc["y"][i]
            dist = max(abs(px - kx), abs(py - ky)) if px is not None and kx is not None else None
            al = []
            for cid, cc in rc.items():
                if cid != p and champs[cid]["team"] == us and cc["alive"][i] and px is not None:
                    al.append(f"{champs[cid]['name'][:4]}{max(abs(cc['x'][i] - px), abs(cc['y'][i] - py))}")
            en = []
            for cid, cc in rc.items():
                if cid != k and champs[cid]["team"] != us and cc["alive"][i] and px is not None:
                    dd = max(abs(cc['x'][i] - px), abs(cc['y'][i] - py))
                    if dd <= 10:
                        en.append(f"{champs[cid]['name'][:4]}{dd}")
            pa = " ".join(f"t{t}:{s}" for t, s in acts.get(p, []))
            ka = " ".join(f"t{t}:{s}" for t, s in acts.get(k, []))
            print(f" r{r} P({px},{py}) hp {c['hp'][i]:.0f}/{c['maxHp'][i]:.0f} g{c['gems'][i]} gold{c['gold'][i]} turn{c['turn'][i]} stun{c['stun'][i]} [{pa}] | K({kx},{ky}) d{dist} str{kc['str'][i]:.0f} hp{kc['hp'][i]:.0f} [{ka}] | allies {' '.join(al)} | foes {' '.join(en)}")
        shown += 1


if __name__ == "__main__":
    main()
