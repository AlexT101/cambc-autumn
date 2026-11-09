# Stage v87+ finished live scrims vs Fish/Mite as .repl26a; write games.json keyed by match id.
import json, zipfile, os
N = '/home/ubuntu/tmp-offload/nukeguard2/'; R = '/home/ubuntu/cambc-autumn/'
games = {}
for l in open(R + 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    r = json.loads(l)
    if r.get('status') != 'finished' or r['version'] < 83 or not os.path.exists(R + r['replay']): continue
    if r['opp_name'] not in ('Intercontinental Fish', 'Mite'): continue
    games[r['match']] = dict(version=r['version'], opp=r['opp_name'][:4], side=r['side'], result=r['result'], map=r['map'],
                             our=r['our_picks'], their=r['opp_picks'])
    if r['version'] < 87: continue
    f = N + f"repl/{r['match']}.repl26a"
    if not os.path.exists(f):
        z = zipfile.ZipFile(R + r['replay']); n = [x for x in z.namelist() if x.endswith('.repl26a')][0]
        open(f, 'wb').write(z.read(n))
json.dump(games, open(N + 'games.json', 'w'))
print(len(games))
