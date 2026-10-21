"""Full A/B of two bots through run_batched.py: ladder, generated and fresh-seed maps, both sides.

    py tools/ab.py orch/my-branch main --name my-change
    py tools/ab.py HEAD hecate
    py tools/ab.py main HEAD~1 --no-test-draft --suites ladder,gen

CAND and REF are each a git ref (branch, sha, main), whose bots/hyperion (bots/hecate before the
2026-10-21 rename) is materialised with git archive into bots/variants/ab-<name>-<cand|ref>-<sha7>/
with params::test_draft switched on, or a bot directory under bots/ (hecate) used as it is. Wins are CAND's.
Suites: ladder (maps/), gen (maps/gen), fresh (every maps/gen-s*/), or any directory of maps."""

import argparse
from datetime import datetime
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import tarfile
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "fuel"))
import oof  # noqa: E402

VARIANTS = ROOT / "bots" / "variants"
TEST_DRAFT = re.compile(r"^(\s*(?:inline\s+)?constexpr\s+bool\s+test_draft\s*=\s*)(false|true)(\s*;)", re.M)


def git(*args, binary=False):
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=not binary)
    return done.stdout if done.returncode == 0 else None


def slug(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "x"


def resolve(spec):
    for path in (ROOT / "bots" / spec, Path(spec)):
        if (path / "src").is_dir():
            return {"spec": spec, "kind": "dir", "path": path.resolve()}
    sha = git("rev-parse", "--verify", "--quiet", f"{spec}^{{commit}}")
    if not sha:
        raise ValueError(f"{spec!r} is neither a bot directory under bots/ nor a git ref")
    return {"spec": spec, "kind": "git", "sha": sha.strip()}


def write_if_changed(path, data):
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def materialise(side, role, name, test_draft):
    """Write the bot at side's commit into a variant directory, rewriting only changed files
    so its build cache stays incremental."""
    sha = side["sha"]
    # bots/hecate was the worked-on bot until it was renamed hyperion; since then it is the pre-rename reference.
    for bot in ("bots/hyperion", "bots/hecate"):
        data = git("archive", "--format=tar", f"{sha}:{bot}", binary=True)
        if data:
            break
    else:
        raise ValueError(f"git archive found neither bots/hyperion nor bots/hecate at {side['spec']} ({sha[:7]})")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            rel = Path(member.name).as_posix()
            if member.isfile() and rel.split("/")[0] != ".cambc":
                files[rel] = tar.extractfile(member).read()
    if test_draft:
        text = files.get("src/params.h", b"").decode("utf-8")
        found = TEST_DRAFT.findall(text)
        if len(found) != 1:
            raise ValueError(f"{bot}/src/params.h at {side['spec']} ({sha[:7]}) needs exactly one "
                             f"'constexpr bool test_draft = false;' line (found {len(found)}); "
                             "pass --no-test-draft to use it unchanged")
        files["src/params.h"] = TEST_DRAFT.sub(r"\1true\3", text).encode("utf-8")
    target = VARIANTS / f"ab-{name}-{role}-{sha[:7]}"
    for rel, blob in files.items():
        write_if_changed(target / rel, blob)
    for path in sorted(target.rglob("*"), reverse=True):
        rel = path.relative_to(target).as_posix()
        if rel.split("/")[0] in (".cambc", "ab.json"):
            continue
        if path.is_file() and rel not in files:
            path.unlink()
        elif path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    write_if_changed(target / "ab.json", (json.dumps(
        {"spec": side["spec"], "sha": sha, "test_draft": test_draft}, indent=2) + "\n").encode("utf-8"))
    return target


def suites(tokens):
    """[(label, run_batched args)] plus notes on suites that have no maps."""
    out, notes = [], []
    for token in tokens:
        if token == "ladder":
            out.append(("ladder", []))
        elif token == "gen":
            out.append(("gen", ["--gen"]))
        elif token == "fresh":
            dirs = sorted(d for d in (ROOT / "maps").glob("gen-s*") if d.is_dir())
            out += [(f"fresh/{d.name}", ["--maps-dir", str(d)]) for d in dirs]
            if not dirs:
                notes.append("fresh: no maps/gen-s*/ directories, skipped")
        elif Path(token).is_dir():
            out.append((Path(token).resolve().name, ["--maps-dir", str(Path(token).resolve())]))
        else:
            raise ValueError(f"Unknown suite {token!r}: use ladder, gen, fresh or a directory of maps")
    return out, notes


def wilson(wins, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return 100 * (c - h), 100 * (c + h)


def rate(wins, n):
    lo, hi = wilson(wins, n)
    pct = f"{100 * wins / n:.1f}%" if n else "-"
    return f"{pct} of {n} ({wins}-{n - wins}), 95% CI {lo:.1f}-{hi:.1f}"


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


def describe(side):
    return f"{side['spec']} ({side['sha'][:7]})" if side["kind"] == "git" else f"{side['spec']} (dir)"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("cand", help="Candidate: git ref, or bot directory under bots/")
    parser.add_argument("ref", help="Reference: git ref, or bot directory under bots/")
    parser.add_argument("--name", help="Run name (default: <cand>-vs-<ref>); results in replays/ab/<name>/")
    parser.add_argument("--threads", type=int, default=22, help="Concurrent matches (default: 22)")
    parser.add_argument("--suites", default="ladder,gen,fresh",
                        help="Comma-separated: ladder, gen, fresh, or directories of maps (default: all three)")
    parser.add_argument("--no-test-draft", action="store_true",
                        help="Leave materialised copies' params.h untouched, so each plays its own draft")
    parser.add_argument("--fuel", type=int, help="Fuel per turn, passed to run_batched.py --fuel")
    args = parser.parse_args()
    started = perf_counter()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        sides = [resolve(args.cand), resolve(args.ref)]
        name = slug(args.name or f"{args.cand}-vs-{args.ref}")
        plan, notes = suites([t.strip() for t in args.suites.split(",") if t.strip()])
        if not plan:
            raise ValueError("No suites to play")
        for side, role in zip(sides, ("cand", "ref")):
            if side["kind"] == "git":
                side["path"] = materialise(side, role, name, not args.no_test_draft)
                side["test_draft"] = not args.no_test_draft
    except (ValueError, OSError) as error:
        parser.error(str(error))
    out_dir = ROOT / "replays" / "ab" / name
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"A/B {name}: CAND {describe(sides[0])} vs REF {describe(sides[1])}", flush=True)

    results = []
    for label, extra in plan:
        batch = ROOT / "replays" / f"batch-{stamp}-ab-{name}-{slug(label)}"
        log = out_dir / f"{slug(label)}.log"
        command = [sys.executable, str(ROOT / "run_batched.py"), str(sides[0]["path"]), str(sides[1]["path"]),
                   "--threads", str(args.threads), "--output", str(batch), *extra]
        if args.fuel is not None:
            command += ["--fuel", str(args.fuel)]
        print(f"  {label}: running, log {rel(log)}", flush=True)
        with log.open("w", encoding="utf-8") as stream:
            code = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT).returncode
        entry = {"suite": label, "batch": rel(batch), "log": rel(log), "exit": code,
                 "games": 0, "wins": 0, "errors": 0, "failed": [], "oof": None}
        try:
            report = json.loads((batch / "results.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            entry["failed"].append({"map": None, "error": f"run_batched exit {code}, no results; see {rel(log)}"})
            entry["errors"] = 1
            results.append(entry)
            continue
        entry["errors"] = report["errors"]
        entry["games"] = report["completed"] - report["errors"]
        entry["wins"] = report["wins"][0]
        entry["failed"] = [{"map": Path(m["map"]).name, "cand_side": "AB"[m["order"].index(0)],
                            "error": m["error"]} for m in report["matches"] if "error" in m]
        if code and not entry["errors"]:
            entry["errors"] = 1
            entry["failed"].append({"map": None, "error": f"run_batched exit {code}; see {rel(log)}"})
        try:
            _, turns, games, _, _ = oof.count(batch)
            entry["oof"] = {"cand": [turns[1], games[1]], "ref": [turns[2], games[2]]}
        except (OSError, KeyError, ValueError) as error:
            entry["oof_error"] = str(error)
        results.append(entry)

    wall = perf_counter() - started
    games = sum(r["games"] for r in results)
    wins = sum(r["wins"] for r in results)
    errors = sum(r["errors"] for r in results)
    oof_total = {k: [sum(r["oof"][k][i] for r in results if r["oof"]) for i in (0, 1)] for k in ("cand", "ref")}
    lo, hi = wilson(wins, games)
    summary = {
        "name": name, "started": stamp, "wall_seconds": round(wall, 1), "threads": args.threads,
        "fuel": args.fuel, "cand": {**sides[0], "path": rel(sides[0]["path"])},
        "ref": {**sides[1], "path": rel(sides[1]["path"])}, "games": games, "cand_wins": wins,
        "cand_win_pct": round(100 * wins / games, 2) if games else None, "ci95": [round(lo, 2), round(hi, 2)],
        "errors": errors, "oof": oof_total, "notes": notes, "suites": results,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    width = max(len(r["suite"]) for r in results)
    lines = [f"CAND {rate(wins, games)}"]
    lines += [f"  {r['suite']:<{width}}  {rate(r['wins'], r['games'])}" + (f", {r['errors']} failed" if r["errors"] else "")
              for r in results]
    lines += notes
    failed = [(r["suite"], f) for r in results for f in r["failed"]]
    lines.append(f"Failed matches: {len(failed)}")
    lines += [f"  {s} {f['map'] or ''} {('CAND=' + f['cand_side']) if f.get('cand_side') else ''}: {f['error']}"
              for s, f in failed[:5]]
    if len(failed) > 5:
        lines.append(f"  ... {len(failed) - 5} more in summary.json")
    lines.append(f"Out-of-fuel turns: CAND {oof_total['cand'][0]} in {oof_total['cand'][1]} games, "
                 f"REF {oof_total['ref'][0]} in {oof_total['ref'][1]} games")
    lines.append(f"Wall time: {int(wall // 60)}m{int(wall % 60):02d}s")
    lines.append(f"Results: {rel(out_dir)}/summary.md")
    print("\n".join(lines))

    md = [f"# A/B {name}", "", f"CAND {describe(sides[0])}, `{rel(sides[0]['path'])}`",
          f"REF {describe(sides[1])}, `{rel(sides[1]['path'])}`", "",
          f"Started {stamp}; threads {args.threads}; fuel {args.fuel or 'default'}; "
          f"wall {wall / 60:.1f} min", "",
          "| Suite | CAND win % | Games | 95% CI | Failed | OOF CAND | OOF REF | Batch |", "|---|---|---|---|---|---|---|---|"]
    for r in results + [{"suite": "**total**", "games": games, "wins": wins, "errors": errors,
                         "oof": oof_total, "batch": ""}]:
        a, b = wilson(r["wins"], r["games"])
        pct = f"{100 * r['wins'] / r['games']:.1f}" if r["games"] else "-"
        o = r["oof"] or {"cand": ["?", "?"], "ref": ["?", "?"]}
        md.append(f"| {r['suite']} | {pct} | {r['games']} | {a:.1f}-{b:.1f} | {r['errors']} | "
                  f"{o['cand'][0]} | {o['ref'][0]} | {('`' + r['batch'] + '`') if r['batch'] else ''} |")
    md += [""] + [f"- {n}" for n in notes]
    if failed:
        md += ["", "Failed matches:"] + [f"- {s} {f['map'] or ''}: {f['error']}" for s, f in failed]
    (out_dir / "summary.md").write_text("\n".join(md).rstrip() + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
