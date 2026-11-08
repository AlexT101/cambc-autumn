import pickle, sys, numpy as np
r, bodies = sys.argv[1], sys.argv[2:]
A = pickle.load(open(f'econ-o29-r{r}.pkl', 'rb')); Bs = [{(x['map'], x['side'], x['opp']): x for x in pickle.load(open(f'econ-{b}-r{r}.pkl', 'rb'))} for b in bodies]
T = ['Vesper Vale', 'Heart of Ruin', 'Marcella', 'Vendetta', 'Prism', 'Issac', 'Cassi', 'Tavi', 'Willow']
for o in 'FM':
    rs = [a for a in A if a['opp'] == o and all((a['map'], a['side'], a['opp']) in B for B in Bs)]
    def col(k):
        return [np.mean([x['live_opp'].get(k, 0) for x in rs]), np.mean([x['spar_opp'].get(k, 0) for x in rs])] + [np.mean([B[(x['map'], x['side'], x['opp'])]['spar_opp'].get(k, 0) for x in rs]) for B in Bs]
    print(f'r{r} {o} n{len(rs)}  columns: live / o29 / ' + ' / '.join(bodies))
    for k in ('earned', 'cap_gold', 'caps', 'campatk', 'champatk', 'kills', 'deaths', 'win'):
        print(f'   {k:9s} ' + ' / '.join(f'{v:7.2f}' if k == 'win' else f'{v:7.0f}' if v > 50 else f'{v:7.1f}' for v in col(k)))
    for t in T:
        sel = [x for x in rs if 'earned_' + t in x['live_opp']]
        if len(sel) < 20: continue
        vals = [np.mean([x['live_opp']['earned_' + t] for x in sel]), np.mean([x['spar_opp'].get('earned_' + t, 0) for x in sel])] + [np.mean([B[(x['map'], x['side'], x['opp'])]['spar_opp'].get('earned_' + t, 0) for x in sel]) for B in Bs]
        print(f'   {t[:9]:9s} ' + ' / '.join(f'{v:7.0f}' for v in vals) + f'  n{len(sel)}')
