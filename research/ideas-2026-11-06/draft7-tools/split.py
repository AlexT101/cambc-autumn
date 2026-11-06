# split.py BATCHDIR [ALTARS.json]: CAND (bot index 0) win % overall, on one-altar maps and the rest, with 95% CIs by map pair.
import json, sys, math, collections
r = json.load(open(f'{sys.argv[1]}/results.json'))
alt = json.load(open(sys.argv[2] if len(sys.argv) > 2 else '/home/ubuntu/tmp-offload/draft7/altars.json'))
import os
by = collections.defaultdict(list)
for m in r['matches']:
    if m.get('winner') is None: continue
    by[os.path.realpath(m['map'])].append(1.0 if m['winner'] == 0 else 0.0)
def stat(keys):
    s = [sum(by[k]) / len(by[k]) for k in keys if by[k]]
    n = sum(len(by[k]) for k in keys)
    if len(s) < 2: return f'{len(s)} maps'
    mu = sum(s) / len(s); sd = math.sqrt(sum((x - mu) ** 2 for x in s) / (len(s) - 1)) / math.sqrt(len(s))
    return f'{100 * mu:.1f}% of {n} ({100 * (mu - 1.96 * sd):.1f}-{100 * (mu + 1.96 * sd):.1f})'
keys = list(by)
missing = [k for k in keys if k not in alt]
one = [k for k in keys if alt.get(k) == 1]; rest = [k for k in keys if alt.get(k, 0) != 1]
print(f'all {stat(keys)}; one-altar {stat(one)} [{len(one)} maps]; multi-altar {stat(rest)}' + (f'; {len(missing)} maps without an altar count' if missing else ''))
