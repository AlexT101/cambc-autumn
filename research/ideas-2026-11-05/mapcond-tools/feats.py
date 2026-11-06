"""Map features (draft-time knowable) for the SPSA pools and the A/B suites analysed (mapgen metrics: index.json or check)."""
import json, os, math, glob
from pathlib import Path
ROOT = Path('/home/ubuntu/cambc-autumn'); W = Path(os.environ.get('MAPCOND_DIR', '.'))
ABS = ['oct-tuned-vs-base1', 'oct-tuned-vs-astraeus', 'oct-base1-vs-astraeus', 'oct-tuned-vs-proteus', 'oct-base1-vs-proteus', 'oct-mid-vs-base1',
       'oc3-tuned3-vs-combo2-confirm', 'oc3-tuned3-vs-combo2-confirm2', 'oc3-tuned3-vs-combo2-varied', 'ocean-d5-vs-ast', 'oport-fix',
       'v2-conf-f5', 'v2-conf2-f5sf300mc', 'oc3-vs-astr-now-1105', 'oc3-vs-panel-astraeus', 'oc4-ast', 'ceil-5b66bde', 'gv-farm']
ABS += [p.name for p in (ROOT / 'replays/ab').glob('oc3-p*-*') if p.is_dir()]
dirs = {ROOT / d for d in ['maps/suites/fresh/fresh-%d' % s for s in range(517000, 517020)]}
for ab in ABS:
    for s in json.load(open(ROOT / 'replays/ab' / ab / 'summary.json'))['suites']:
        for m in json.load(open(ROOT / s['batch'] / 'results.json'))['matches']:
            p = Path(m['map']).resolve().parent
            dirs.add(p if p.exists() else ROOT / 'maps/suites/fresh' / p.name)
raw = {}
for line in list(open(W / 'ladder-check.jsonl')) + list(open(W / 'adgato.jsonl')):
    r = json.loads(line)
    if r['metrics']: raw[Path(r['file']).name] = r['metrics']
for d in dirs:
    if (d / 'index.json').exists():
        for m in json.load(open(d / 'index.json'))['maps']: raw[m['file']] = m['metrics']
def f(m):
    return {'log_area': math.log(m['area']), 'picks': m['picks'], 'sym_rot': float(m['sym'] == 'rotational'),
            'spawn_dist': m['spawn_dist'], 'camp_density': m['camp_density'], 'log_gems': math.log(max(1, m['gems_side'])),
            'big_share': m['big_share'], 'contested': m['contested_share'], 'altars': m['altars'],
            'sym': m['sym'], 'camps_side': m['camps_side']}
out = {k: f(m) for k, m in raw.items()}
json.dump(out, open(W / 'features.json', 'w'))
print(len(out), 'maps from', len(dirs), 'dirs')
