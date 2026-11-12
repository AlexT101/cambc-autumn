"""Fidelity table: mean per-game statistics of the Mite side ('m') and ours ('o'), live against local runs, on the
same (map, side) cells.   py cmpstats.py [--ver 116] RUN...   (RUN = a mitefit/stats/*.jsonl stem)"""
import json, sys, os, math, collections
M = os.path.expanduser('~/tmp-offload/mitefit')
argv = sys.argv[1:]; ver = None
if '--ver' in argv: i = argv.index('--ver'); ver = int(argv[i + 1]); del argv[i:i + 2]
live = [json.loads(l) for l in open(f'{M}/live/stats.jsonl')]
if ver: live = [x for x in live if x['version'] == ver]
runs = {r: [json.loads(l) for l in open(f'{M}/stats/{r}.jsonl')] for r in argv}
cells = {(x['map'], x['side']) for x in live}
runs = {r: [x for x in v if (x['map'], x['side']) in cells] for r, v in runs.items()}
KEYS = ['clear_bodies200', 'vesper_gold100', 'coh_r20', 'coh_r60', 'caps300', 'capgold300', 'capgems300', 'earned100', 'earned300', 'earned600', 'trib', 'trib_gems', 'bag_med', 'bag_mean',
        'trib100', 'first_trib', 'deaths300', 'deaths', 'kills300', 'kills', 'died_gems', 'camp_deaths', 'conv', 'assist', 'coh5',
        'enemy_half', 'locks', 'crystals', 'wards', 'recalls', 'casts', 'casts_champ', 'att_champ', 'att_camp', 'prism', 'prism_maxbag', 'gems_final']
def mean(v):
    v = [x for x in v if x is not None]
    if not v: return None, 0
    m = sum(v) / len(v); s = math.sqrt(sum((x - m) ** 2 for x in v) / max(1, len(v) - 1)) / math.sqrt(len(v))
    return m, s
def f(ms):
    m, s = ms
    return '-' if m is None else (f'{m:.2f} ±{1.96*s:.2f}' if abs(m) < 10 else f'{m:.0f} ±{1.96*s:.0f}')
cols = [('live', live)] + list(runs.items())
print(f"Cells {len(cells)}; games: " + ', '.join(f'{n} {len(v)}' for n, v in cols))
print('| stat | ' + ' | '.join(n for n, _ in cols) + ' |'); print('|---' * (len(cols) + 1) + '|')
print('| Mite win % | ' + ' | '.join(f"{100*sum(x['mite_win'] for x in v)/max(1,len(v)):.1f}" for _, v in cols) + ' |')
print('| rounds | ' + ' | '.join(f(mean([x['rounds'] for x in v])) for _, v in cols) + ' |')
for side, lab in (('m', 'Mite'), ('o', 'ours')):
    for k in KEYS:
        print(f'| {lab} {k} | ' + ' | '.join(f(mean([x[side].get(k, 0) if k in x[side] else (0 if k not in ("clear_bodies200","vesper_gold100","coh_r20","coh_r60","conv","assist") else None) for x in v])) for _, v in cols) + ' |')
