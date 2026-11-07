"""CAND (oc-mode-p2) minus REF (oc-base19) in the same games: shopping, banking, deaths, farm. CAND is side A when
the replay name ends -12. usage: mech_ab.py ANALYSIS_DIR"""
import gzip, json, os, sys
import numpy as np
rows = []
for g in os.listdir(sys.argv[1]):
    d = os.path.join(sys.argv[1], g)
    try:
        m = json.load(open(os.path.join(d, 'meta.json')))
    except Exception:
        continue
    src = os.path.basename(m['source']).replace('.repl26a', '')
    ct = 0 if src.endswith('-12') else 1
    per = [dict(spent=0.0, earned=0.0, collected=0, deaths=0, bag_lost=0, big_deaths=0, tributes=0, trib_gems=0, shop_trips=0) for _ in range(2)]
    team = {c['id']: c['team'] for c in m['champions']}
    for c in m['champions']:
        s = c['stats']; p = per[c['team']]
        p['spent'] += s['spentGold']; p['earned'] += s['earnedGold']; p['collected'] += s['collectedGems']
    for line in gzip.open(os.path.join(d, 'events.jsonl.gz'), 'rt'):
        if '"death"' not in line and '"tribute_end"' not in line and '"shop"' not in line:
            continue
        e = json.loads(line)
        if e['k'] == 'death':
            p = per[team[e['v']]]; p['deaths'] += 1; p['bag_lost'] += e.get('gems', 0); p['big_deaths'] += e.get('gems', 0) >= 50
        elif e['k'] == 'tribute_end':
            p = per[team[e['a']]]; p['tributes'] += 1; p['trib_gems'] += e['gems']
        elif e['k'] == 'shop':
            per[team[e['a']]]['shop_trips'] += 1
    for p in per:
        p['unspent'] = p['earned'] - p['spent']
        p['gems_per_trib'] = p['trib_gems'] / p['tributes'] if p['tributes'] else np.nan
    res = m['result']
    rows.append(dict(win=float(res['winner'] == ct), c=per[ct], r=per[1 - ct], rounds=res['rounds']))
print('games', len(rows), 'CAND win', round(100 * np.mean([x['win'] for x in rows]), 1))
print(f'{"metric":14}{"CAND":>10}{"REF":>10}{"diff":>9}{"95%":>8}')
for k in ['spent', 'unspent', 'earned', 'shop_trips', 'collected', 'tributes', 'gems_per_trib', 'deaths', 'bag_lost', 'big_deaths']:
    c = np.array([x['c'][k] for x in rows], float); r = np.array([x['r'][k] for x in rows], float)
    ok = ~(np.isnan(c) | np.isnan(r)); dd = c[ok] - r[ok]
    print(f'{k:14}{np.mean(c[ok]):10.1f}{np.mean(r[ok]):10.1f}{dd.mean():+9.2f}{1.96*dd.std()/np.sqrt(len(dd)):8.2f}')
