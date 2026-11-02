# Self-play vs ladder (level 2, r<=260), stand verdicts with an exchange by our champion within 5 rounds: death within 10
# by verdict (ok / ok but our champion falls in the play-out / lost) and sim size (1v1 / multi).
import json, gzip
from collections import defaultdict
for src in ('selfplay', 'ladder'):
    rs = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
    rs = [x for x in rs if x['kind'] == 'stand' and x['r'] <= 260]
    d = defaultdict(list)
    for x in rs:
        s = next(f for f in x['us'] if f['h'] == x['c'])
        if not (sum(s['took'][:5]) > 0 and sum(s['a_any'][:5]) > 0): continue
        v = 'lost' if x['lost'] else ('ok,falls' if x['falls'] else 'ok')
        size = '1v1' if x['n_us'] == 1 and x['n_them'] == 1 else 'multi'
        d[(size, v)].append(x['self_death'] is not None and x['self_death'] <= 10)
    print(src + ': ' + '  '.join('%s/%s %d %.3f' % (k[0], k[1], len(v), sum(v) / len(v)) for k, v in sorted(d.items())))
