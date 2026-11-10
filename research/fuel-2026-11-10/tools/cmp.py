"""cmp.py BASE.json CAND.json: paired per-game comparison at the real budget with bootstrap CIs (games resampled)."""
import json, sys, random, statistics
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
def key(g): return (g['map'], g['side'])
A = {key(g): g for g in a['games'] if 'error' not in g}; B = {key(g): g for g in b['games'] if 'error' not in g}
ks = sorted(set(A) & set(B))
def sc(g, skip=('out-of-fuel',)): return sum(v for k, v in (g.get('shortcuts') or {}).items() if k not in skip and 'SLOT' not in k)
def rows(G): return [(G[k].get('out_of_fuel') or 0, sc(G[k]), sum(G[k]['play']), len(G[k]['play'])) for k in ks]
RA, RB = rows(A), rows(B)
def tot(R, idx): return [sum(R[i][j] for i in idx) for j in range(4)]
def stats(idx):
    ta, tb = tot(RA, idx), tot(RB, idx)
    return (tb[0] / ta[0] - 1, tb[1] / ta[1] - 1, (tb[2] / tb[3]) / (ta[2] / ta[3]) - 1, (tb[0] / tb[3]) / (ta[0] / ta[3]) - 1, (tb[1] / tb[3]) / (ta[1] / ta[3]) - 1)
n = len(ks); base = stats(range(n)); rng = random.Random(1); bs = [stats([rng.randrange(n) for _ in range(n)]) for _ in range(400)]
names = ['OOF turns', 'shortcuts', 'mean fuel/turn', 'OOF per turn', 'shortcuts per turn']
ta, tb = tot(RA, range(n)), tot(RB, range(n))
print(f'{n} paired games; OOF {ta[0]} -> {tb[0]}; shortcuts {ta[1]} -> {tb[1]}; turns {ta[3]} -> {tb[3]}; mean {ta[2]/ta[3]:.0f} -> {tb[2]/tb[3]:.0f}')
for j, nm in enumerate(names):
    v = sorted(x[j] for x in bs)
    print(f'  {nm:20s} {100*base[j]:+6.2f}%  (95% CI {100*v[10]:+.2f} .. {100*v[389]:+.2f})')
same = sum(1 for k in ks if A[k].get('replay') == B[k].get('replay'))
print(f'  identical replays {same}/{n}')
