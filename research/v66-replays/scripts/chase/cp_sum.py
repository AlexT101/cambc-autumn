import json, sys, statistics as S
from collections import Counter
X = [x for x in json.load(open(sys.argv[1])) if x['cut'] is not None]
def q(v): v = sorted(v); return '%s/%s/%s' % tuple(round(v[int(len(v) * p)], 2) for p in (.25, .5, .75))
print('first contacts:', Counter(x['side'] for x in X))
print('%-34s %-22s %-22s' % ('feature at first contact (q25/50/75)', 'us', 'them'))
for k in ('home', 'cut', 'dn', 'da', 'nA', 'nE', 'open', 'detour', 'branch', 'hp'):
    print('%-34s %-22s %-22s' % (k, q([x[k] for x in X if x['side'] == 'us']), q([x[k] for x in X if x['side'] == 'them'])))
for k in ('own', 'bush'):
    print('%-34s %-22.2f %-22.2f' % (k + ' (share)', S.mean(x[k] for x in X if x['side'] == 'us'), S.mean(x[k] for x in X if x['side'] == 'them')))
print('cut off (enemy nearer our spawn than us) share: us %.2f them %.2f' % tuple(S.mean(x['cut'] < 0 for x in X if x['side'] == s) for s in ('us', 'them')))
print('who strikes first within 10 rounds:', {s: {k: round(v / sum(1 for x in X if x['side'] == s), 2) for k, v in Counter(x['first'] for x in X if x['side'] == s).items()} for s in ('us', 'them')})
print('died within 20 rounds: us %.3f them %.3f' % tuple(S.mean(x['died20'] for x in X if x['side'] == s) for s in ('us', 'them')))
def tab(lab, bins):
    print('== death within 20 rounds by', lab)
    for name, f in bins:
        row = []
        for s in ('us', 'them'):
            Y = [x for x in X if x['side'] == s and f(x)]
            row.append('%s n=%5d (%.2f) died %.3f' % (s, len(Y), len(Y) / sum(1 for x in X if x['side'] == s), S.mean(x['died20'] for x in Y) if Y else 0))
        print('  %-20s %s' % (name, '   |   '.join(row)))
tab('cut-off margin', [('cut <= -3', lambda x: x['cut'] <= -3), ('cut -2..0', lambda x: -2 <= x['cut'] <= 0), ('cut 1..4', lambda x: 1 <= x['cut'] <= 4), ('cut 5..10', lambda x: 5 <= x['cut'] <= 10), ('cut > 10', lambda x: x['cut'] > 10)])
tab('ally margin dn-da', [('<= -4', lambda x: x['dn'] - x['da'] <= -4), ('-3..0', lambda x: -3 <= x['dn'] - x['da'] <= 0), ('1..4', lambda x: 1 <= x['dn'] - x['da'] <= 4), ('>4', lambda x: x['dn'] - x['da'] > 4)])
tab('open tiles within 2', [('<=12', lambda x: x['open'] <= 12), ('13-19', lambda x: 13 <= x['open'] <= 19), ('20-24', lambda x: x['open'] >= 20)])
tab('homeward branches', [('1', lambda x: x['branch'] == 1), ('2', lambda x: x['branch'] == 2), ('3+', lambda x: x['branch'] >= 3)])
tab('half', [('own half', lambda x: x['own']), ('their half', lambda x: not x['own'])])
tab('numbers within 8', [('nA<nE', lambda x: x['nA'] + 1 < x['nE']), ('even', lambda x: x['nA'] + 1 == x['nE']), ('nA>nE', lambda x: x['nA'] + 1 > x['nE'])])
tab('first strike', [('we strike first', lambda x: x['first'] == 'me'), ('they strike first', lambda x: x['first'] == 'them'), ('same round', lambda x: x['first'] == 'tie'), ('no hit in 10', lambda x: x['first'] is None)])
