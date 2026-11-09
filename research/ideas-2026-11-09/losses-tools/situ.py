"""sp-y2's situation per game on 00expanse/00quadrants: a cleared single-holder gold group, no enemy on it, our Cassi or
Issac within pick_up_radius (7) of it, and another ally of ours (not C&I, alive) within the C&I's distance + 2."""
import sys, os, json, gzip, math, collections
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'
def holders(gems):
    n = 1
    while n < 3 and math.ceil((gems // n + gems % n) / 10) > 11: n += 1
    return n
def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json'))
    nm = meta['map']['name']; nm = 'expanse' if 'expanse' in nm else 'quadrants' if 'quadrants' in nm else None
    if not nm: return None
    mp = json.load(open(os.path.normpath(os.path.join(A + d, meta['mapFile']))))
    rd = json.load(gzip.open(A + d + '/rounds.json.gz'))
    us = 0 if src.endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    groups = [g for g in mp['groups'] if int(g['gold']) > 0 and 'Monolith' not in g['types'] and holders(int(g['gems'])) == 1]
    tiles = {int(g['id']): [tuple(t) for t in g['tiles']] for g in groups}
    state = {}; rows = rd['groups']; ri = 0
    rr = rd['round']; ch = rd['champions']
    n_sit = n_on_ci = n_enemy = 0
    for i, r in enumerate(rr):
        while ri < len(rows) and rows[ri][0] <= r: state[rows[ri][1]] = rows[ri][2]; ri += 1
        if r > 600: break
        if r % 5: continue
        pos = {c['id']: (c['x'][i], c['y'][i]) for c in ch if c['alive'][i] and c['x'][i] is not None}
        for g, ts in tiles.items():
            if state.get(g) != 2: continue
            dist = lambda p: min(max(abs(p[0] - x), abs(p[1] - y)) for x, y in ts)
            if any(team[c] != us and dist(p) == 0 for c, p in pos.items()):
                n_enemy += 1; continue
            ci = [dist(p) for c, p in pos.items() if team[c] == us and name[c] in ('Cassi', 'Issac')]
            if not ci or min(ci) > 7: continue
            n_on_ci += 1
            m = min(ci)
            if any(team[c] == us and name[c] not in ('Cassi', 'Issac') and dist(p) <= m + 2 for c, p in pos.items()): n_sit += 1
    return {'k': k, 'opp': opp, 'map': nm, 'v': src.split('-')[-3] if 'livemaps' in src else '', 'win': meta['result']['winner'] == us, 'sit': n_sit, 'ci_near': n_on_ci, 'enemy_on': n_enemy,
            'ours': sorted(set(name[c] for c in team if team[c] == us))}
if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (k, o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=4):
            if f: out.write(json.dumps(f) + '\n')
