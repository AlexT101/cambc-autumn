"""lqan.py DIR [--bank 0|1]: the fuel round 7 farm-loop probe (probe.py's LQ/LQE lines) under DIR's bundles.

Loop fuel by stage reached and by exit past prunes(trip). Per exit: the group's cost, its fuel up to prunes(trip)
(pre) and after (post), and the calls' fuel: tab (crew table read), work (crew_work), plan (plan_crew), clear
(clearing estimate), alt (centre_to_altar in too_late), home (home_trip), live (live_steps).
"""
import collections
import glob
import sys
import zipfile

D = sys.argv[1]
bank = int(sys.argv[sys.argv.index("--bank") + 1]) if "--bank" in sys.argv else None
NAMES = ["tab", "work", "plan", "clear", "alt", "home", "live"]
loops = loopfuel = 0
by_stage, n_stage = collections.Counter(), collections.Counter()
acc_all = collections.Counter()
ex = collections.defaultdict(lambda: collections.Counter())
for z in glob.glob(D + "/**/*.repl26a", recursive=True):
    with zipfile.ZipFile(z) as f:
        for n in f.namelist():
            if not n.endswith(".stdout"):
                continue
            for l in f.read(n).replace(b"\0", b"").decode("utf-8", "replace").splitlines():
                x = l.split()
                try:
                    if x[0] == "LQE":
                        if bank is not None and int(x[5]) != bank:
                            continue
                        loops += 1
                        loopfuel += int(x[6])
                    elif x[0] == "LQ":
                        if bank is not None and int(x[4]) != bank:
                            continue
                        st, e = int(x[5]), x[6]
                        cost, pre, post = int(x[7]), int(x[8]), int(x[9])
                        acc = [int(v) for v in x[15:22]]
                    else:
                        continue
                except (IndexError, ValueError):
                    continue
                if x[0] != "LQ":
                    continue
                key = f"{st}" if st < 6 else f"6{e}"
                by_stage[key] += cost
                n_stage[key] += 1
                for i, v in enumerate(acc):
                    acc_all[NAMES[i]] += v
                r = ex[key]
                r["n"] += 1
                r["cost"] += cost
                r["pre"] += pre
                r["post"] += post
                for i, v in enumerate(acc):
                    r[NAMES[i]] += v
                    r[NAMES[i] + "#"] += v > 0
tot = sum(by_stage.values()) or 1
print(f"loops {loops} loop fuel {loopfuel} ({loopfuel / max(1, loops):.0f} a loop); groups' fuel {tot} ({tot / max(1, loopfuel):.0%} of loop)")
print("calls' share of groups' fuel: " + ", ".join(f"{k} {acc_all[k] / tot:.1%}" for k in NAMES))
print("stage/exit: groups, share, per group | pre post | per group: call fuel (share of groups with the call)")
for k in sorted(by_stage):
    r = ex[k]
    n = r["n"] or 1
    calls = " ".join(f"{c} {r[c] / n:.0f}({r[c + '#'] / n:.0%})" for c in NAMES if r[c])
    print(f"  {k:4s} {n_stage[k]:8d} {by_stage[k] / tot:6.1%} {by_stage[k] / n_stage[k]:6.0f} | {r['pre'] / n:5.0f} {r['post'] / n:5.0f} | {calls}")
