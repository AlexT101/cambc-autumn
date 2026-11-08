# Stage finished scrim replays (versions given) into ~/tmp-offload/bigl/repl/<match>.repl26a; write games.json keyed by match.
import json, zipfile, os, sys
B = os.path.expanduser('~/tmp-offload/bigl/'); R = '/home/ubuntu/cambc-autumn/'
vers = set(int(v) for v in sys.argv[1:]) or {86, 87, 88, 89}
games = {}
for l in open(R + 'research/ladder-scrims-2026-11-06/data/games.jsonl'):
    r = json.loads(l)
    if r.get('status') != 'finished' or r['version'] not in vers or not r.get('replay'): continue
    if not os.path.exists(R + r['replay']): continue
    games[r['match']] = r
    f = B + f"repl/{r['match']}.repl26a"
    if not os.path.exists(f):
        z = zipfile.ZipFile(R + r['replay']); n = [x for x in z.namelist() if x.endswith('.repl26a')][0]
        open(f, 'wb').write(z.read(n))
json.dump(games, open(B + 'games.json', 'w'))
print(len(games))
