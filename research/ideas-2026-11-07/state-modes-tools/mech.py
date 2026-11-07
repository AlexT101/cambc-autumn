# Mechanism metrics of extracted games, CAND (team named `cand`) minus REF, by factorial level.
# usage: mech.py ANALYSIS_DIR CAND_NAME [KEYS.json --pass2]   (without KEYS: a plain A/B, CAND - REF means)
import gzip, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from draws import levels

root, cand = sys.argv[1], sys.argv[2]
keys = None
if len(sys.argv) > 3:
    keys = {k['map']: k for k in json.load(open(sys.argv[3]))}
STATES = ['even', 'ahead', 'behind']; KNOBS = ['fight_risk', 'kill_value', 'bank', 'shop', 'camp']

def game(d):
    m = json.load(open(os.path.join(d, 'meta.json')))
    names = [t['name'] for t in m['teams']]
    if names.count(cand) != 1: return None
    ct = names.index(cand)
    per = [dict(deaths=0, home_deaths=0, bag_lost=0, big_bag_deaths=0, camp_deaths=0, gold=0.0, spent=0.0, collected=0, tributed=0) for _ in range(2)]
    for c in m['champions']:
        s = c['stats']; p = per[c['team']]
        p['gold'] += s['earnedGold']; p['spent'] += s['spentGold']; p['collected'] += s['collectedGems']; p['tributed'] += s['submittedGems']
    W, H = m['map']['width'], m['map']['height']
    with gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt') as f:
        for line in f:
            if '"death"' not in line: continue
            e = json.loads(line)
            if e['k'] != 'death': continue
            p = per[e['t']]
            p['deaths'] += 1; p['bag_lost'] += e.get('gems', 0)
            if e.get('gems', 0) >= 50: p['big_bag_deaths'] += 1
            if e.get('cause') != 'Attack': p['camp_deaths'] += 1
    res = m['result']
    win = 0.5 if res['winner'] not in (0, 1) else float(res['winner'] == ct)
    return dict(map=m['map']['name'], cand_a=ct == 0, win=win, rounds=res['rounds'],
                **{k: per[ct][k] - per[1 - ct][k] for k in per[0]}, **{'c_' + k: per[ct][k] for k in per[0]})

rows = []
for g in os.listdir(root):
    d = os.path.join(root, g)
    if os.path.isfile(os.path.join(d, 'meta.json')):
        try:
            r = game(d)
            if r: rows.append(r)
        except Exception:
            pass
print('games', len(rows))
metrics = ['win', 'deaths', 'bag_lost', 'big_bag_deaths', 'camp_deaths', 'gold', 'spent', 'collected', 'tributed', 'rounds']
def ci(x):
    x = np.asarray(x, float); return x.mean(), 1.96 * x.std() / np.sqrt(len(x))
for k in metrics + ['c_deaths', 'c_bag_lost', 'c_gold']:
    mu, h = ci([r[k] for r in rows]); print(f'{k:16s} {mu:+9.2f} +- {h:.2f}')
if keys:
    print('\nper cell: metric mean at level +1 minus level -1 (+-95%)')
    for s in range(3):
        for k in range(5):
            out = []
            for met in ['win', 'deaths', 'bag_lost', 'gold', 'tributed']:
                lv = [levels(keys[r['map']], r['cand_a'], S=3, K=5)[s][k] if r['map'] in keys else 0 for r in rows]
                a = [r[met] for r, l in zip(rows, lv) if l == 1]; b = [r[met] for r, l in zip(rows, lv) if l == -1]
                d = np.mean(a) - np.mean(b); h = 1.96 * np.sqrt(np.var(a) / len(a) + np.var(b) / len(b))
                out.append(f'{met} {d:+.2f}({h:.2f})')
            print(f'{STATES[s]}.{KNOBS[k]:11s} ' + '  '.join(out))
