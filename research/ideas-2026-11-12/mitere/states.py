"""Mite's decoded priority state (set during turn r) against the turn's context (round-start positions)."""
import fl, collections, mprio, sys
VS = sys.argv[1:] or ['r7']
G = fl.load(lambda g: g['vg'] in VS)
def mv(f):
    if f[8] is None: return None
    return 'away' if f[8] > f[4] else ('toward' if f[8] < f[4] else 'hold')
rows = []
for g in G:
    for f in g['fights']:
        if g['team'][f[1]] != g['mite']: continue
        st = mprio.decode(f[14])[0]
        if st in ('quietT',): st = 'quiet'
        if st.startswith('c') and st != 'chan' and st != 'contact': st = 'const'
        rows.append((st, f, g['name'][f[1]]))
STS = ['quiet', 'contact', 'zero', 'retreat', 'kill', 'retkill', 'chan', 'const', 'dead', 'other']
def hb(h): return '<.2' if h < .2 else '.2-.4' if h < .4 else '.4-.6' if h < .6 else '.6-.8' if h < .8 else '>=.8'
def gb(x): return '0' if x == 0 else '1-9' if x < 10 else '10-29' if x < 30 else '30-99' if x < 100 else '100+'
def tab(key, keys, filt, title):
    print(title)
    print('   ' + ' '.join(f'{s:>7}' for s in STS) + '     n')
    for k in keys:
        rs = [x for x in rows if filt(x[1]) and key(x[1]) == k]
        if not rs: continue
        c = collections.Counter(x[0] for x in rs)
        print(f'   {str(k):>6} ' + ' '.join(f'{c[s]/len(rs):7.2f}' for s in STS) + f' {len(rs):6d}')
tab(lambda f: f[4], [1, 2, 3, 4, 5, 6], lambda f: True, 'by distance to the nearest enemy')
tab(lambda f: hb(f[2]), ['<.2', '.2-.4', '.4-.6', '.6-.8', '>=.8'], lambda f: f[4] <= 4, 'enemy within 4: by own hp')
tab(lambda f: gb(f[3]), ['0', '1-9', '10-29', '30-99', '100+'], lambda f: f[4] <= 4 and f[2] >= .6, 'enemy within 4, hp>=.6: by own bag')
tab(lambda f: max(-2, min(2, f[5] - f[6] - 1)), [-2, -1, 0, 1, 2], lambda f: f[4] <= 4 and f[2] >= .6 and f[3] < 10, 'enemy within 4, hp>=.6, bag<10: (enemies within 5) - (team within 5 incl self)')
tab(lambda f: f[15], [0, 1], lambda f: f[4] <= 4, 'enemy within 4: does it see an enemy within 5')
tab(lambda f: hb(f[16]), ['<.2', '.2-.4', '.4-.6', '.6-.8', '>=.8'], lambda f: f[4] <= 4 and f[2] >= .6, 'enemy within 4, own hp>=.6: by the nearest enemy hp')
print('actions by state (enemy within 4):')
for s in STS:
    rs = [x[1] for x in rows if x[0] == s and x[1][4] <= 4]
    if len(rs) < 30: continue
    m = collections.Counter(mv(f) for f in rs)
    print(f'   {s:>8} n={len(rs)} away {m["away"]/len(rs):.2f} toward {m["toward"]/len(rs):.2f} hold {m["hold"]/len(rs):.2f} hit {sum(f[9] for f in rs)/len(rs):.2f} '
          f'camp {sum(f[19] for f in rs)/len(rs):.2f} die {sum(1-f[10] for f in rs)/len(rs):.3f} hp {fl.med([f[2] for f in rs]):.2f} bag {fl.med([f[3] for f in rs])} recall {sum(f[20] for f in rs)/len(rs):.2f}')
print('state by champion type (enemy within 4):')
by = collections.defaultdict(collections.Counter)
for s, f, nm in rows:
    if f[4] <= 4: by[nm][s] += 1
for nm, c in by.items():
    n = sum(c.values()); print(f'   {nm:>12} n={n} ' + ' '.join(f'{s} {c[s]/n:.2f}' for s in STS if c[s]))
