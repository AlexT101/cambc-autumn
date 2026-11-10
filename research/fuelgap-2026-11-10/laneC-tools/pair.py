"""Paired-by-map diff of two ab.py logs (bot 1 = the arm): mean win difference, 95% CI from a bootstrap over maps."""
import re, sys, random, collections
pat = re.compile(r'^\[\s*\d+/\d+\]\s+(\S+)\s+A=(\d)\s+B=(\d):\s+bot (\d) wins')

def read(path):
    out = {}
    for l in open(path):
        m = pat.match(l)
        if m:
            mp, a, b, w = m.groups()
            out[(mp, a)] = 1.0 if w == '1' else 0.0
    return out

x, y = read(sys.argv[1]), read(sys.argv[2])
keys = sorted(set(x) & set(y))
bymap = collections.defaultdict(list)
for k in keys:
    bymap[k[0]].append(x[k] - y[k])
maps = list(bymap)
per = [sum(bymap[m]) for m in maps]
cnt = [len(bymap[m]) for m in maps]
n = sum(cnt)
mean = sum(per) / n
changed = sum(1 for k in keys if x[k] != y[k]) / len(keys)
random.seed(1)
bs = []
for _ in range(2000):
    s = c = 0
    for _ in range(len(maps)):
        i = random.randrange(len(maps))
        s += per[i]; c += cnt[i]
    bs.append(s / c)
bs.sort()
print(f'games {n}  arm {100*sum(x[k] for k in keys)/n:.2f}%  ref {100*sum(y[k] for k in keys)/n:.2f}%  paired diff {100*mean:+.2f} '
      f'(95% {100*bs[50]:+.2f} to {100*bs[1949]:+.2f}, +-{100*(bs[1949]-bs[50])/2:.2f})  results changed {100*changed:.0f}%')
