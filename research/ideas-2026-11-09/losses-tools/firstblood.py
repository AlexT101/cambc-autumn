"""The game's first champion death (either side) in context, for the loss analysis.
    python3 firstblood.py BATCHES_TXT OUT.jsonl"""
import sys, os, json, gzip
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'

def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); rd = json.load(gzip.open(A + d + '/rounds.json.gz'))
    mp = json.load(open(A + d + '/' + meta['mapFile'])) if 'mapFile' in meta else None
    us = 0 if src.endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    rr = rd['round']; idx = {r: i for i, r in enumerate(rr)}; ch = {c['id']: c for c in rd['champions']}
    ev = [json.loads(l) for l in gzip.open(A + d + '/events.jsonl.gz', 'rt')]
    W, H = meta['map']['width'], meta['map']['height']
    sp = [((s['minX'] + s['maxX']) / 2, (s['minY'] + s['maxY']) / 2) for s in mp['spawn']] if mp else None
    res = {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp, 'win': meta['result']['winner'] == us}
    camp_hit = {}  # champion -> last round it hit a camp
    first_hit = {}
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('cdmg'): camp_hit[e['a']] = e['r']
        if e['k'] == 'death' and 'camp' not in e and e['v'] in team:
            v, r = e['v'], e['r']; i = idx.get(r - 1, 0); p = (ch[v]['x'][i], ch[v]['y'][i])
            if p[0] is None: continue
            du = max(abs(p[0] - sp[team[v]][0]), abs(p[1] - sp[team[v]][1])); dt = max(abs(p[0] - sp[1 - team[v]][0]), abs(p[1] - sp[1 - team[v]][1]))
            res.update({'fb_r': r, 'fb_ours': team[v] == us, 'fb_who': name[v], 'fb_by': name.get(e.get('by')),
                        'fb_half': 'own' if du < 0.8 * dt else 'enemy' if dt < 0.8 * du else 'mid',  # victim's own half
                        'fb_farming': camp_hit.get(v, -99) >= r - 3, 'fb_gems': e.get('gems', 0),
                        'fb_hp_by': None})
            break
    return res

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (int(k), o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args))
