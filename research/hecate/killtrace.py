"""killtrace.py BATCH_DIR: KILL trace lines of hx-kill2 (bot 1) and what followed (target died / we died soon)."""
import zipfile, glob, collections, re, json, gzip, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; AN = ROOT / "replays" / ".analysis"
batch = Path(sys.argv[1]).resolve()
idx = json.loads((AN / "index.json").read_text(encoding="utf-8"))
dirs = {}
for g in idx["games"]:
    src = Path(g["source"]); src = src if src.is_absolute() else ROOT / src
    if src.resolve().parent == batch: dirs[src.name] = g["dir"]
C = collections.Counter()
for f in sorted(glob.glob(str(batch / "*.repl26a"))):
    name = Path(f).name; side = "a" if name.endswith("-12.repl26a") else "b"; team = 0 if side == "a" else 1
    kills = []
    for l in zipfile.ZipFile(f).read(f"team-{side}.stdout").decode(errors="replace").replace("\x00", "").splitlines():
        m = re.match(r"KILL (\d+) (\d+) hp(\d+)/(\d+) target(\d+) thp(\d+) low(\d) fight(\d) fightx(\d)", l)
        if m: kills.append(tuple(map(int, m.groups())))
    if not kills or name not in dirs: continue
    d = AN / dirs[name]; meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
    ours = [c["id"] for c in meta["champions"] if c["team"] == team]; theirs = [c["id"] for c in meta["champions"] if c["team"] != team]
    deaths = [(e["r"], e["v"], e.get("by")) for e in (json.loads(x) for x in gzip.open(d / "events.jsonl.gz", "rt")) if e["k"] == "death"]
    for r, h, hp, mx, t, thp, low, fi, fx in kills:
        kind = "low" if low else ("fight" if fi and not fx else "other")
        if kind == "other": continue
        C[kind] += 1
        tid = theirs[t] if t < len(theirs) else None
        me = ours[h] if h < len(ours) else h
        if any(dr == r and v == tid for dr, v, b in deaths): C[kind + "_target_died_same_round"] += 1
        if any(r <= dr <= r + 3 and v == me for dr, v, b in deaths): C[kind + "_we_died_within_3"] += 1
print(dict(C))
