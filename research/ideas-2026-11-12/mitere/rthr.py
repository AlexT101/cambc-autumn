"""Retreat-state thresholds: hp and bag, by version."""
import fl, collections, mprio, sys
for vg in ('v0', 'v1', 'v2', 'r7'):
    G = fl.load(lambda g: g['vg'] == vg)
    H = collections.defaultdict(lambda: [0, 0]); B = collections.defaultdict(lambda: [0, 0]); D = collections.defaultdict(lambda: [0, 0])
    for g in G:
        for f in g['fights']:
            if g['team'][f[1]] != g['mite']: continue
            st = mprio.decode(f[14])[0]
            if st in ('dead', 'chan'): continue
            ret = st in ('retreat', 'retkill')
            if f[4] <= 4 and f[3] < 10:
                k = min(19, int(f[2] * 20)); H[k][0] += 1; H[k][1] += ret
            if f[4] <= 4 and f[2] >= .6:
                k = min(f[3], 30); B[k][0] += 1; B[k][1] += ret
            if f[2] >= .6 and f[3] >= 15:
                D[f[4]][0] += 1; D[f[4]][1] += ret
    print(vg, 'bag<10, enemy<=4: retreat share by hp (x0.05):', ' '.join(f'{k*5}:{v[1]/v[0]:.2f}' for k, v in sorted(H.items()) if v[0] > 20))
    print('   hp>=.6, enemy<=4: retreat share by bag:', ' '.join(f'{k}:{v[1]/v[0]:.2f}' for k, v in sorted(B.items()) if v[0] > 20))
    print('   hp>=.6, bag>=15: retreat share by nearest enemy distance:', ' '.join(f'{k}:{v[1]/v[0]:.2f}' for k, v in sorted(D.items()) if v[0] > 20))
