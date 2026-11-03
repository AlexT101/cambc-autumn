"""Where an A/B's out-of-fuel excess lives: per-map CAND - REF OOF turns over every batch of an ab.py run.

    python3 research/aggro-2026-11-03/oof_maps.py fix-aggro-x6-null-vs-ast294
"""
import json, sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
sys.path.insert(0, "tools/fuel"); sys.path.insert(0, "tools")
import oof

def one(args):
    batch, files = args
    _, turns, games, phases, maps = oof.count(batch, files)
    return maps

def main():
    run = json.loads(Path(f"replays/ab/{sys.argv[1]}/summary.json").read_text())
    jobs = []
    for s in run["suites"]:
        files = sorted(Path(s["batch"]).glob("*.repl26a"))
        jobs += [(s["batch"], files[i:i + 64]) for i in range(0, len(files), 64)]
    c, r = {}, {}
    with ProcessPoolExecutor(64) as ex:
        for maps in ex.map(one, jobs):
            for k, v in maps[1].items(): c[k] = c.get(k, 0) + v
            for k, v in maps[2].items(): r[k] = r.get(k, 0) + v
    keys = set(c) | set(r)
    d = sorted(((c.get(k, 0) - r.get(k, 0), k) for k in keys), reverse=True)
    tot = sum(x for x, _ in d)
    print(f"CAND {sum(c.values())} REF {sum(r.values())} excess {tot} over {len(keys)} maps")
    pos = [x for x, _ in d if x > 0]; neg = [x for x, _ in d if x < 0]
    print(f"maps CAND more {len(pos)} (+{sum(pos)}), fewer {len(neg)} ({sum(neg)})")
    for frac in (10, 50, 200):
        print(f"  top {frac} maps: +{sum(x for x, _ in d[:frac])}")
    print("  top:", ", ".join(f"{k} {x:+d}" for x, k in d[:8]))
    print("  bottom:", ", ".join(f"{k} {x:+d}" for x, k in d[-5:]))


if __name__ == "__main__":
    main()
