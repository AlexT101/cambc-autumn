"""Q1: Prism hunt opportunities (stronger Prism S sees weaker V at 5-9) from pd_rows.pkl."""
import pickle
from collections import Counter

G = pickle.load(open('research/mx-rhea/scripts/pd_rows.pkl', 'rb'))
E = [e for g in G for e in g['episodes']]
n = len(E)
def pct(a, b): return f'{a}/{b} ({100 * a / b:.1f}%)' if b else f'{a}/0'
def rate(sel, f=lambda e: e['died']): return pct(sum(1 for e in sel if f(e)), len(sel))

print('games with both Prisms', len(G), 'episodes', n, 'per game', f'{n / len(G):.2f}')
print('games with >=1 episode', sum(1 for g in G if g['episodes']))
print('start < 400:', sum(1 for e in E if e['r0'] < 400), ' >= 400:', sum(1 for e in E if e['r0'] >= 400))
print('episode length (opp rounds) median', sorted(e['n'] for e in E)[n // 2], ' d0', Counter(e['d0'] for e in E))
print('V died within 20:', rate(E), ' by', Counter(e['by'] for e in E if e['died']))
print('S died within 20:', rate(E, lambda e: e['Sdied']), ' both:', rate(E, lambda e: e['Sdied'] and e['died']))
print('S closed to <=4:', rate(E, lambda e: e['closed']))
print('  V death | closed', rate([e for e in E if e['closed']]), ' | not closed', rate([e for e in E if not e['closed']]))
print('S team won game:', rate(E, lambda e: e['Swin']))
print('  S team won | V died', rate([e for e in E if e['died']], lambda e: e['Swin']), ' | V survived', rate([e for e in E if not e['died']], lambda e: e['Swin']))
print('\n(a) allies of S within 8 of V at start (excl S):')
for k in range(5):
    sel = [e for e in E if min(e['allies'], 4) == k]
    print(f'  {k}{"+" if k == 4 else ""}: n={len(sel):4d}  V died {rate(sel)}  S closed {rate(sel, lambda e: e["closed"])}  S died {rate(sel, lambda e: e["Sdied"])}')
print('\n(b) an S ally on the escape side (path distance to V spawn < V\'s), among episodes with >=1 ally within 8:')
for lab, key in (('path', 'esc'), ('cheb-to-centre', 'esc_c')):
    for esc in (False, True):
        sel = [e for e in E if e['allies'] >= 1 and (e[key] > 0) == esc]
        print(f'  [{lab}] escape-side ally={esc!s:5}: n={len(sel):4d}  V died {rate(sel)}  closed {rate(sel, lambda e: e["closed"])}')
print('\n(a)x(b) path version: V death rate')
for k in (1, 2, 3):
    row = []
    for esc in (False, True):
        sel = [e for e in E if min(e['allies'], 3) == k and (e['esc'] > 0) == esc]
        row.append(f'esc={esc!s:5} {rate(sel)}')
    print(f'  allies {k}{"+" if k == 3 else ""}: ' + '   '.join(row))
print('\nV allies within 8 of V at start:')
for k in range(4):
    sel = [e for e in E if min(e['vallies'], 3) == k]
    print(f'  {k}{"+" if k == 3 else ""}: n={len(sel):4d}  V died {rate(sel)}')
print('\nnet numbers (S allies - V allies within 8 of V):')
for k in range(-3, 4):
    sel = [e for e in E if max(-3, min(3, e['allies'] - e['vallies'])) == k]
    print(f'  {k:+d}: n={len(sel):4d}  V died {rate(sel)}  S died {rate(sel, lambda e: e["Sdied"])}')
print('\nV escape (within 20 rounds, before death):')
print('  reached own spawn', rate(E, lambda e: e['reached_sp']), ' regrouped (2+ allies within 3)', rate(E, lambda e: e['regroup']),
      ' either', rate(E, lambda e: e['reached_sp'] or e['regroup']))
for lab, f in (('reached spawn', lambda e: e['reached_sp']), ('regrouped only', lambda e: e['regroup'] and not e['reached_sp']),
               ('neither', lambda e: not e['regroup'] and not e['reached_sp'])):
    sel = [e for e in E if f(e)]
    print(f'  {lab:15s} n={len(sel):4d} V died {rate(sel)}')
print('\nV path distance to own spawn at start:')
for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 25), (25, 999)):
    sel = [e for e in E if lo <= e['dvsp'] < hi]
    print(f'  [{lo},{hi}): n={len(sel):4d} V died {rate(sel)}  reached spawn {rate(sel, lambda e: e["reached_sp"])}')
print('\nFocus ratio S/V at start:')
for lo, hi in ((1.2, 1.5), (1.5, 2), (2, 3), (3, 99)):
    sel = [e for e in E if lo <= e['fS'] / e['fV'] < hi]
    print(f'  [{lo},{hi}): n={len(sel):4d} V died {rate(sel)}  closed {rate(sel, lambda e: e["closed"])}')
print('\nV hp fraction at start:')
for lo, hi in ((0, .4), (.4, .7), (.7, 1.01)):
    sel = [e for e in E if lo <= e['hpV'] < hi]
    print(f'  [{lo},{hi}): n={len(sel):4d} V died {rate(sel)}')
print('\nS branch at start:', Counter(e['bS'] for e in E).most_common())
for b, _ in Counter(e['bS'] for e in E).most_common(7):
    sel = [e for e in E if e['bS'] == b]
    print(f'  S={b}: n={len(sel):4d} closed {rate(sel, lambda e: e["closed"])} V died {rate(sel)}')
print('V branch at start:', Counter(e['bV'] for e in E).most_common())
print('V saw S at start:', rate(E, lambda e: e['seenV']), ' V died | V saw S', rate([e for e in E if e['seenV']]), ' | unseen', rate([e for e in E if not e['seenV']]))
print('\nbefore/after 400:')
for lab, f in (('<400', lambda e: e['r0'] < 400), ('>=400', lambda e: e['r0'] >= 400)):
    sel = [e for e in E if f(e)]
    print(f'  {lab}: n={len(sel)} per game {len(sel) / len(G):.2f}  V died {rate(sel)} closed {rate(sel, lambda e: e["closed"])}')
# per game: first episode only
F = [g['episodes'] and min(g['episodes'], key=lambda e: e['r0']) for g in G]
F = [e for e in F if e]
print('\nfirst episode per game: n', len(F), ' V died', rate(F), ' closed', rate(F, lambda e: e['closed']), ' S team won', rate(F, lambda e: e['Swin']))
