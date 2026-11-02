import json, sys
from collections import Counter
X = json.load(open(sys.argv[1]))
def row(lab, Y):
    c = Counter(x['end'] for x in Y); n = len(Y) or 1
    print('  %-46s n=%4d kill %.2f quit %.2f home %.2f stand %.2f P_died %.2f' % (lab, len(Y), c['kill']/n, c['quit']/n, c['home']/n, c['stand']/n, c['P_died']/n))
for side in ('us','them'):
    print('pursuer', side, '(pursuer hp >= .6)')
    B = [x for x in X if x['side']==side and x['Php']>=.6 and x['Phome'] is not None]
    for tlab, f in (('T<.35', lambda x: x['Thp']<.35), ('T .35-.5', lambda x: .35<=x['Thp']<.5), ('T .5-.75', lambda x: .5<=x['Thp']<.75), ('T>=.75', lambda x: x['Thp']>=.75)):
        row(tlab+' target on its own half', [x for x in B if f(x) and x['Thome'] < x['Phome']])
        row(tlab+' target on pursuer half', [x for x in B if f(x) and x['Thome'] >= x['Phome']])
