"""Champion kills by bag: who takes the victim's bag, and how often our Prism stood near a non-Prism ally's kill
(mirror; W/L = the killer's side). Usage: kill_bags.py ANALYSIS_ROOT SOURCE_SUBSTR [MAX_GAMES]"""
import gzip, json, sys
from collections import Counter
from pathlib import Path
root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
n = 0; c = Counter()
for dd in sorted(root.iterdir()):
    mf = dd / 'meta.json'
    if not mf.exists(): continue
    m = json.loads(mf.read_text())
    if bname not in (m.get('source') or ''): continue
    try:
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
        R = json.load(gzip.open(dd / 'rounds.json.gz', 'rt'))
    except Exception: continue
    n += 1
    if n > mx: break
    w = m['result']['winner']
    name = {x['id']: x['name'] for x in m['champions']}; team = {x['id']: x['team'] for x in m['champions']}
    ch = {x['id']: x for x in R['champions']}
    prism = {team[i]: i for i in name if name[i] == 'Prism'}
    for e in ev:
        if e['k'] != 'death' or e['v'] not in team or e.get('linked') is not None: continue
        k = e.get('by')
        if k not in team or team[k] == team[e['v']]: continue
        side = 'W' if team[k] == w else 'L'; g = e.get('gemsTo', e.get('gems', 0)) or 0
        ph = 'r<=300' if e['r'] <= 300 else 'r301-600' if e['r'] <= 600 else 'r601+'
        c[(side, 'kills')] += 1; c[(side, 'gems')] += g; c[(side, ph, 'gems')] += g
        if name[k] == 'Prism':
            c[(side, 'prism_kill_gems')] += g; continue
        p = prism.get(team[k])
        if p is None: c[(side, 'noprism_gems')] += g; continue
        i = e['r'] - 1; pc = ch[p]
        if i >= len(pc['alive']) or not pc['alive'][i]: c[(side, 'prism_dead_gems')] += g; continue
        d = max(abs(pc['x'][i] - e['at'][0]), abs(pc['y'][i] - e['at'][1]))
        dsq = (pc['x'][i] - e['at'][0]) ** 2 + (pc['y'][i] - e['at'][1]) ** 2
        b = 'd2<=16' if dsq <= 16 else 'd2<=36' if dsq <= 36 else 'd2<=64' if dsq <= 64 else 'far'
        c[(side, 'ally_kill_gems', b)] += g; c[(side, 'ally_kills', b)] += 1
        c[(side, 'ally_kill_gems', b, ph)] += g
print('games', n)
for k in sorted(c, key=str): print(*k, f'{c[k]/n:.2f}', sep='\t')
