import cls4, collections, numpy as np, os, sys
rows = cls4.load([os.path.expanduser('~/tmp-offload/battlecats/ds_bc.pkl')])
split = '2026-11-11T00'
test = [s for s in rows if s['created'] >= split]
# Mite test sides: token mix and raw values
for team in ('Mite', 'Team Kungarna', 'Trzy Kwaterki'):
    S = [s for s in rows if s['team'] == team]
    S2 = [s for s in S if s['created'] >= split] if team == 'Mite' else S
    tk = collections.Counter(); vals = collections.Counter()
    for s in S2:
        for r, t in cls4.stream(s): tk[cls4.TOK[t]] += 1
        for o in s['obs']: vals[int(o[2])] += 1
    print(team, len(S2), 'sides', 'created', min((s['created'] for s in S2), default=None), max((s['created'] for s in S2), default=None))
    print('  tokens', tk.most_common(8)); print('  values', vals.most_common(25))
