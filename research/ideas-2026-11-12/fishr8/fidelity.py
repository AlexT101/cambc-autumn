"""Fidelity table: live Fish r8 vs bodies on the statistics that changed (stats/{m,f,v}-<name>.jsonl).
    py fidelity.py NAME...   (NAME: r8-all for live, or a run name)"""
import json, os, sys, statistics as st
S = os.path.expanduser('~/tmp-offload/fishr8/stats/')
def L(k, n): p = f'{S}{k}-{n}.jsonl'; return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def mean(v): v = [x for x in v if x is not None]; return st.mean(v) if v else float('nan')
rows = [('games', lambda m, f, v: len(m)),
        ('Fish win', lambda m, f, v: mean([g['mite_win'] for g in m])),
        ('Fish gold r100', lambda m, f, v: mean([g['m'].get('earned100') for g in m])),
        ('Fish gold r300', lambda m, f, v: mean([g['m'].get('earned300') for g in m])),
        ('Fish gold r600', lambda m, f, v: mean([g['m'].get('earned600') for g in m])),
        ('our gold r300', lambda m, f, v: mean([g['o'].get('earned300') for g in m])),
        ('Fish capture gold r300', lambda m, f, v: mean([g['m'].get('capgold300') for g in m])),
        ('Vesper share of capture gold r100', lambda m, f, v: mean([g.get('vshare_r100') for g in v if g['has_v']])),
        ('Vesper share all game', lambda m, f, v: mean([g.get('vshare_all') for g in v if g['has_v']])),
        ('Vesper Greed by game end', lambda m, f, v: mean([g.get('greed_round') is not None for g in v if g['has_v']])),
        ('Vesper Strength r400', lambda m, f, v: mean([g['v_str'][1] for g in v if g['has_v'] and g['rounds'] >= 400])),
        ('Vesper Strength r600', lambda m, f, v: mean([g['v_str'][2] for g in v if g['has_v'] and g['rounds'] >= 600])),
        ('Vesper max HP r600', lambda m, f, v: mean([g['v_hp'][2] for g in v if g['has_v'] and g['rounds'] >= 600])),
        ('Vesper deaths', lambda m, f, v: mean([g.get('v_deaths') for g in v if g['has_v']])),
        ('Vesper kills', lambda m, f, v: mean([g.get('v_kills') for g in v if g['has_v']])),
        ('our deaths', lambda m, f, v: mean([g['o'].get('deaths', 0) for g in m])),
        ('Fish deaths', lambda m, f, v: mean([g['m'].get('deaths', 0) for g in m])),
        ('share of our deaths by Vesper', lambda m, f, v: sum(g['killers'].get('Vesper Vale', 0) for g in v if g['has_v']) / max(1, sum(g['our_deaths'] for g in v if g['has_v']))),
        ('Fish tributes', lambda m, f, v: mean([g['m'].get('trib') for g in m])),
        ('Fish mean bag', lambda m, f, v: mean([g['m'].get('bag_mean') for g in m])),
        ('Fish first tribute', lambda m, f, v: mean([g['m'].get('first_trib') for g in m])),
        ('Fish kills / engagement', lambda m, f, v: sum(g['m'].get('eng_kills', 0) for g in f) / max(1, sum(g['m'].get('eng', 0) for g in f))),
        ('Fish mates within 5 r60', lambda m, f, v: mean([g['m'].get('coh_r60') for g in m])),
        ('rounds', lambda m, f, v: mean([g['rounds'] for g in m])),
        ]
D = [(n, L('m', n), L('f', n), L('v', n)) for n in sys.argv[1:]]
print('| stat | ' + ' | '.join(n.replace('fr-lab-emb6-c520-ps-', '').replace('-ladder-all', '') for n, *_ in D) + ' |'); print('|---' * (1 + len(D)) + '|')
for lab, fn in rows:
    vals = []
    for n, m, f, v in D:
        try: x = fn(m, f, v); vals.append(f'{x:.3f}' if isinstance(x, float) and abs(x) < 10 else f'{x:.0f}')
        except Exception: vals.append('-')
    print(f'| {lab} | ' + ' | '.join(vals) + ' |')
