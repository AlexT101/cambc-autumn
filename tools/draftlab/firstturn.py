"""First draft turn fuel of a bot's model draft (tools/draftlab/PLAN-draft3.md, "Features: what ships").

Builds a release copy of BOT (bots/variants/firstturn-<name>) whose draft bot prints, in draft round 0, the fuel used
of the 10M first turn: on entering play_draft (start-up), after the model draft (map read, engine fields, compute,
team ranking: what must fit before the first pick) and after analyse() (budgeted: it spills to later draft turns),
and whether the analysis finished. Plays it against itself for the draft only (--rounds 0: no round is played, so
held-out suites may be measured) and writes ft.jsonl and a summary.

    py tools/draftlab/firstturn.py MAPS... [--bot bots/astraeus] [--every] [--jobs 8] [--name NAME]
    py tools/draftlab/firstturn.py --sample replays/draftlab/draft3/maps.jsonl [--heavy 100] [--random 2500]

--sample takes a lab's maps.jsonl instead of MAPS: the --heavy largest maps by each of area, camps, bush tiles and
walkable tiles (their union, a few hundred), plus --random others. --every measures all of map_features' features,
not only those draft_model.h names. A team-draft without an FT line ran out of fuel (or crashed) before it: a random
draft."""
import argparse, json, random, shutil, statistics, subprocess, sys, time, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402

BUDGET = 10_000_000
PLAY = """    if (params::test_draft || model_draft() || cambc::draft::team_size() != 3) draft_order();
    try {
        analyse(state);
    } catch (const std::exception&) {
        analysis().done = true; // a member's tiles may be half written: only finished groups count
    }
"""


def make(bot, dst, every):
    if (dst / "src").exists():
        shutil.rmtree(dst / "src")
    shutil.copytree(bot / "src", dst / "src")
    p = dst / "src" / "draft" / "draft.cc"
    s = p.read_text(encoding="utf-8")
    mask = "params::draft_parity ? mapfeat::every : mapfeat::model_features()"
    if mask not in s or PLAY not in s:
        sys.exit("draft.cc changed: update firstturn.py")
    if every:
        s = s.replace(mask, "mapfeat::every")
    s = s.replace(PLAY, f"""    const bool first_turn = draft_round() == 0;
    const auto ft0 = {BUDGET} - cambc::fuel_remaining();
""" + PLAY.replace("    try {", f"""    const auto ft1 = {BUDGET} - cambc::fuel_remaining();
    try {{""") + f"""    const auto ft2 = {BUDGET} - cambc::fuel_remaining();
    if (first_turn)
        std::printf("FT %llu %llu %llu %d %d\\n", static_cast<unsigned long long>(ft0), static_cast<unsigned long long>(ft1),
                    static_cast<unsigned long long>(ft2), analysis().done ? 1 : 0, model_draft() ? 1 : 0);
""")
    p.write_text(s, encoding="utf-8")


def sample(maps_jsonl, heavy, others, seed=1):
    rows = [json.loads(l) for l in Path(maps_jsonl).read_text().splitlines() if l.strip()]
    rows = [r for r in rows if not r["set"].startswith("prior:")]
    keys = [lambda f: f["area"], lambda f: f.get("camps_side", 0), lambda f: f["bushes"] * f["area"], lambda f: f.get("walkable", 0)]
    chosen = {r["path"] for k in keys for r in sorted(rows, key=lambda r: -k(r["f"]))[:heavy]}
    rest = sorted({r["path"] for r in rows} - chosen)
    chosen |= set(random.Random(seed).sample(rest, min(others, len(rest))))
    return [(ROOT / p).resolve() for p in sorted(chosen)]


def map_files(specs):
    out = []
    for spec in specs:
        p = (ROOT / spec).resolve()
        out += sorted(p.glob("*.map26a")) if p.is_dir() else [p]
    return out


def summary(rows):
    ok = [r for r in rows if r.get("ft")]
    lost = [r for r in rows if not r.get("ft")]
    pre, post = [r["ft"][1] for r in ok], [r["ft"][2] for r in ok]
    q = lambda xs, p: sorted(xs)[int(p * (len(xs) - 1))]
    out = [f"{len({r['map'] for r in rows})} maps, {len(ok)} team-drafts measured, {len(lost)} without an FT line (out of fuel before it)"]
    if ok:
        out += [f"start-up: max {max(r['ft'][0] for r in ok)}",
                f"before the first pick's analysis (start-up + model draft): median {statistics.median(pre):.0f}, p99 {q(pre, .99)}, "
                f"p99.9 {q(pre, .999)}, max {max(pre)}; over 8.5M: {sum(1 for v in pre if v > 8_500_000)}",
                f"after analyse(): median {statistics.median(post):.0f}, max {max(post)}",
                f"analysis unfinished after draft round 0: {sum(1 for r in ok if not r['ft'][3])} of {len(ok)}",
                f"model draft not used: {sum(1 for r in ok if not r['ft'][4])}"]
        out += [f"  {r['ft'][1]:>9} {r['map']} {r['team']}" for r in sorted(ok, key=lambda r: -r["ft"][1])[:10]]
    out += [f"  lost {r['map']} {r['team']}" for r in lost[:20]]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("maps", nargs="*", help="map files or directories (non-recursive)")
    ap.add_argument("--sample", help="a lab's maps.jsonl to sample from instead")
    ap.add_argument("--heavy", type=int, default=100)
    ap.add_argument("--random", type=int, default=2500)
    ap.add_argument("--bot", default="bots/astraeus")
    ap.add_argument("--every", action="store_true")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--name", default=time.strftime("%Y%m%d-%H%M%S"))
    args = ap.parse_args()
    dst = ROOT / "bots" / "variants" / f"firstturn-{args.name}"
    make(ROOT / args.bot, dst, args.every)
    b = subprocess.run(["cambc", "build", "--release", str(dst)], cwd=ROOT, capture_output=True, text=True)
    if b.returncode:
        sys.exit(f"build failed:\n{b.stdout[-3000:]}{b.stderr[-3000:]}")
    out = ROOT / "replays" / "draftlab" / "firstturn" / args.name
    out.mkdir(parents=True, exist_ok=True)
    maps = sample(args.sample, args.heavy, args.random) if args.sample else map_files(args.maps)
    rows, bot = [], dst.as_posix()
    for c in range(0, len(maps), 2000):
        chunk = maps[c:c + 2000]
        (out / "manifest.txt").write_text("".join(f"{bot} {bot} {m.as_posix()} m{i:05d}.repl26a\n" for i, m in enumerate(chunk)))
        with open(out / "run.log", "a") as log:
            subprocess.run(["cambc", "run-batch", "manifest.txt", "--jobs", str(args.jobs), "--rounds", "0", "--release",
                            "--color", "never", "--timeout", "600"], cwd=out, env=cambc_env.env(), stdout=log, stderr=subprocess.STDOUT)
        for i, m in enumerate(chunk):
            p = out / f"m{i:05d}.repl26a"
            rel = m.relative_to(ROOT).as_posix() if m.is_relative_to(ROOT) else str(m)
            if not p.is_file():
                rows += [{"map": rel, "team": t} for t in "ab"]
                continue
            with zipfile.ZipFile(p) as z:
                for t in "ab":
                    txt = z.read(f"team-{t}.stdout").replace(b"\0", b"").decode("utf-8", "replace")
                    ft = next((l.split()[1:] for l in txt.splitlines() if l.startswith("FT ")), None)
                    rows.append({"map": rel, "team": t, "ft": [int(x) for x in ft] if ft else None})
            p.unlink()
        print(f"{min(c + 2000, len(maps))}/{len(maps)} maps", flush=True)
    (out / "ft.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    text = summary(rows)
    (out / "summary.txt").write_text(text + "\n")
    print(text)
    print(f"output: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
