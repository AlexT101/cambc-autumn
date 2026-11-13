"""Unspent gold and earned gold by champion type and phase, winner vs loser (mirror)."""
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
    try: R = json.load(gzip.open(dd / 'rounds.json.gz'))
    except Exception: continue
    n += 1
    if n > mx: break
    w = m['result']['winner']
    names = {c['id']: c['name'] for c in m['champions']}
    for c in R['champions']:
        side = 'W' if c['team'] == w else 'L'
        ty = names[c['id']]
        for i, r in enumerate(R['round']):
            ph = 'r1-300' if r <= 300 else 'r301-600' if r <= 600 else 'r601+'
            k = (side, ty, ph)
            acc[k]['gold'] += c['gold'][i] or 0
            acc[k]['n'] += 1
            acc[k]['alive'] += c['alive'][i]
        acc[(side, ty, 'end')]['earned'] += c['earned'][-1] or 0
        acc[(side, ty, 'end')]['games'] += 1
print('games', n)
tys = sorted(set(k[1] for k in acc))
print('type\tside\tunspent r1-300\tr301-600\tr601+\tearned/game')
for ty in tys:
    for s in 'WL':
        row = [f"{acc[(s,ty,ph)]['gold']/max(1,acc[(s,ty,ph)]['n']):.0f}" for ph in ('r1-300','r301-600','r601+')]
        e = acc[(s,ty,'end')]; print(ty, s, *row, f"{e['earned']/max(1,e['games']):.0f} ({e['games']:.0f})", sep='\t')
