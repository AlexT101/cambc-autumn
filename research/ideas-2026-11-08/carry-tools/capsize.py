import pickle, sys, collections, numpy as np
rows = pickle.load(open(sys.argv[1], 'rb')); RW = int(sys.argv[2])
def base_gold(c): return c['gems']  # gems unaffected by bonuses
bins = [(0, 0), (1, 7), (8, 11), (12, 19), (20, 39), (40, 999)]
for o in 'FM':
    rs = [r for r in rows if r['opp'] == o]; ng = len(rs)
    print(f'== {o} r<={RW}: per game captures by gems bin  [count | joint(>=2 dealers >20%) | carry-held]')
    for side in ('live', 'spar', 'live_us'):
        C = [c for r in rs for c in r[side] if c['r'] <= RW]
        out = []
        for lo, hi in bins:
            cc = [c for c in C if lo <= c['gems'] <= hi]
            j = sum(sum(v > 0.2 * max(1e-9, sum(c['dealers'].values())) for v in c['dealers'].values()) >= 2 for c in cc)
            car = sum(any(h in ('Vesper Vale', 'Marcella') for h in c['holders']) for c in cc)
            out.append(f'{lo}-{hi}: {len(cc)/ng:4.1f}|{j/ng:4.1f}|{car/ng:4.1f}')
        print(f'  {side:8s} ' + '  '.join(out) + f'   gems tot {sum(c["gems"] for c in C)/ng:.0f}')
