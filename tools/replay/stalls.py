"""Stalls: a bot's champions standing on one tile, alive and off their spawn, for many rounds.

    py tools/replay/stalls.py <ab name or batch dir>... [--min 100] [--bot 0]

Reads replays/.analysis (run tools/replay/extract.mjs on the batches first). --bot is the index in results.json's
`bots` (0: CAND in an ab.py batch). One line per champion with its longest stall: replay, champion, rounds, first
round, tile, bag and the game's winner; then the count and the champion-rounds stood.
"""
import argparse
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def batches(spec):
    if os.path.exists(os.path.join(spec, "results.json")):
        return [spec]
    summary = os.path.join(ROOT, "replays", "ab", spec, "summary.json")
    if os.path.exists(summary):
        return [os.path.join(ROOT, s["batch"]) for s in json.load(open(summary, encoding="utf-8"))["suites"]]
    sys.exit(f"no batch or A/B named {spec}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--min", type=int, default=100, help="shortest stall reported, in rounds")
    ap.add_argument("--bot", type=int, default=0)
    args = ap.parse_args()
    analysis = os.path.join(ROOT, "replays", ".analysis")
    index = json.load(open(os.path.join(analysis, "index.json"), encoding="utf-8"))
    by_source = {os.path.normcase(os.path.abspath(os.path.join(ROOT, g["source"]))): g for g in index["games"]}
    names = json.load(open(os.path.join(analysis, "enums.json"), encoding="utf-8"))["champions"]
    games = missing = found = stood = 0
    for spec in args.specs:
        for b in batches(spec):
            for m in json.load(open(os.path.join(b, "results.json"), encoding="utf-8"))["matches"]:
                g = by_source.get(os.path.normcase(os.path.abspath(m["replay"])))
                if not g:
                    missing += 1
                    continue
                team = 0 if m["order"][0] == args.bot else 1
                d = os.path.join(analysis, g["dir"])
                rounds = json.load(gzip.open(os.path.join(d, "rounds.json.gz")))
                meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
                spawn = json.load(open(os.path.join(d, meta["mapFile"]), encoding="utf-8"))["spawn"][team]
                types = {c["id"]: c["type"] for c in meta["champions"]}
                games += 1
                for c in rounds["champions"]:
                    if c["team"] != team:
                        continue
                    run, start, worst = 0, 0, (0, 0, None, 0)
                    for i in range(len(rounds["round"])):
                        x, y = c["x"][i], c["y"][i]
                        home = x is not None and spawn["minX"] <= x <= spawn["maxX"] and spawn["minY"] <= y <= spawn["maxY"]
                        if i > 0 and x is not None and not home and c["alive"][i] and (x, y) == (c["x"][i - 1], c["y"][i - 1]):
                            run += 1
                        else:
                            run, start = 0, i
                        if run > worst[0]:
                            worst = (run, rounds["round"][start], (x, y), c["gems"][i])
                    if worst[0] >= args.min:
                        found += 1
                        stood += worst[0]
                        print(f"{os.path.basename(m['replay']):48} {names[types[c['id']]]:13} still {worst[0]:4} "
                              f"from r{worst[1]:<4} at {worst[2]} gems {worst[3]:3} winner={'us' if m['winner'] == args.bot else 'them'}")
    print(f"{games} games: {found} stalls of {args.min}+ rounds, {stood} champion-rounds"
          + (f"; {missing} replays not extracted" if missing else ""))


if __name__ == "__main__":
    main()
