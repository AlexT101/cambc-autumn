"""Early-game detail per game (deaths by round bin and champion, first death, gold curves) for the loss analysis.
    python3 early.py BATCHES_TXT OUT.jsonl"""
import sys, os, json, gzip, collections
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'
BINS = (50, 100, 150, 200, 300, 450, 600)

def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); rd = json.load(gzip.open(A + d + '/rounds.json.gz'))
    us = 0 if src.endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    rr = rd['round']; idx = {r: i for i, r in enumerate(rr)}
    f = {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp, 'win': meta['result']['winner'] == us,
         'ours': sorted(name[c] for c in team if team[c] == us), 'theirs': sorted(name[c] for c in team if team[c] != us)}
    for r in BINS:
        i = idx.get(r, len(rr) - 1)
        f[f'earn{r}'] = [sum(c['earned'][i] for c in rd['champions'] if c['team'] == t) for t in (us, 1 - us)]
        f[f'trib{r}'] = [rd['gems'][us][i], rd['gems'][1 - us][i]]
    deaths = []
    for l in gzip.open(A + d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'death':
            v = e['v']; by = e.get('by')
            deaths.append({'r': e['r'], 'ours': team[v] == us, 'who': name[v], 'gems': e.get('gems', 0), 'camp': 'camp' in e,
                           'by': name.get(by) if by is not None else None, 'at': e.get('at')})
    f['deaths'] = deaths
    return f

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (int(k), o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args))
