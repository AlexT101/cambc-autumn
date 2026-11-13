import json
from collections import Counter, defaultdict
E = [json.loads(l) for l in open('/tmp/mxi-study/episodes.jsonl')]
N = len(E)
eps = [e for g in E for e in g['eps']]
for e in eps: e['walk'] = e['cls'].get('walk', 0) + e['cls'].get('walk_bag', 0)
print('## F-target episodes per game by team, side and outcome: count, rounds, walk rounds, gems to the champion')
agg = defaultdict(lambda: [0, 0, 0, 0, 0])
for e in eps:
    k = (e['team'], e['side'], e['out'])
    a = agg[k]; a[0] += 1; a[1] += e['len']; a[2] += e['walk']; a[3] += e['mine']; a[4] += e['hit'] > 0
for side in ('own', 'mid', 'enemy'):
    for out in ('own_cap', 'enemy_cap', 'none'):
        line = []
        for team in 'WL':
            a = agg[(team, side, out)]
            line.append(f'{team}: n {a[0]/N:5.2f} rnds {a[1]/N:6.1f} walk {a[2]/N:5.1f} gems {a[3]/N:5.1f} hit% {a[4]/max(1,a[0]):.0%}')
        print(f'{side:5s} {out:9s} | ' + ' | '.join(line))
print('\n## no-capture episodes: how they ended (next branch), rounds per game')
for team in 'WL':
    c = Counter(); cw = Counter()
    for e in eps:
        if e['team'] == team and e['out'] != 'own_cap':
            c[(e['side'], e['next'])] += e['len']; cw[(e['side'], e['next'])] += e['walk']
    for side in ('own', 'mid', 'enemy'):
        print(team, side, ', '.join(f'{k[1]} {c[k]/N:.1f}r/{cw[k]/N:.1f}w' for k in sorted(c, key=lambda k: -c[k]) if k[0] == side and c[k] / N >= 0.3))
print('\n## episodes ending without own capture and without hitting, by next branch, nearest enemy at end (rounds/game)')
for team in 'WL':
    c = Counter()
    for e in eps:
        if e['team'] == team and e['out'] != 'own_cap' and e['hit'] == 0:
            band = '<=8' if e['nd_end'] <= 8 else '9-16' if e['nd_end'] <= 16 else '>16'
            c[(e['next'], band)] += e['len']
    print(team, ', '.join(f'{k} {c[k]/N:.1f}' for k in sorted(c, key=lambda k: -c[k])[:12]))
print('\n## by type: rounds/game in F episodes that did not end in own capture (W vs L), and capture-episode rounds')
ty = defaultdict(lambda: [0, 0, 0, 0])
for e in eps:
    i = 0 if e['team'] == 'W' else 1
    if e['out'] == 'own_cap': ty[e['type']][i] += e['len']
    else: ty[e['type']][2 + i] += e['len']
for k, v in sorted(ty.items(), key=lambda kv: -(kv[1][3] - kv[1][2])):
    print(f'{k:13s} cap-ep W {v[0]/N:5.1f} L {v[1]/N:5.1f} | fail-ep W {v[2]/N:5.1f} L {v[3]/N:5.1f}')
print('\n## mid-group targeting: per game mid episodes by team; gems per own-cap episode')
for team in 'WL':
    m = [e for e in eps if e['team'] == team and e['side'] == 'mid']
    oc = [e for e in m if e['out'] == 'own_cap']
    print(team, f'mid eps {len(m)/N:.2f}, own_cap {len(oc)/N:.2f}, total group gems captured per cap-ep {sum(e["cap_total"] for e in oc)/max(1,len(oc)):.1f}, enemy_cap {sum(e["out"]=="enemy_cap" for e in m)/N:.2f}, none {sum(e["out"]=="none" for e in m)/N:.2f}')
