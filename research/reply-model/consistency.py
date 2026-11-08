"""PLAN2.md step 2's consistency counters, from a trace build's DGW / DGS lines (params::danger::trace).

    python3 research/reply-model/consistency.py BATCH [BATCH...] [--bot NAME]

DGW round handle leave x y mend: want_home's verdict at the turn start, on turns with an enemy within 10.
DGS round handle x0 y0 x1 y1 attacked holding mask: the strike search chose this turn; mask is want_home_parts at
the tile it left us on (1 drawn home, 2 camp trap, 4 camp fled, 8 Willow exposure, 16 stand lost).

- chosen-tile-rejected: DGS lines with a non-zero mask (by part), of those that moved and of all;
- strike-then-leave: DGS at round r followed by DGW leave = 1 at r + 1 (same champion), of DGS with a DGW at r + 1;
- A-B-A flips: DGW triples at r, r + 1, r + 2 with v(r) != v(r + 1) == ... v(r + 2) == v(r), of all triples.
"""
import collections
import json
import re
import sys
import zipfile
from pathlib import Path


def lines(batches, want):
    for d in map(Path, batches):
        bots = json.loads((d / "results.json").read_text())["bots"]
        for b in sorted(d.glob("*.repl26a")):
            order = b.stem.rsplit("-", 1)[1]
            with zipfile.ZipFile(b) as z:
                for team in "ab":
                    bot = Path(bots[0 if (team == "a") == (order == "12") else 1]).name
                    if want and bot != want:
                        continue
                    out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    yield b.name, team, bot, re.findall(r"^(DG[WS]) (.*)$", out, re.M)


def main():
    a = sys.argv[1:]
    want = None
    if "--bot" in a:
        i = a.index("--bot")
        want = a[i + 1]
        del a[i:i + 2]
    c = collections.Counter()
    parts = collections.Counter()
    games = 0
    for game, team, bot, ls in lines(a, want):
        games += 1
        w, s = {}, {}
        for tag, rest in ls:
            v = rest.split()
            r, h = int(v[0]), int(v[1])
            if tag == "DGW":
                w[(h, r)] = int(v[2])
            else:
                s[(h, r)] = (int(v[2]), int(v[3]), int(v[4]), int(v[5]), int(v[6]), int(v[7]), int(v[8]))
        for (h, r), (x0, y0, x1, y1, att, hold, mask) in s.items():
            moved = (x0, y0) != (x1, y1)
            c["dgs"] += 1
            c["dgs_moved"] += moved
            c["rej"] += mask != 0
            c["rej_moved"] += moved and mask != 0
            for bit, name in ((1, "drawn"), (2, "camp_trap"), (4, "camp_fled"), (8, "willow"), (16, "stand_lost")):
                if mask & bit:
                    parts[name] += 1
                    parts[name + "_moved"] += moved
            if (h, r + 1) in w:
                c["stl_n"] += 1
                c["stl"] += w[(h, r + 1)]
                c["stl_n_moved"] += moved
                c["stl_moved"] += moved and w[(h, r + 1)]
                c["stl_rej"] += (mask != 0) and w[(h, r + 1)]
                c["stl_rej_n"] += mask != 0
        for (h, r), v in w.items():
            if (h, r + 1) in w and (h, r + 2) in w:
                c["tri"] += 1
                c["aba"] += v != w[(h, r + 1)] and w[(h, r + 2)] == v
            c["dgw"] += 1
            c["leave"] += v
    pct = lambda x, n: f"{100 * x / max(1, n):.2f}% ({x}/{n})"
    print(f"{games} team-games; DGW {c['dgw']} (leave {pct(c['leave'], c['dgw'])}); DGS {c['dgs']} (moved {c['dgs_moved']})")
    print(f"chosen tile want_home would leave: {pct(c['rej'], c['dgs'])}; moved {pct(c['rej_moved'], c['dgs_moved'])}")
    print("  by part (all / moved): " + ", ".join(f"{n} {parts[n]}/{parts[n + '_moved']}" for n in ("drawn", "camp_trap", "camp_fled", "willow", "stand_lost")))
    print(f"strike-then-leave: {pct(c['stl'], c['stl_n'])}; moved {pct(c['stl_moved'], c['stl_n_moved'])}; of rejected {pct(c['stl_rej'], c['stl_rej_n'])}")
    print(f"A-B-A flips: {pct(c['aba'], c['tri'])}")


if __name__ == "__main__":
    main()
