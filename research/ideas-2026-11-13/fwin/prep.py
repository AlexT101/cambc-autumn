"""Unzip downloaded Fish replays (~/tmp-offload/fwin/dl/<match>.zip) into others/raw and write others/frows.json
(match id -> fish team index, opp, map, created, kind)."""
import json, os, zipfile, glob
H = os.path.expanduser('~/tmp-offload/fwin')
rows = {r['match_id']: r for r in json.load(open(f'{H}/rows.json'))}
os.makedirs(f'{H}/others/raw', exist_ok=True)
out = {}; bad = 0
for z in glob.glob(f'{H}/dl/*.zip'):
    mid = os.path.basename(z)[:-4]; dst = f'{H}/others/raw/{mid}.repl26a'
    if not os.path.exists(dst):
        try:
            with zipfile.ZipFile(z) as zf: open(dst, 'wb').write(zf.read('replay.repl26a'))
        except Exception: bad += 1; continue
    r = rows[mid]
    out[mid] = {'fish': 0 if r['f_side'] == 'a' else 1, 'opp': r['opp'], 'map': r['map'], 'created': r['created_at'], 'kind': r['kind']}
json.dump(out, open(f'{H}/others/frows.json', 'w'))
print(len(out), 'games', bad, 'bad zips')
