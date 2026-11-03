"""A team's crystal purchases and hops in extracted replays (tools/replay/extract.mjs output).

    python3 research/crystal-2026-11-03/team_crystals.py replays/uw-x "Univardisty of Shingtonwash"

A hop is a teleport channel (rounds' `chan`) followed by a jump; reported with the round, the jump, and the walking
steps it replaced (static terrain BFS between source and landing, holes and altars impassable).
"""
import gzip, json, sys
from collections import deque, Counter
from pathlib import Path

def bfs(block, w, h, src):
    d = {src: 0}; q = deque([src])
    while q:
        x, y = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                n = (x + dx, y + dy)
                if 0 <= n[0] < w and 0 <= n[1] < h and n not in block and n not in d:
                    d[n] = d[(x, y)] + 1; q.append(n)
    return d

root = Path(sys.argv[1]); team_name = sys.argv[2]
games = buys = 0; hops = []; chan_kinds = Counter(); by_map = Counter()
for g in sorted(root.iterdir()):
    if not (g / "meta.json").exists(): continue
    meta = json.loads((g / "meta.json").read_text())
    names = [t["name"] for t in meta["teams"]]
    if team_name not in names: continue
    t = names.index(team_name); games += 1
    data = json.load(gzip.open(g / "rounds.json.gz"))
    for line in gzip.open(g / "events.jsonl.gz", "rt"):
        if not line.strip(): continue
        e = json.loads(line)
        if e["k"] == "shop" and "cons" in e and "Teleport crystal" in e["cons"] and e.get("t") == t: buys += 1
    mp = json.loads((root / "maps" / f"{meta['map']['hash']}.json").read_text()) if (root / "maps").exists() else None
    block = set(map(tuple, mp["walls"] + mp["holes"] + mp["altars"])) if mp else set()
    for c in data["champions"]:
        if c["team"] != t: continue
        for i, ch in enumerate(c["chan"]): 
            chan_kinds[ch] += 1
        for i in range(1, len(c["x"])):
            if c["chan"][i - 1] == 4 and c["chan"][i] != 4:
                a = (c["x"][i - 1], c["y"][i - 1]); b = (c["x"][i], c["y"][i])
                walk = bfs(block, mp["width"], mp["height"], a).get(b, -1) if mp else -1
                hops.append((meta["map"].get("name", ""), data["round"][i], a, b, walk)); by_map[meta["map"].get("name", "")] += 1
print(f"{team_name}: {games} games, {buys} crystals bought, {len(hops)} hops")
print("channel kinds:", chan_kinds.most_common())
print("hops by map:", by_map.most_common(15))
for h in hops[:25]: print("  ", h)
