"""Game-by-game replay comparison of two run_batched batches on the same maps (a fuel-only change's check, as
tools/fuel/bench.py compare does): the replay itself, not the stdout or fuel files.

    python3 same_replays.py BATCH_A BATCH_B
"""
import sys
import zipfile
from pathlib import Path


def body(p):
    with zipfile.ZipFile(p) as z:
        return z.read("replay.repl26a")


a, b = Path(sys.argv[1]), Path(sys.argv[2])
names = sorted({p.name.split("-", 1)[1] for p in a.glob("*.repl26a")} & {p.name.split("-", 1)[1] for p in b.glob("*.repl26a")})
fa = {p.name.split("-", 1)[1]: p for p in a.glob("*.repl26a")}
fb = {p.name.split("-", 1)[1]: p for p in b.glob("*.repl26a")}
diff = [n for n in names if body(fa[n]) != body(fb[n])]
print(f"{len(names)} games, {len(names) - len(diff)} identical, {len(diff)} differ")
for n in diff[:20]:
    print("  differs:", n)
