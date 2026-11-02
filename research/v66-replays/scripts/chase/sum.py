import json, sys, statistics as S
from collections import Counter
X = json.load(open(sys.argv[1]))
MELEE = {'Ryth','Vendetta','Marcella','Ren','Varg','Heart of Ruin','Issac'}
def table(lab, f):
    print('==', lab)
    for side in ('us', 'them'):
        Y = [x for x in X if x['side'] == side and f(x)]
        if not Y: continue
        c = Counter(x['end'] for x in Y); n = len(Y)
        print('  pursuer=%-4s n=%5d ' % (side, n) + ' '.join('%s %.2f' % (k, c[k] / n) for k in ('kill','home','quit','outrun','stand','P_died','cap')),
              ' | dmgPT %.0f dmgTP %.0f oth %.0f adjT %.2f len %.1f' % tuple(S.mean([x[k] for x in Y]) for k in ('dmgPT','dmgTP','dmgOthT','adj','len')))
table('all', lambda x: True)
table('target healthy >=.6', lambda x: x['Thp'] >= .6)
table('target .35-.6', lambda x: .35 <= x['Thp'] < .6)
table('target <.35', lambda x: x['Thp'] < .35)
table('pursuer melee', lambda x: x['P'] in MELEE)
table('pursuer ranged', lambda x: x['P'] not in MELEE)
table('target melee', lambda x: x['T'] in MELEE)
table('target ranged', lambda x: x['T'] not in MELEE)
table('target home <=8', lambda x: x['Thome'] <= 8)
table('target home 9-20', lambda x: 9 <= x['Thome'] <= 20)
table('target home >20', lambda x: x['Thome'] > 20)
table('pursuer adjacent at start', lambda x: x['d0'] <= 1)
table('pursuer 2-3 at start', lambda x: x['d0'] >= 2)
table('pursuer outnumbered allyP<allyT', lambda x: x['allyP'] < x['allyT'])
table('even allyP==allyT', lambda x: x['allyP'] == x['allyT'])
table('pursuer ahead allyP>allyT', lambda x: x['allyP'] > x['allyT'])
