"""Unzip our live scrims against one Mite pin (games.jsonl) into ~/tmp-offload/mitefit/live/raw and write rows.json
(match id -> version, map, side, result, picks).   py live_ds.py [refset=r7]"""
import json, os, sys, zipfile
R = '/home/ubuntu/cambc-autumn/'; OUT = os.path.expanduser('~/tmp-offload/mitefit/live')
ref = sys.argv[1] if len(sys.argv) > 1 else 'r7'
rows = {}
for l in open(R + 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    g = json.loads(l)
    if g.get('opp_name') != 'Mite' or g.get('refset') != ref or g.get('status') != 'finished': continue
    dst = f'{OUT}/raw/{g["match"]}.repl26a'
    if not os.path.exists(dst):
        with zipfile.ZipFile(R + g['replay']) as z: open(dst, 'wb').write(z.read('replay.repl26a'))
    rows[g['match']] = {k: g[k] for k in ('version', 'map', 'side', 'result', 'our_picks', 'opp_picks', 'rounds',
                                          'created', 'group', 'our_gems', 'opp_gems', 'our_kills', 'opp_kills')}
json.dump(rows, open(f'{OUT}/rows-{ref}.json', 'w'))
print(len(rows), 'games')
