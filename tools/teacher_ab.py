"""A/B a teacher with unlimited fuel against an unchanged bot at normal fuel.

    py tools/teacher_ab.py astraeus_teacher astraeus --maps DIR --name teacher-v1

Exactly 10,000 games by default: a deterministic sample of 5,000 maps, both sides.
Requires the native fast runner with FASTRUNNER_UNLIMITED_BOTS support. Both bots
use their own drafts. Sources are frozen by run_batched.py as for ordinary A/Bs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("teacher")
    parser.add_argument("opponent")
    parser.add_argument("--maps", type=Path, required=True, help="Directory of maps; searched recursively")
    parser.add_argument("--name", required=True)
    parser.add_argument("--games", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0, help="Map-sampling seed")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--teacher-fuel", type=int, help="Finite per-turn quantum for fuel controls; default unlimited")
    args = parser.parse_args()
    if args.teacher_fuel is not None and not 0 < args.teacher_fuel <= 2**63 - 1:
        parser.error("--teacher-fuel must be positive and fit i64")
    teacher_fuel = args.teacher_fuel or "unlimited"
    if args.games < 2 or args.games % 2:
        parser.error("--games must be a positive even number")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.name):
        parser.error("--name must contain only letters, digits, underscores, dots and hyphens")
    bots = []
    for spec in (args.teacher, args.opponent):
        bot = next((p.resolve() for p in (ROOT / "bots" / spec, Path(spec)) if (p / "src").is_dir()), None)
        if bot is None:
            parser.error(f"not a bot directory: {spec}")
        params = (bot / "src" / "params.h").read_text()
        if not re.search(r"\btest_draft\s*=\s*false\s*;", params):
            parser.error(f"{bot.name} must use its own draft (test_draft = false)")
        bots.append(bot)
    if bots[0].name == bots[1].name:
        parser.error("teacher and opponent need distinct directory names")
    runner = ROOT / "tools/fastengine/runner/fastrunner"
    library = runner.parent / "target/release/libfastrunner.so"
    if not library.is_file() or b"FASTRUNNER_UNLIMITED_BOTS" not in library.read_bytes():
        parser.error("build the native fast runner with unlimited-bot support first")
    maps = sorted(set(p.resolve() for p in args.maps.rglob("*.map26a")))
    count = args.games // 2
    if len(maps) < count:
        parser.error(f"need {count} maps, found {len(maps)}")
    chosen = sorted(random.Random(args.seed).sample(maps, count))
    out = ROOT / "replays/ab" / args.name
    if out.exists():
        parser.error(f"run already exists: {out}")
    suite = out / "maps"
    suite.mkdir(parents=True)
    records = []
    for i, path in enumerate(chosen):
        name = f"{i:05d}-{path.name}"
        (suite / name).symlink_to(path)
        records.append({"map": name, "source": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    settings = {"teacher": str(bots[0]), "opponent": str(bots[1]), "teacher_fuel": teacher_fuel,
                "opponent_fuel": 100_000, "games": args.games, "seed": args.seed, "maps": records,
                "runner_sha256": hashlib.sha256(library.read_bytes()).hexdigest()}
    (out / "teacher.json").write_text(json.dumps(settings, indent=2) + "\n")
    env = os.environ.copy()
    env.update(CAMBC_BIN=str(runner), FASTRUNNER_MODE="native", FASTRUNNER_UNLIMITED_BOTS=bots[0].name)
    env.pop("FASTRUNNER_BOT_FUEL", None)
    if args.teacher_fuel:
        env.pop("FASTRUNNER_UNLIMITED_BOTS", None)
        env["FASTRUNNER_BOT_FUEL"] = f"{bots[0].name}:{args.teacher_fuel}"
    # External overrides must not replace the verified library or either program.
    for key in ("FASTRUNNER_LIB", "FASTRUNNER_NATIVE_SO", "FASTRUNNER_CAMBC"):
        env.pop(key, None)
    command = [sys.executable, str(ROOT / "tools/ab.py"), *map(str, bots), "--no-test-draft",
               "--suites", str(suite), "--name", args.name]
    if args.threads is not None:
        command += ["--threads", str(args.threads)]
    result = subprocess.run(command, cwd=ROOT, env=env)
    summary = out / "summary.json"
    if summary.exists():
        data = json.loads(summary.read_text())
        data["teacher_fuel"] = teacher_fuel
        data["opponent_fuel"] = 100_000
        summary.write_text(json.dumps(data, indent=2) + "\n")
        with (out / "summary.md").open("a") as f:
            f.write(f"\nTeacher fuel: {teacher_fuel}. Opponent fuel: normal (100,000; engine first-turn multipliers).\n")
        if data.get("games") != args.games or data.get("errors") or data.get("oof", {}).get("cand", [0])[0]:
            print("Teacher benchmark failed validation: incomplete games, match errors, or teacher fuel exhaustion", file=sys.stderr)
            return 1
    elif result.returncode == 0:
        print("Teacher benchmark produced no summary", file=sys.stderr)
        return 1
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
