"""Killer type -> victim type counts per game, winner/loser side of the victim (mirror), with round phases."""
import gzip, json, sys
from collections import defaultdict, Counter
from pathlib import Path
root = Path(sys.argv[1]); bname = sys.argv[2]; mx = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
c = Counter(); n = 0; ph = Counter()
for dd in sorted(root.iterdir()):
    mf = dd / 'meta.json'
    if not mf.exists(): continue
    m = json.loads(mf.read_text())
    if bname not in (m.get('source') or ''): continue
    try: ev = [json.loads(l) for l in gzip.open(dd / 'events.jsonl.gz', 'rt')]
    except Exception: continue
    n += 1
    if n > mx: break
    w = m['result']['winner']
    names = {x['id']: x['name'] for x in m['champions']}; team = {x['id']: x['team'] for x in m['champions']}
    for e in ev:
        if e['k'] != 'death' or e['v'] not in team or e.get('linked') is not None: continue
        if len(sys.argv) > 4 and e["r"] > int(sys.argv[4]): continue
        side = "W" if team[e["v"]] == w else "L"
        killer = names.get(e.get('by'), 'camp' if e.get('camp') is not None else '?')
        c[(side, names[e['v']], killer)] += 1
        r = e['r']; ph[(side, 'r<=300' if r <= 300 else 'r301-600' if r <= 600 else 'r601+')] += 1
print('games', n)
for (side, v, k), x in sorted(c.items(), key=lambda kv: -kv[1])[:40]:
    print(side, v, '<-', k, f'{x/n:.3f}', sep='\t')
print({k: round(v/n, 2) for k, v in sorted(ph.items())})
