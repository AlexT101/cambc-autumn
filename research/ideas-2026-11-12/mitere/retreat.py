"""Contact behaviour: retreat, engage and chase, from per-round contact rows (round-start positions)."""
import fl, collections, sys
G = fl.load()
VS = sys.argv[1:] or ['v1', 'v2', 'r7']
def mv(f):
    if f[8] is None: return None
    return 'away' if f[8] > f[4] else ('toward' if f[8] < f[4] else 'hold')
def table(rows, key, keys, title):
    print(title)
    for k in keys:
        rs = [f for f in rows if key(f) == k]
        if not rs: continue
        m = collections.Counter(mv(f) for f in rs)
        print(f'   {k}: n={len(rs)} away {m["away"]/len(rs):.2f} toward {m["toward"]/len(rs):.2f} hit {sum(f[9] for f in rs)/len(rs):.2f} '
              f'camp {sum(f[19] for f in rs)/len(rs):.2f} die {sum(1-f[10] for f in rs)/len(rs):.3f}')
def hb(h): return '<.25' if h < .25 else '.25-.5' if h < .5 else '.5-.75' if h < .75 else '>=.75'
for v in VS:
    for who in ('M', 'O'):
        rows = []
        for g in G:
            if g['vg'] != v: continue
            t = g['mite'] if who == 'M' else 1 - g['mite']
            rows += [f for f in g['fights'] if g['team'][f[1]] == t and f[21] == 0 and g['name'][f[1]] != 'Issac' or (g['team'][f[1]] == t and f[21] == 0 and g['name'][f[1]] == 'Issac')]
        print(f'== {v} {who}')
        r3 = [f for f in rows if f[4] <= 3]
        table(r3, lambda f: hb(f[2]), ['<.25', '.25-.5', '.5-.75', '>=.75'], ' enemy within 3, by own hp')
        table([f for f in r3 if f[2] >= .5], lambda f: max(-2, min(2, f[5] - f[6] - 1)), [-2, -1, 0, 1, 2], ' within 3, hp>=.5, by (enemies within 5) - (team within 5 incl self)')
        table([f for f in r3 if f[2] >= .5], lambda f: '0' if f[3] == 0 else '1-49' if f[3] < 50 else '50+', ['0', '1-49', '50+'], ' within 3, hp>=.5, by own bag')
        # chase: nearest enemy hurt, at distance 2-5, own hp >= .5
        ch = [f for f in rows if 2 <= f[4] <= 5 and f[2] >= .5]
        table(ch, lambda f: hb(f[16]), ['<.25', '.25-.5', '.5-.75', '>=.75'], ' enemy at 2-5, own hp>=.5, by the nearest enemy hp')
        table(ch, lambda f: '0' if f[17] == 0 else '1-49' if f[17] < 50 else '50+', ['0', '1-49', '50+'], ' enemy at 2-5, own hp>=.5, by the nearest enemy bag')
        table([f for f in rows if 4 <= f[4] <= 6 and f[2] >= .75], lambda f: f[5] - f[6] - 1 if abs(f[5] - f[6] - 1) <= 1 else ('<=-2' if f[5] - f[6] - 1 < 0 else '>=2'), [-1, 0, 1, '<=-2', '>=2'], ' enemy at 4-6, own hp>=.75: approach by numbers')
