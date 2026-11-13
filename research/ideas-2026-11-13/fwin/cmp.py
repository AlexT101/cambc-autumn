"""Winners vs losers against Fish r8, overall and within cells (map, Fish side) that hold both outcomes.
    py cmp.py FEAT.jsonl [FEAT2.jsonl ...] [--team NAME] [--keys k1,k2]"""
import json, sys, collections, math
args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] not in ('--team', '--keys')]
team = sys.argv[sys.argv.index('--team') + 1] if '--team' in sys.argv else None
G = []
for f in args:
    if f == team: continue
    for l in open(f): G.append(json.loads(l))
if team: G = [g for g in G if g.get('opp') == team]
G = [g for g in G if g.get('has_v')]
print(len(G), 'games with a Fish Vesper; opp wins', sum(not g['fish_win'] for g in G))
def val(g, k):
    if k.startswith('d_'):   # Fish minus opponent
        a, b = g.get('f_' + k[2:]), g.get('o_' + k[2:])
        return None if a is None and b is None else (a or 0) - (b or 0)
    v = g.get(k)
    return v
C = (100, 200, 300, 500, 800)
keys = []
for c in C:
    keys += [f'd_earned_{c}', f'f_earned_{c}', f'o_earned_{c}', f'v_earned_{c}', f'd_gems_{c}', f'f_kills_{c}', f'o_kills_{c}', f'v_deaths_{c}', f'v_kills_{c}',
             f'f_capgold_all_{c}', f'o_capgold_all_{c}', f'o_capgold_enemy_{c}', f'f_capgold_enemy_{c}', f'o_capgold_mid_{c}', f'f_capgold_mid_{c}', f'o_gemslost_{c}', f'f_gemslost_{c}']
keys += ['f_trib1', 'o_trib1', 'f_ntrib100', 'o_ntrib100', 'v_greed', 'rounds', 'o_locks', 'f_locks']
if '--keys' in sys.argv: keys = sys.argv[sys.argv.index('--keys') + 1].split(',')
cell = collections.defaultdict(lambda: ([], []))
for g in G: cell[(g['map'], g['fish'])][0 if g['fish_win'] else 1].append(g)
mixed = [(L, W) for L, W in cell.values() if L and W]
print(len(mixed), 'mixed cells')
print(f"{'feature':24s} {'opp loses':>10s} {'opp wins':>10s} | {'within-cell diff (win - loss)':>30s}")
for k in keys:
    a = [val(g, k) for g in G if g['fish_win']]; b = [val(g, k) for g in G if not g['fish_win']]
    a = [x for x in a if x is not None]; b = [x for x in b if x is not None]
    if not a or not b: continue
    ds = []
    for L, W in mixed:
        x = [val(g, k) for g in L]; y = [val(g, k) for g in W]
        x = [t for t in x if t is not None]; y = [t for t in y if t is not None]
        if x and y: ds.append(sum(y) / len(y) - sum(x) / len(x))
    m = sum(ds) / len(ds) if ds else float('nan')
    se = math.sqrt(sum((d - m) ** 2 for d in ds) / max(1, len(ds) - 1) / max(1, len(ds))) if len(ds) > 1 else float('nan')
    print(f"{k:24s} {sum(a)/len(a):10.1f} {sum(b)/len(b):10.1f} | {m:+10.1f} ±{se:6.1f} (z {m/se if se else 0:+5.1f}, {len(ds)} cells)")
