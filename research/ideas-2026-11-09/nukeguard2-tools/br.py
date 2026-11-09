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
want = sys.argv[2].split(',')
agg = collections.defaultdict(lambda: np.zeros(5)); tot = collections.Counter()
for g in res:
    for x in g['rows']:
        if not x['ours']: continue
        k = (z(x, 'fr') + '>' + z(x, 'to')) if x['moved'] else (z(x, 'fr') + ' stand')
        if k not in want: continue
        agg[(k, x['br'])] += [1, x['died_champ'], x['dealt'] > 0, x['esc'] > 0, x['gems']]
        tot[k] += 1
for (k, b), a in sorted(agg.items(), key=lambda t: (t[0][0], -t[1][0])):
    print(f"{k:8s} {b or '?':2s} n {int(a[0]):5d} ({a[0]/tot[k]:.2f})  died {a[1]/a[0]:.3f}  hit {a[2]/a[0]:.2f}  escape-available {a[3]/a[0]:.2f}  gems {a[4]/a[0]:.1f}")
