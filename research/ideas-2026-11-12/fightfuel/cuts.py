"""Shortcuts by the Prism's decision on fight turns, and the fuel left when they fire: python3 cuts.py BATCHGLOB [--who=prism|other|all]"""
import collections, sys
import fzread
from instr_ids import IDS

who = 'prism'
for a in sys.argv[1:]:
    if a.startswith('--who='): who = a[6:]
R = fzread.rows([a for a in sys.argv[1:] if not a.startswith('--')])
R = [r for r in R if r['round'] > 2 and r['hp'] >= 0 and r['seen'] > 0 and (who == 'all' or r['prism'] == (who == 'prism'))]
games = len({r['game'] for r in R})
print(f'{len(R)} fight turns of {who} in {games} games ({len(R) / games:.1f} a game)')
dec = collections.Counter(r['dec'] for r in R)
cuts = sorted({c for r in R for c in r['cuts']}, key=lambda c: -sum(1 for r in R if c in r['cuts']))[:12]
print('decision  turns/game  OOF%   ' + '  '.join(f'{c[:14]:>14s}' for c in cuts) + '   (per 1000 turns of the decision)')
for d, n in dec.most_common(12):
    S = [r for r in R if r['dec'] == d]
    print(f'   {d}     {n / games:8.2f}  {100 * sum(1 for r in S if r["oof"] is not None) / n:5.2f}   ' + '  '.join(f'{1000 * sum(1 for r in S if c in r["cuts"]) / n:14.1f}' for c in cuts))
print('\nper game, by enemies in sight: turns, any cut, OOF')
for k in (1, 2, 3, 4, 5):
    S = [r for r in R if min(r['seen'], 5) == k]
    if S: print(f'  {k}{"+" if k == 5 else " "} {len(S) / games:7.2f}  cut {sum(1 for r in S if r["cuts"] - {"out-of-fuel"}) / games:6.2f}  oof {sum(1 for r in S if r["oof"] is not None) / games:6.3f}   near<=5: {sum(1 for r in S if r["near"] <= 5) / games:6.2f}')
