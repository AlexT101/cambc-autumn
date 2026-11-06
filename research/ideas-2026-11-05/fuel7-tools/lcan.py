"""lcan.py DIR: probe3.py's call counters (the last LC line per champion and bundle), summed."""
import glob
import sys
import zipfile

NAMES = ["work_arrival", "  its misses", "plan_crew", "  price", "    min_camp_damage", "    share_damage", "crew_available_bits",
         "crew_allies", "crew_bound pass", "crew_work", "prey", "  preyable", "  chase_trade", "step_guard", "  new_fight", "  exposure"]
tot = [[0, 0] for _ in NAMES]
for z in glob.glob(sys.argv[1] + "/**/*.repl26a", recursive=True):
    with zipfile.ZipFile(z) as f:
        for n in f.namelist():
            if not n.endswith(".stdout"):
                continue
            last = {}
            for l in f.read(n).replace(b"\0", b"").decode("utf-8", "replace").splitlines():
                if l.startswith("LC "):
                    x = l.split()
                    last[x[2]] = x
            for x in last.values():
                v = [int(a) for a in x[3:]]
                for i in range(len(NAMES)):
                    tot[i][0] += v[2 * i]
                    tot[i][1] += v[2 * i + 1]
for name, (c, fu) in zip(NAMES, tot):
    print(f"{name:22s} calls {c:9d} fuel {fu:12d} per call {fu / max(1, c):7.0f}")
