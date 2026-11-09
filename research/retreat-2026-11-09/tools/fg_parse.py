#!/usr/bin/env python3
"""Collect FG / FGO lines of CAND (bot 1) from a batch's replays into a jsonl.
usage: fgparse.py BATCH OUT.jsonl"""
import sys, zipfile, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor


def one(b):
    b = Path(b)
    order = b.stem.rsplit("-", 1)[1]
    team = "a" if order == "12" else "b"
    rows = []
    try:
        with zipfile.ZipFile(b) as z:
            out = z.read(f"team-{team}.stdout").translate(None, b"\0").decode("utf-8", "replace")
    except Exception:
        return rows
    oofph = {}
    for line in out.split("\n"):
        if line.startswith("OOF "):
            p = line.split()
            oofph[int(p[1])] = p[2] if len(p) > 2 else "?"
    for line in out.split("\n"):
        if line.startswith("FG "):
            p = line.split()
            rows.append({"g": b.stem, "k": "FG", "r": int(p[1]), "h": int(p[2]), "v": [int(x) for x in p[3:]]})
        elif line.startswith("FGO "):
            p = line.split()
            r = int(p[1])
            rows.append({"g": b.stem, "k": "FGO", "r": r, "now": int(p[2]), "h": int(p[3]), "v": [int(x) for x in p[4:]], "ph": oofph.get(r)})
    return rows


if __name__ == "__main__":
    files = sorted(Path(sys.argv[1]).glob("*.repl26a"))
    with ProcessPoolExecutor(16) as ex, open(sys.argv[2], "w") as f:
        for rows in ex.map(one, files, chunksize=8):
            for r in rows:
                f.write(json.dumps(r) + "\n")
    print(len(files), "replays")
