import pickle, sys, collections, numpy as np
res = pickle.load(open(sys.argv[1], 'rb'))
def z(x, s):
    if x['sv_' + s] >= 0: return 'N'
    if x['svt_' + s] >= x['H']: return 'L'
    return '-'
by = collections.defaultdict(list)
for g in res: by[g['bot']].append(g)
cats = ['->N', '->L', 'N>N', 'L>L', 'L>-', 'N>-', 'L stand', 'N stand']
print(f"{'bot':5s} {'games':>5s} {'win':>5s} {'deaths':>6s} {'kills':>6s} " + ' '.join(f'{c:>12s}' for c in cats))
for b in ['base', 'rs', 'rs2', 'wg', 'pr']:
    G = by.get(b, [])
    if not G: continue
    agg = collections.defaultdict(lambda: np.zeros(2))
    for g in G:
        for x in g['rows']:
            if not x['ours']: continue
            k = (z(x, 'fr') + '>' + z(x, 'to')) if x['moved'] else (z(x, 'fr') + ' stand')
            agg[k] += [1, x['died_champ']]
    n = len(G)
    cells = ' '.join(f"{agg[c][0]/n:5.2f}({agg[c][1]/max(1,agg[c][0]):.2f})" for c in cats)
    print(f"{b:5s} {n:5d} {100*np.mean([g['win'] for g in G]):5.1f} {np.mean([g['od'] for g in G]):6.2f} {np.mean([g['ok'] for g in G]):6.2f} {cells}")
print('cells: per game (died before next turn)')
