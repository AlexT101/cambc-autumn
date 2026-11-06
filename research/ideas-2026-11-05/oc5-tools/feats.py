"""Draft-time map features for oc5's pool and A/B suites: mapgen metrics (index.json, or `mapgen check --json` for the
ladder in $MC/ladder-check.jsonl + adgato.jsonl). Writes $MC/features.json keyed by path relative to the repo."""
import json, math, os, sys
from pathlib import Path
ROOT = Path('/home/ubuntu/cambc-autumn'); MC = Path(os.environ.get('MC', '/home/ubuntu/tmp-offload/tune5/mc'))
SEEDS = list(range(546000, 546020)) + list(range(546100, 546140)) + list(range(546200, 546210)) + list(range(546300, 546310))
raw = {}
for line in list(open(MC / 'ladder-check.jsonl')) + list(open(MC / 'adgato.jsonl')):
    r = json.loads(line)
    if r.get('metrics'): raw['maps/' + Path(r['file']).name] = r['metrics']
for s in SEEDS:
    d = ROOT / f'maps/suites/fresh/fresh-{s}'
    for m in json.load(open(d / 'index.json'))['maps']:
        raw[f'maps/suites/fresh/fresh-{s}/{m["file"]}'] = m['metrics']
def f(m):
    return {'log_area': math.log(m['area']), 'picks': m['picks'], 'sym_rot': float(m['sym'] == 'rotational'),
            'sym_vert': float(m['sym'] == 'vertical'), 'spawn_dist': m['spawn_dist'], 'camp_density': m['camp_density'],
            'log_gems': math.log(max(1, m['gems_side'])), 'log_gold': math.log(max(1, m['gold_side'])),
            'big_share': m['big_share'], 'contested': m['contested_share'], 'altars': m['altars'], 'bushes': m['bushes']}
out = {k: f(m) for k, m in raw.items()}
json.dump(out, open(MC / 'features.json', 'w'))
print(len(out), 'maps')
