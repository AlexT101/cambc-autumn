"""Out-of-fuel turns per bot in A/B batches: overall, without shared-gem maps, by round bucket, finish gap and
champion-game run size.

    py tools/fuel/oof_bot.py replays/batch-A replays/batch-B ...
    py tools/fuel/oof_bot.py "replays/batch-*-ab-m4*/*.repl26a"

Arguments are batch directories or globs of replays. Shared-gem maps (`gen-shared-gems-*`) hold mutual livelocks
whose counts swing with one rerouted game, so judge without them too. The finish gap is rounds from a turn that ran
out to the round it finished in (the late finish, CHANGES 217). Run sizes bucket each champion-game's out-of-fuel
turns (<10, 10-49, >=50), counting turns.
"""
import argparse
import collections
import glob
import json
import re
import zipfile
from pathlib import Path


def bucket(r):
    return "1" if r <= 1 else "2-10" if r <= 10 else "11-60" if r <= 60 else "61-300" if r <= 300 else "300+"


def replays(args):
    for a in args:
        p = Path(a)
        yield from sorted(p.glob("*.repl26a")) if p.is_dir() else sorted(map(Path, glob.glob(a)))


def bot_names(args):
    names = set()
    for a in args:
        r = Path(a) / "results.json"
        if r.is_file():
            names.add(tuple(Path(b).name for b in json.loads(r.read_text())["bots"]))
    return names.pop() if len(names) == 1 else ("bot 1", "bot 2")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+", help="batch directories or replay globs")
    a = ap.parse_args()
    tot, nosg = collections.Counter(), collections.Counter()
    rb, gap, run = ({1: collections.Counter(), 2: collections.Counter()} for _ in range(3))
    games = 0
    for b in replays(a.paths):
        games += 1
        order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
        name = b.stem.split("-", 1)[1].rsplit("-", 1)[0]
        with zipfile.ZipFile(b) as z:
            for t in "ab":
                bot = 1 if (t == "a") == (order == "12") else 2
                out = z.read(f"team-{t}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                hits = [m for m in re.finditer(r"^OOF (\d+) (.+)$", out, re.M) if not m[2].startswith("draft")]
                tot[bot] += len(hits)
                if "shared-gems" not in name:
                    nosg[bot] += len(hits)
                for m in hits:
                    rb[bot][bucket(int(m[1]))] += 1
                for r0, r1 in re.findall(r"^r(\d+) turn ran out of fuel, finished in r(\d+)", out, re.M):
                    gap[bot][int(r1) - int(r0)] += 1
                per = collections.Counter(c for _, c in re.findall(r"^SHORTCUT (\d+) (\d+) out-of-fuel", out, re.M))
                for v in per.values():
                    run[bot][">=50" if v >= 50 else "10-49" if v >= 10 else "<10"] += v
    names = bot_names(a.paths)
    print(f"{games} games")
    for k in (1, 2):
        print(f"{names[k - 1]}: OOF {tot[k]}, without shared-gems {nosg[k]}")
        print(f"  rounds {dict(sorted(rb[k].items(), key=lambda kv: int(kv[0].split('-')[0].rstrip('+'))))}")
        print(f"  finish gap {dict(sorted(gap[k].items()))}")
        print(f"  champion-game run sizes {({s: run[k][s] for s in ('<10', '10-49', '>=50')})}")


if __name__ == "__main__":
    main()
