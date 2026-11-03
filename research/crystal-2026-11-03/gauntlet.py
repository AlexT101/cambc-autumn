"""Candidate vs reference against a panel of opponents: each plays every opponent on the same maps, both sides, and the
difference is paired by map and side.

    python3 research/crystal-2026-11-03/gauntlet.py run CAND REF OPP... [--suites S] [--tag T]   # plays what is missing
    python3 research/crystal-2026-11-03/gauntlet.py report CAND REF OPP... [--tag T]

Bots are directories under bots/ (variants/x, baselines/v67, hyperion). Runs go through tools/ab.py (own drafts,
fastrunner native) as replays/ab/gl-<tag>-<bot>-vs-<opp>/, reused when present, so a reference is played once per panel.
The report gives each side's win % per opponent and CAND - REF with a bootstrap 95% CI over map pairs, then the mean
over opponents (each weighted equally).
"""
import argparse, json, os, random, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_name(tag, bot, opp):
    return f"gl-{tag}-{bot.replace('/', '-')}-vs-{opp.replace('/', '-')}"


def games(name):
    s = json.loads((ROOT / "replays" / "ab" / name / "summary.json").read_text())
    out = {}
    for su in s["suites"]:
        r = json.loads((ROOT / su["batch"] / "results.json").read_text())
        for m in r["matches"]:
            if m.get("winner") is None:
                continue
            # order [0, 1]: bot 0 (the first ab.py argument) is team A; winner is the bot index.
            out[(su["suite"], Path(m["map"]).name, tuple(m["order"]))] = 1.0 if m["winner"] == 0 else 0.0
    return out


def boot(d, n=2000, seed=1):
    rng = random.Random(seed)
    k = len(d)
    ms = sorted(sum(d[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run", "report"])
    ap.add_argument("cand")
    ap.add_argument("ref")
    ap.add_argument("opps", nargs="+")
    ap.add_argument("--suites", default="ladder,gen,fresh")
    ap.add_argument("--tag", default="p1")
    a = ap.parse_args()
    if a.cmd == "run":
        env = dict(os.environ, CAMBC_BIN=str(ROOT / "tools/fastengine/runner/fastrunner"), FASTRUNNER_MODE="native")
        for opp in a.opps:
            for bot in (a.ref, a.cand):
                name = run_name(a.tag, bot, opp)
                if (ROOT / "replays" / "ab" / name / "summary.json").exists():
                    continue
                print(f"=== {bot} vs {opp}", flush=True)
                subprocess.run([sys.executable, "tools/ab.py", bot, opp, "--no-test-draft", "--suites", a.suites, "--name", name],
                               cwd=ROOT, env=env, stdout=subprocess.DEVNULL, check=False)
    rows, means = [], []
    for opp in a.opps:
        try:
            c, r = games(run_name(a.tag, a.cand, opp)), games(run_name(a.tag, a.ref, opp))
        except FileNotFoundError:
            print(f"{opp}: missing")
            continue
        keys = [k for k in c if k in r]
        d = [c[k] - r[k] for k in keys]
        lo, hi = boot(d)
        cw, rw = sum(c[k] for k in keys) / len(keys), sum(r[k] for k in keys) / len(keys)
        means.append(cw - rw)
        rows.append(f"| {opp} | {len(keys)} | {100 * rw:.1f} | {100 * cw:.1f} | {100 * (cw - rw):+.1f} [{100 * lo:+.1f}, {100 * hi:+.1f}] |")
    print(f"{a.cand} vs {a.ref}, tag {a.tag}")
    print("| Opponent | Games | REF win % | CAND win % | CAND - REF [95% CI] |\n|---|---|---|---|---|")
    print("\n".join(rows))
    if means:
        print(f"Mean over {len(means)} opponents: {100 * sum(means) / len(means):+.2f} points")


if __name__ == "__main__":
    main()
