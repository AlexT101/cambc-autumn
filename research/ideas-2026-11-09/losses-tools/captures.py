"""Captures by round 300, by group side (own / middle / enemy half, from the capturer's view), for the loss analysis.
    python3 captures.py BATCHES_TXT OUT.jsonl"""
import sys, os, json, gzip
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'

def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); mp = json.load(open(A + d + '/' + meta['mapFile']))
    us = 0 if src.endswith('-12.repl26a') else 1
    side = {g['id']: g['side'] for g in mp['groups']}; gold = {g['id']: g['gold'] for g in mp['groups']}; gems = {g['id']: g['gems'] for g in mp['groups']}
    res = {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp, 'win': meta['result']['winner'] == us, 'caps': []}
    for l in gzip.open(A + d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['k'] == 'capture' and e['r'] <= 300:
            t = e['team']; s = side.get(e['g'], -1)
            where = 'mid' if s == -1 else 'own' if s == t else 'enemy'
            res['caps'].append([e['r'], t == us, where, e['g'], gold.get(e['g'], 0), gems.get(e['g'], 0)])
    return res

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (int(k), o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args))
