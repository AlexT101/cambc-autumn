"""Is a placebo edit a no-op in the vehicle? Mirror games on the pool's first maps with team A carrying each edit
set, team B none: sets that differ only by placebos must give the same game (outcome.mjs rows compared).
    py placebo_noop.py LAB N "13" "16" "144,225" "13,144,225" ...   (the empty set is always played)"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/emblab"))
import elab, edits as ed, evehicle as ev
from elab import dlab, vehicle
lab = elab.LABS / sys.argv[1]
cfg = elab.config(lab)
reg = ed.load(ROOT / cfg["registry"])
defs = ed.defs_header(reg, [n for n, _ in ev.FLAGS])
maps = dlab.jsonl(lab / "maps.jsonl")[:int(sys.argv[2])]
sets = [[]] + [[int(x) for x in s.split(",") if x] for s in sys.argv[3:]]
cdir = lab / "noop"
shutil.rmtree(cdir, ignore_errors=True); cdir.mkdir()
bots, lines = [], {}
for i, ids in enumerate(sets):
    veh, _ = ev.make_edit(ROOT / cfg["source"], f"ee-{lab.name}-noop{i}", [(m["key"], 0, ids) for m in maps] + [(m["key"], 1, []) for m in maps], defs)
    bots.append(veh)
    for j, m in enumerate(maps):
        lines[f"n{i}-{j:04d}"] = f"{veh.as_posix()} {veh.as_posix()} {(ROOT / m['path']).as_posix()} {cdir.resolve().as_posix()}/n{i}-{j:04d}.repl26a\n"
elab.release_build([b for b in bots if not elab.built(b)])
elab.play(cdir, lines, dlab.cpu_slots.SIZE, cfg["timeout"])
dlab.node(dlab.HERE / "outcome.mjs", cdir, "--out", cdir / "outcomes.jsonl", "--delete", "--threads", 16)
rows = {o["file"].removesuffix(".repl26a"): {k: v for k, v in o.items() if k != "file"} for o in dlab.jsonl(cdir / "outcomes.jsonl")}
for i, ids in enumerate(sets):
    print(ids, "same game as", *[f"{sets[k]}: {sum(rows.get(f'n{i}-{j:04d}') == rows.get(f'n{k}-{j:04d}') for j in range(len(maps)))}/{len(maps)}" for k in range(i)])
