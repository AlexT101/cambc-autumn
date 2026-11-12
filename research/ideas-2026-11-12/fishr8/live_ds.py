"""Unzip our live scrims against Fish (games.jsonl) into ~/tmp-offload/fishr8/live/raw and write rows-<ref>.json
(match id -> version, map, side, result, picks, ...).   py live_ds.py REF [MINVERSION]   (REF r2, r8, ...)"""
import json, os, sys, zipfile
R = '/home/ubuntu/cambc-autumn/'; OUT = os.path.expanduser('~/tmp-offload/fishr8/live')
ref = sys.argv[1]; vmin = int(sys.argv[2]) if len(sys.argv) > 2 else 0
rows = {}; miss = 0
for l in open(R + 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    g = json.loads(l)
    if g.get('opp_name') != 'Intercontinental Fish' or g.get('refset') != ref or g.get('status') != 'finished': continue
    if g['version'] < vmin or not g.get('replay'): continue
    dst = f'{OUT}/raw/{g["match"]}.repl26a'
    if not os.path.exists(dst):
        try:
            with zipfile.ZipFile(R + g['replay']) as z: open(dst, 'wb').write(z.read('replay.repl26a'))
        except Exception: miss += 1; continue
    rows[g['match']] = {k: g.get(k) for k in ('version', 'map', 'side', 'result', 'our_picks', 'opp_picks', 'rounds',
                                          'created', 'group', 'task', 'our_gems', 'opp_gems', 'our_kills', 'opp_kills', 'our_gold', 'opp_gold', 'end_reason')}
json.dump(rows, open(f'{OUT}/rows-{ref}.json', 'w'))
print(len(rows), 'games', miss, 'missing')
