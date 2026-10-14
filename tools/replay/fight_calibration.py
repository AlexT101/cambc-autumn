"""Fight-model calibration: aphelios' fight predictions against what happened.

Build aphelios with `debug_fights = true` (bots/aphelios/src/util.h), play a batch with replays,
extract it, then:

    py run_batched.py aphelios baselines/v7 --gen
    node tools/replay/extract.mjs replays/batch-X
    py tools/replay/fight_calibration.py replays/batch-X [more batches...]

Each champion prints "FF" for every turn that starts in reach of a credible enemy (Safety::fight
at its tile) and "FC" for every chase (Safety::fight at the prey's tile): round, id, tile, health,
the turn's branch letter (see `decision` in bot.cpp), lost, turns to kill us / them, allies,
enemies, pooled health of each side, target, camp damage, lethal, then the enemies in reach.
Outcomes are deaths within K rounds. Bot 1 must be the logging aphelios (`-12` files: team A).
"""
import gzip
import hashlib
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

AN = Path(__file__).resolve().parents[2] / "replays" / ".analysis"
K = 10


def parse(text):
    out = []
    for line in text.splitlines():
        p = line.replace("\x00", "").split()
        if not p or p[0] not in ("FF", "FC"):
            continue
        try:
            out.append(dict(tag=p[0], r=int(p[1]), me=int(p[2]), x=int(p[3]), y=int(p[4]), hp=int(p[5]), dec=p[6],
                            lost=int(p[7]), tku=int(p[8]), tkt=int(p[9]), allies=int(p[10]), enemies=int(p[11]),
                            ourpool=int(p[12]), theirpool=int(p[13]), target=int(p[14]), camp=int(p[15]),
                            lethal=int(p[16]), foes=[(int(s[:-1]), s[-1]) for s in p[17:]]))
        except (ValueError, IndexError):
            continue
    return out


def games(dirs):
    for a in dirs:
        for path in sorted(Path(a).glob("*.repl26a")):
            folder = AN / hashlib.sha256(path.read_bytes()).hexdigest()[:16]
            if not (folder / "meta.json").is_file():
                print(f"skip {path}: not extracted", file=sys.stderr)
                continue
            side = 0 if path.stem.endswith("-12") else 1
            name = "team-a.stdout" if side == 0 else "team-b.stdout"
            z = zipfile.ZipFile(path)
            text = z.read(name).decode("utf-8", "replace") if name in z.namelist() else ""
            meta = json.loads((folder / "meta.json").read_text())
            events = [json.loads(line) for line in gzip.open(folder / "events.jsonl.gz", "rt") if line.strip()]
            yield path, side, parse(text), meta, events


def main():
    rows = defaultdict(Counter)
    deaths = Counter()
    for path, side, lines, meta, events in games(sys.argv[1:]):
        died_at = defaultdict(list)
        for e in events:
            if e["k"] == "death":
                died_at[e["v"]].append((e["r"], e.get("linked")))

        def died(cid, r):
            return any(r <= d <= r + K for d, _ in died_at.get(cid, []))

        by_me = defaultdict(list)
        for d in lines:
            by_me[d["me"]].append(d)
            share = d["hp"] / max(1, d["ourpool"]) * d["allies"]
            role = "solo" if d["allies"] == 1 else "weakest" if share < 0.7 else "strongest" if share >= 1.3 else "average"
            me_dead = died(d["me"], d["r"])
            foe_dead = any(died(f, d["r"]) for f, _ in d["foes"])
            for key in [(d["tag"], d["dec"], d["lost"]), (d["tag"], d["lost"], role, "lethal" if d["lethal"] else "")]:
                rows[key]["n"] += 1
                rows[key]["we die"] += me_dead
                rows[key]["they die"] += foe_dead
        for c in meta["champions"]:
            if c["team"] != side:
                continue
            for r, linked in died_at.get(c["id"], []):
                prev = [d for d in by_me[c["id"]] if r - 6 <= d["r"] <= r]
                if linked is not None:
                    deaths["partner died"] += 1
                elif not prev:
                    deaths["no fight logged in the 6 rounds before"] += 1
                else:
                    deaths[f"last {prev[-1]['tag']} {prev[-1]['dec']} {'lost' if prev[-1]['lost'] else 'won'}"] += 1
    print(f"Outcomes within {K} rounds (tag, branch, lost) and (tag, lost, our share of the pool, lethal):")
    for k in sorted(rows, key=str):
        v = rows[k]
        print(f"  {str(k):40} n={v['n']:6} we die {100 * v['we die'] / v['n']:5.1f}%  an enemy in reach dies {100 * v['they die'] / v['n']:5.1f}%")
    print(f"Our deaths ({sum(deaths.values())}) by the last logged prediction:")
    for k, v in deaths.most_common():
        print(f"  {v:5} {k}")


main()
