"""pq.py P.json MODE [ARG] [N]: fuel profile queries (sites: [count, kind, frames innermost-first [file, line, fn]]).
  outer        self fuel by real (outermost-frame) function
  inner        self fuel by innermost frame's function
  line FILE    fuel by line of FILE, any inline depth (inclusive over inline frames)
  fn  SUBSTR   lines (any depth) inside frames whose function contains SUBSTR
  kind         by site kind
"""
import json, sys, collections
D = json.load(open(sys.argv[1])); sites = D['sites']; mode = sys.argv[2]
arg = sys.argv[3] if len(sys.argv) > 3 else None
N = int(sys.argv[4]) if len(sys.argv) > 4 else 50
tot = sum(c for c, _, _ in sites); print('total', tot)
cnt = collections.Counter()
for c, k, fr in sites:
    if not fr: cnt['?'] += c; continue
    if mode == 'outer': cnt[fr[-1][2][:110]] += c
    elif mode == 'inner': cnt[fr[0][2][:110]] += c
    elif mode == 'kind': cnt[k] += c
    elif mode == 'line':
        seen = set()
        for f, l, fn in fr:
            if f == arg and l not in seen: seen.add(l); cnt[(l, fn[:70])] += c
    elif mode == 'fn':
        seen = set()
        for f, l, fn in fr:
            if arg in fn and (f, l) not in seen: seen.add((f, l)); cnt[(f, l, fn[:60])] += c
    elif mode == 'outerfn':
        if arg in fr[-1][2]:
            cnt[tuple((f, l) for f, l, fn in fr[::-1][:3])] += c
for key, c in cnt.most_common(N): print(f'{100*c/tot:6.2f}%  {c:>13}  {key}')
if mode in ('top', 'topouter'):
    # self fuel by innermost source line (top) or by the outermost-frame line (topouter), draft and start-up left out
    skip = ('draft/', 'analyse', 'write_index', 'PlanFacts', 'StaticMap::build', 'make_leads', 'decode_steps', 'init_beliefs', 'measure_')
    cnt = collections.Counter(); t2 = 0
    for c, k, fr in sites:
        if not fr or any(s in fr[-1][2] or s in fr[-1][0] for s in skip): continue
        t2 += c
        f, l, fn = fr[0] if mode == 'top' else fr[-1]
        cnt[(f, l, k, fn[:60])] += c
    print('kept', t2)
    for key, c in cnt.most_common(N): print(f'{100*c/t2:6.2f}%  {c:>11}  {key}')
