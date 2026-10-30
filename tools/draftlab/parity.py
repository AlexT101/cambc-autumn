"""In-game parity of astraeus's model draft with the draft lab's JS (tools/draftlab/README.md, deployment).

Builds a debug copy of a bot with params::draft_parity on (bots/variants/dl-parity), plays it against itself
for one round on each map (cambc run-batch --rounds 1: the draft and round 1), reads the FEAT / TEAM /
FEATFUEL lines its draft bot prints in draft round 0 from the replays' team stdout, and compares them with
features.mjs (the 19 features, the map key) and model.mjs teams (the team in pick order). Its DRAFTTURN line
says whether the draft analysis still finished in round 0 (the model's fuel comes first).

    py tools/draftlab/parity.py --lab replays/draftlab/night1 maps maps/gen [--jobs 4] [--max 60]

Exit code 0 when every map matches. Output in replays/draftlab/parity/<timestamp>/ (manifest, replays, report.txt).
"""
import argparse, json, random, re, shutil, subprocess, sys, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402
CAMBC = shutil.which("cambc") or "cambc"


def node(*args):
    r = subprocess.run(["node", *map(str, args)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"node {args[0]} failed:\n{r.stderr}")
    return r.stdout


def make_copy(bot, target):
    """A copy of bot's src/ with draft_parity on; .cambc/ (the build cache) is kept only if it is the target's own."""
    params = (bot / "src" / "params.h").read_text(encoding="utf-8")
    assert re.search(r"constexpr bool test_draft = false;", params), "the bot's test_draft must be off (the model is off on test drafts)"
    assert params.count("constexpr bool draft_parity = false;") == 1, "params.h has no draft_parity switch"
    if (target / "src").exists():
        shutil.rmtree(target / "src")
    shutil.copytree(bot / "src", target / "src")
    (target / "src" / "params.h").write_text(params.replace("constexpr bool draft_parity = false;", "constexpr bool draft_parity = true;"),
                                             encoding="utf-8")


def map_files(specs):
    out = []
    for spec in specs:
        p = (ROOT / spec).resolve() if not Path(spec).is_absolute() else Path(spec)
        out += sorted(p.glob("*.map26a")) if p.is_dir() else [p]
    return out


def team_lines(replay):
    """{prefix: [fields]} per team ('a', 'b') from the replay bundle's stdout."""
    found = {}
    with zipfile.ZipFile(replay) as z:
        for team in "ab":
            try:
                out = z.read(f"team-{team}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
            except KeyError:
                continue
            for line in out.splitlines():
                parts = line.split()
                if parts and parts[0] in ("FEAT", "TEAM", "FEATFUEL", "FEATFAIL"):
                    found.setdefault(team, {})[parts[0]] = parts[1:]
                elif len(parts) >= 3 and parts[0] == "DRAFTTURN" and parts[1] == "0":
                    found.setdefault(team, {})["DRAFTTURN"] = parts[1:]
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("maps", nargs="+", help="map files or directories (non-recursive)")
    ap.add_argument("--lab", required=True, help="the lab whose model.json / prior.json made bots/astraeus/src/draft/draft_model.h")
    ap.add_argument("--bot", default="bots/astraeus")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--max", type=int, default=0, help="at most N maps, sampled with --seed")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--counters", action="store_true", help="the header was generated with model.mjs cpp --counters")
    args = ap.parse_args()

    maps = map_files(args.maps)
    if args.max and len(maps) > args.max:
        maps = sorted(random.Random(args.seed).sample(maps, args.max))
    out = ROOT / "replays" / "draftlab" / "parity" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True)
    copy = ROOT / "bots" / "variants" / "dl-parity"
    make_copy(ROOT / args.bot, copy)
    print(f"building {copy.relative_to(ROOT)} (debug)...", flush=True)
    b = subprocess.run([CAMBC, "build", str(copy)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if b.returncode:
        shutil.rmtree(copy / ".cambc", ignore_errors=True)
        sys.exit(f"build failed:\n{b.stdout[-3000:]}{b.stderr[-3000:]}")

    v = copy.as_posix()
    (out / "manifest.txt").write_text("".join(f"{v} {v} {m.as_posix()} m{i:04d}.repl26a\n" for i, m in enumerate(maps)), encoding="utf-8")
    print(f"playing {len(maps)} maps, 1 round each...", flush=True)
    with open(out / "run.log", "w", encoding="utf-8") as log:
        subprocess.run([CAMBC, "run-batch", "manifest.txt", "--jobs", str(args.jobs), "--rounds", "1", "--color", "never",
                        "--timeout", str(args.timeout)], cwd=out, env=cambc_env.env(), stdout=log, stderr=subprocess.STDOUT)

    # The JS side: features.mjs rows (it skips a map whose key repeats an earlier one's) and model.mjs teams.
    node(HERE / "features.mjs", *maps, "--out", out / "features.jsonl")
    rows = {}
    for line in (out / "features.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[(ROOT / r["path"]).resolve()] = r
    teams = {}
    for line in node(HERE / "model.mjs", "teams", "--lab", args.lab, "--features", out / "features.jsonl", *(["--counters"] if args.counters else [])).splitlines():
        key, picks, name, team = line.split()
        teams[key] = team
    names = json.loads((Path(args.lab) / "model.json").read_text(encoding="utf-8"))["features"]

    report, bad, fuel, spilled = [], 0, [], 0
    feature_bad = {}
    for i, m in enumerate(maps):
        rel = m.relative_to(ROOT).as_posix() if m.is_relative_to(ROOT) else str(m)
        row, replay = rows.get(m.resolve()), out / f"m{i:04d}.repl26a"
        if row is None:
            report.append(f"{rel}: no features.mjs row (decode failed or duplicate key)")
            continue
        if not replay.is_file():
            report.append(f"{rel}: no replay")
            bad += 1
            continue
        lines = team_lines(replay)
        spilled += sum(1 for t in lines.values() if t.get("DRAFTTURN", ["0", "analysed", "1"])[2] == "0")
        # The bot has no model for these pick counts, and declines spawns joined only by dash or crystal.
        modelled = row["picks"] in (3, 4, 5)
        if not any("FEAT" in t for t in lines.values()):
            why = next((" ".join(t["FEATFAIL"]) for t in lines.values() if "FEATFAIL" in t), "")
            if not modelled or "dash or crystal" in why:
                note = why or f"{row['picks']} picks"
                report.append(f"{rel}: no model draft, as expected ({note})")
            else:
                report.append(f"{rel}: no FEAT lines (model draft failed{f': {why}' if why else ''}, so table_draft drafted)")
                bad += 1
            continue
        if not modelled:
            report.append(f"{rel}: FEAT lines on {row['picks']} picks")
            bad += 1
            continue
        problems = []
        if len({json.dumps(t, sort_keys=True) for t in ({k: v for k, v in d.items() if k in ("FEAT", "TEAM")} for d in lines.values())}) > 1:
            problems.append("teams A and B printed different lines")
        d = next(t for t in lines.values() if "FEAT" in t)
        key, values = d["FEAT"][0], d["FEAT"][1:]
        if key != row["key"]:
            problems.append(f"key c++ {key} js {row['key']}")
        for name, text in zip(names, values):
            js, c = row["f"].get(name), float(text)
            if (js is None and c == c) or (js is not None and c != js):
                problems.append(f"{name} js {js} c++ {text}")
                feature_bad[name] = feature_bad.get(name, 0) + 1
        c_team, js_team = d.get("TEAM", ["", "", "?"])[2], teams.get(row["key"])
        if c_team != js_team:
            problems.append(f"team c++ {c_team} js {js_team}")
        if "FEATFUEL" in d:
            fuel.append((int(d["FEATFUEL"][1]), row["W"] * row["H"], rel))
        bad += bool(problems)
        report.append(f"{rel}: {'; '.join(problems) if problems else 'ok'} ({c_team})")

    summary = [f"{len(maps)} maps, {bad} with differences" +
               (f" (features: {', '.join(f'{k} {n}' for k, n in feature_bad.items())})" if feature_bad else "")]
    if fuel:
        fuel.sort()
        summary.append(f"feature extraction + model fuel: median {fuel[len(fuel) // 2][0]}, max {fuel[-1][0]} ({fuel[-1][2]}, "
                       f"{fuel[-1][1]} tiles); debug build, debug_block paused")
    summary.append(f"draft analysis unfinished after draft round 0: {spilled} team-games (it resumes next draft turn)")
    (out / "report.txt").write_text("\n".join(summary + report) + "\n", encoding="utf-8")
    for line in report:
        if not line.endswith(")") or ": ok (" not in line:
            print(line)
    print("\n".join(summary))
    print(f"report: {(out / 'report.txt').relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
