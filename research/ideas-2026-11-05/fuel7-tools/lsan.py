"""lsan.py DIR: probe2.py's segment profile (LS/LX lines, the last of each champion and loop kind per bundle).

Kinds: bit 0 banks a bag, 1 farm_banking, 2 repricing, 4 first turn. Mark cost is taken off each segment.
"""
import collections
import glob
import sys
import zipfile

import ast
import re
_src = open(__file__.rsplit("/", 1)[0] + "/probe2.py").read()
SEGS = ast.literal_eval(re.search(r"SEGS = (\[.*?\])", _src, re.S).group(1))

D = sys.argv[1]
kinds = sys.argv[2].split(",") if len(sys.argv) > 2 else None
N = len(SEGS)
tot = collections.defaultdict(lambda: collections.Counter())
for z in glob.glob(D + "/**/*.repl26a", recursive=True):
    with zipfile.ZipFile(z) as f:
        for n in f.namelist():
            if not n.endswith(".stdout"):
                continue
            last = {}
            for l in f.read(n).replace(b"\0", b"").decode("utf-8", "replace").splitlines():
                if l.startswith("LS ") or l.startswith("LX "):
                    x = l.split()
                    last[(x[0], x[2], x[3])] = x
            for (t, h, kind), x in last.items():
                c = tot[kind]
                v = [int(a) for a in x[4:]]
                if t == "LS":
                    c["loops"] += v[0]; c["loop_fuel"] += v[1]; c["groups"] += v[2]; c["marks"] += v[3]; c["markn"] += 1
                    for i in range(N):
                        c[f"seg{i}"] += v[4 + 2 * i]; c[f"cnt{i}"] += v[5 + 2 * i]
                else:
                    for i in range(N):
                        c[f"xn{i}"] += v[2 * i]; c[f"xf{i}"] += v[2 * i + 1]
for kind in sorted(tot, key=int):
    if kinds and kind not in kinds:
        continue
    c = tot[kind]
    mark = c["marks"] / max(1, c["loops"])
    marks = sum(c[f"cnt{i}"] for i in range(N)) * mark
    net = c["loop_fuel"] - marks
    print(f"kind {kind}: loops {c['loops']} groups {c['groups']} ({c['groups'] / max(1, c['loops']):.1f} a loop), loop fuel {c['loop_fuel'] / max(1, c['loops']):.0f} a loop, "
          f"less marks ({mark:.0f} each) {net / max(1, c['loops']):.0f}")
    print(f"  {'segment':12s} {'share':>6s} {'per run':>8s} {'runs':>9s} | {'exits':>8s} {'exit cost':>9s}")
    for i, name in enumerate(SEGS):
        seg = c[f"seg{i}"] - c[f"cnt{i}"] * mark
        xn = c[f"xn{i}"]
        print(f"  {name:12s} {seg / max(1, net):6.1%} {seg / max(1, c[f'cnt{i}']):8.0f} {c[f'cnt{i}']:9d} | {xn:8d} {(c[f'xf{i}'] / max(1, xn)) if xn else 0:9.0f}")
