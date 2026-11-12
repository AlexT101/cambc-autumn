import bl, collections, statistics as S, sys
ver = (sys.argv[1] or None) if len(sys.argv) > 1 else None
lim = int(sys.argv[2]) if len(sys.argv) > 2 else 150
st = collections.defaultdict(list); n = 0
for g in bl.games(filt=lambda g: ver is None or g['ver'] == ver, limit=lim):
    n += 1
    C = g['rd']['champions']
    bc = [c for c in C if c['team'] == g['bc']]; en = [c for c in C if c['team'] != g['bc']]
    for c in bc:
        for i, p in enumerate(c['prio']):
            if not c['alive'][i]: cls = 'dead'
            else: cls = 'lo' if 8 <= p <= 13 else 'hi' if 15 <= p <= 20 else str(p) if p in (35, 40) else 'neg' if p < 0 else 'x%d' % p
            d = 99
            if c['alive'][i]:
                for e in en:
                    if e['alive'][i] and e['x'][i] is not None: d = min(d, max(abs(e['x'][i] - c['x'][i]), abs(e['y'][i] - c['y'][i])))
            st[cls].append((c['hp'][i] / max(c['maxHp'][i], 1) if c['alive'][i] else 0, c['gems'][i], d, p, i))
print(n, 'games')
for k, v in sorted(st.items(), key=lambda x: -len(x[1])):
    hp = [x[0] for x in v]; gm = [x[1] for x in v]; d = [x[2] for x in v]
    print(k, len(v), 'hp %.2f' % S.mean(hp), 'gems med %d mean %.1f' % (S.median(gm), S.mean(gm)),
          'enemy<=4 %.2f <=8 %.2f' % (sum(x <= 4 for x in d) / len(d), sum(x <= 8 for x in d) / len(d)), 'round med', S.median([x[4] for x in v]))
