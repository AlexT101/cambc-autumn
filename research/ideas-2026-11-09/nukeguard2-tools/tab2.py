import pickle, sys, collections, numpy as np
import os
SEEN = os.environ.get('SEEN') == '1'
res = pickle.load(open(sys.argv[1], 'rb'))
def z(x, s):
    if SEEN:
        if x['sv_' + s] >= 0: return 'N'
        if x['svt_' + s] >= x['H']: return 'L'
        return '-'
    if x['s_' + s] >= 0: return 'N'
    if x['tot_' + s] >= x['H']: return 'L'
    return '-'
for who in (1, 0):
    for opp in ('Inte', 'Mite'):
        G = [g for g in res if g['opp'] == opp]
        agg = collections.defaultdict(lambda: np.zeros(8))
        for g in G:
            for x in g['rows']:
                if x['ours'] != who: continue
                k = (z(x, 'fr') + '>' + z(x, 'to')) if x['moved'] else (z(x, 'fr') + ' stand')
                if k in ('- stand', '->-'): continue
                agg[k] += [1, x['died_champ'], x['dealt'] > 0, x['closer'] < 0, x['closer'] > 0, x['died_gems'], x['gems'], x['killed_now'] > 0]
        print(('ours' if who else 'theirs'), opp, len(G), 'games   (N single nuke, L combined lethal, - neither)')
        print(f"{'from>to':10s} {'/game':>7s} {'died':>6s} {'hit':>6s} {'closer':>6s} {'away':>6s} {'gemsLost':>8s} {'gems':>6s} {'kill':>6s}")
        for k in sorted(agg):
            a = agg[k]; print(f"{k:10s} {a[0]/len(G):7.2f} {a[1]/a[0]:6.3f} {a[2]/a[0]:6.3f} {a[3]/a[0]:6.3f} {a[4]/a[0]:6.3f} {a[5]/a[0]:8.2f} {a[6]/a[0]:6.1f} {a[7]/a[0]:6.3f}")
