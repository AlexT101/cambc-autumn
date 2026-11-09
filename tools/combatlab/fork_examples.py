"""Decode fork examples: replay chosen forks' games with the run's own options plus `forkgame --trace`, then print
per example the champions near the decider and, for ocean's own arm and an alternative, each round's positions and
health over the first rounds, with both arms' per-rep scores.

    py tools/combatlab/fork_examples.py RUN_DIR ROWS.jsonl --pick GAME@FORK@CLASS [--pick ...] [--rounds 10]
        [--lib target-an2's libfastrunner.so] [--key CL]

The rerun is deterministic: the same games, triggers, gap, max-forks and seed give the same forks.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("rows")
    ap.add_argument("--pick", action="append", required=True, help="GAME@FORK@CLASS (the class's first arm)")
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--key", default="CL")
    ap.add_argument("--lib", default=str(ROOT / "tools/fastengine/runner/target-an2/release/libfastrunner.so"))
    ap.add_argument("--work", default=None)
    a = ap.parse_args()
    run = Path(a.run)
    picks = []
    for p in a.pick:
        g, f, c = p.split("@")
        picks.append((g, int(f), c))
    work = Path(a.work or (run / "examples"))
    work.mkdir(exist_ok=True)
    games = [json.loads(l) for l in open(run / "games.jsonl")]
    want = {g for g, _, _ in picks}
    gfile = work / "games.jsonl"
    with open(gfile, "w") as f:
        for g in games:
            if g["id"] in want:
                f.write(json.dumps(g) + "\n")
    out = work / "forks.jsonl"
    cmd = shlex.split((run / "command.txt").read_text())
    i = 0
    new = []
    while i < len(cmd):
        if cmd[i] in ("--games", "--out", "--jobs"):
            i += 2
            continue
        new.append(cmd[i])
        i += 1
    new += ["--games", str(gfile), "--out", str(out), "--jobs", str(min(8, len(want))), "--trace", str(a.rounds + 1)]
    env = dict(os.environ, FASTRUNNER_ENGINE="wasm", FASTRUNNER_MODE="native", FASTRUNNER_LIB=a.lib)
    subprocess.run(new, cwd=ROOT, env=env, check=True, stderr=subprocess.DEVNULL)
    rows = {(r["game"], r["fork"]): r for r in map(json.loads, open(a.rows))}
    forks, arms = {}, {}
    for l in open(out):
        x = json.loads(l)
        if x.get("type") == "fork":
            forks[(x["game"], x["fork"])] = x
        elif x.get("type") == "arm" and x.get("rep", 0) == 0:
            arms[(x["game"], x["fork"], x["arm"])] = x
    for g, fi, cls in picks:
        r = rows[(g, fi)]
        fk = forks[(g, fi)]
        dec = fk["decider"]
        alt = next(x for x in r["arms"] if x["cls"] == cls and not x["same_as_ocean"])
        none = next(x for x in r["arms"] if x["cls"] == "none")
        me = next(c for c in fk["champions"] if c["id"] == dec)
        near = [c for c in fk["champions"] if c["alive"] and c["x"] is not None and max(abs(c["x"] - me["x"]), abs(c["y"] - me["y"])) <= 12]
        s = r["sit"]
        print(f"\n### {g} round {fk['round']} decider {dec} ({s['dtype']}, team {'AB'[fk['team']]}) branch {s['branch']} trigger {fk['trigger']}")
        print(f"map {Path(next(x['map'] for x in games if x['id'] == g)).stem}; home {s['home']} steps, nearest enemy {s['near_type']} at {s['d_enemy']}")
        print("near the decider: " + "; ".join(
            f"{c['id']} {['ryth','vesper','vendetta','cassi','issac','stellar','prism','marcella','willow','ren','varg','tavi','hor'][c['type']]}"
            f"{'*' if c['team'] == fk['team'] else ''} ({c['x']},{c['y']}) {c['hp']:.0f}/{c['max_hp']:.0f} cd{c['cd']} g{c['gems']}" for c in near))
        for name, arm in (("ocean", none), (cls, alt)):
            row = arms[(g, fi, arm["arm"])]
            sc = {mk: [round(v[a.key], 2) if v else None for v in arm["sc"][mk]] for mk in arm["sc"]}
            print(f"  [{name}] label {arm['label']} first {row.get('first', {}).get('to')} hits {row.get('first', {}).get('hits')} "
                  f"branches {row.get('branches')} {a.key} by mark/rep {sc}")
            ids = [c["id"] for c in near]
            for rnd, cs in row.get("trace", [])[: a.rounds + 1]:
                d = {c[0]: c for c in cs}
                print("    r%d " % rnd + " ".join(f"{i}:({d[i][1]},{d[i][2]}){d[i][3]:.0f}" if d[i][4] else f"{i}:dead" for i in ids))


if __name__ == "__main__":
    main()
