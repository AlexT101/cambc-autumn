"""Policy-level variants of ocean's learned emblem table (bots/<bot>/src/economy/emblem_table.h), for clean A/Bs:

    py collectors.py SRC OUT --at K [--family collectors] [--drop-early] [--stat main|hp]   # a family as every champion's K-th new emblem

The family (default Collectors, +1% damage per family owned) goes into cell K of every (pick count, type) row that has no Collectors at
or before K, in the type's usual stat (the commonest stat of its table arms from ordinal 3 on); a later Collectors
cell then falls back to the current logic, as any owned passive does. --drop-early also returns ordinals 0-2 to the
current logic, wherever Collectors was not just put."""
import argparse, collections, re, shutil
from pathlib import Path

TYPES = ["ryth", "vesper_vale", "vendetta", "cassi", "issac", "stellar", "prism", "marcella", "willow", "ren", "varg", "tavi", "heart_of_ruin"]
FAMILIES = ["monster", "power", "durability", "treasure", "jungle", "home", "bruiser", "tribute", "capture", "prospector", "hunter", "skirmish", "greed", "collectors"]
ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--at", type=int, action="append", default=[])
ap.add_argument("--drop-early", action="store_true"); ap.add_argument("--stat", default="main")
ap.add_argument("--types", help="comma-separated: only these types get the family")
ap.add_argument("--family", default="collectors")
a = ap.parse_args()
COLLECTORS = FAMILIES.index(a.family)
src, out = Path(a.src), Path(a.out)
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
p = out / "src/economy/emblem_table.h"
text = p.read_text()
rows = [list(map(int, m.group(1).split(", "))) for m in re.finditer(r"\{([\d, ]+)\}, // \w+", text)]
assert len(rows) == 39
main = {}
for t in range(13):
    c = collections.Counter(x % 3 for q in range(3) for x in rows[q * 13 + t][3:] if x != 255)
    main[t] = c.most_common(1)[0][0] if c else 0
only = set(a.types.split(",")) if a.types else None
put = dropped = 0
for i, r in enumerate(rows):
    t = i % 13
    placed = set()
    if only is None or TYPES[t] in only:
        for k in a.at:
            if all(x == 255 or x // 3 != COLLECTORS for x in r[:k + 1]):
                r[k] = COLLECTORS * 3 + (2 if a.stat == "hp" else main[t])
                placed.add(k)
                put += 1
    if a.drop_early:
        for k in range(3):
            if k not in placed and r[k] != 255:
                r[k] = 255
                dropped += 1
it = iter(rows)
text = re.sub(r"\{([\d, ]+)\}, // (\w+)", lambda m: "{" + ", ".join(map(str, next(it))) + "}, // " + m.group(2), text)
p.write_text(text)
print(f"{out.name}: {a.family} put in {put} cells at {a.at}; {dropped} early cells to the current logic; main stats {[['str','foc','hp'][main[t]] for t in range(13)]}")
