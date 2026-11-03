"""Branch counts per bot from the census D lines (`D round champ BRANCH ...`) of a run_batched batch: how often each
bot takes each decide branch (R retreat, F farm, ...), per 1000 turns.

    python3 branches.py BATCH [BATCH2]   # bot 1 vs bot 2; with two batches, bot 1 of each
"""
import collections
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path


def one(path):
    out = [collections.Counter(), collections.Counter()]
    tag = path.stem.rsplit("-", 1)[1]
    with zipfile.ZipFile(path) as z:
        for team, name in ((0, "team-a.stdout"), (1, "team-b.stdout")):
            bot = team if tag == "12" else 1 - team
            for l in z.read(name).decode(errors="replace").replace("\x00", "").splitlines():
                if l.startswith("D "):
                    p = l.split()
                    if len(p) > 3:
                        out[bot][p[3]] += 1
    return out


def load(d, which):
    tot = collections.Counter()
    with ProcessPoolExecutor(48) as pool:
        for o in pool.map(one, sorted(Path(d).glob("*.repl26a")), chunksize=8):
            tot.update(o[which])
    return tot


def main():
    a = load(sys.argv[1], 0)
    b = load(sys.argv[2], 0) if len(sys.argv) > 2 else load(sys.argv[1], 1)
    na, nb = sum(a.values()), sum(b.values())
    print(f"turns {na} {nb}")
    for k in sorted(set(a) | set(b), key=lambda k: -a[k]):
        print(f"  {k:3s} {1000 * a[k] / na:8.2f} {1000 * b[k] / nb:8.2f}   ({a[k]} / {b[k]})")


if __name__ == "__main__":
    main()
