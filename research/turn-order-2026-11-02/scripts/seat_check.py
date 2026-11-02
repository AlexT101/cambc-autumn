"""Commitment holds from PRI/SEAT trace lines in run_batched batches.

    python3 seat_check.py BOTNAME batch-dir [batch-dir ...]

For each of BOTNAME's teams: rebuild next round's team order from every ally's PRI lines (the priority it
set, which applies from the next round and persists), then check each committed SEAT line's deadline.
"""
import collections
import json
import re
import sys
import zipfile
from pathlib import Path

bot_name = sys.argv[1]
stats = collections.Counter()
by_kind = collections.Counter()
examples = []
for d in map(Path, sys.argv[2:]):
    bots = json.loads((d / "results.json").read_text())["bots"]
    for b in sorted(d.glob("*.repl26a")):
        order = b.stem.rsplit("-", 1)[1]
        with zipfile.ZipFile(b) as z:
            for team in "ab":
                bot = Path(bots[0 if (team == "a") == (order == "12") else 1]).name
                if bot != bot_name:
                    continue
                out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                pri = collections.defaultdict(dict)  # round -> handle -> priority set that round
                seats = []
                pos = {}  # (round, handle) -> line position: the turn order within the round
                seen = {}
                handles = set()
                for m in re.finditer(r"^PRI (\d+) (\d+) (-?\d+)$", out, re.M):
                    r, h, p = map(int, m.groups())
                    pri[r][h] = p
                    handles.add(h)
                    pos[r, h] = m.start()
                for m in re.finditer(r"^SEAT (.*)$", out, re.M):
                    try:
                        f = list(map(int, m.group(1).split()))
                    except ValueError:
                        stats["garbled"] += 1
                        continue
                    if len(f) < 10:
                        stats["garbled"] += 1
                        continue
                    seats.append(f[:10])
                    if len(f) > 10:
                        seen[f[0], f[1]] = f[10]
                if not seats:
                    continue
                stats["games"] += 1
                last_round = max(pri)
                # Priority in effect at round R+1: the latest set at or before R.
                cur = {h: 0 for h in handles}
                order_at = {}
                for r in range(1, last_round + 1):
                    for h, p in pri.get(r, {}).items():
                        cur[h] = p
                    ranks = sorted(handles, key=lambda h: (-cur[h], h))
                    order_at[r + 1] = {h: i for i, h in enumerate(ranks)}
                for s in seats:
                    r, h, seat, natural, rank, top, top_seen, deadline, commit, hard = s
                    stats["turns"] += 1
                    if top != top_seen:
                        stats["assumed_binds_top"] += 1
                        if rank >= top > top_seen:
                            stats["assumed_moved_us"] += 1
                    if seat != natural:
                        stats["seat_differs_natural"] += 1
                    if rank != natural:
                        stats["placed_off_natural"] += 1
                    if not commit:
                        continue
                    kind = "hard" if hard else "soft"
                    stats["commits"] += 1
                    by_kind[kind, "commits"] += 1
                    actual = order_at.get(r + 1, {}).get(h)
                    if actual is None or r + 1 > last_round:
                        stats["no_next_round"] += 1
                        continue
                    if actual > deadline:
                        stats["broken"] += 1
                        by_kind[kind, "broken"] += 1
                        # Who ranks above it next round, and could they see each other this round?
                        nxt = order_at[r + 1]
                        for o in handles:
                            if o == h or nxt[o] >= actual:
                                continue
                            later = pos.get((r, o), -1) > pos[r, h]
                            if later:
                                saw = seen.get((r, o), 0) >> h & 1
                                stats["above:later_" + ("saw" if saw else "blind")] += 1
                            else:
                                saw = seen.get((r, h), 0) >> o & 1
                                stats["above:earlier_" + ("seen" if saw else "unseen")] += 1
                        if len(examples) < 12:
                            examples.append((b.name, team, s, actual))
                    if actual > rank:
                        stats["pushed_down"] += 1
for k, v in sorted(stats.items()):
    print(f"{k}: {v}")
for k, v in sorted(by_kind.items()):
    print(f"{k}: {v}")
if stats["commits"]:
    print(f"broken share: {stats['broken'] / stats['commits']:.4f}")
for e in examples:
    print("example", e)
