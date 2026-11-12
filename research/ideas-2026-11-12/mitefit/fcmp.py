"""Fight fidelity table: live (one of our versions) against local runs, on the same (map, side) cells, from fstats.py.
    py fcmp.py [--ver 116] RUN...   (RUN = a mitefit/fstats/*.jsonl stem)"""
import json, os, sys, math
M = os.path.expanduser('~/tmp-offload/mitefit/fstats')
argv = sys.argv[1:]; ver = 116
if '--ver' in argv: i = argv.index('--ver'); ver = int(argv[i + 1]); del argv[i:i + 2]
live = [x for x in map(json.loads, open(f'{M}/live.jsonl')) if x['version'] == ver]
cells = {(x['map'], x['side']) for x in live}
cols = [('live', live)] + [(r, [x for x in map(json.loads, open(f'{M}/{r}.jsonl')) if (x['map'], x['side']) in cells]) for r in argv]

def mean(gs, f):
    xs = [v for v in (f(g) for g in gs) if v is not None]
    if len(xs) < 2: return '-'
    m = sum(xs) / len(xs); se = math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1) / len(xs))
    return f'{m:.2f} ±{1.96 * se:.2f}'

def ratio(gs, s, a, b):
    A = sum(g[s].get(a, 0) for g in gs); B = sum(g[s].get(b, 0) for g in gs)
    return f'{A / B:.3f} ({B})' if B else '-'

rows = []
for s, who in (('m', 'Mite'), ('o', 'ours')):
    rows += [
        (f'{who} win %', lambda gs, s=s: f"{100 * sum((g['mite_win'] == (s == 'm')) for g in gs) / len(gs):.1f}"),
        (f'{who} kills', lambda gs, s=s: mean(gs, lambda g: g[s].get('kills', 0))),
        (f'{who} deaths', lambda gs, s=s: mean(gs, lambda g: g[s].get('deaths', 0))),
        (f'{who} Vesper kills (has Vesper)', lambda gs, s=s: mean(gs, lambda g: g[s].get('vesper_kills', 0) if g[s].get('has_vesper') else None)),
        (f'{who} Vesper kills in its wins', lambda gs, s=s: mean(gs, lambda g: g[s].get('vesper_kills', 0) if g[s].get('has_vesper') and g['mite_win'] == (s == 'm') else None)),
        (f'{who} Vesper deaths (has Vesper)', lambda gs, s=s: mean(gs, lambda g: g[s].get('vesper_deaths', 0) if g[s].get('has_vesper') else None)),
        (f'{who} Prism deaths (has Prism)', lambda gs, s=s: mean(gs, lambda g: g[s].get('prism_deaths', 0) if g[s].get('has_prism') else None)),
        (f'{who} deaths with bag 11+', lambda gs, s=s: mean(gs, lambda g: g[s].get('deaths_bag11', 0))),
        (f'{who} champion damage done', lambda gs, s=s: mean(gs, lambda g: g[s].get('dmg_done', 0))),
        (f'{who} kills / engagement', lambda gs, s=s: ratio(gs, s, 'eng_kills', 'eng')),
        (f'{who} engagements won (more kills) / engagement', lambda gs, s=s: ratio(gs, s, 'eng_won', 'eng')),
        (f'{who} engagements started / engagement', lambda gs, s=s: ratio(gs, s, 'eng_first', 'eng')),
        (f'{who} kills / engagement it started', lambda gs, s=s: ratio(gs, s, 'first_kills', 'eng_first')),
        (f'{who} losses / engagement it started', lambda gs, s=s: ratio(gs, s, 'first_lost', 'eng_first')),
    ]
    for k in ('lo', 'mid', 'hi', 'lo_bag', 'mid_bag', 'hi_bag'):
        rows.append((f'{who} retreat after a hit, health {k}', lambda gs, s=s, k=k: ratio(gs, s, 'ret_' + k, 'hit_' + k)))
rows.insert(0, ('engagements a game', lambda gs: mean(gs, lambda g: g['m'].get('eng', 0))))
print(f'v{ver} cells {len(cells)}; games ' + ', '.join(f'{n} {len(g)}' for n, g in cols))
print('| stat | ' + ' | '.join(n for n, _ in cols) + ' |'); print('|---' * (len(cols) + 1) + '|')
for name, f in rows: print(f'| {name} | ' + ' | '.join(f(g) for _, g in cols) + ' |')
