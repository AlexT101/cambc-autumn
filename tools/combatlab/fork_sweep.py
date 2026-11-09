"""Fork real games and sweep the deciding champion's legal actions: regret of ocean's own choice.

    py tools/combatlab/fork_sweep.py --bot-a variants/lab-cl2 --bot-b variants/lab-cl2 \\
        --maps maps/suites/merged/cl2-dev --games 32 --seed 1 --out DIR [--both-sides] \\
        [--trigger near:6,branch:RC] [--max-forks 8] [--gap 20] [--marks 10,30,60] [--holds 1,3] \\
        [--arms none,sweep] [--jobs 16] [--weights trib=1,gems=0.5,...] [--runner-args "..."]
    py tools/combatlab/fork_sweep.py --analyze DIR [--weights ...]        # re-score DIR/forks.jsonl

Plays each game with `fastrunner forkgame` (src/forkgame.rs; RUNNER.md "Forks of real games"): pass 1 plays it
whole and finds the fork points (triggers on the --bot-a bot's champions); pass 2 replays it and, at each, plays
every arm for max(marks) rounds from the full state (every bot's memory, shared memory, captures, channels...):
`none` (ocean's own turn), and with `sweep` one arm per legal one-turn action of the decider (walk, dash, attack,
cast, end the turn), forced at the start of its decide with ocean playing the rest of that turn and every later one.

Writes DIR/forks.jsonl (the runner's lines: game, fork, arm) and DIR/regret.jsonl, a row per fork and mark: each
arm's value and parts, the best arm, and regret = best value - the `none` arm's value. Values are from the
decider's team, as changes since the fork, own minus enemy:
    trib (tributed gems), gems (carried), wealth (gold + items at shop price), kills and deaths (bodies), work
    (own team's turns spent on a work branch, FPGBTW, with no enemy within 8; lab bots only), self_dead (the
    decider is dead at the mark)
    value = sum(weight * part); default weights below (--weights to change; placeholders, not fitted).
Results are single deterministic continuations: chaotic, so read them across many forks, not one at a time.
"""
import argparse
import json
import os
import random
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools/fastengine/runner"
WEIGHTS = {"trib": 1.0, "gems": 0.5, "wealth": 0.02, "kills": 40.0, "deaths": -40.0, "work": 0.25, "self_dead": -20.0}


def slot_dir():
    r = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, capture_output=True, text=True)
    base = Path(r.stdout.strip()) if r.returncode == 0 else ROOT / ".git"
    return (base if base.is_absolute() else ROOT / base) / "cambc-slots"


def pick_maps(spec, games, seed):
    out = []
    for part in spec.split(","):
        p = Path(part)
        if not p.is_absolute():
            p = ROOT / p
        if p.is_dir():
            out += sorted(str(x) for x in p.glob("*.map26a"))
        elif p.suffix == ".txt":
            out += [l.strip() for l in p.read_text().splitlines() if l.strip()]
        else:
            out.append(str(p))
    if games and games < len(out):
        out = random.Random(seed).sample(out, games)
    return out


def run(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    maps = pick_maps(a.maps, a.games, a.seed)
    lib = a.lib or next((str(p) for p in [RUNNER / "target-lab2/release/libfastrunner.so", RUNNER / "target/release/libfastrunner.so"] if p.exists()), None)
    env = dict(os.environ, FASTRUNNER_ENGINE="wasm", FASTRUNNER_MODE="native")
    if lib:
        env["FASTRUNNER_LIB"] = lib
    with open(out / "games.jsonl", "w") as f:
        for m in maps:
            for swap in ([False, True] if a.both_sides else [False]):
                f.write(json.dumps({"id": f"{Path(m).stem}#{'b' if swap else 'a'}", "map": m, "swap": swap}) + "\n")
    cmd = [str(RUNNER / "fastrunner"), "forkgame", "--bot-a", a.bot_a, "--bot-b", a.bot_b, "--games", str(out / "games.jsonl"),
           "--out", str(out / "forks.jsonl"), "--jobs", str(a.jobs), "--slot-dir", str(slot_dir()),
           "--slots", os.environ.get("CAMBC_SLOTS", "86"), "--trigger", a.trigger, "--max-forks", str(a.max_forks),
           "--gap", str(a.gap), "--marks", a.marks, "--holds", a.holds, "--arms", a.arms, "--seed", str(a.seed)]
    cmd += a.runner_args.split()
    (out / "command.txt").write_text(" ".join(cmd) + "\n")
    print(f"fork_sweep: {len(maps)} maps{' x 2 sides' if a.both_sides else ''} -> {out}/forks.jsonl", file=sys.stderr)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def parts(arm, fork, mark):
    t = arm["team"]
    at = arm["at"].get(str(mark))
    if at is None:
        return None
    own, opp = at["teams"][t], at["teams"][1 - t]
    base = [{"gems": 0, "wealth": 0} for _ in range(2)]
    for c in fork["champions"]:
        base[c["team"]]["gems"] += c["gems"] if c["alive"] else 0
        base[c["team"]]["wealth"] += c["gold"] + c["items"]
    trib0 = fork["trib"]
    me = at["champions"][str(arm["decider"])]
    return {
        "trib": (own["trib"] - trib0[t]) - (opp["trib"] - trib0[1 - t]),
        "gems": (own["gems"] - base[t]["gems"]) - (opp["gems"] - base[1 - t]["gems"]),
        "wealth": (own["gold"] + own["items"] - base[t]["wealth"]) - (opp["gold"] + opp["items"] - base[1 - t]["wealth"]),
        "kills": opp["deaths"],
        "deaths": own["deaths"],
        "work": own["work"],
        "self_dead": 0 if me["alive"] else 1,
    }


def value(p, w):
    return sum(w.get(k, 0.0) * v for k, v in p.items())


def label(l):
    k = l["kind"]
    s = k
    if "x" in l:
        s += f"({l['x']},{l['y']})"
    if "target" in l:
        s += f"->{l['target']}"
    if "slot" in l:
        s += f"/s{l['slot']}"
    if "verdict" in l:
        s += f"={l['verdict']}"
    if l.get("span", 1) != 1:
        s += f"x{l['span']}"
    return s


def analyze(a):
    out = Path(a.out or a.analyze)
    w = dict(WEIGHTS)
    for kv in filter(None, (a.weights or "").split(",")):
        k, v = kv.split("=")
        w[k] = float(v)
    forks, arms, games = {}, defaultdict(list), []
    for line in open(out / "forks.jsonl"):
        d = json.loads(line)
        if d.get("type") == "fork":
            forks[(d["game"], d["fork"])] = d
        elif d.get("type") == "arm":
            arms[(d["game"], d["fork"])].append(d)
        elif d.get("type") == "game":
            games.append(d)
    marks = sorted({int(m) for v in arms.values() for x in v for m in x["at"]})
    rows = []
    for key, fk in forks.items():
        al = arms.get(key, [])
        none = [x for x in al if x["label"]["kind"] == "none"]
        if not none:
            continue
        for mk in marks:
            scored = []
            for x in al:
                p = parts(x, fk, mk)
                if p is not None:
                    scored.append((value(p, w), x, p))
            if not scored:
                continue
            nv = next(v for v, x, _ in scored if x["label"]["kind"] == "none")
            np_ = next(p for _, x, p in scored if x["label"]["kind"] == "none")
            best = max(scored, key=lambda s: s[0])
            rows.append({
                "game": key[0], "fork": key[1], "mark": mk, "round": fk["round"], "decider": fk["decider"], "trigger": fk["trigger"],
                "type": next(c["type"] for c in fk["champions"] if c["id"] == fk["decider"]),
                "ocean": {"value": nv, "parts": np_, "first": none[0].get("first")},
                "best": {"value": best[0], "label": best[1]["label"], "parts": best[2]},
                "regret": best[0] - nv, "arms": len(scored),
                "rank": 1 + sum(1 for v, _, _ in scored if v > nv),
                "values": [[label(x["label"]), round(v, 2)] for v, x, _ in sorted(scored, key=lambda s: -s[0])],
            })
    with open(out / "regret.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    ok = [g for g in games if "error" not in g]
    print(f"{len(games)} games ({len(games) - len(ok)} errors), {len(forks)} forks, {sum(len(v) for v in arms.values())} arms; "
          f"weights {w}")
    bad = [g for g in ok if not g["check"]["main_ok"] or g["check"]["none_arms_differing"]]
    print(f"determinism: main line == pass 1 in {len(ok) - sum(1 for g in ok if not g['check']['main_ok'])}/{len(ok)} games; "
          f"none arms differing from pass 1: {sum(g['check']['none_arms_differing'] for g in ok)}")
    if bad:
        print("  games failing a check:", [g["id"] for g in bad][:10])
    cpu = sum(g.get("cpu_ms", 0) for g in ok) / 1e3
    narms = sum(g.get("arms", 0) for g in ok)
    if cpu:
        print(f"CPU {cpu:.1f} s: {len(forks) / cpu:.2f} forks/s, {narms / cpu:.1f} arms/s a core "
              f"(arms {sum(g.get('arm_cpu_ms', 0) for g in ok) / 1e3:.1f} s, pass 1 {sum(g.get('pass1_cpu_ms', 0) for g in ok) / 1e3:.1f} s)")
    for mk in marks:
        rs = [r for r in rows if r["mark"] == mk]
        if not rs:
            continue
        reg = [r["regret"] for r in rs]
        print(f"mark {mk}: {len(rs)} forks, regret mean {statistics.mean(reg):.1f} median {statistics.median(reg):.1f}, "
              f"ocean best (or tied) in {sum(1 for r in rs if r['regret'] <= 1e-9)}/{len(rs)}, mean rank {statistics.mean(r['rank'] for r in rs):.1f} "
              f"of {statistics.mean(r['arms'] for r in rs):.1f}")
        kinds = Counter(r["best"]["label"]["kind"] for r in rs if r["regret"] > 1e-9)
        print(f"  best arm kinds where ocean lost: {dict(kinds.most_common())}")
        by = defaultdict(list)
        for r in rs:
            for t in r["trigger"]:
                by[t.split(":")[0]].append(r["regret"])
        print("  regret by trigger: " + ", ".join(f"{k} {statistics.mean(v):.1f} (n {len(v)})" for k, v in sorted(by.items())))
        diff = defaultdict(float)
        for r in rs:
            for k in r["ocean"]["parts"]:
                diff[k] += (r["best"]["parts"][k] - r["ocean"]["parts"][k]) / len(rs)
        print("  best - ocean, mean parts: " + ", ".join(f"{k} {v:+.2f}" for k, v in diff.items()))
    print(f"-> {out}/regret.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bot-a", default="variants/lab-cl2")
    ap.add_argument("--bot-b", default="variants/lab-cl2")
    ap.add_argument("--maps", default="maps/suites/merged/cl2-dev")
    ap.add_argument("--games", type=int, default=16, help="maps sampled (0: all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out")
    ap.add_argument("--both-sides", action="store_true")
    ap.add_argument("--trigger", default="near:6,branch:RC")
    ap.add_argument("--max-forks", type=int, default=8)
    ap.add_argument("--gap", type=int, default=20)
    ap.add_argument("--marks", default="10,30,60")
    ap.add_argument("--holds", default="1")
    ap.add_argument("--arms", default="none,sweep")
    ap.add_argument("--jobs", type=int, default=16)
    ap.add_argument("--lib", help="libfastrunner.so (default: target-lab2's, else target's)")
    ap.add_argument("--runner-args", default="", help="more forkgame options, e.g. '--hash --full'")
    ap.add_argument("--weights", help="k=v,...: trib, gems, wealth, kills, deaths, work, self_dead")
    ap.add_argument("--analyze", metavar="DIR", help="only re-score DIR/forks.jsonl")
    a = ap.parse_args()
    if not a.analyze:
        if not a.out:
            ap.error("--out is required")
        run(a)
    analyze(a)


main()
