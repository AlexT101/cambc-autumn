"""Batch exact re-runs of a version's ladder games against opponent puppets, with validation.

    py tools/replay/harness/batch.py [--version vN] [--keys K1,K2 | --keys-file F] [--jobs N]
                                   [--stages gen,build,release,validate,summary] [--force]

Paths below are under the version's directory (versions.py: replays/<version>, release bot ws/bots/<version>-release).

For each game (manifest.json `games`, key `<group8>-<position>`):
  gen       puppet ws/bots/p-<key> from inputs/ladder/<key>.json.gz (files rewritten only when changed)
  build     the release bot, then each puppet in release and debug mode (direct_batch.py plays the debug one)
  release   the release bot --release vs the puppet (cambc run-batch)  -> runs/batch/<key>/release.repl26a
  validate  inputs, round hashes, result and our per-turn fuel vs the ladder -> <key>/validation.json
  summary   runs/batch/validation.json (one row per game) and VALIDATION.md

Idempotent: a run is redone only when its replay is missing, --force is given, or the wasm of either
bot differs from the one recorded in <key>/stamp.json; validation is redone when a run was redone or
its validation.json is missing. Run from anywhere; cambc runs in <dir>/ws.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import versions

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CFG = V = WS = OUT = REL = None


def configure(cfg):
    global CFG, V, WS, OUT, REL
    CFG, V, WS, OUT, REL = cfg, cfg.dir, cfg.ws, cfg.batch, cfg.release


WASM = {"release": ".cambc/build-release/bot-injected.wasm", "debug": ".cambc/build/bot-injected.wasm"}


def games():
    out = {}
    for g in json.loads(CFG.manifest.read_text(encoding="utf-8"))["games"]:
        key = f"{g['group'][:8]}-{g['position']}"
        out[key] = g
    return out


def sha(p):
    p = Path(p)
    return hashlib.sha1(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(cmd, cwd=None, check=True):
    r = subprocess.run(cmd, cwd=cwd or WS, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"{' '.join(map(str, cmd))} failed ({r.returncode}):\n{r.stdout[-3000:]}\n{r.stderr[-3000:]}")
    return r


def puppet_dir(key):
    return WS / "bots" / f"p-{key}"


def opp_team(g):
    return 1 if g["our_side"] == "a" else 0


def stage_gen(keys, G, jobs):
    def one(k):
        r = run(["node", str(HERE / "gen_puppet.mjs"), str(V / "inputs" / "ladder" / f"{k}.json.gz"), str(opp_team(G[k])), str(puppet_dir(k))])
        info = json.loads(r.stdout.strip().splitlines()[-1])
        (OUT / k).mkdir(parents=True, exist_ok=True)
        (OUT / k / "puppet.json").write_text(json.dumps(info))
        return k, info
    changed = 0
    with cf.ThreadPoolExecutor(jobs) as ex:
        for k, info in ex.map(one, keys):
            changed += bool(info.get("changed"))
    log(f"gen: {len(keys)} puppets, {changed} changed")


def stage_build(keys, jobs):
    t0 = time.time()
    run(["cambc", "build", str(REL), "--release"])

    def one(k):
        run(["cambc", "build", str(puppet_dir(k)), "--release"])
        run(["cambc", "build", str(puppet_dir(k))])
        return k
    with cf.ThreadPoolExecutor(jobs) as ex:
        for i, _ in enumerate(ex.map(one, keys), 1):
            if i % 25 == 0 or i == len(keys):
                log(f"build: {i}/{len(keys)} ({time.time() - t0:.0f} s)")
    return time.time() - t0


def stamp_for(k):
    return {"bot": sha(REL / WASM["release"]), "puppet": sha(puppet_dir(k) / WASM["release"])}


def read_stamp(k):
    p = OUT / k / "stamp.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def stage_run(keys, G, jobs, force):
    """The release re-runs. Returns (keys run, seconds)."""
    mode = "release"
    name = f"{mode}.repl26a"
    todo = []
    for k in keys:
        st = read_stamp(k)
        if force or not (OUT / k / name).exists() or st.get(mode) != stamp_for(k):
            todo.append(k)
    if not todo:
        log(f"{mode}: all {len(keys)} up to date")
        return [], 0.0
    bot = REL
    lines = []
    for k in todo:
        g = G[k]
        mp = WS / "maps" / (g["map"].replace("_", "-") + ".map26a")
        a, b = (bot, puppet_dir(k)) if g["our_side"] == "a" else (puppet_dir(k), bot)
        (OUT / k).mkdir(parents=True, exist_ok=True)
        tmp = OUT / k / f"{mode}.tmp.repl26a"
        if tmp.exists():
            tmp.unlink()
        lines.append(f"{a} {b} {mp} {tmp}")
    manifest = OUT / f"_{mode}-manifest.txt"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = ["cambc", "run-batch", str(manifest), "--jobs", str(jobs), "--color", "never", "--release"]
    log(f"{mode}: running {len(todo)} games")
    t0 = time.time()
    r = run(cmd, check=False)
    dt = time.time() - t0
    (OUT / f"_{mode}-run-batch.log").write_text(r.stdout + r.stderr, encoding="utf-8")
    done = []
    for k in todo:
        tmp = OUT / k / f"{mode}.tmp.repl26a"
        if not tmp.exists():
            log(f"{mode}: {k} produced no replay (see _{mode}-run-batch.log)")
            continue
        os.replace(tmp, OUT / k / name)
        st = read_stamp(k)
        st[mode] = stamp_for(k)
        (OUT / k / "stamp.json").write_text(json.dumps(st))
        v = OUT / k / "validation.json"
        if v.exists():
            v.unlink()
        done.append(k)
    log(f"{mode}: {len(done)}/{len(todo)} games in {dt:.0f} s (exit {r.returncode})")
    return done, dt


def stage_validate(keys, G, jobs, force):
    todo = [k for k in keys if force or not (OUT / k / "validation.json").exists()]
    if not todo:
        log("validate: all up to date")
        return 0.0
    rows = []
    for k in todo:
        g = G[k]
        info_p = OUT / k / "puppet.json"
        rows.append({
            "key": k, "inputs": str(V / "inputs" / "ladder" / f"{k}.json.gz"), "ladderFuel": str(ROOT / g["fuel"]),
            "team": 0 if g["our_side"] == "a" else 1,
            "release": str(OUT / k / "release.repl26a"),
            "out": str(OUT / k / "validation.json"),
            "extra": {"map": g["map"], "our_side": g["our_side"], "opponent": g["opponent"], "opp_rank": g["opp_rank"], "kind": g["kind"],
                      "ladder": {"result": g["result"], "rounds": g["rounds"], "our_score": g["our_score"], "opp_score": g["opp_score"]},
                      "puppet": json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else None, "stamp": read_stamp(k)},
        })
    jf = OUT / "_validate-jobs.json"
    jf.write_text(json.dumps(rows))
    t0 = time.time()
    r = subprocess.run(["node", str(HERE / "validate_batch.mjs"), str(jf), "--threads", str(jobs)], cwd=ROOT)
    log(f"validate: {len(todo)} games in {time.time() - t0:.0f} s (exit {r.returncode})")
    return time.time() - t0


def fuel_cell(f):
    if not f:
        return "-"
    if "error" in f:
        return f["error"]
    if not f["diffs"]:
        return "0"
    return f"{f['diffs']}{' (first turns)' if f['firstTurnOnly'] else ''}"


def first_div(r):
    if not r:
        return "not run"
    if r["exact"]:
        return ""
    parts = []
    d = r.get("firstInputDiff")
    if d:
        parts.append(f"input #{d['index']} r{d['round']} actor {d.get('actor')}: {d.get('kind')} vs {d.get('rerunKind')}")
    if r.get("firstRoundDiff"):
        parts.append(f"hash r{r['firstRoundDiff']['round']}")
    if not r["resultMatch"]:
        parts.append("result")
    return "; ".join(parts)


def stage_summary(G):
    rows = []
    for k in G:
        p = OUT / k / "validation.json"
        if not p.exists():
            continue
        v = json.loads(p.read_text(encoding="utf-8"))
        rel = v.get("release")
        row = {
            "key": k, "map": v["map"], "our_side": v["our_side"], "opponent": v["opponent"], "rounds": v["ladder"]["rounds"],
            "score": f"{v['ladder']['our_score']}-{v['ladder']['opp_score']}",
            "opp_rollovers": (v.get("puppet") or {}).get("rollovers"),
            "puppet_errors": (v.get("puppetErrors") or {}).get("count"),
        }
        for name, r in (("release", rel),):
            if not r:
                row[name] = None
                continue
            row[name] = {
                "exact": r["exact"], "exact_ignoring_rollovers": r["exactIgnoringRollovers"],
                "inputs": r["inputs"], "rounds_matched": r["roundsMatched"], "rounds": r["rounds"],
                "first_input_diff": {x: r["firstInputDiff"].get(x) for x in ("index", "round", "step", "actor", "kind", "rerunKind", "original", "rerun")} if r["firstInputDiff"] else None,
                "first_round_diff": r["firstRoundDiff"], "result_match": r["resultMatch"], "result": r["result"][1],
                "fuel_diffs": (r.get("fuel") or {}).get("diffs"), "fuel_first_turn_only": (r.get("fuel") or {}).get("firstTurnOnly"),
                "fuel_diff_turns": [{x: e.get(x) for x in ("index", "what", "round", "id", "turn", "delta", "first", "rollover")} for e in (r.get("fuel") or {}).get("list", [])],
            }
        row["exact"] = bool(rel and rel["exact"])
        rows.append(row)
    (OUT / "validation.json").write_text(json.dumps(rows, indent=1))
    n = len(rows)
    ex = sum(r["exact"] for r in rows)
    rel_f = sum(bool(r["release"] and r["release"]["fuel_diffs"]) for r in rows)
    md = [
        f"# {CFG.name} re-run validation", "",
        "Generated by `tools/replay/harness/batch.py`. Exact = every input of both teams, every round-start snapshot hash and the result",
        "match the ladder game. Fuel = our team's per-turn fuel against the ladder `.fuel` (number of differing turns; \"first turns\"",
        "means only bots' first turns differ).", "",
        f"- Games validated: {n}; release exact: {ex}; release fuel differs in {rel_f} games.", "",
        "| key | map | side | opponent | rounds | score | opp rollovers | release | release fuel | first divergence |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda r: (r["exact"], r["key"])):
        rel = r["release"]
        mark = lambda x: "-" if not x else ("exact" if x["exact"] else f"{x['rounds_matched']}/{x['rounds'][0]} hashes")
        div = first_div({"exact": rel["exact"], "firstInputDiff": rel["first_input_diff"], "firstRoundDiff": rel["first_round_diff"], "resultMatch": rel["result_match"]}) if rel else "not run"
        md.append(f"| {r['key']} | {r['map']} | {r['our_side']} | {r['opponent']} | {r['rounds']} | {r['score']} | {r['opp_rollovers']} | {mark(rel)} | "
                  f"{fuel_cell({'diffs': rel['fuel_diffs'], 'firstTurnOnly': rel['fuel_first_turn_only']}) if rel else '-'} | {div} |")
    (OUT / "VALIDATION.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log(f"summary: {n} games, {ex} release exact; release fuel differs in {rel_f}")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    versions.add_arg(ap)
    ap.add_argument("--keys")
    ap.add_argument("--keys-file")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--stages", default="gen,build,release,validate,summary")
    ap.add_argument("--force", action="store_true", help="redo runs and validation for the selected games")
    args = ap.parse_args()
    configure(versions.get(args.version))
    G = games()
    keys = list(G)
    if args.keys:
        keys = args.keys.split(",")
    elif args.keys_file:
        keys = Path(args.keys_file).read_text(encoding="utf-8").split()
    missing = [k for k in keys if k not in G or not (V / "inputs" / "ladder" / f"{k}.json.gz").exists()]
    if missing:
        sys.exit(f"unknown keys or missing inputs: {missing[:10]}")
    stages = args.stages.split(",")
    OUT.mkdir(parents=True, exist_ok=True)
    times = {}
    t0 = time.time()
    if "gen" in stages:
        stage_gen(keys, G, args.jobs)
        times["gen"] = time.time() - t0
    if "build" in stages:
        times["build"] = stage_build(keys, args.jobs)
    if "release" in stages:
        _, times["release"] = stage_run(keys, G, args.jobs, args.force)
    if "validate" in stages:
        times["validate"] = stage_validate(keys, G, args.jobs, args.force)
    if "summary" in stages:
        stage_summary(G)
    times["total"] = time.time() - t0
    log("times (s): " + ", ".join(f"{k} {v:.0f}" for k, v in times.items()))
    with open(OUT / "_times.jsonl", "a") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "keys": len(keys), "jobs": args.jobs, "times": times}) + "\n")


if __name__ == "__main__":
    main()
