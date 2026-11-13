import json, statistics
from collections import Counter, defaultdict
C = [json.loads(l) for l in open('/tmp/mxi-study/cycles.jsonl')]
F = {json.loads(l)['dir']: json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')}
N = len(C)
gap = sum(f['parts']['farm'] for f in F.values())
cyc = [dict(c, dir=g['dir'], w0=g['w0'], w1=g['w1']) for g in C for c in g['cycles']]
cap = [c for c in cyc if c['cap'] in 'WL' and c['w0'] <= c['z'] <= c['w1']]

def kind(c, team):
    o = 'L' if team == 'W' else 'W'
    if c[o + '_hitdmg'] > 0:
        return 'other hit' + (' & cleared' if c['clear'] == o else '')
    if c[o + '_hold']: return 'other held'
    if c[o + '_tgt']: return 'other targeted only'
    return 'uncontested'
print('## captures in window by captor, location (rel. loser) and what the other team did; gems/game and share of gap')
tab = defaultdict(lambda: [0, 0])
for c in cap:
    k = (c['side_L'], c['cap'], kind(c, c['cap']))
    tab[k][0] += c['gems']; tab[k][1] += 1
for k in sorted(tab):
    sign = 1 if k[1] == 'W' else -1
    print(f'{k[0]:5s} {k[1]} {k[2]:22s} gems/game {tab[k][0]/N:6.1f} caps/game {tab[k][1]/N:.2f}  gap share {sign*tab[k][0]/gap:+.0%}')

print('\n## contested cycles (both teams targeted) captured in window, by side: captor by who targeted / hit first')
for side in ('own', 'mid', 'enemy'):
    cc = [c for c in cap if c['side_L'] == side and c['W_tgt'] and c['L_tgt']]
    if not cc: continue
    res = Counter()
    for c in cc:
        ft = 'W first' if (c['W_tgt_first'] or 9e9) < (c['L_tgt_first'] or 9e9) else 'L first' if (c['L_tgt_first'] or 9e9) < (c['W_tgt_first'] or 9e9) else 'same'
        fh = 'Whit1' if c['W_firsthit'] and (not c['L_firsthit'] or c['W_firsthit'] < c['L_firsthit']) else 'Lhit1' if c['L_firsthit'] else 'nohit'
        res[(ft, c['cap'])] += 1
        res[(fh, c['cap'])] += 1
    print(side, f'{len(cc)/N:.2f}/game', dict(sorted(res.items())))
    print('   gems W', sum(c['gems'] for c in cc if c['cap'] == 'W') / N, 'L', sum(c['gems'] for c in cc if c['cap'] == 'L') / N)

print('\n## how the loser\'s targeters stopped on cycles the winner captured (champion count per game), by side')
for side in ('own', 'mid', 'enemy'):
    e = Counter(); tot = 0; rounds = 0
    for c in cap:
        if c['side_L'] != side or c['cap'] != 'W': continue
        for name, r, nxt, nd, dg, k in c['L_ends']:
            band = '<=4' if nd <= 4 else '5-8' if nd <= 8 else '>8'
            e[(nxt, band)] += 1; tot += 1; rounds += k
    print(side, f'targeters/game {tot/N:.2f}, their target rounds/game {rounds/N:.1f}:', ', '.join(f'{k[0]}@{k[1]} {v/N:.2f}' for k, v in e.most_common(10)))
print('   (winner analogue on cycles the loser captured)')
for side in ('own', 'mid', 'enemy'):
    e = Counter(); tot = 0; rounds = 0
    for c in cap:
        if c['side_L'] != side or c['cap'] != 'L': continue
        for name, r, nxt, nd, dg, k in c['W_ends']:
            band = '<=4' if nd <= 4 else '5-8' if nd <= 8 else '>8'
            e[(nxt, band)] += 1; tot += 1; rounds += k
    print(side, f'targeters/game {tot/N:.2f}, rounds/game {rounds/N:.1f}:', ', '.join(f'{k[0]}@{k[1]} {v/N:.2f}' for k, v in e.most_common(8)))

print('\n## target rounds per game: on cycles captured by self / by the other team / uncaptured, by side (rel. that team)')
for team in 'WL':
    t = Counter()
    for c in cyc:
        side = c['side_L'] if team == 'L' else {'own': 'enemy', 'enemy': 'own', 'mid': 'mid'}[c['side_L']]
        out = 'self' if c['cap'] == team else 'other' if c['cap'] in 'WL' else 'none'
        t[(side, out)] += c[team + '_tgt']
    print(team, ', '.join(f'{k[0]}/{k[1]} {t[k]/N:.1f}' for k in sorted(t)))

print('\n## Prism at the window start (games with Prism on both sides)')
pw = [(g['prism']['W'], g['prism']['L']) for g in C if 'W' in g['prism']]
print('games', len(pw), 'bag W median', statistics.median(a[0] for a, b in pw), 'L', statistics.median(b[0] for a, b in pw),
      'mean', sum(a[0] for a, b in pw) / len(pw), sum(b[0] for a, b in pw) / len(pw), 'focus W', sum(a[1] for a, b in pw) / len(pw), 'L', sum(b[1] for a, b in pw) / len(pw),
      'L bag > W bag', sum(b[0] > a[0] for a, b in pw) / len(pw), 'L Prism dead', sum(not b[2] for a, b in pw) / len(pw), 'W Prism dead', sum(not a[2] for a, b in pw) / len(pw))
