import json, sys, statistics as S
X = json.load(open(sys.argv[1]))
MELEE = {'Ryth','Vendetta','Marcella','Ren','Varg','Heart of Ruin','Issac'}
for side in ('us','them'):
    for lab, f in (('all', lambda x: True), ('T melee', lambda x: x['T'] in MELEE), ('T ranged', lambda x: x['T'] not in MELEE)):
        Y = [x for x in X if x['side']==side and x['len']>=2 and f(x)]
        # damage per round of the episode, pursuer->target and target->pursuer, against the pursuer's Strength
        pr = sum(x['dmgPT'] for x in Y) / sum(x['Pstr']*x['len'] for x in Y)
        tr = sum(x['dmgTP'] for x in Y) / sum(x['len'] for x in Y)
        pp = sum(x['dmgPT'] for x in Y) / sum(x['len'] for x in Y)
        print('pursuer=%-4s %-8s n=%5d  P->T %.0f/round (%.2f x P str)  T->P %.0f/round  ratio T/P %.2f' % (side, lab, len(Y), pp, pr, tr, tr/pp))
