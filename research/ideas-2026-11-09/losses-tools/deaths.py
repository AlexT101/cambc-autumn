"""Champion deaths (both sides; fields from the victim's side) before round 600 in context (local numbers, hp, channel, who struck first) for the loss analysis.
    python3 deaths.py BATCHES_TXT OUT.jsonl"""
import sys, os, json, gzip
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'

def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); rd = json.load(gzip.open(A + d + '/rounds.json.gz'))
    us = 0 if src.endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    rr = rd['round']; idx = {r: i for i, r in enumerate(rr)}; ch = {c['id']: c for c in rd['champions']}
    ev = [json.loads(l) for l in gzip.open(A + d + '/events.jsonl.gz', 'rt')]
    out = []
    hits = []  # (r, attacker, victim) champion damage
    for e in ev:
        if e['k'] in ('attack', 'cast') and e.get('dmg'):
            for v, amt in e['dmg']:
                if v in team and amt > 0: hits.append((e['r'], e['a'], v))
    for e in ev:
        if e['k'] != 'death' or e['r'] > 600 or 'camp' in e or e['v'] not in team: continue
        r, v = e['r'], e['v']; i = idx.get(r - 1, 0)
        p = (ch[v]['x'][i], ch[v]['y'][i])
        if p[0] is None: continue
        vt = team[v]
        def near(t, rad=8):
            return sum(1 for c in rd['champions'] if c['team'] == t and c['id'] != v and c['alive'][i] and c['x'][i] is not None
                       and max(abs(c['x'][i] - p[0]), abs(c['y'][i] - p[1])) <= rad)
        hp = ch[v]['hp'][i] / max(1, ch[v]['maxHp'][i])
        win = [h for h in hits if r - 12 <= h[0] <= r]
        first = min(win, key=lambda h: h[0]) if win else None
        we_first = first is not None and team[first[1]] == vt  # the victim's side struck first
        out.append({'r': r, 'who': name[v], 'by': name.get(e.get('by')), 'gems': e.get('gems', 0), 'hp0': round(hp, 2),
                    'ours': vt == us, 'allies': near(vt), 'enemies': near(1 - vt), 'chan': ch[v]['chan'][i], 'we_first': we_first,
                    'bodies_own': sum(c['alive'][i] for c in rd['champions'] if c['team'] == vt),
                    'bodies_other': sum(c['alive'][i] for c in rd['champions'] if c['team'] != vt)})
    return {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp, 'win': meta['result']['winner'] == us,
            'deaths': out}

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (int(k), o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args))
