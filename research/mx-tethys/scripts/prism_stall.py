"""Why chased Prisms (first hit to death >= 8 rounds) stand still: stunned, own attack/cast (both spend the walk for a
ranged champion / exclusive spells), or neither.  py prism_stall.py ROWS.jsonl"""
import gzip, json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import prism_mech as pm
rows = [json.loads(l) for l in open(sys.argv[1])]
c = Counter(); tot = 0
for x in rows:
    if x['killer'] == 'camp' or not x['first_hit'] or x['D'] - x['first_hit'][0] < 8: continue
    dd = pm.WT / 'replays/.analysis' / x['dir']
    act = set()
    for l in gzip.open(dd / 'events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e.get('a') == x['v'] and e['k'] in ('attack', 'cast') and e.get('ab') != 'Dash': act.add(e['r'])
    tr = {r['r']: r for r in x['trace']}
    rs = [r for r in range(x['first_hit'][0], x['D']) if r in tr and r + 1 in tr]
    for r in rs:
        tot += 1
        moved = tr[r]['p'] != tr[r + 1]['p']
        k = 'moved' if moved else 'stunned' if tr[r + 1]['turn'] == 5 or tr[r]['turn'] == 5 else 'attacked/cast' if (r + 1) in act or r in act else 'idle/other'
        c[k] += 1
print(tot, {k: f'{v / tot * 100:.0f}%' for k, v in c.most_common()})
