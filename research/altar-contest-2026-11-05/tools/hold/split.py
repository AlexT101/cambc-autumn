import json, glob, math, os, collections, sys
Z = json.load(open(sys.argv[1]))
rows = []
for f in glob.glob(sys.argv[2]):
    for m in json.load(open(f))['matches']:
        rows.append((Z[os.path.basename(m['map'])], m['winner'] == 0, m))
print('total', len(rows), 'cand wins', sum(w for _, w, _ in rows))
def ci(w, n):
    p = w / n; z = 1.96; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{100*p:.1f}% of {n} (95% CI {100*(c-h):.1f}-{100*(c+h):.1f})"
groups = collections.defaultdict(list)
for z, w, m in rows:
    groups['one-zone' if z['zones'] == 1 else 'multi-zone'].append(w)
    groups['one-altar' if z['altars'] == 1 else ('one-zone, 2+ altars' if z['zones'] == 1 else 'multi')].append(w)
    groups[f"zones={min(z['zones'],4)}"].append(w)
for k in sorted(groups): print(f"  {k:22s} {ci(sum(groups[k]), len(groups[k]))}")
