"""Trace v38 ladder games: the instrumented bot (tools/replay/harness/trace-bot) with the tracer
harness (wrappers/harness_trace.h), replaying each game's recorder run against its puppet.

    py tools/replay/harness/trace_batch.py [--keys K1,K2 | --all] [--slots 2] [--level 1] [--rounds R0-R1]
                                         [--batch replays/v38-top20/runs/batch] [--force]

Per game it reads <batch>/<key>/rec.stdout (the recorder's stdout for our team) and rec.repl26a, and
writes <batch>/<key>/trace.stdout.gz (our team's stdout: the trace and the harness lines),
trace.repl26a and trace_validation.json; <batch>/trace_validation.json collects them. A game whose
trace_validation.json is newer than its rec.stdout is skipped unless --force (resumable).

Each slot is a bot directory ws/bots/v38-trace-s<N> kept in sync with the variant, so a new game
rebuilds only its rec_data.cpp. Runs from the ws workspace (cambc 3.0.5) with the puppet
ws/bots/p-<key>, which must be built.

Validation: "exact_vs_rec" means the trace run's inputs (rollovers included), round hashes and result
equal the recorder run's, and there is no host-call mismatch (@! lines, the final unflushed segment's
"tail" excepted); "exact_vs_ladder" compares with the ladder replay's decoded inputs.
"""
import argparse
import gzip
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
V38 = REPO / "replays/v38-top20"
WS = V38 / "ws"
VARIANT = HERE / "trace-bot"
REC_TABLE = WS / "bots/v38-rec/src/zz_harness.json"
CAMBC = shutil.which("cambc") or "cambc"
NODE = shutil.which("node") or "node"

def ensure_workspace():
    """The ws workspace with the cambc_debug_depth SDK patch and the recorder's wrapper table: made or
    completed by setup_ws.py (agent C's, idempotent) when either is missing."""
    sdk = WS / "sdk/cpp/cambc.h"
    if sdk.exists() and "cambc_debug_depth" in sdk.read_text(encoding="utf-8") and REC_TABLE.exists():
        return
    print("workspace not ready: running tools/replay/harness/setup_ws.py", flush=True)
    r = subprocess.run([sys.executable, str(HERE / "setup_ws.py"), "--ws", str(WS)], cwd=REPO)
    if r.returncode != 0 or "cambc_debug_depth" not in sdk.read_text(encoding="utf-8") or not REC_TABLE.exists():
        raise SystemExit("setup_ws.py did not produce the patched SDK and ws/bots/v38-rec/src/zz_harness.json")


def write_if_changed(path, data):
    path = Path(path)
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return True


def sync_slot(slot, zz):
    """The variant's sources, the harness headers and the generated wrappers, rewriting only changed
    files so that the slot's build stays incremental."""
    src = slot / "src"
    src.mkdir(parents=True, exist_ok=True)
    wanted = {"zz_harness.cpp", "rec_data.cpp"}
    for f in sorted((VARIANT / "src").iterdir()):
        if f.is_file():
            write_if_changed(src / f.name, f.read_bytes())
            wanted.add(f.name)
    for f in ("harness_trace.h", "harness_trace_data.h"):
        write_if_changed(src / f, (HERE / "wrappers" / f).read_bytes())
        wanted.add(f)
    write_if_changed(src / "zz_harness.cpp", zz)
    for f in src.iterdir():
        if f.name not in wanted:
            f.unlink()


def games():
    m = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    return {f"{g['group'][:8]}-{g['position']}": g for g in m["games"]}


def run(cmd, cwd=WS, timeout=1800):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def compare(orig, rerun):
    r = run([NODE, str(HERE / "compare.mjs"), str(orig), str(rerun)], cwd=REPO)
    if r.returncode != 0:
        return {"error": (r.stderr or r.stdout)[-500:]}
    d = json.loads(r.stdout)
    return {k: d.get(k) for k in ("exact", "exactIgnoringRollovers", "inputs", "roundsMatched", "rounds", "resultMatch",
                                  "result", "firstInputDiff", "firstRoundDiff")}


def check_stdout(text, rec_text):
    """Harness lines: mismatches by kind, the first one, and the offline @v/@y comparison."""
    seg_round, mism, first, tails = {}, {}, None, 0
    v = {}
    for line in text.splitlines():
        if not line.startswith("@"):
            continue
        p = line.split()
        if p[0] == "@v":
            seg_round[(int(p[1]), int(p[2]))] = int(p[3])
            v[(int(p[1]), int(p[2]))] = tuple(map(int, p[3:6]))
        elif p[0] == "@!":
            kind = p[1]
            if kind == "tail":
                tails += 1
                continue
            mism[kind] = mism.get(kind, 0) + 1
            if first is None:
                first = line
    y = {}
    rec_line = re.compile(r"@y (-?\d+) (\d+) (\d+) (\d+) (\d+)$")
    for line in rec_text.splitlines():
        if "@y" in line and (m := rec_line.search(line)):
            y[(int(m.group(1)), int(m.group(2)))] = tuple(map(int, m.group(3, 4, 5)))
    common = [k for k in v if k in y]
    differ = sorted(k for k in common if v[k] != y[k])
    out = {"segments": len(v), "rec_segments": len(y), "segments_equal": len(common) - len(differ),
           "segments_differ": len(differ), "mismatches": mism, "tail_segments": tails, "first_mismatch": first}
    if differ:
        out["first_segment_differ"] = {"champion": differ[0][0], "segment": differ[0][1], "round": v[differ[0]][0]}
    if (fm := first_mismatch(text)) is not None:
        out["first_mismatch_at"] = {"round": fm[0], "champion": fm[1], "segment": fm[2], "call": fm[3] if fm[3] < 1 << 30 else None}
    return out


def rec_points(rec_text):
    """The recorder's @r points (me, seg, idx, round) and @x points (me, seg, idx)."""
    r, x = [], []
    pat = re.compile(r"@([rx]) (-?\d+) (\d+) (\d+)(?: (\d+))?$")
    for line in rec_text.splitlines():
        if line.startswith("@") and (m := pat.match(line)):
            (r if m.group(1) == "r" else x).append(tuple(int(v) for v in m.groups()[1:] if v is not None))
    return r, x


def first_mismatch(text):
    """The earliest @! line by (round, champion, segment, call), tails excepted, or None."""
    seg_round, best = {}, None
    lines = text.splitlines()
    for line in lines:
        if line.startswith("@v "):
            p = line.split()
            seg_round[(int(p[1]), int(p[2]))] = int(p[3])
    for line in lines:
        if not line.startswith("@! ") or line.startswith("@! tail") or line.startswith("@! inst"):
            continue
        p = line.split()
        me, seg = int(p[2]), int(p[3])
        idx = 1 << 30 if p[1] == "yield" else int(p[4])
        # The round in effect: printed on fuel lines, the new one on round and oof lines, the yield's.
        rnd = int(p[5]) if p[1] in ("fuel", "round", "oof") and len(p) > 5 else int(p[4]) if p[1] == "yield" else seg_round.get((me, seg), 1 << 30)
        k = (rnd, me, seg, idx)
        if best is None or k < best:
            best = k
    return best


def trace_game(key, g, slot, args, lock):
    gdir = Path(args.batch) / key
    rec_stdout, rec_replay = gdir / "rec.stdout", gdir / "rec.repl26a"
    out_json = gdir / "trace_validation.json"
    if not rec_stdout.exists() or not rec_replay.exists():
        return {"key": key, "status": "no-recording"}
    if out_json.exists() and not args.force and out_json.stat().st_mtime > rec_stdout.stat().st_mtime:
        return json.loads(out_json.read_text())
    puppet = WS / "bots" / args.puppet_for.get(key, f"p-{key}")
    if not (puppet / ".cambc/build/bot-injected.wasm").exists():
        return {"key": key, "status": "no-puppet"}
    rec_text = rec_stdout.read_text(encoding="utf-8", errors="replace").replace("\0", "")
    rollovers, loose = rec_points(rec_text)
    t0 = time.time()
    r = run([sys.executable, str(HERE / "trace_data.py"), str(rec_stdout), str(slot / "src/rec_data.cpp"), "--game", key,
             "--level", str(args.level)] + (["--rounds", args.rounds] if args.rounds else []), cwd=REPO)
    if r.returncode != 0:
        return {"key": key, "status": "rec-data-failed", "error": r.stderr[-500:]}
    b = run([CAMBC, "build", str(slot.relative_to(WS))])
    if b.returncode != 0:
        return {"key": key, "status": "build-failed", "error": (b.stderr + b.stdout)[-1500:]}
    t1 = time.time()
    tmp = gdir / f"_trace_{slot.name}"
    shutil.rmtree(tmp, ignore_errors=True)
    ours, theirs = str(slot.relative_to(WS)), str(puppet.relative_to(WS))
    pair = [ours, theirs] if g["our_side"] == "a" else [theirs, ours]
    m = run([CAMBC, "run", *pair, "--map", g["map"].replace("_", "-"), "-o", str(tmp), "--log-limit", str(args.log_limit)])
    replays = list(tmp.glob("*.repl26a"))
    if m.returncode != 0 or not replays:
        return {"key": key, "status": "run-failed", "error": (m.stderr + m.stdout)[-1500:]}
    t2 = time.time()
    trace_replay = gdir / "trace.repl26a"
    shutil.move(str(replays[0]), trace_replay)
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(trace_replay) as z:
        text = z.read(f"team-{g['our_side']}.stdout").replace(b"\0", b"").decode("utf-8", errors="replace")
    with gzip.open(gdir / "trace.stdout.gz", "wt", encoding="utf-8", compresslevel=6) as fh:
        fh.write(text)
    round_of = {(me, seg, idx): rnd for me, seg, idx, rnd in rollovers}
    res = {"key": key, "status": "ok", "map": g["map"], "our_side": g["our_side"], "rounds": g["rounds"],
           "trace_bytes": len(text), "trace_lines": text.count("\n"), "build_s": round(t1 - t0, 1), "run_s": round(t2 - t1, 1),
           "forced_oof": sum(1 for line in text.splitlines() if line.startswith("@o ")), "rec_oof": len(rollovers),
           "rec_x": len(loose), "rec_x_first_round": min((round_of.get(p, 1 << 30) for p in loose), default=None),
           "level": args.level, "window": args.rounds or None}
    res.update(check_stdout(text, rec_text))
    res["vs_rec"] = compare(rec_replay, trace_replay)
    ladder = V38 / "inputs/ladder" / f"{key}.json.gz"
    res["vs_ladder"] = compare(ladder, trace_replay) if ladder.exists() else None
    vr = res["vs_rec"]
    res["exact_vs_rec"] = bool(vr.get("exact")) and not res["mismatches"] and res["segments_differ"] == 0
    res["exact_vs_ladder"] = bool(res["vs_ladder"] and res["vs_ladder"].get("exact"))
    res["exact_vs_ladder_ignoring_rollovers"] = bool(res["vs_ladder"] and res["vs_ladder"].get("exactIgnoringRollovers"))
    # Rounds whose every turn the ladder game shares: the trace explains the ladder through this
    # round, and the recorder's game (with a puppet replaying the ladder blindly) after it.
    if res["exact_vs_ladder_ignoring_rollovers"] or res["exact_vs_ladder"]:
        res["ladder_trusted_through"] = g["rounds"]
    elif res["vs_ladder"]:
        diffs = [x["round"] for x in (res["vs_ladder"].get("firstInputDiff"), res["vs_ladder"].get("firstRoundDiff")) if x]
        res["ladder_trusted_through"] = min(diffs) - 1 if diffs else None
    if not res["exact_vs_rec"]:
        res["rec_trusted_through"] = (res.get("first_mismatch_at") or {}).get("round", 1) - 1
    out_json.write_text(json.dumps(res, indent=1))
    with lock:
        print(f"{key}: rec {'EXACT' if res['exact_vs_rec'] else 'DIFF'} ladder {'EXACT' if res['exact_vs_ladder'] else 'diff'} "
              f"trusted {res.get('ladder_trusted_through')}/{g['rounds']} mism {sum(res['mismatches'].values())} seg {res['segments']} "
              f"oof {res['forced_oof']}/{res['rec_oof']} x {res['rec_x']} {res['trace_bytes'] / 1e6:.1f} MB "
              f"build {res['build_s']}s run {res['run_s']}s", flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--slots", type=int, default=2)
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--rounds", default="")
    ap.add_argument("--batch", default=str(V38 / "runs/batch"))
    ap.add_argument("--log-limit", type=int, default=1 << 30)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--puppet-for", action="append", default=[], help="KEY=BOTDIR: a puppet other than ws/bots/p-KEY")
    args = ap.parse_args()
    args.puppet_for = dict(x.split("=", 1) for x in args.puppet_for)
    all_games = games()
    keys = list(all_games) if args.all else [k for k in args.keys.split(",") if k]
    if not keys:
        raise SystemExit("--keys or --all")
    unknown = [k for k in keys if k not in all_games]
    if unknown:
        raise SystemExit(f"unknown keys {unknown}")
    ensure_workspace()
    zz_path = V38 / "runs/_trace_zz_harness.cpp"
    r = run([sys.executable, str(HERE / "gen_wrappers.py"), "--mode", "trace", "--all", "--sdk", str(WS / "sdk/cpp"),
             "--out", str(zz_path), "--rec-table", str(REC_TABLE)], cwd=REPO)
    if r.returncode != 0:
        raise SystemExit(r.stderr)
    zz = zz_path.read_bytes()
    slots = [WS / "bots" / f"v38-trace-s{i}" for i in range(args.slots)]
    for s in slots:
        sync_slot(s, zz)
    lock = threading.Lock()
    queue = list(keys)
    results = {}

    def worker(slot):
        while True:
            with lock:
                if not queue:
                    return
                key = queue.pop(0)
            try:
                res = trace_game(key, all_games[key], slot, args, lock)
            except Exception as e:  # keep the batch going
                res = {"key": key, "status": "error", "error": repr(e)}
            with lock:
                results[key] = res
                if res.get("status") != "ok":
                    print(f"{key}: {res.get('status')} {res.get('error', '')[:300]}", flush=True)

    threads = [threading.Thread(target=worker, args=(s,)) for s in slots]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    summary_path = Path(args.batch) / "trace_validation.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    summary.update(results)
    summary_path.write_text(json.dumps(dict(sorted(summary.items())), indent=1))
    ok = [r for r in results.values() if r.get("status") == "ok"]
    print(f"{len(ok)}/{len(results)} traced; exact vs rec {sum(r['exact_vs_rec'] for r in ok)}, "
          f"vs ladder {sum(r['exact_vs_ladder'] for r in ok)}; summary {summary_path}")


if __name__ == "__main__":
    main()
