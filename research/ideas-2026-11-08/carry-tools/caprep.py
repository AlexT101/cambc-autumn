import pickle, sys, collections, numpy as np
rows = pickle.load(open(sys.argv[1], 'rb')); RW = int(sys.argv[2]) if len(sys.argv) > 2 else 600
CAR = {'Vesper Vale', 'Marcella', 'Heart of Ruin'}
for o in 'FM':
    rs = [r for r in rows if r['opp'] == o]
    print(f'== {o} ({len(rs)} games), captures r<={RW}')
    for side in ('live', 'spar', 'live_us'):
        C = [c for r in rs for c in r[side] if c['r'] <= RW]; ng = len(rs)
        by = collections.defaultdict(lambda: [0, 0, 0, 0.0, 0.0, 0, 0])  # n, gold, gems, own dmg share, solo-clear, helped-not-held, duration
        for c in C:
            for h in c['holders']:
                b = by[h]; b[0] += 1; b[1] += c['gold'] / c['n']; b[2] += c['gems'] / c['n']
                dl = c['dealers']; tot = max(1e-9, sum(dl.values()))
                b[3] += dl.get(h, 0) / tot
                b[4] += (dl.get(h, 0) / tot > 0.9)
                b[6] += c['r'] - c['start']
            for dname, v in c['dealers'].items():
                if dname not in c['holders'] and v > 0.2 * max(1e-9, sum(c['dealers'].values())): by[dname][5] += 1
        print(f'  [{side}] caps/game {len(C)/ng:.1f}, gold/cap {np.mean([c["gold"] for c in C]):.0f} gems/cap {np.mean([c["gems"] for c in C]):.1f}, '
              f'multi-dealer {np.mean([sum(v>0.2*max(1e-9,sum(c["dealers"].values())) for v in c["dealers"].values())>=2 for c in C]):.2f}')
        for h, b in sorted(by.items(), key=lambda x: -x[1][1]):
            if b[0] < 30: continue
            print(f'     {h:13s} holds/g {b[0]/ng:5.2f} gold/g {b[1]/ng:6.0f} gold/hold {b[1]/b[0]:5.0f} gems/hold {b[2]/b[0]:5.1f} own-dmg {b[3]/b[0]:.2f} solo {b[4]/b[0]:.2f} clear-rounds {b[6]/b[0]:5.1f} helped-not-held/g {b[5]/ng:.2f}')
