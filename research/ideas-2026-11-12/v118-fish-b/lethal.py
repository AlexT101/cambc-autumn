"""The lethal bound at the tile our hoarding Prism ended its turns on, before its deaths (trace run g: PX and HG lines),
on reproduced rounds only.

    py research/ideas-2026-11-12/v118-fish-b/lethal.py
PX round handle lethal(end tile) turns_to_kill_idle(end tile, 8): 0 = nothing kills us there within 8 idle turns.
HG: each visible enemy whose strike reaches our end tile, with its strike damage and blow."""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dlib  # noqa: E402
D = json.load(open(REPO / "replays/v118b/deathctx.json"))
F = {f["key"]: f for f in json.load(open(REPO / "replays/v118b/feat.json"))}
val = dlib.validation("g")
P = [d for d in D if d["v"] == "Prism" and d["bag"] >= 100]
ok = [d for d in P if (val.get(d["key"], {}).get("ladder_trusted_through") or 0) >= d["r"]]
print(f"{len(P)} Prism deaths with 100+ gems; {len(ok)} in rounds trace run g reproduces; games exact {sum(1 for v in val.values() if v.get('exact'))}/{len(val)}, "
      f"rounds trusted {sum(v.get('ladder_trusted_through') or 0 for v in val.values())}/{sum(v['rounds'] for v in val.values())}")
last = Counter(); two = Counter(); ttk = Counter(); hgk = Counter()
for d in ok:
    f = F[d["key"]]; pid = [c["id"] for c in f["champs"] if c["us"] and c["type"] == "Prism"][0]
    kid = {c["id"] for c in f["champs"] if not c["us"] and c["type"] == d["by"]}
    px = {}; hg = defaultdict(list)
    for w in dlib.lines("g", d["key"], {"PX", "HG"}):
        try:
            if int(w[2]) != pid: continue
            if w[0] == "PX": px[int(w[1])] = (int(w[3]), int(w[4]))
            else: hg[int(w[1])] = [x.split(":") for x in " ".join(w).split("|")[1].split()]
        except (ValueError, IndexError):
            pass
    r = d["r0"] - 1  # the Prism's last turn end before the fatal run's first hit
    if r in px:
        last["lethal" if px[r][0] else "not lethal"] += 1
        ttk["never (0)" if px[r][1] == 0 else f"{min(px[r][1], 5)}{'+' if px[r][1] >= 5 else ''} idle turns"] += 1
        inreach = any(int(x[0]) in kid for x in hg.get(r, []))
        hgk["killer's strike reaches the end tile" if inreach else "killer not in reach of the end tile (as modelled)"] += 1
    else:
        last["no PX line (on spawn / dead / bag < 50)"] += 1
    rr = d["r"] - 1
    if rr in px and rr != r:
        two["lethal" if px[rr][0] else "not lethal"] += 1
print("end tile of the last turn before the first hit of the fatal run: lethal bound says", dict(last))
print("   turns_to_kill_idle there:", dict(ttk))
print("   HG:", dict(hgk))
print("end tile of the last turn before the death (when later than that):", dict(two))
