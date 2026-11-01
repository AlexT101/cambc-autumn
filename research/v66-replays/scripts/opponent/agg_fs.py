import json, glob
from collections import defaultdict, Counter
S = 'replays/v66-analysis'
F = [json.load(open(p)) for p in glob.glob(S + '/opp/fs/*.json')]
OPP = ['Fish', 'Mite', 'UoS', 'PBG']
by = defaultdict(list)
for f in F: by[f['opp']].append(f)
pct = lambda a, b: f'{a/b*100:.0f}%' if b else '-'
mean = lambda a: sum(a) / len(a) if a else float('nan')
for o in OPP:
    print(f'== {o}: {len(by[o])} games')
    for ro in ('us', 'them'):
        S_ = []
        for f in by[o]:
            u = f['us']
            t = u if ro == 'us' else 1 - u
            for s in f['starts']:
                if s['init'] == t: S_.append((f, s, t))
        n = len(S_)
        adv = Counter(); res = defaultdict(lambda: [0, 0, 0])
        for f, s, t in S_:
            dlt = s['before'][t] - s['before'][1 - t]
            b = '<=-1' if dlt <= -1 else ('0' if dlt == 0 else '>=+1')
            adv[b] += 1
            x = res[b]; x[0] += 1; x[1] += s['kills'][t]; x[2] += s['kills'][1 - t]
        reinf_i = mean([s['mx'][t] - s['before'][t] for f, s, t in S_]); reinf_d = mean([s['mx'][1 - t] - s['before'][1 - t] for f, s, t in S_])
        kd = sum(s['kills'][t] for f, s, t in S_), sum(s['kills'][1 - t] for f, s, t in S_)
        sides = Counter(s['side'] for f, s, t in S_)
        print(f'  {ro} initiates {n/len(by[o]):.1f}/game; init bodies-adv before: ' + ', '.join(f'{b} {pct(adv[b],n)}' for b in ('<=-1', '0', '>=+1')) +
              f' | kills init/def within 15r: {kd[0]}/{kd[1]} | +bodies within 5r: init {reinf_i:.2f} def {reinf_d:.2f} | where: ' + ', '.join(f'{k} {pct(v,n)}' for k, v in sides.items()))
        print('     kills per start by adv bucket (init/def): ' + ', '.join(f'{b}: {res[b][1]/max(1,res[b][0]):.2f}/{res[b][2]/max(1,res[b][0]):.2f} (n{res[b][0]})' for b in ('<=-1', '0', '>=+1')))
    # all starts: max bodies per team within 5 rounds
    mxu = []; mxt = []
    for f in by[o]:
        u = f['us']
        for s in f['starts']:
            mxu.append(s['mx'][u]); mxt.append(s['mx'][1 - u])
    c = Counter((min(a, 3), min(b, 3)) for a, b in zip(mxu, mxt))
    print(f'  all fights: mean max bodies within 8 in first 5 rounds: us {mean(mxu):.2f} them {mean(mxt):.2f}; them>us in {pct(sum(1 for a,b in zip(mxu,mxt) if b>a),len(mxu))}, us>them {pct(sum(1 for a,b in zip(mxu,mxt) if a>b),len(mxu))}')
# per-map consistency of "them bring more bodies"
print('\n== per map: maps where mean(them max bodies) > mean(us)')
for o in OPP:
    pm = defaultdict(lambda: [[], []])
    for f in by[o]:
        u = f['us']
        for s in f['starts']:
            pm[f['map']][0].append(s['mx'][u]); pm[f['map']][1].append(s['mx'][1 - u])
    k = sum(1 for a, b in pm.values() if mean(b) > mean(a)); e = sum(1 for a, b in pm.values() if mean(b) == mean(a))
    print(f'  {o}: {k}/{len(pm)} maps (ties {e})')
print('\n== per map: share of initiations made while outnumbered (picks within 8), us > them')
for o in OPP:
    pm = defaultdict(lambda: {'us': [0, 0], 'them': [0, 0]})
    for f in by[o]:
        u = f['us']
        for s in f['starts']:
            ro = 'us' if s['init'] == u else 'them'; t = s['init']
            pm[f['map']][ro][1] += 1; pm[f['map']][ro][0] += (s['before'][t] < s['before'][1 - t])
    ok = [v for v in pm.values() if v['us'][1] >= 3 and v['them'][1] >= 3]
    print(f"  {o}: {sum(1 for v in ok if v['us'][0]/v['us'][1] > v['them'][0]/v['them'][1])}/{len(ok)} maps")
print('\n== kill balance of fights by initiator, per map: maps where fights WE start net-lose kills')
for o in OPP:
    pm = defaultdict(lambda: [0, 0])
    for f in by[o]:
        u = f['us']
        for s in f['starts']:
            if s['init'] == u: pm[f['map']][0] += s['kills'][u]; pm[f['map']][1] += s['kills'][1 - u]
    print(f"  {o}: {sum(1 for a,b in pm.values() if b>a)}/{len(pm)} maps (ties {sum(1 for a,b in pm.values() if a==b)})")
