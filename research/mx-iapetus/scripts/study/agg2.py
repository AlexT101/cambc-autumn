import json
from collections import Counter, defaultdict
G = [json.loads(l) for l in open('/tmp/mxi-study/farmwin.jsonl')]
N = len(G)
print('## retreat-branch rounds per game')
for team in 'WL':
    c = Counter()
    for g in G:
        for k, v in g['retreats'][team].items():
            c[tuple(k.split('|'))] += v
    tot = sum(c.values())
    nod = sum(v for k, v in c.items() if k[1] == 'nodmg')
    print(team, f'R rounds/game {tot/N:.1f}, no damage in next 5 rounds {nod/N:.1f} ({nod/tot:.0%})')
    by = Counter(); byn = Counter()
    for k, v in c.items():
        by[k[0]] += v
        if k[1] == 'nodmg': byn[k[0]] += v
    print('   by type (all / nodmg):', ', '.join(f'{k} {by[k]/N:.1f}/{byn[k]/N:.1f}' for k, _ in by.most_common()))
    band = Counter(); bandn = Counter()
    for k, v in c.items():
        band[(k[3], k[4])] += v
        if k[1] == 'nodmg': bandn[(k[3], k[4])] += v
    print('   by nearest enemy dist, seen (all / nodmg):', ', '.join(f'{k} {band[k]/N:.1f}/{bandn[k]/N:.1f}' for k in sorted(band)))
# split by loser dead rounds
print('\n## split by loser dead champion-rounds in window')
def dead(g, t): return sum(d['lost_rounds'] for d in g['deaths'] if d['team'] == t)
for lo, hi in ((0, 0), (1, 40), (41, 100), (101, 10**6)):
    S = [g for g in G if lo <= dead(g, 'L') <= hi]
    if not S: continue
    loc = Counter()
    for g in S:
        for c in g['caps']:
            loc[(c['team'], c['rel_L'])] += c['gems']
    k = len(S)
    gap = sum(g['parts']['farm'] for g in S)
    print(f'L dead {lo}-{hi}: games {k} ({k/N:.0%}), gap/game {gap/k:.1f} (share of total {gap/sum(g["parts"]["farm"] for g in G):.0%}); W dead {sum(dead(g,"W") for g in S)/k:.1f}; '
          + ' '.join(f'{a}{b} {loc[(a,b)]/k:.1f}' for a in 'WL' for b in ('own', 'mid', 'enemy')))
# Prism capture detail
print('\n## captures: gems per capture and sharers per capture, by team and location')
for team in 'WL':
    for side in ('own', 'mid', 'enemy'):
        cs = [c for g in G for c in g['caps'] if c['team'] == team and c['rel_L'] == side]
        if not cs: continue
        print(team, side, f'caps {len(cs)/N:.2f}/game, gems/cap {sum(c["gems"] for c in cs)/len(cs):.1f}, sharers/cap {sum(len(c["sharers"]) for c in cs)/len(cs):.2f}, with Prism {sum("Prism" in c["sharers"] for c in cs)/len(cs):.0%}')
# group types captured
print('\n## W-L capture gems per game by group type (top)')
ty = Counter()
for g in G:
    for c in g['caps']:
        ty[c['types']] += c['gems'] * (1 if c['team'] == 'W' else -1)
for k, v in ty.most_common(12): print(k, f'{v/N:.1f}')
