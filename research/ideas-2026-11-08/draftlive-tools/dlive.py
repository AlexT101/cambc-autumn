"""Draft lab against live drafts: vehicle k (oc-base25 + trainer table) plays team k of each ladder map's list
against spar bodies (fixed Fish/Mite live picks per map and side). py dlive.py prep|run NAME [--opps spar-oc29]"""
import json, random, sys, time, subprocess, tempfile, argparse
from pathlib import Path
sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools/draftlab'); sys.path.insert(0, '/home/ubuntu/cambc-autumn/tools')
import lab, vehicle, cpu_slots
ROOT = Path('/home/ubuntu/cambc-autumn'); W = Path('/home/ubuntu/tmp-offload/draftlive')
ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('name')
ap.add_argument('--source', default='bots/variants/oc-base25'); ap.add_argument('--top', type=int, default=40)
ap.add_argument('--rand', type=int, default=40); ap.add_argument('--seed', type=int, default=1270001)
ap.add_argument('--opps', default='spar-oc29'); ap.add_argument('--veh', default=''); ap.add_argument('--scores', default=str(W / 'f92scores.json'))
a = ap.parse_args()
D = W / a.name; D.mkdir(exist_ok=True)
CH = vehicle.CHAMPS
if a.cmd == 'prep':
    S = json.load(open(a.scores)); lists = {}
    for m in S:
        teams = sorted(m['teams'], key=lambda t: -t[1])
        assert teams[0][0] == m['best'] or teams[0][1] == teams[1][1]
        top = [m['best']] + [t[0] for t in teams if t[0] != m['best']][:a.top - 1]
        rest = [t[0] for t in teams if t[0] not in top]
        random.Random(f"{a.seed}|{m['name']}").shuffle(rest)
        lists[m['name']] = {'key': m['key'], 'picks': m['picks'], 'teams': top + rest[:a.rand]}
    json.dump(lists, open(D / 'lists.json', 'w'))
    nv = max(len(v['teams']) for v in lists.values())
    paths = []
    for k in range(nv):
        entries = [(v['key'], t, [CH[c] for c in v['teams'][k]]) for v in lists.values() if k < len(v['teams']) for t in (0, 1)]
        p, changed = vehicle.make(ROOT / a.source, f'dl-{a.name}-v{k}', entries)
        if changed or not vehicle.built(p): paths.append(p)
    opps = [ROOT / 'bots/variants' / f'{o}-{x}' for o in a.opps.split(',') for x in 'FM']
    opps.append(ROOT / a.source)
    paths += [p for p in opps if not vehicle.built(p)]
    print('building', len(paths), flush=True)
    print('built in', vehicle.build_all(paths, par=12), flush=True)
    cli, fast, env = lab.runner()
    allp = [ROOT / 'bots/variants' / f'dl-{a.name}-v{k}' for k in range(nv)] + opps
    with tempfile.TemporaryDirectory() as tmp:
        man = Path(tmp) / 'warm.txt'
        man.write_text(''.join(f'{p} {p} {ROOT}/maps/00ambush.map26a {tmp}/w{i}.repl26a\n' for i, p in enumerate(allp)))
        t0 = time.time(); subprocess.run([cli, 'run-batch', str(man), '--rounds', '1', '--jobs', '16', '--log-limit', '0'], cwd=ROOT, env=env, capture_output=True)
        print('native warm', time.time() - t0, flush=True)
    (D / 'prepared').write_text('ok\n')
elif a.cmd == 'run':
    veh_name = a.veh or a.name
    if a.veh and not (D / 'lists.json').exists(): import shutil; shutil.copy(W / a.veh / 'lists.json', D / 'lists.json')
    lists = json.load(open(D / 'lists.json')); games = []
    for o in a.opps.split(','):
        for x in 'FM':
            for name, v in lists.items():
                for k in range(len(v['teams'])):
                    veh, sp = f'dl-{veh_name}-v{k}', f'{o}-{x}'
                    games.append({'vehicle_a': veh, 'vehicle_b': sp, 'map': f'maps/{name}.map26a', 'meta': [name, k, 'a', x, o]})
                    games.append({'vehicle_a': sp, 'vehicle_b': veh, 'map': f'maps/{name}.map26a', 'meta': [name, k, 'b', x, o]})
            for name in lists:  # control: the unpatched source, to check vehicle v0 replays it
                games.append({'vehicle_a': Path(a.source).name, 'vehicle_b': f'{o}-{x}', 'map': f'maps/{name}.map26a', 'meta': [name, -1, 'a', x, o]})
                games.append({'vehicle_a': f'{o}-{x}', 'vehicle_b': Path(a.source).name, 'map': f'maps/{name}.map26a', 'meta': [name, -1, 'b', x, o]})
    for g in games: g['vehicle_name'] = g['vehicle_a']
    random.Random(a.seed).shuffle(games)
    json.dump(games, open(D / 'games.json', 'w'))
    bdir = D / 'batch'; bdir.mkdir(exist_ok=True)
    feed = lab.OutcomeFeed(bdir, 8)
    try:
        lab.run_batch(bdir, games, cpu_slots.SIZE, 900, on_done=feed.add)
    finally:
        feed.close()
    (D / 'done').write_text('ok\n')
