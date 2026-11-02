# Paired win-rate difference: two A/B names against the same REF on the same maps and sides.
import json, glob, sys, math, os
def load(name):
    out = {}
    for d in glob.glob(f'replays/batch-*-ab-{name}-*'):
        f = d + '/results.json'
        if not os.path.exists(f): continue
        for m in json.load(open(f))['matches']:
            if m.get('winner') is None: continue
            out[(os.path.basename(m['map']), tuple(m['order']))] = 1.0 if m['winner'] == 0 else 0.0
    return out
a, b = load(sys.argv[1]), load(sys.argv[2])
keys = sorted(set(a) & set(b))
d = [a[k] - b[k] for k in keys]; n = len(d)
mean = sum(d) / n; sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (n - 1)); se = sd / math.sqrt(n)
print(f'{sys.argv[1]}: {100*sum(a[k] for k in keys)/n:.1f}%  {sys.argv[2]}: {100*sum(b[k] for k in keys)/n:.1f}%  on {n} shared games')
print(f'paired {100*mean:+.2f} points ({100*(mean-1.96*se):+.2f}..{100*(mean+1.96*se):+.2f}), z {mean/se if se else 0:.2f}')
