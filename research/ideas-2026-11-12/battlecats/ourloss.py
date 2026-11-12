"""Games BattleCats wins against us (current BC version): what differs from the ones we win."""
import collections, fl, json, glob, os
G = fl.load(lambda g: g['ver'] == 'cur' and g['oc'] == 'us')
L = [g for g in G if g['win']]; W = [g for g in G if g['win'] is False]
print(len(G), 'games vs us; BC wins', len(L))
def agg(S, f): return fl.mean(f(g) for g in S)
def us(g): return 1 - g['bc']
def deaths(g, t, name=None): return sum(1 for d in g['deaths'] if g['team'][d[1]] == t and g['name'][d[1]] != 'Issac' and (name is None or g['name'][d[1]].startswith(name)))
def gl(g, t): return sum(d[3] or 0 for d in g['deaths'] if g['team'][d[1]] == t)
def bigtrib(g, t, ok=None): return sum(1 for x in g['tribs'] if g['team'][x[1]] == t and x[2] >= 100 and (ok is None or (x[5] == 'end') == ok))
def lockedus(g): return sum(1 for x in g['tribs'] if g['team'][x[1]] == us(g) and x[5] == 'lock')
rows = [('our deaths', lambda g: deaths(g, us(g))), ('BC deaths', lambda g: deaths(g, g['bc'])),
        ('our gems lost to deaths', lambda g: gl(g, us(g))), ('BC gems lost to deaths', lambda g: gl(g, g['bc'])),
        ('our Prism deaths', lambda g: deaths(g, us(g), 'Prism')), ('our C&I deaths', lambda g: deaths(g, us(g), 'Cassi')),
        ('our 100+ tributes completed', lambda g: bigtrib(g, us(g), True)), ('our 100+ tributes cancelled', lambda g: bigtrib(g, us(g), False)),
        ('our tributes cancelled by lock', lockedus),
        ('BC 100+ tributes completed', lambda g: bigtrib(g, g['bc'], True)), ('BC 100+ cancelled', lambda g: bigtrib(g, g['bc'], False)),
        ('rounds', lambda g: g['rounds']), ('altars', lambda g: len(g['altars'])), ('map area', lambda g: g['W'] * g['H']),
        ('gems r400 (BC-us)', lambda g: g['ck']['400']['gems'][g['bc']] - g['ck']['400']['gems'][us(g)] if '400' in g['ck'] else 0),
        ('earned r400 (BC-us)', lambda g: g['ck']['400']['earned'][g['bc']] - g['ck']['400']['earned'][us(g)] if '400' in g['ck'] else 0)]
print(f'{"":32s} {"BC wins":>9s} {"we win":>9s}')
for k, f in rows: print(f'{k:32s} {agg(L, f):9.2f} {agg(W, f):9.2f}')
# how BC wins: end reason ~ gems; who scores the last big tributes
lastt = collections.Counter()
for g in L:
    tr = [x for x in g['tribs'] if g['team'][x[1]] == g['bc'] and x[5] == 'end']
    if tr: lastt[(g['name'][tr[-1][1]], 'bag>=100' if tr[-1][2] >= 100 else 'bag<100')] += 1
print('BC wins: last completed BC tribute by', lastt.most_common(8))
# BC win rate vs us by number of altars and by map, all current-version games (capture rows, no replays needed)
import meta
A = [r for r in meta.rows() if r['created_at'] >= '2026-11-10T09' and r['opp'] == meta.US and r['bc_win'] is not None]
bymap = collections.defaultdict(lambda: [0, 0])
for r in A: bymap[r['map']][0] += r['bc_win']; bymap[r['map']][1] += 1
alt = {g['map']: len(g['altars']) for g in G}
byalt = collections.defaultdict(lambda: [0, 0])
for m, (w, n) in bymap.items():
    if m in alt: byalt[alt[m]][0] += w; byalt[alt[m]][1] += n
print('\nBC win rate vs us by altar count (current BC, all our games incl. no-replay):', {k: f'{v[0] / v[1]:.2f} of {v[1]}' for k, v in sorted(byalt.items())})
top = sorted(((w / n, n, m) for m, (w, n) in bymap.items() if n >= 8), reverse=True)
print('maps where BC beats us most (n>=8):', [(m, f'{p:.2f}', n, alt.get(m)) for p, n, m in top[:15]])
print('maps where we beat BC most:', [(m, f'{p:.2f}', n, alt.get(m)) for p, n, m in top[-8:]])
