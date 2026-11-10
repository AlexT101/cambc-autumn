"""Audit 1 of round 4 (tools/emblab/PLAN-round5.md): round 4's final selection (replays/emblab/r4/sel/dense-tb-z2.json:
one arm X per type x ordinal bucket, which candidate.py wrote into every cell of the bucket) as the policy the fit
scored: X once, at the bucket's first ordinal, and the table's own arm everywhere else; nothing where X's passive is
already in the row by then.   py audit1.py BASE_BOT OUT_BOT [--full]   (--full: every cell, as round 4 deployed it)"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/emblab"))
import edits as ed
base, out, full = ROOT / sys.argv[1], ROOT / sys.argv[2], "--full" in sys.argv
sel = json.load(open(ROOT / "replays/emblab/r4/sel/dense-tb-z2.json"))["tb-z2"]
if out.exists():
    shutil.rmtree(out)
shutil.copytree(base, out, ignore=shutil.ignore_patterns(".cambc", "compile_commands.json"))
p = out / "src/economy/emblem_table.h"
text = p.read_text()
table = ed.read_table(text)
bucket = lambda k: k if k < 3 else 3 if k < 6 else 4
put = skipped = 0
seen = set()
for x in sorted(sel, key=lambda x: (x["picks"], x["type"], x["k"])):
    pi, t, k, arm = x["picks"] - 3, ed.TYPES.index(x["type"]), x["k"], x["arm"]
    row = table[pi][t]
    if not full:
        if (pi, t, bucket(k)) in seen:
            continue
        seen.add((pi, t, bucket(k)))
        f = arm // 3
        if f not in (ed.FAM["power"], ed.FAM["bruiser"]) and any(a != 255 and a // 3 == f for a in row[:k]):
            skipped += 1
            continue
    put += row[k] != arm
    row[k] = arm
p.write_text(ed.write_table(text, table))
print(f"{out.name}: {put} cells changed, {skipped} buckets skipped (X already in the row)")
