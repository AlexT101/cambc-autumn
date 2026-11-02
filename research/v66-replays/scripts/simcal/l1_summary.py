# All 609 traced games (level 1, trusted rounds, r<=260): stand verdicts with an enemy and an exchange within 5 rounds
# (our champion both took and dealt champion damage), by opponent and by our champion type: death within 10 rounds.
import json, gzip
from collections import defaultdict
rows = [json.loads(l) for l in gzip.open('replays/v66-analysis/simcal/l1.jsonl.gz', 'rt')]
rows = [x for x in rows if x['kind'] == 'stand' and x['r'] <= 260 and sum(x['taken'][:5]) > 0 and sum(x['dealt'][:5]) > 0]
def v(x): return 'lost' if x['lost'] else ('ok,falls' if x['falls'] == '1' else 'ok')
def d10(x): return x['death_in'] is not None and x['death_in'] <= 10
def tab(key, title):
    d = defaultdict(lambda: defaultdict(list))
    for x in rows: d[key(x)][v(x)].append(x)
    print('\n## ' + title)
    print('  %-10s %18s %18s %18s   ok share' % ('', 'ok n/die10', 'ok,falls n/die10', 'lost n/die10'))
    for k in sorted(d):
        c = d[k]; tot = sum(len(z) for z in c.values())
        cells = ['%7d %6.3f' % (len(c[vv]), sum(map(d10, c[vv])) / max(1, len(c[vv]))) for vv in ('ok', 'ok,falls', 'lost')]
        print('  %-10s %18s %18s %18s   %.2f' % (k, *cells, len(c['ok']) / tot))
tab(lambda x: x['opp'], 'by opponent')
tab(lambda x: x['t'], 'by our champion')
tab(lambda x: x['opp'] + '/' + ('1v1' if x['al'] == 1 and x['en'] == 1 else 'multi'), 'by opponent and sim size')
