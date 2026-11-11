"""Per-turn fuel of tools/replay/harness/direct_batch.py re-runs against the ladder .fuel, on turns before each game's first divergence.

    python3 fueldiff.py VERSION RUN_NAME"""
import collections, json, struct, sys, zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
v, name = sys.argv[1:3]
man = {f"{g['group'][:8]}-{g['position']}": g for g in json.load(open(REPO / f"replays/{v}/manifest.json"))["games"]}
res = json.load(open(REPO / f"replays/{v}/runs/{name}/direct_validation.json"))


def rd(x):
    return [struct.unpack_from("<Q", x, 13 + 8 * i)[0] for i in range((len(x) - 13) // 8)]


tot, nt = collections.Counter(), 0
for k, r in sorted(res.items()):
    if r.get("status") != "ok" or not r["exact"]:
        continue
    g = man[k]
    a = rd((REPO / g["fuel"]).read_bytes())
    c = rd(zipfile.ZipFile(REPO / f"replays/{v}/runs/{name}/{k}/direct.repl26a").read(f"team-{g['our_side']}.fuel"))
    n = min(len(a), len(c))
    nt += n
    tot.update(c[i] - a[i] for i in range(n))
print(f"exact games' turns {nt}: share equal {tot[0] / max(nt, 1):.4f}; commonest differences {tot.most_common(10)}")
