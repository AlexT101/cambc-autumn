# plan.cc prices a blow at hit_given_reach = 0.25 (model/safety.h): the chance an enemy within reach hits us before our
# next turn. Realised: enemies the stand sim has striking now (arrives 0) that hit any of ours / a sim participant in the round after the stand turn (round r+1).
import json, gzip
from collections import defaultdict
for src in ('selfplay', 'ladder'):
    rs = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
    rs = [x for x in rs if x['kind'] == 'stand' and x['r'] <= 260]
    d = defaultdict(lambda: [0, 0, 0])
    for x in rs:
        selfh = x['c']
        for f in x['them']:
            if f['arr'] != 0: continue
            for k in (x['opp'], 'all'):
                d[k][0] += 1; d[k][1] += f['a_hits'][1] > 0
                d[k][2] += f['a_part'][1] > 0
    print(src + ': ' + '  '.join('%s n=%d hit-any %.2f hit-participant %.2f' % (k, v[0], v[1] / v[0], v[2] / v[0]) for k, v in sorted(d.items())))
