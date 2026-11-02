# Calibration tables from l1.jsonl.gz: predicted fight result vs what happened next.
# usage: python3 cal_l1.py [kind]   (kind: stand | fs | chase)
import sys, json, gzip
from collections import defaultdict, Counter
rows = [json.loads(l) for l in gzip.open(sys.argv[2] if len(sys.argv) > 2 else 'replays/v66-analysis/simcal/l1.jsonl.gz', 'rt')]
kind = sys.argv[1] if len(sys.argv) > 1 else 'stand'
rows = [x for x in rows if x['kind'] == kind]
EARLY = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
rows = [x for x in rows if x['r'] <= EARLY]


def died(x, h): return x['death_in'] is not None and x['death_in'] <= h


def pbin(x):
    if x['lost']:
        k = x['tku']
        return 'L tku=' + ('1-2' if k <= 2 else '3-4' if k <= 4 else '5-8' if k <= 8 else '9+')
    k = x['tkt']
    f = 'F' if x['falls'] == '1' else ''
    return 'W%s tkt=' % f + ('?' if k == 0 else '1-2' if k <= 2 else '3-4' if k <= 4 else '5-8' if k <= 8 else '9+')


def taken_rate(x, n):
    return sum(x['taken'][:n]) / n


def table(rs, by, title):
    d = defaultdict(list)
    for x in rs: d[by(x)].append(x)
    print('\n## ' + title)
    print('%-22s %7s %7s %7s %7s %8s %8s %8s' % ('bin', 'n', 'die5', 'die10', 'die17', 'xloss', 'tak/r', 'hp'))
    for k in sorted(d):
        v = d[k]
        n = len(v)
        xl = [x for x in v if 'us_dead15' in x]
        loss = sum(x['us_dead15'] > x['them_dead15'] for x in xl) / max(1, len(xl))
        print('%-22s %7d %7.3f %7.3f %7.3f %7.3f %8.1f %8.0f' % (k, n, sum(died(x, 5) for x in v) / n, sum(died(x, 10) for x in v) / n,
                                                         sum(died(x, 17) for x in v) / n, loss, sum(taken_rate(x, 5) for x in v) / n,
                                                         sum(x['hp'] / x['mh'] for x in v) / n * 100))


if __name__ == '__main__':
    print('kind', kind, 'rows', len(rows))
    table(rows, pbin, 'by predicted bin (all opponents)')
    for o in ['Fish', 'Mite', 'UoS', 'PBG']:
        table([x for x in rows if x['opp'] == o], pbin, 'opp ' + o)
    table([x for x in rows if not x['lost']], lambda x: x['t'], 'predicted not lost, by champion')
    table([x for x in rows if not x['lost']], lambda x: '%d v %d' % (x['al'], x['en']), 'predicted not lost, by sim allies v enemies')
