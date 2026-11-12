"""The Prism's deaths after fuel cuts: python3 hazard.py BATCHGLOB
For its fight turns (an enemy in sight within NEAR, default 5): the share dead within the next 3 rounds, by cut or
out-of-fuel on the turn, within strata of enemies in sight and health (so a cut is compared with turns as dangerous)."""
import collections, sys
import fzread

near = 5
R = fzread.rows([a for a in sys.argv[1:] if not a.startswith('--')])
by = collections.defaultdict(list)
for r in R:
    if r['prism']: by[(r['game'], r['handle'])].append(r)
rows = []
for k, S in by.items():
    S.sort(key=lambda r: r['round'])
    dead = [r['round'] for i, r in enumerate(S) if r['hp'] < 0 and i and S[i - 1]['hp'] >= 0]
    for r in S:
        if r['hp'] < 0 or r['seen'] == 0 or r['near'] > near or r['round'] <= 2: continue
        d = any(r['round'] < x <= r['round'] + 3 for x in dead)
        rows.append((r, d))
print(len(rows), 'Prism turns with an enemy within', near, '; dead within 3 rounds:', f'{100 * sum(d for _, d in rows) / len(rows):.2f}%')
def stratum(r): return (min(r['seen'], 4), 0 if r['hp'] < 40 else 1 if r['hp'] < 70 else 2)
base = collections.defaultdict(lambda: [0, 0])
for r, d in rows:
    b = base[stratum(r)]; b[0] += 1; b[1] += d
feats = {'out of fuel': lambda r: r['oof'] is not None, 'any cut': lambda r: bool(r['cuts'] - {'out-of-fuel'}), 'left after decide < 10k': lambda r: r['oof'] is None and r['left_decide'] < 10000}
for c in ('farm-partial-evaluation', 'chase-plan-fuel', 'step-guard-entry', 'prey-cut-short', 'esc-no-slack', 'esc-min-fuel', 'turn-order', 'turn-end-short'):
    feats[c] = (lambda c: lambda r: c in r['cuts'])(c)
print(f'{"feature":28s} turns   died%   expected% (same enemies and health)   ratio')
for name, f in feats.items():
    S = [(r, d) for r, d in rows if f(r)]
    if not S: continue
    exp = sum(base[stratum(r)][1] / base[stratum(r)][0] for r, _ in S) / len(S)
    got = sum(d for _, d in S) / len(S)
    print(f'{name:28s} {len(S):6d}  {100 * got:5.2f}   {100 * exp:5.2f}   {got / exp if exp else 0:5.2f}')
print('\nby decision (same strata):')
for dec in 'FCRTPBUG?':
    S = [(r, d) for r, d in rows if r['dec'] == dec]
    if len(S) < 50: continue
    exp = sum(base[stratum(r)][1] / base[stratum(r)][0] for r, _ in S) / len(S); got = sum(d for _, d in S) / len(S)
    print(f'  {dec} {len(S):6d}  {100 * got:5.2f}   {100 * exp:5.2f}   {got / exp if exp else 0:5.2f}')
    for c in ('chase-plan-fuel', 'step-guard-entry', 'esc-min-fuel', 'esc-no-slack', 'farm-partial-evaluation', 'prey-cut-short'):
        T = [(r, d) for r, d in S if c in r['cuts']]
        if len(T) < 40: continue
        e2 = sum(base[stratum(r)][1] / base[stratum(r)][0] for r, _ in T) / len(T); g2 = sum(d for _, d in T) / len(T)
        print(f'      with {c:24s} {len(T):6d}  {100 * g2:5.2f}   {100 * e2:5.2f}   {g2 / e2 if e2 else 0:5.2f}')
