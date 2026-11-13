"""Per champion type: capture shares, tributes, gems per tribute, rounds alive carrying, rounds carrying and moving,
deaths carrying, per game. Mirror (winner/loser)."""
import gzip, json, sys
from collections import defaultdict
from pathlib import Path
root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
acc = defaultdict(lambda: defaultdict(float)); n = 0
for dd in sorted(root.iterdir()):
    mf = dd / 'meta.json'
    if not mf.exists(): continue
    m = json.loads(mf.read_text())
    if bname not in (m.get('source') or ''): continue
    try:
        R = json.load(gzip.open(dd / 'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception: continue
    n += 1
    if n > mx: break
    w = m['result']['winner']
    names = {c['id']: c['name'] for c in m['champions']}
    team = {c['id']: c['team'] for c in m['champions']}
    key = lambda cid: ('W' if team[cid] == w else 'L', names[cid])
    for c in R['champions']:
        k = key(c['id']); acc[k]['games'] += 1
        for i in range(1, len(R['round'])):
            if c['alive'][i] and (c['gems'][i] or 0) > 0:
                acc[k]['carry'] += 1
                if c['x'][i] != c['x'][i-1] or c['y'][i] != c['y'][i-1]: acc[k]['carrymove'] += 1
                if R['round'][i] <= 300: acc[k]['carry300'] += 1
    for e in ev:
        if e['k'] == 'capture':
            for cid, gm, gd in e['shares']:
                if cid in team: acc[key(cid)]['shares'] += 1; acc[key(cid)]['capgems'] += gm; acc[key(cid)]['capgold'] += gd
        elif e['k'] == 'tribute_end' and e['a'] in team:
            acc[key(e['a'])]['trib'] += 1; acc[key(e['a'])]['tribgems'] += e['gems']
        elif e['k'] == 'tribute_start' and e['a'] in team:
            acc[key(e['a'])]['tstart'] += 1
        elif e['k'] == 'death' and e['v'] in team:
            acc[key(e['v'])]['deaths'] += 1; acc[key(e['v'])]['dgems'] += e.get('gems') or 0
        elif e['k'] == 'recall_end' and e['a'] in team:
            acc[key(e['a'])]['recalls'] += 1
print('games', n)
cols = ['shares', 'capgems', 'capgold', 'tstart', 'trib', 'tribgems', 'carry', 'carry300', 'carrymove', 'recalls', 'deaths', 'dgems']
print('type side', *cols, 'gems/trib', sep='\t')
for k in sorted(acc, key=lambda k: (k[1], k[0])):
    a = acc[k]; g = max(1, a['games'])
    print(f'{k[1][:10]} {k[0]}', *[f'{a[c]/g:.1f}' for c in cols], f"{a['tribgems']/max(1,a['trib']):.0f}", sep='\t')
