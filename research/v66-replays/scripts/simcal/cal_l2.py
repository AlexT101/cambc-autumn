# Reliability and damage-rate calibration of the fight sims in l2_<src>.jsonl.gz.
# usage: cal_l2.py selfplay|ladder [stand|chase|all] [max_round]
import sys, json, gzip
from collections import defaultdict
src = sys.argv[1]; kind = sys.argv[2] if len(sys.argv) > 2 else 'all'; RMAX = int(sys.argv[3]) if len(sys.argv) > 3 else 1 << 30
rows = [json.loads(l) for l in gzip.open(f'replays/v66-analysis/simcal/l2_{src}.jsonl.gz', 'rt')]
rows = [x for x in rows if (kind == 'all' or x['kind'] == kind) and x['r'] <= RMAX]
K = 5  # rounds compared with the sim's first K turns


def died(d, h): return d is not None and d <= h


def xloss(x, h=10):
    ud = sum(died(f['death'], h) for f in x['us']); td = sum(died(f['death'], h) for f in x['them'])
    return ud > td


def engaged(x):
    a = sum(sum(f['a_part'][:K]) for f in x['us']); b = sum(sum(f['a_part'][:K]) for f in x['them'])
    return a > 0 and b > 0


def mbin(m):
    for lo, name in ((0.6, '+0.6..1'), (0.3, '+0.3..0.6'), (0.1, '+0.1..0.3'), (0.0, '+0..0.1'), (-0.1, '-0.1..0'), (-0.3, '-0.3..-0.1'), (-0.6, '-0.6..-0.3')):
        if m > lo or (lo == 0.0 and m == 0): return name
    return '-1..-0.6'


ORDER = ['+0.6..1', '+0.3..0.6', '+0.1..0.3', '+0..0.1', '-0.1..0', '-0.3..-0.1', '-0.6..-0.3', '-1..-0.6']


def rel(rs, title):
    d = defaultdict(list)
    for x in rs: d[mbin(x['margin'])].append(x)
    print('\n## ' + title + '  (n=%d)' % len(rs))
    print('%-11s %6s %7s %7s %7s %7s %7s' % ('margin', 'n', 'p_lost', 'die10', 'xloss10', 'engag', 'kill10'))
    for k in ORDER:
        v = d.get(k, [])
        if not v: continue
        n = len(v)
        print('%-11s %6d %7.2f %7.3f %7.3f %7.2f %7.3f' % (k, n, sum(x['lost'] for x in v) / n, sum(died(x['self_death'], 10) for x in v) / n,
                                                  sum(xloss(x) for x in v) / n, sum(engaged(x) for x in v) / n,
                                                  sum(any(died(f['death'], 10) for f in x['them']) for x in v) / n))


def rates(rs, title):
    rs = [x for x in rs if engaged(x)]
    P = defaultdict(float); A = defaultdict(float)
    for x in rs:
        for side in ('us', 'them'):
            P[side] += sum(f['pd'] * f['pacts'] for f in x[side]) / 5
            A[side] += sum(sum(f['a_part'][:K]) for f in x[side]) / K
            A[side + '_any'] += sum(sum(f['a_any'][:K]) for f in x[side]) / K
        A['extra'] += sum(sum(e['dmg'][:K]) for e in x['extra']) / K
    if not rs: return
    print('\n## damage per round, engaged sims: ' + title + ' (n=%d)' % len(rs))
    print('  them->us: predicted %.1f  actual(on participants) %.1f  ratio %.2f  (+ outsiders %.1f -> %.2f)' % (
        P['them'] / len(rs), A['them'] / len(rs), A['them'] / P['them'], A['extra'] / len(rs), (A['them'] + A['extra']) / P['them']))
    print('  us->them: predicted %.1f  actual(on participants) %.1f  ratio %.2f  (on anyone %.2f)' % (
        P['us'] / len(rs), A['us'] / len(rs), A['us'] / P['us'], A['us_any'] / P['us']))
    print('  overrating index (them ratio / our ratio): %.2f; with outsiders %.2f' % (
        (A['them'] / P['them']) / (A['us'] / P['us']), ((A['them'] + A['extra']) / P['them']) / (A['us'] / P['us'])))


if __name__ == '__main__':
    print('src', src, 'kind', kind, 'rows', len(rows))
    groups = [('all', rows)]
    if src == 'ladder':
        for o in ('Fish', 'Mite', 'UoS', 'PBG'): groups.append((o, [x for x in rows if x['opp'] == o]))
    for name, rs in groups:
        rel(rs, name + ' all sims')
        rel([x for x in rs if engaged(x)], name + ' engaged')
        rates([x for x in rs if not x['lost']], name + ' predicted not lost')
        rates([x for x in rs if x['lost']], name + ' predicted lost')
