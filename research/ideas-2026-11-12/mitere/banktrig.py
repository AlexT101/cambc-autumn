"""Banking trigger: Mite carriers' (not Prism) movement toward altars and tribute starts by bag and altar distance."""
import p2l, collections, fl, sys, mprio
I = p2l.I
VS = sys.argv[1:] or ['r7']
mv = collections.defaultdict(lambda: [0, 0, 0]); st = collections.defaultdict(lambda: [0, 0]); stq = collections.defaultdict(lambda: [0, 0])
ret = collections.defaultdict(lambda: [0, 0])
for g in p2l.load(lambda g: g['vg'] in VS):
    for who in ('M', 'O'):
        t = g['mite'] if who == 'M' else 1 - g['mite']
        for row in g['rows']:
            c = row[I['cid']]
            if g['team'][c] != t or g['name'][c] == 'Prism' or row[I['chan']]: continue
            b = row[I['g0']]
            if b == 0: continue
            bb = min(b // 5 * 5, 60) if b < 60 else (60 if b < 100 else 100)
            q = row[I['dE']] > 8
            if q:
                mv[(who, bb)][0] += 1; mv[(who, bb)][1] += row[I['dA1']] < row[I['dA0']]; mv[(who, bb)][2] += row[I['dA1']] > row[I['dA0']]
            if row[I['dA0']] <= 1:
                st[(who, bb)][0] += 1; st[(who, bb)][1] += row[I['trib']]
            if who == 'M' and q:
                s = mprio.decode(row[I['prio']])[0]
                ret[bb][0] += 1; ret[bb][1] += s in ('retreat', 'retkill')
for who in ('M', 'O'):
    print(who, 'no enemy within 8: toward / away from the nearest altar, by bag')
    print('   ' + ' '.join(f'{k}:{v[1]/v[0]:.2f}/{v[2]/v[0]:.2f}' for k, v in sorted((k[1], v) for k, v in mv.items() if k[0] == who) if v[0] > 30))
    print(who, 'within 1 of an altar: tribute start rate by bag')
    print('   ' + ' '.join(f'{k}:{v[1]/v[0]:.2f}(n{v[0]})' for k, v in sorted((k[1], v) for k, v in st.items() if k[0] == who) if v[0] > 20))
print('M quiet (no enemy within 8): share in retreat state by bag:', ' '.join(f'{k}:{v[1]/v[0]:.2f}' for k, v in sorted(ret.items()) if v[0] > 30))
