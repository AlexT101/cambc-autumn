"""Play forced-draft variants against each other with run_batched.py and tabulate win rates.

    py tools/variants/matrix.py varg,tavi,ryth,stellar,ren willow,ren,ryth --one-side
    py tools/variants/matrix.py --focus --cols hecate@
    py tools/variants/matrix.py --resume replays/matrix-20261013-220000

A spec is [BOT@]DRAFT (see make_variant.py), or BOT@ for that bot's own draft. Rows use --bot
unless the spec names one; columns default to the row drafts on --vs-bot. --focus makes one row
per champion (default all 11): that champion first, then --filler. Each distinct pair is one
run_batched.py batch, run one after another; a pair of identical entries is a mirror match,
reported as team A's win rate. Output: replays/matrix-TIMESTAMP/ with matrix.md, matrix.csv
(overall row win rates), cells.csv (per cell and map) and pairs/<n>-<a>-vs-<b>/ batches."""

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_variant import ROOT, bot_dir, champions, make_variant, parse_draft  # noqa: E402

RUNNER = ROOT / "tools" / "run_batched.py"
DEFAULT_FILLER = "varg,tavi,ryth,stellar,ren"


def parse_spec(spec, default_bot):
    bot, sep, draft = spec.rpartition("@")
    source = bot_dir(bot if sep else default_bot)
    return source, parse_draft(draft) if draft else None


def entry_for(source, draft, default_source, focus=False):
    if draft is None:
        return {"name": source.name, "path": str(source), "source": str(source), "draft": None,
                "display": f"{source.name} (own draft)"}
    path, manifest, _ = make_variant(source, draft)
    shown = draft[0] if focus else "-".join(d[:4] for d in manifest["given"])
    if source != default_source:
        shown = f"{source.name}:{shown}"
    return {"name": manifest["name"], "path": str(path), "source": manifest["source"],
            "draft": manifest["draft"], "padded": manifest["padded"], "display": shown}


def build(entry):
    done = subprocess.run(["cambc", "build", entry["path"]], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    return entry, done.returncode, done.stdout + done.stderr


def plan_matrix(args, output):
    row_bot = bot_dir(args.bot)
    col_bot = bot_dir(args.vs_bot or args.bot)
    if args.focus is not None:
        focus = parse_draft(args.focus) if args.focus else champions()
        filler = parse_draft(args.filler)
        row_specs = [(row_bot, [c, *[f for f in filler if f != c]][:5]) for c in focus]
    else:
        if not args.specs:
            raise ValueError("Give at least one spec, or --focus")
        row_specs = [parse_spec(s, row_bot) for s in args.specs]
    if args.cols:
        col_specs = [parse_spec(s, col_bot) for s in args.cols]
    else:
        col_specs = [(col_bot if src == row_bot else src, draft) for src, draft in row_specs]

    entries = {}

    def add(source, draft, default_source):
        entry = entry_for(source, draft, default_source, args.focus is not None)
        known = entries.setdefault(entry["name"], entry)
        if (known["path"], known["draft"]) != (entry["path"], entry["draft"]):
            raise ValueError(f"Two specs map to variant {entry['name']} with different contents")
        return entry["name"]

    rows = list(dict.fromkeys(add(s, d, row_bot) for s, d in row_specs))
    cols = list(dict.fromkeys(add(s, d, col_bot) for s, d in col_specs))
    pairs = {}
    for r in rows:
        for c in cols:
            if not (r == c and args.no_mirrors):
                pairs.setdefault(frozenset((r, c)), (r, c))
    return {"created": output.name, "rows": rows, "cols": cols, "entries": entries,
            "pairs": [{"dir": f"pairs/{i + 1:03d}-{a}-vs-{b}", "bots": [a, b]} for i, (a, b) in enumerate(pairs.values())],
            "runner_args": runner_args(args)}


def runner_args(args):
    extra = ["--threads", str(args.threads)]
    if args.one_side:
        extra += ["--one-side", "--side-seed", str(args.side_seed)]
    if args.maps_dir:
        extra += ["--maps-dir", str(Path(args.maps_dir).resolve())]
    if args.fuel:
        extra += ["--fuel", str(args.fuel)]
    if args.timeout:
        extra += ["--timeout", str(args.timeout)]
    if args.no_replays:
        extra.append("--no-replays")
    return extra


def complete(batch):
    try:
        report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return report if report["completed"] == report["scheduled"] else None


def run_pairs(plan, output, build_jobs):
    todo = [p for p in plan["pairs"] if complete(output / p["dir"]) is None]
    if not todo:
        return
    needed = {name for p in todo for name in p["bots"]}
    print(f"Building {len(needed)} bot(s)...", flush=True)
    with ThreadPoolExecutor(build_jobs) as pool:
        for entry, code, log in pool.map(build, (plan["entries"][n] for n in sorted(needed))):
            if code:
                raise RuntimeError(f"{entry['name']} failed to build:\n{log[-3000:]}")
    for i, pair in enumerate(todo, 1):
        batch = output / pair["dir"]
        if batch.exists():
            shutil.rmtree(batch)
        batch.parent.mkdir(parents=True, exist_ok=True)
        a, b = (plan["entries"][n]["path"] for n in pair["bots"])
        print(f"\n=== Pair {i}/{len(todo)}: {pair['bots'][0]} vs {pair['bots'][1]}", flush=True)
        subprocess.run([sys.executable, str(RUNNER), a, b, "--output", str(batch), *plan["runner_args"]], cwd=ROOT)


def blank():
    return {"games": 0, "errors": 0, "wins": 0, "games_a": 0, "wins_a": 0, "team_a_wins": 0}


def tally(plan, output):
    """cells[(row, col)][map] from the row's side; mirror cells count bot 1 as the row."""
    cells = defaultdict(lambda: defaultdict(blank))
    total = blank()
    maps = set()
    for pair in plan["pairs"]:
        try:
            report = json.loads((output / pair["dir"] / "results.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        a, b = pair["bots"]
        for match in report["matches"]:
            name = Path(match["map"]).stem
            maps.add(name)
            total["games"] += 1
            if "error" in match:
                total["errors"] += 1
            else:
                total["team_a_wins"] += match["winner"] == match["order"][0]
            for me, key in ((0, (a, b)), (1, (b, a))):
                if a == b and me == 1:
                    continue
                for cell in (cells[key][name], cells[key]["ALL"]):
                    cell["games"] += 1
                    if "error" in match:
                        cell["errors"] += 1
                        continue
                    a_side = match["order"][0] == me
                    won = match["winner"] == me
                    cell["wins"] += won
                    cell["games_a"] += a_side
                    cell["wins_a"] += won and a_side
                    cell["team_a_wins"] += match["winner"] == match["order"][0]
    return cells, sorted(maps), total


def rate(wins, games):
    return wins / games if games else None


def pct(value):
    return "-" if value is None else f"{100 * value:.0f}%"


def write_reports(plan, output):
    cells, maps, total = tally(plan, output)
    entries, rows, cols = plan["entries"], plan["rows"], plan["cols"]
    show = lambda n: entries[n]["display"]

    def played(cell):
        return cell["games"] - cell["errors"]

    def cell_text(r, c, m, short=False):
        cell = cells.get((r, c), {}).get(m)
        if not cell or not cell["games"]:
            return ""
        n = played(cell)
        if r == c:
            text = f"A {cell['team_a_wins']}/{n}" if short else f"A {pct(rate(cell['team_a_wins'], n))} ({cell['team_a_wins']}/{n})"
        else:
            text = f"{cell['wins']}/{n}" if short else f"{pct(rate(cell['wins'], n))} ({cell['wins']}/{n})"
        return text + (f" E{cell['errors']}" if cell["errors"] else "")

    def row_mean(r):
        wins = games = 0
        for c in cols:
            cell = cells.get((r, c), {}).get("ALL")
            if r != c and cell:
                wins, games = wins + cell["wins"], games + played(cell)
        return rate(wins, games), games

    def table(m, short):
        lines = ["| row \\ col | " + " | ".join(show(c) for c in cols) + (" | mean |" if m == "ALL" else " |"),
                 "|---" * (len(cols) + 1 + (m == "ALL")) + "|"]
        for r in rows:
            mean = f" | {pct(row_mean(r)[0])} |" if m == "ALL" else " |"
            lines.append(f"| {show(r)} | " + " | ".join(cell_text(r, c, m, short) for c in cols) + mean)
        return lines

    side = rate(total["team_a_wins"], total["games"] - total["errors"])

    md = [f"# Matrix {plan['created']}", "",
          f"Runner args: `{' '.join(plan['runner_args'])}`. Cells give the row's win rate (wins/games); "
          "mirror cells give team A's. Mean is over non-mirror cells.",
          f"Team A won {pct(side)} of {total['games'] - total['errors']} games "
          f"({total['errors']} errors).", "", "## Entries", "", "| entry | name | source | draft |", "|---|---|---|---|"]
    for n in dict.fromkeys(rows + cols):
        e = entries[n]
        draft = "own" if e["draft"] is None else ",".join(e["draft"]) + (
            f" (padded {','.join(e['padded'])})" if e.get("padded") else "")
        md.append(f"| {e['display']} | {n} | {e['source']} | {draft} |")
    md += ["", "## Overall", "", *table("ALL", False)]
    mirrors = [r for r in rows if r in cols and (r, r) in cells]
    if mirrors:
        md += ["", "## Mirrors", "",
               "Both sides run the same deterministic code, so with both orders played each map should be "
               "won by the same team twice.", "", "| entry | team A wins | maps split | split maps |", "|---|---|---|---|"]
        for r in mirrors:
            both = [m for m in maps if played(cells[(r, r)][m]) == 2]
            split = [m for m in both if cells[(r, r)][m]["team_a_wins"] == 1]
            count = f"{len(split)}/{len(both)}" if both else "- (one side only)"
            md.append(f"| {show(r)} | {cell_text(r, r, 'ALL')} | {count} | {', '.join(split)} |")
    md += ["", "## Per map", ""]
    for m in maps:
        md += [f"### {m}", "", *table(m, True), ""]
    (output / "matrix.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    with (output / "matrix.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["row", *cols, "mean"])
        for r in rows:
            values = []
            for c in cols:
                cell = cells.get((r, c), {}).get("ALL")
                value = cell and rate(cell["team_a_wins" if r == c else "wins"], played(cell))
                values.append("" if value is None else f"{value:.4f}")
            mean = row_mean(r)[0]
            w.writerow([r, *values, "" if mean is None else f"{mean:.4f}"])

    with (output / "cells.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["row", "col", "mirror", "map", "games", "errors", "row_wins", "row_games_as_a",
                    "row_wins_as_a", "team_a_wins"])
        for r in rows:
            for c in cols:
                for m in ["ALL", *maps]:
                    cell = cells.get((r, c), {}).get(m)
                    if cell and cell["games"]:
                        w.writerow([r, c, int(r == c), m, cell["games"], cell["errors"], cell["wins"],
                                    cell["games_a"], cell["wins_a"], cell["team_a_wins"]])
    return output / "matrix.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("specs", nargs="*", help="Row specs: [BOT@]DRAFT, or BOT@")
    parser.add_argument("--cols", nargs="+", metavar="SPEC", help="Column specs (default: the row drafts on --vs-bot)")
    parser.add_argument("--bot", default="hyperion", help="Default row bot (default: hyperion)")
    parser.add_argument("--vs-bot", help="Default column bot (default: --bot)")
    parser.add_argument("--focus", nargs="?", const="", metavar="CHAMPS",
                        help="One row per champion (default all), each first pick before --filler")
    parser.add_argument("--filler", default=DEFAULT_FILLER, help=f"Focus picks 2-5 (default: {DEFAULT_FILLER})")
    parser.add_argument("--no-mirrors", action="store_true", help="Skip pairs of identical entries")
    parser.add_argument("--resume", type=Path, metavar="DIR", help="Finish an earlier matrix's unfinished pairs")
    parser.add_argument("--report", type=Path, metavar="DIR", help="Only rewrite an earlier matrix's reports")
    parser.add_argument("--build-jobs", type=int, default=4, help="Variants built in parallel (default: 4)")
    parser.add_argument("--threads", type=int, default=16, help="run_batched.py --threads (default: 16)")
    parser.add_argument("--one-side", action="store_true")
    parser.add_argument("--side-seed", type=int, default=0)
    parser.add_argument("--maps-dir")
    parser.add_argument("--fuel", type=int)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--no-replays", action="store_true")
    args = parser.parse_args()
    try:
        if args.resume or args.report:
            output = (args.resume or args.report).resolve()
            plan = json.loads((output / "matrix.json").read_text(encoding="utf-8"))
        else:
            output = ROOT / "replays" / datetime.now().strftime("matrix-%Y%m%d-%H%M%S")
            output.mkdir(parents=True, exist_ok=False)
            plan = plan_matrix(args, output)
            (output / "matrix.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Matrix: {output}\n{len(plan['rows'])} row(s) x {len(plan['cols'])} col(s), {len(plan['pairs'])} pair(s)",
          flush=True)
    if not args.report:
        try:
            run_pairs(plan, output, args.build_jobs)
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return 1
    report = write_reports(plan, output)
    print(f"\nReport: {report}")
    unfinished = [p["dir"] for p in plan["pairs"] if complete(output / p["dir"]) is None]
    if unfinished:
        print(f"Unfinished pairs: {', '.join(unfinished)}; rerun with --resume {output}")
    return 1 if unfinished else 0


if __name__ == "__main__":
    sys.exit(main())
