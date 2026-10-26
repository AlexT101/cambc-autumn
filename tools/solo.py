"""Farming benchmark: CAND and REF each play bots/idle (which never acts) on the same maps; paired per-map metrics.

    py tools/solo.py astraeus variants/astraeus-<sha7> --name my-change
    py tools/solo.py astraeus astraeus --suites ladder --one-side --maps 3     # smoke run

CAND and REF are bot directories under bots/ (or paths), used as they are, params.h included. Games go through
run_batched.py, then tools/replay/extract.mjs into replays/solo/<name>/analysis/. Suites as ab.py's.
Per game, for the non-idle team: the round tributed gems reach 1000 (the game then ends), tributed and collected
(tributed + carried) gems at rounds 150/300/600, lifetime gold earned at 300/600, and as sanity checks its champion
damage (should be 0), its out-of-fuel turns and either team's bot-error turns. CAND and REF games pair by map and
side; differences (CAND - REF; log ratio for the 1000 round) are averaged per map and bootstrapped over maps."""

import argparse
from datetime import datetime
import gzip
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from ab import resolve, rel, slug, suites  # noqa: E402
from run_batched import find_maps, GEN_DIR  # noqa: E402

IDLE = ROOT / "bots" / "idle"
# A game that never reaches 1000 counts as reaching it just after the round limit.
CENSORED = 2001
CHECKPOINTS = (150, 300, 600)
METRICS = (["r1000"] + [f"trib{r}" for r in CHECKPOINTS] + [f"coll{r}" for r in CHECKPOINTS]
           + ["gold300", "gold600"])
LABELS = {"r1000": "round to 1000 (log ratio)", **{f"trib{r}": f"tributed @{r}" for r in CHECKPOINTS},
          **{f"coll{r}": f"collected @{r}" for r in CHECKPOINTS}, "gold300": "gold earned @300",
          "gold600": "gold earned @600"}


def suite_maps(extra):
    if not extra:
        return find_maps(ROOT / "maps")
    if extra[0] == "--gen":
        return find_maps(GEN_DIR)
    return find_maps(Path(extra[1]))


def limit(label, extra, n, seed, out_dir):
    """A seeded sample of n of the suite's maps, copied to a directory so run_batched.py plays only them."""
    maps = suite_maps(extra)
    if n >= len(maps):
        return extra
    target = out_dir / "maps" / slug(label)
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for path in random.Random(seed).sample(maps, n):
        shutil.copy2(path, target / path.name)
    return ["--maps-dir", str(target)]


def at(rounds, values, r):
    """State at the end of round r; a game that ended earlier keeps its final state."""
    i = min(r, rounds[-1]) - rounds[0]
    return values[i]


def game_metrics(game_dir, team):
    meta = json.loads((game_dir / "meta.json").read_text(encoding="utf-8"))
    data = json.load(gzip.open(game_dir / "rounds.json.gz"))
    rounds, gems = data["round"], data["gems"][team]
    ours = [c for c in data["champions"] if c["team"] == team]
    m = {"rounds": meta["result"]["rounds"], "end_gems": gems[-1]}
    m["r1000"] = next((r for r, g in zip(rounds, gems) if g >= 1000), None)
    for r in CHECKPOINTS:
        m[f"trib{r}"] = at(rounds, gems, r)
        m[f"coll{r}"] = m[f"trib{r}"] + sum(at(rounds, c["gems"], r) for c in ours)
    for r in (300, 600):
        m[f"gold{r}"] = round(sum(at(rounds, c["earned"], r) for c in ours), 1)
    m["champion_damage"] = round(sum(c["stats"]["championDamageDone"] for c in meta["champions"] if c["team"] == team), 1)
    m["oof_turns"] = sum(t == 6 for c in ours for t in c["turn"])
    m["error_turns"] = sum(t == 7 for c in ours for t in c["turn"])
    m["idle_error_turns"] = sum(t == 7 for c in data["champions"] if c["team"] != team for t in c["turn"])
    return m


def bootstrap(values, samples=2000, seed=0):
    if not values:
        return None, None, None
    rng = random.Random(seed)
    n = len(values)
    means = sorted(sum(rng.choices(values, k=n)) / n for _ in range(samples))
    return sum(values) / n, means[int(0.025 * samples)], means[int(0.975 * samples) - 1]


def compare(pairs):
    """Per metric: mean CAND - REF over maps (each map averaged over its sides) with a bootstrap 95% CI."""
    by_map = {}
    for (suite, name, side), (c, r) in pairs.items():
        by_map.setdefault((suite, name), []).append((c, r))
    out = {"maps": len(by_map)}
    games = [g for gs in by_map.values() for g in gs]
    value = lambda m, key: (m[key] or CENSORED) if key == "r1000" else m[key]
    for key in METRICS:
        diffs = []
        for pair in by_map.values():
            if key == "r1000":
                d = [math.log(value(c, key) / value(r, key)) for c, r in pair]
            else:
                d = [c[key] - r[key] for c, r in pair]
            diffs.append(sum(d) / len(d))
        mean, lo, hi = bootstrap(diffs)
        out[key] = {"mean": mean, "lo": lo, "hi": hi,
                    "cand": sum(value(c, key) for c, _ in games) / len(games) if games else None,
                    "ref": sum(value(r, key) for _, r in games) / len(games) if games else None}
        if key == "r1000":
            out[key].update(faster=sum(d < 0 for d in diffs), slower=sum(d > 0 for d in diffs),
                            identical=sum(d == 0 for d in diffs))
    out["censored"] = {"cand": sum(c["r1000"] is None for c, _ in pairs.values()),
                       "ref": sum(r["r1000"] is None for _, r in pairs.values())}
    return out


def fmt(key, s):
    if s["mean"] is None:
        return "-"
    if key == "r1000":
        pct = lambda x: f"{100 * (math.exp(x) - 1):+.1f}%"
        return f"{pct(s['mean'])} [{pct(s['lo'])}, {pct(s['hi'])}]"
    return f"{s['mean']:+.1f} [{s['lo']:+.1f}, {s['hi']:+.1f}]"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cand", help="Candidate: bot directory under bots/")
    parser.add_argument("ref", help="Reference: bot directory under bots/")
    parser.add_argument("--name", help="Run name (default: <cand>-vs-<ref>); results in replays/solo/<name>/")
    parser.add_argument("--threads", type=int, default=22, help="Concurrent matches (default: 22)")
    parser.add_argument("--suites", default="ladder,gen,fresh",
                        help="Comma-separated: ladder, gen, fresh, or directories of maps (default: all three)")
    parser.add_argument("--fuel", type=int, help="Fuel per turn, passed to run_batched.py --fuel")
    parser.add_argument("--one-side", action="store_true", help="Play each map from one side (the same for both bots)")
    parser.add_argument("--maps", type=int, metavar="N", help="Only N maps per suite, sampled by --map-seed")
    parser.add_argument("--map-seed", type=int, default=0, help="Seed for --maps (default: 0)")
    args = parser.parse_args()
    started = perf_counter()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = slug(args.name or f"{args.cand}-vs-{args.ref}")
    out_dir = ROOT / "replays" / "solo" / name
    try:
        sides = [resolve(args.cand), resolve(args.ref)]
        for side in sides:
            if side["kind"] != "dir":
                raise ValueError(f"{side['spec']!r} is a git ref; export it to a bot directory first "
                                 "(AGENTS.md: git archive <sha> bots/astraeus into bots/variants/)")
        plan, notes = suites([t.strip() for t in args.suites.split(",") if t.strip()])
        if not plan:
            raise ValueError("No suites to play")
        out_dir.mkdir(parents=True, exist_ok=True)
        if args.maps:
            plan = [(label, limit(label, extra, args.maps, args.map_seed, out_dir)) for label, extra in plan]
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Solo {name}: CAND {sides[0]['spec']} vs REF {sides[1]['spec']}, each against idle", flush=True)

    batches, failed = [], []
    for label, extra in plan:
        for side, role in zip(sides, ("cand", "ref")):
            batch = ROOT / "replays" / f"batch-{stamp}-solo-{name}-{slug(label)}-{role}"
            log = out_dir / f"{slug(label)}-{role}.log"
            command = [sys.executable, str(ROOT / "tools" / "run_batched.py"), str(side["path"]), str(IDLE),
                       "--threads", str(args.threads), "--output", str(batch), *extra]
            if args.fuel is not None:
                command += ["--fuel", str(args.fuel)]
            if args.one_side:
                command.append("--one-side")
            print(f"  {label} {role}: running, log {rel(log)}", flush=True)
            with log.open("w", encoding="utf-8") as stream:
                code = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT).returncode
            try:
                report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                failed.append({"suite": label, "role": role, "map": None, "error": f"exit {code}, no results; see {rel(log)}"})
                continue
            failed += [{"suite": label, "role": role, "map": Path(m["map"]).name, "error": m["error"]}
                       for m in report["matches"] if "error" in m]
            batches.append((label, role, batch, report))

    print("  extracting replays", flush=True)
    analysis = out_dir / "analysis"
    subprocess.run(["node", str(ROOT / "tools" / "replay" / "extract.mjs"), *(str(b) for _, _, b, _ in batches),
                    "--out", str(analysis)], cwd=ROOT, stdout=subprocess.DEVNULL)
    index = {}
    try:
        index = {row["source"]: row for row in json.loads((analysis / "index.json").read_text(encoding="utf-8"))["games"]}
    except (OSError, ValueError):
        pass

    games = {}
    for label, role, batch, report in batches:
        for m in report["matches"]:
            if "error" in m or not m["replay"]:
                continue
            row = index.get(rel(m["replay"]))
            key = (label, Path(m["map"]).stem, "AB"[m["order"].index(0)])
            if not row or not row["ok"]:
                failed.append({"suite": label, "role": role, "map": key[1], "error": "replay not extracted"})
                continue
            games.setdefault(key, {})[role] = game_metrics(analysis / row["dir"], m["order"].index(0))
    pairs = {k: (v["cand"], v["ref"]) for k, v in games.items() if len(v) == 2}

    results = {"total": compare(pairs)}
    for label, _ in plan:
        results[label] = compare({k: v for k, v in pairs.items() if k[0] == label})
    flags = [{"suite": k[0], "map": k[1], "side": k[2], "role": role, **{f: g[f] for f in
              ("champion_damage", "error_turns", "idle_error_turns") if g[f]}}
             for k, v in sorted(games.items()) for role, g in v.items()
             if g["champion_damage"] or g["error_turns"] or g["idle_error_turns"]]
    oof = {role: sum(v[role]["oof_turns"] for v in games.values() if role in v) for role in ("cand", "ref")}
    wall = perf_counter() - started
    summary = {"name": name, "started": stamp, "wall_seconds": round(wall, 1), "threads": args.threads,
               "fuel": args.fuel, "one_side": args.one_side, "maps_per_suite": args.maps,
               "cand": {**sides[0], "path": rel(sides[0]["path"])}, "ref": {**sides[1], "path": rel(sides[1]["path"])},
               "pairs": len(pairs), "results": results, "oof_turns": oof, "flags": flags, "failed": failed,
               "notes": notes, "batches": [rel(b) for _, _, b, _ in batches],
               "games": [{"suite": k[0], "map": k[1], "cand_side": k[2], **v} for k, v in sorted(games.items())]}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    cols = [(label, results[label]) for label in results if len(results) > 2 or label == "total"]
    md = [f"# Solo {name}", "", f"CAND `{rel(sides[0]['path'])}`, REF `{rel(sides[1]['path'])}`, each against bots/idle.",
          f"Started {stamp}; {len(pairs)} paired games; {'one side' if args.one_side else 'both sides'}; "
          f"fuel {args.fuel or 'default'}; wall {wall / 60:.1f} min.", "",
          "Mean CAND - REF per map, bootstrap 95% CI over maps; the round to 1000 as a % change (negative is faster), "
          f"a game that never reaches it counting as round {CENSORED}.", "",
          "| Metric | " + " | ".join(f"{label} ({r['maps']} maps)" for label, r in cols) + " | CAND mean | REF mean |",
          "|---|" + "---|" * (len(cols) + 2)]
    for key in METRICS:
        t = results["total"][key]
        md.append(f"| {LABELS[key]} | " + " | ".join(fmt(key, r[key]) for _, r in cols)
                  + (f" | {t['cand']:.1f} | {t['ref']:.1f} |" if t["mean"] is not None else " | - | - |"))
    t = results["total"]
    md += ["", f"Maps where CAND reaches 1000 faster / slower / identical: "
           f"{t['r1000'].get('faster', 0)} / {t['r1000'].get('slower', 0)} / {t['r1000'].get('identical', 0)}",
           f"Games never reaching 1000: CAND {t['censored']['cand']}, REF {t['censored']['ref']}",
           f"Out-of-fuel turns: CAND {oof['cand']}, REF {oof['ref']}",
           f"Games with champion damage or bot errors: {len(flags)}"]
    md += [f"- {f}" for f in flags[:10]] + ([f"- ... {len(flags) - 10} more in summary.json"] if len(flags) > 10 else [])
    md.append(f"Failed matches: {len(failed)}")
    md += [f"- {f['suite']} {f['role']} {f['map'] or ''}: {f['error']}" for f in failed[:10]]
    md += [f"- {n}" for n in notes] + ["", f"Results: {rel(out_dir)}/summary.json"]
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md[2:]))
    return 1 if failed or not pairs else 0


if __name__ == "__main__":
    sys.exit(main())
