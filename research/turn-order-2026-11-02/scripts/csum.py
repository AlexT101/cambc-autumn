"""Totals of sfuel_instrument.py's CSUM lines (cumulative per-component fuel) per bot over a run_batched batch.

    python3 csum.py BATCH_DIR [BATCH_DIR2]   # bot 1 vs bot 2 of each batch; with two batches, bot 1 of each

Per component: inclusive fuel per turn (all turns), self fuel per turn, calls per turn, and inclusive fuel per
heavy turn (>= 85k). Counters (n.*, t.*) are calls only.
"""
import re
import sys
import zipfile
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HEAD = ("turns", "spent", "heavy", "hspent", "over100", "near", "nspent")


def one(path):
    out = [defaultdict(float), defaultdict(float)]  # by bot index (0: bot 1)
    tag = path.stem.rsplit("-", 1)[1]
    with zipfile.ZipFile(path) as z:
        for team, name in ((0, "team-a.stdout"), (1, "team-b.stdout")):
            bot = team if tag == "12" else 1 - team
            try:
                text = z.read(name).decode(errors="replace").replace("\x00", "")
            except KeyError:
                continue
            o = out[bot]
            o["games"] += 0.5
            for l in text.splitlines():
                if not l.startswith("CSUM "):
                    continue
                head, _, comps = l.partition(" | ")
                p = head.split()
                if len(p) < 4 + 2 * len(HEAD) or not comps.rstrip().endswith(tuple("0123456789")):
                    continue  # cut short by the stdout cap
                for i, k in enumerate(HEAD):
                    o[k] += int(p[5 + 2 * i])
                for m in re.finditer(r"(\S+)=(\d+):(\d+):(\d+):(\d+)", comps):
                    lab = m[1]
                    o[lab + "|incl"] += int(m[2])
                    o[lab + "|self"] += int(m[3])
                    o[lab + "|calls"] += int(m[4])
                    o[lab + "|heavy"] += int(m[5])
    return out


def load(d, which):
    files = sorted(Path(d).glob("*.repl26a"))
    tot = defaultdict(float)
    with ProcessPoolExecutor(48) as pool:
        for o in pool.map(one, files, chunksize=8):
            for k, v in o[which].items():
                tot[k] += v
    return tot


def main():
    a = sys.argv[1]
    b = sys.argv[2] if len(sys.argv) > 2 else None
    A = load(a, 0)
    B = load(b, 0) if b else load(a, 1)
    print(f"{'':28s} {'A':>12s} {'B':>12s} {'A-B':>10s}")
    for k in HEAD:
        print(f"{k:28s} {A[k]:12.0f} {B[k]:12.0f} {A[k]-B[k]:10.0f}")
    print(f"{'fuel/turn':28s} {A['spent']/A['turns']:12.1f} {B['spent']/B['turns']:12.1f} {A['spent']/A['turns']-B['spent']/B['turns']:10.1f}")
    print(f"{'heavy share %':28s} {100*A['heavy']/A['turns']:12.3f} {100*B['heavy']/B['turns']:12.3f}")
    print(f"{'over100 share %':28s} {100*A['over100']/A['turns']:12.3f} {100*B['over100']/B['turns']:12.3f}")
    labs = sorted({k.split("|")[0] for k in list(A) + list(B) if "|" in k})
    rows = []
    for lab in labs:
        ta, tb = A["turns"], B["turns"]
        ia, ib = A[lab + "|incl"] / ta, B[lab + "|incl"] / tb
        sa, sb = A[lab + "|self"] / ta, B[lab + "|self"] / tb
        ca, cb = A[lab + "|calls"] / ta, B[lab + "|calls"] / tb
        ha = A[lab + "|heavy"] / max(1, A["heavy"])
        hb = B[lab + "|heavy"] / max(1, B["heavy"])
        rows.append((ia - ib, lab, ia, ib, sa, sb, ca, cb, ha, hb))
    rows.sort(key=lambda r: -abs(r[0]))
    print(f"\n{'per turn':22s} {'incl A':>9s} {'incl B':>9s} {'d':>7s} {'self A':>8s} {'self B':>8s} {'d':>7s} {'calls A':>8s} {'calls B':>8s} {'heavyA':>8s} {'heavyB':>8s}")
    for d, lab, ia, ib, sa, sb, ca, cb, ha, hb in rows:
        print(f"{lab:22s} {ia:9.1f} {ib:9.1f} {d:7.1f} {sa:8.1f} {sb:8.1f} {sa-sb:7.1f} {ca:8.3f} {cb:8.3f} {ha:8.0f} {hb:8.0f}")


if __name__ == "__main__":
    main()
