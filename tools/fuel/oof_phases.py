"""Out-of-fuel play turns per bot, tallied by the Phase path each ran out in (`OOF round phase path=...`,
printed by local builds with `debug_phases` on in hyperion's util.h). A line without a path counts
under its phase.

    py tools/fuel/oof_phases.py replays/batch-A replays/fuel/games/x some-game.repl26a
    py tools/fuel/oof_phases.py replays/batch-A --depth 3 --top 40

Each argument is a replay bundle or a directory: a run_batched.py batch (named by its results.json)
or any directory holding bundles, searched recursively, whose bots come from `A-vs-B-<time>.repl26a`.
"""
import argparse
import collections
import json
import re
import zipfile
from pathlib import Path

LINE = re.compile(r"^OOF (\d+) (.+?)(?: path=(\S+))?$", re.M)


def bundles(arg):
    """(bundle, team A's bot, team B's bot) for each replay bundle under arg."""
    p = Path(arg)
    if p.is_file():
        return [(p, *names_from_stem(p))]
    results = p / "results.json"
    if results.exists():
        bots = [Path(b).name for b in json.loads(results.read_text())["bots"]]
        out = []
        for b in sorted(p.glob("*.repl26a")):
            order = b.stem.rsplit("-", 1)[1]  # 12: bot 1 is team A
            out.append((b, *(bots if order == "12" else bots[::-1])))
        return out
    return [(b, *names_from_stem(b)) for b in sorted(p.rglob("*.repl26a"))]


def names_from_stem(b):
    m = re.match(r"(.+)-vs-(.+)-\d+$", b.stem)
    return (m[1], m[2]) if m else ("team-a", "team-b")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--depth", type=int, default=0, help="keep the first N phases of each path (0: all)")
    ap.add_argument("--top", type=int, default=25, help="rows per bot")
    args = ap.parse_args()

    paths = collections.defaultdict(collections.Counter)
    games = collections.Counter()
    read = 0
    for arg in args.paths:
        for bundle, team_a, team_b in bundles(arg):
            read += 1
            with zipfile.ZipFile(bundle) as z:
                for team, bot in (("a", team_a), ("b", team_b)):
                    # The engine pads stdout with NULs at line starts, which would hide lines from ^.
                    out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    hits = [m for m in LINE.finditer(out) if not m[2].startswith("draft")]
                    paths[bot].update()
                    games[bot] += bool(hits)
                    for m in hits:
                        path = m[3] or m[2].strip().replace(" ", "_")
                        if args.depth:
                            path = "/".join(path.split("/")[:args.depth])
                        paths[bot][path] += 1
    print(f"{read} games")
    for bot in sorted(paths, key=lambda b: -sum(paths[b].values())):
        tally = paths[bot]
        total = sum(tally.values())
        print(f"\n{bot}: {total} out-of-fuel turns in {games[bot]} games")
        if not total:
            continue
        width = max(len("path"), *(len(p) for p, _ in tally.most_common(args.top)))
        print(f"  {'path':<{width}}  count   share")
        for p, n in tally.most_common(args.top):
            print(f"  {p:<{width}}  {n:5}  {n / total:6.1%}")
        if len(tally) > args.top:
            rest = total - sum(n for _, n in tally.most_common(args.top))
            print(f"  {f'({len(tally) - args.top} more)':<{width}}  {rest:5}  {rest / total:6.1%}")


if __name__ == "__main__":
    main()
