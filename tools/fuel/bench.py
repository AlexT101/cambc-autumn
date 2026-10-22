"""Fuel benchmark: per-turn fuel use, and a behaviour check for fuel optimisations.

With a per-turn budget far above what any turn needs (the default), no fuel gate trips, so a bot's
games are fully determined by its logic: a pure fuel optimisation must leave every replay
byte-identical while the fuel it records drops.

    py tools/fuel/bench.py run hyperion --out replays/fuel/base.json     # bots/ names or paths
    py tools/fuel/bench.py run variants/x --out replays/fuel/x.json
    py tools/fuel/bench.py compare replays/fuel/base.json replays/fuel/x.json

`run` options: --opp (default hecate), --maps (default a small mixed set; ladder names or map paths),
--set wide (26 ladder, maps/gen and maps/gen-s1 maps instead), --test-draft (play a copy of each bot
whose params::test_draft is off with it on, so both draft a top-10 ladder composition by map and side),
--per-map, --fuel (per-turn quantum, default 100000000; 0 for the real 100000), --jobs. Each game's
bundle is kept under --games (default replays/fuel/games/<out stem>/). Fuel used per turn comes from
the bundle's team-<x>.fuel: a 77-byte header, then one little-endian u64 per turn: the draft turns,
then every body's turn of round 1, round 2, ... The `all` summary covers turns from round 2 (round 1
has a double budget; JSONs before 2026-10-22 included it) with turns over 100k. `SHORTCUT` stdout
lines (bots' note_shortcut) are counted too, which matters only with the real budget.
"""
import argparse
import hashlib
import json
import re
import shutil
import statistics
import struct
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAPS = ["00ambush", "00lanes", "01hooks", "00corners", "00contest", "00interlock", "00fragment", "00expanse"]
MAP_SETS = {"wide": [
    "00ambush", "00lanes", "01hooks", "00corners", "00contest", "00interlock", "00fragment", "00expanse", "00swirl",
    "00pilgrimage", "00monolith", "01boss-battle",
    *(f"maps/gen/gen-{m}.map26a" for m in (
        "chambers-102106111", "hourglass-102105800", "huge-shared-102107800", "labyrinth-102106300",
        "classic-102100000", "monolith-heavy-102107600", "city-102106900", "close-spawns-102107300",
        "long-thin-102107200", "caves-102100400", "dense-camps-102108100", "open-field-102107100")),
    "maps/gen-s1/gen-chambers-102206117.map26a", "maps/gen-s1/gen-hourglass-102205812.map26a",
]}
HEADER = 77
BUDGET = 100_000
TEST_DRAFT = re.compile(r"^(\s*(?:inline\s+)?constexpr\s+bool\s+test_draft\s*=\s*)false(\s*;)", re.M)


def bot_path(name):
    p = Path(name)
    if p.exists():
        return p.resolve()
    return (ROOT / "bots" / name).resolve()


def map_key(m):
    """A map's name in results and game directories: a path's stem, so maps/gen/x.map26a is x."""
    return Path(m).stem if m.endswith(".map26a") else m


def with_test_draft(bot):
    """bot itself if its test_draft is on, else a copy under bots/variants/ with it on (no .cambc/;
    unchanged files are left alone so the copy's build stays incremental)."""
    params = (bot / "src" / "params.h").read_text(encoding="utf-8")
    if not TEST_DRAFT.search(params):
        return bot
    target = ROOT / "bots" / "variants" / f"bench-td-{re.sub(r'[^A-Za-z0-9._-]+', '-', bot.name)}"
    files = {}
    for f in bot.rglob("*"):
        rel = f.relative_to(bot)
        if f.is_file() and rel.parts[0] != ".cambc":
            files[rel.as_posix()] = f.read_bytes()
    files["src/params.h"] = TEST_DRAFT.sub(r"\1true\2", params, count=1).encode("utf-8")
    for rel, blob in files.items():
        dest = target / rel
        if not (dest.is_file() and dest.read_bytes() == blob):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(blob)
    for f in sorted(target.rglob("*"), reverse=True):
        rel = f.relative_to(target).as_posix()
        if rel.split("/")[0] == ".cambc":
            continue
        if f.is_file() and rel not in files:
            f.unlink()
        elif f.is_dir() and not any(f.iterdir()):
            f.rmdir()
    return target


def build(bot):
    r = subprocess.run(["cambc", "build", str(bot)], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"build failed for {bot}:\n{r.stdout[-2000:]}{r.stderr[-2000:]}")


def fuel_turns(data):
    return [struct.unpack_from("<Q", data, i)[0] for i in range(HEADER, len(data) - 7, 8)]


def play(bot, opp, map_name, side, fuel, games_dir):
    a, b = (bot, opp) if side == "a" else (opp, bot)
    map_path, map_name = map_name, map_key(map_name)
    out = games_dir / f"{map_name}-{side}"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    cmd = ["cambc", "run", str(a), str(b), "--map", map_path, "-o", str(out)]
    if fuel:
        cmd += ["--fuel", str(fuel)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    bundles = list(out.glob("*.repl26a"))
    if r.returncode != 0 or not bundles:
        return {"map": map_name, "path": map_path, "side": side, "error": (r.stdout + r.stderr)[-1500:]}
    log = r.stdout + r.stderr
    row = next((l for l in log.splitlines() if re.match(rf"\s+{side.upper()}\s", l)), "")
    draft = [d.strip() for d in row.split("  ")[-1].split(",")] if row else []
    bodies = len(draft) + sum(d.startswith("Cassi") for d in draft)
    with zipfile.ZipFile(bundles[0]) as z:
        replay = hashlib.sha256(z.read("replay.repl26a")).hexdigest()
        turns = fuel_turns(z.read(f"team-{side}.fuel"))
        # Concurrent bodies' output can arrive NUL-padded.
        stdout = z.read(f"team-{side}.stdout").decode("utf-8", "replace").replace("\x00", "")
    winner = re.search(r"Team ([AB]) \(", log)
    play_turns = turns[len(draft):]
    shortcuts = {}
    for m in re.finditer(r"SHORTCUT \d+ \d+ ([\w-]+)", stdout):
        shortcuts[m[1]] = shortcuts.get(m[1], 0) + 1
    return {
        "map": map_name, "path": map_path, "side": side, "replay": replay, "winner": winner[1] if winner else None,
        "draft": draft, "picks": len(draft), "bodies": bodies, "draft_fuel": turns[:len(draft)],
        "round1": play_turns[:bodies], "play": play_turns, "shortcuts": shortcuts,
        "out_of_fuel": sum(int(r) > 0 and int(r) <= 2000 and not draft_round(int(r), len(draft)) for r in re.findall(r"r(\d+) turn ran out of fuel", stdout)),
    }


def draft_round(r, picks):
    # A pick ends the draft turn, which main() reports as running out of fuel in rounds 0..picks-1.
    return r < picks


def summary(play_turns):
    if not play_turns:
        return {}
    s = sorted(play_turns)
    q = lambda f: s[min(len(s) - 1, int(f * len(s)))]
    over = sum(t > BUDGET for t in s)
    return {"turns": len(s), "mean": round(statistics.fmean(s)), "p50": q(0.5), "p90": q(0.9), "p99": q(0.99), "max": s[-1],
            "over_100k": over, "over_100k_pct": round(100 * over / len(s), 3)}


def after_round1(g):
    # Round 1 has a double budget, so only later turns can be over 100k.
    return g["play"][g["bodies"]:]


def cmd_run(args):
    bot, opp = bot_path(args.bot), bot_path(args.opp)
    named = bot, opp
    if args.test_draft:
        bot, opp = with_test_draft(bot), with_test_draft(opp)
    maps = MAP_SETS[args.set] if args.set else args.maps
    build(bot)
    build(opp)
    out = Path(args.out)
    games_dir = Path(args.games) if args.games else ROOT / "replays" / "fuel" / "games" / out.stem
    jobs = [(m, s) for m in maps for s in "ab"]
    with ThreadPoolExecutor(args.jobs) as ex:
        games = list(ex.map(lambda j: play(bot, opp, j[0], j[1], args.fuel, games_dir), jobs))
    # Concurrent runs of one bot can race on its build output; such games are replayed one at a time.
    for i, g in enumerate(games):
        for _ in range(2):
            if "error" not in games[i]:
                break
            games[i] = play(bot, opp, g["path"], g["side"], args.fuel, games_dir)
    for g in games:
        if "error" in g:
            print(f"{g['map']}-{g['side']}: ERROR {g['error'][-300:]}")
    ok = [g for g in games if "error" not in g]
    every = [t for g in ok for t in after_round1(g)]
    r1 = [t for g in ok for t in g["round1"]]
    result = {"bot": str(named[0]), "opp": str(named[1]), "played": [str(bot), str(opp)], "test_draft": args.test_draft,
              "fuel": args.fuel, "games": games, "all": summary(every), "round1": summary(r1)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1))
    if args.per_map:
        print(f"{'map':28} {'mean':>6} {'p99':>6} {'max':>7} {'>100k':>6} {'oof':>4}")
        for m in dict.fromkeys(g["map"] for g in ok):
            gs = [g for g in ok if g["map"] == m]
            s = summary([t for g in gs for t in after_round1(g)])
            if s:
                print(f"{m:28} {s['mean']:6} {s['p99']:6} {s['max']:7} {s['over_100k']:6} {sum(g['out_of_fuel'] for g in gs):4}")
    print(f"{len(ok)}/{len(games)} games; play turns after round 1 {result['all']}; round 1 {result['round1']}")
    sc = {}
    for g in ok:
        for k, v in g["shortcuts"].items():
            sc[k] = sc.get(k, 0) + v
    if sc:
        print("shortcuts", dict(sorted(sc.items(), key=lambda x: -x[1])))
    oof = sum(g["out_of_fuel"] for g in ok)
    if oof:
        print("out-of-fuel play turns", oof)


def cmd_compare(args):
    a, b = json.loads(Path(args.a).read_text()), json.loads(Path(args.b).read_text())
    if Path(a["opp"]).name != Path(b["opp"]).name:
        sys.exit(f"different opponents: {a['opp']} vs {b['opp']}")
    key = lambda g: (g["map"], g["side"])
    ga = {key(g): g for g in a["games"] if "error" not in g}
    gb = {key(g): g for g in b["games"] if "error" not in g}
    same, differ = [], []
    for k in sorted(ga.keys() & gb.keys()):
        (same if ga[k]["replay"] == gb[k]["replay"] else differ).append(k)
    print(f"identical replays: {len(same)}/{len(same) + len(differ)}" + (f"; differ: {differ}" if differ else ""))
    for name in ("all", "round1"):
        sa, sb = a[name], b[name]
        if sa and sb:
            print(f"{name:7} " + "  ".join(f"{s} {sa[s]} -> {sb[s]} ({(sb[s] - sa[s]) / max(1, sa[s]):+.1%})" for s in ("mean", "p50", "p90", "p99", "max")))
    # Per-turn comparison is meaningful only where the games are identical.
    if same:
        ta = [t for k in same for t in ga[k]["play"]]
        tb = [t for k in same for t in gb[k]["play"]]
        if len(ta) == len(tb):
            print(f"identical games, total fuel {sum(ta)} -> {sum(tb)} ({(sum(tb) - sum(ta)) / max(1, sum(ta)):+.2%}); "
                  f"turns cheaper {sum(y < x for x, y in zip(ta, tb))}, dearer {sum(y > x for x, y in zip(ta, tb))}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("bot")
    r.add_argument("--opp", default="hecate")
    r.add_argument("--maps", nargs="+", default=DEFAULT_MAPS)
    r.add_argument("--set", choices=sorted(MAP_SETS), help="a named map list instead of --maps")
    r.add_argument("--test-draft", action="store_true")
    r.add_argument("--per-map", action="store_true")
    r.add_argument("--fuel", type=int, default=100_000_000)
    r.add_argument("--jobs", type=int, default=12)
    r.add_argument("--out", required=True)
    r.add_argument("--games")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = p.parse_args()
    {"run": cmd_run, "compare": cmd_compare}[args.cmd](args)


if __name__ == "__main__":
    main()
