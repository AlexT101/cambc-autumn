"""Out-of-fuel turns a game of each arm in its fgate runs (the fast runner's counts in each ab.py summary), on the
pool-v3 batches both it and the reference played: py oof.py ARM..."""
import glob, json, re, sys

def runs(arm):
    out = {}
    for f in glob.glob(f"replays/ab/fbe501-{arm}-*-m2560b*-Pv3/summary.json"):
        m = re.search(rf"fbe501-{re.escape(arm)}-(.+)-m2560b(\d+)-Pv3", f)
        x = json.load(open(f))
        out[(m.group(1), m.group(2))] = (x["oof"]["cand"][0], x["games"])
    return out

ref = runs("rc-524")
for arm in sys.argv[1:]:
    a = runs(arm)
    keys = sorted(set(a) & set(ref))
    ct = sum(a[k][0] for k in keys); cg = sum(a[k][1] for k in keys); rt = sum(ref[k][0] for k in keys); rg = sum(ref[k][1] for k in keys)
    print(f"{arm}: {ct / max(1, cg):.2f} out-of-fuel turns a game ({cg:,} games), reference {rt / max(1, rg):.2f} on the same runs")
