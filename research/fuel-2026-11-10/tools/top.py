import json, collections, os, sys
D = json.load(open(sys.argv[1])); sites = D['sites']; N = int(sys.argv[2]) if len(sys.argv) > 2 else 60
only = sys.argv[3] if len(sys.argv) > 3 else None
tot = sum(c for c, _, _ in sites)
cnt = collections.Counter()
for c, k, fr in sites:
    if fr and (only is None or fr[0][0] == only): cnt[(fr[0][0], fr[0][1], k)] += c
print('total', tot)
for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {key}')
