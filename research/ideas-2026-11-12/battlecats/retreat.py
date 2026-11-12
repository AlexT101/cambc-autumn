"""When BattleCats raises its retreat flag (priority 40) and its chase/strike flags (35/38): state at onset."""
import bl, collections, sys
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 400
on = collections.defaultdict(list); base = []
def hb(h): return min(9, int(h * 10))
cnt = collections.defaultdict(collections.Counter)
n = 0
for g in bl.games(filt=lambda g: g['ver'] == 'cur', limit=lim, events=False):
    n += 1
    C = g['rd']['champions']; bc = [c for c in C if c['team'] == g['bc']]; en = [c for c in C if c['team'] != g['bc']]
    al = bc
    for c in bc:
        nm = [x['name'] for x in g['meta']['champions'] if x['id'] == c['id']][0]
        P = c['prio']
        for i in range(1, len(P)):
            if not c['alive'][i]: continue
            vis = [e for e in en if e['alive'][i] and e['x'][i] is not None and c['id'] in (e['seenBy'][i] or [])]
            if not vis: continue
            d = min(max(abs(e['x'][i] - c['x'][i]), abs(e['y'][i] - c['y'][i])) for e in vis)
            if d > 6: continue
            h = c['hp'][i] / c['maxHp'][i]
            ne = sum(1 for e in vis if max(abs(e['x'][i] - c['x'][i]), abs(e['y'][i] - c['y'][i])) <= 5)
            na = sum(1 for a in al if a is not c and a['alive'][i] and max(abs(a['x'][i] - c['x'][i]), abs(a['y'][i] - c['y'][i])) <= 5)
            key = (hb(h),)
            cnt[key]['n'] += 1; cnt[key]['40'] += P[i] == 40; cnt[key]['35'] += P[i] == 35; cnt[key]['38'] += P[i] == 38
            k2 = ('num', max(-2, min(2, ne - na - 1)), 'hp>=.5' if h >= .5 else 'hp<.5')
            cnt[k2]['n'] += 1; cnt[k2]['40'] += P[i] == 40
            k3 = ('gems', 'carry50+' if c['gems'][i] >= 50 else 'carry1-49' if c['gems'][i] else 'empty', 'hp>=.5' if h >= .5 else 'hp<.5')
            cnt[k3]['n'] += 1; cnt[k3]['40'] += P[i] == 40
            k4 = ('type', nm)
            cnt[k4]['n'] += 1; cnt[k4]['40'] += P[i] == 40; cnt[k4]['hp'] += h
print(n, 'games; BC bodies with a seen enemy within 6: share of rounds with priority 40 (retreat) / 35 (chase) / 38 (strike)')
for k in sorted(cnt, key=str):
    s = cnt[k]; m = s['n']
    print(k, m, f"40: {s['40'] / m:.3f}", f"35: {s['35'] / m:.3f}" if len(k) == 1 else '', f"38: {s['38'] / m:.3f}" if len(k) == 1 else '')
