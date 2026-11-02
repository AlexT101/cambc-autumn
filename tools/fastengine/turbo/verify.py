"""Play the same games with stock cambc and with turbo.so preloaded; check every replay member is byte-identical and
compare CPU time.

    python3 tools/fastengine/turbo/verify.py --turbo /abs/turbo.so --out DIR BOT_A BOT_B
        [--suites ladder,gen,fresh] [--maps N] [--debug] [--jobs 4] [--cpus 2-5] [--chunk 100]
        [--rounds N] [--fuel N] [--env K=V ...]

BOT_A and BOT_B are names under bots/ or paths. Suites are as tools/ab.py's: ladder (maps/*.map26a), gen (maps/gen),
fresh (every maps/gen-s*/), or directories of maps; --maps keeps the first N of each. Every map is played from both
sides with `cambc run-batch` (--release unless --debug: ab.py plays debug builds), stock and turbo alternating by
chunk of --chunk games (in alternating order) so drift cancels, under `taskset -c CPUS`. Run from the repo root.
"""
import argparse
import os
import resource
import subprocess
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import cambc_env  # noqa: E402


def suite_maps(token, limit):
    if token == "ladder":
        dirs = [("ladder", sorted((ROOT / "maps").glob("*.map26a")))]
    elif token == "gen":
        dirs = [("gen", sorted((ROOT / "maps" / "gen").glob("*.map26a")))]
    elif token == "fresh":
        dirs = [(d.name, sorted(d.rglob("*.map26a"))) for d in sorted((ROOT / "maps").glob("gen-s*")) if d.is_dir()]
    else:
        d = Path(token).resolve()
        dirs = [(d.name, sorted(d.rglob("*.map26a")))]
    return [(label, maps[:limit] if limit else maps) for label, maps in dirs]


def bot_path(name):
    p = Path(name)
    return (p if p.is_dir() else ROOT / "bots" / name).resolve()


def workspace(bot):
    for d in [bot, *bot.parents]:
        if (d / "cambc.toml").is_file():
            return d
    return ROOT


def run_batch(games, out, preload, args, cwd, extra_env):
    """Play games [(i, a, b, map)] into out/<i>.repl26a; returns CPU seconds and wall seconds."""
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / f"manifest-{games[0][0]}.txt"
    manifest.write_text("".join(f"{a} {b} {m} {out / f'{i}.repl26a'}\n" for i, a, b, m in games), encoding="utf-8")
    env = cambc_env.env()
    env.update(extra_env)
    if preload:
        env["LD_PRELOAD"] = preload
    cmd = ["taskset", "-c", args.cpus, "cambc", "run-batch", str(manifest), "--jobs", str(args.jobs), "--color", "never"]
    if not args.debug:
        cmd.append("--release")
    if args.rounds:
        cmd += ["--rounds", str(args.rounds)]
    if args.fuel:
        cmd += ["--fuel-quantum", str(args.fuel)]
    c0 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.time()
    r = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    wall = time.time() - t0
    c1 = resource.getrusage(resource.RUSAGE_CHILDREN)
    (out / f"run-{games[0][0]}.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    return (c1.ru_utime + c1.ru_stime) - (c0.ru_utime + c0.ru_stime), wall


def members(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bot_a")
    ap.add_argument("bot_b")
    ap.add_argument("--turbo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--suites", default="ladder")
    ap.add_argument("--maps", type=int, default=0, help="First N maps of each suite (default: all)")
    ap.add_argument("--debug", action="store_true", help="Debug builds, as tools/ab.py plays (default: --release)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--cpus", default="2-5")
    ap.add_argument("--chunk", type=int, default=100)
    ap.add_argument("--rounds", type=int)
    ap.add_argument("--fuel", type=int)
    ap.add_argument("--env", action="append", default=[], help="K=V for the turbo runs (e.g. TURBO_CHECK=1)")
    args = ap.parse_args()
    os.environ.pop("CAMBC_TURBO", None)  # stock must be stock
    a, b = bot_path(args.bot_a), bot_path(args.bot_b)
    cwd = workspace(a)
    turbo_env = dict(kv.split("=", 1) for kv in args.env)
    games = [(label, x, y, m) for token in args.suites.split(",") for label, maps in suite_maps(token, args.maps)
             for m in maps for x, y in ((a, b), (b, a))]
    out = Path(args.out).resolve()
    preload = os.path.abspath(args.turbo)
    cpu = {"stock": 0.0, "turbo": 0.0}
    wall = {"stock": 0.0, "turbo": 0.0}
    indexed = list(enumerate(games))
    for c in range(0, len(indexed), args.chunk):
        chunk = indexed[c:c + args.chunk]
        for mode in ("stock", "turbo") if (c // args.chunk) % 2 == 0 else ("turbo", "stock"):
            ce, we = run_batch([(i, g[1], g[2], g[3]) for i, g in chunk], out / mode, preload if mode == "turbo" else None,
                               args, cwd, turbo_env if mode == "turbo" else {})
            cpu[mode] += ce
            wall[mode] += we
        print(f"  {min(c + args.chunk, len(games))}/{len(games)} games", file=sys.stderr, flush=True)
    same, total, whole = Counter(), Counter(), Counter()
    for i, (label, x, y, m) in indexed:
        total[label] += 1
        rs, rt = out / "stock" / f"{i}.repl26a", out / "turbo" / f"{i}.repl26a"
        if not rs.is_file() or not rt.is_file():
            print(f"MISSING {x.name} vs {y.name} on {m.name}: stock {rs.is_file()} turbo {rt.is_file()}")
            continue
        ms, mt = members(rs), members(rt)
        if ms == mt:
            same[label] += 1
            whole[label] += rs.read_bytes() == rt.read_bytes()
        else:
            diff = [n for n in sorted(set(ms) | set(mt)) if ms.get(n) != mt.get(n)]
            print(f"DIFFERENT {x.name} vs {y.name} on {m.name} (game {i}): {diff}")
    for label in total:
        print(f"{label}: {same[label]}/{total[label]} games byte-identical in every replay member "
              f"({whole[label]} whole replay files identical)")
    n = len(games)
    print(f"all: {sum(same.values())}/{n} identical")
    for mode in ("stock", "turbo"):
        print(f"{mode}: {cpu[mode]:.1f} CPU-s ({cpu[mode] / n:.3f}/game), wall {wall[mode]:.1f} s "
              f"({args.jobs} jobs on CPUs {args.cpus})")
    print(f"speedup: CPU {cpu['stock'] / cpu['turbo']:.2f}x, wall {wall['stock'] / wall['turbo']:.2f}x")


if __name__ == "__main__":
    main()
