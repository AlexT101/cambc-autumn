"""Engagements before round 300 (champion damage chained by <=3 rounds; time only), initiator and deaths, for the loss
analysis.  python3 fights.py BATCHES_TXT OUT.jsonl"""
import sys, os, json, gzip
from multiprocessing import Pool
R = '/home/ubuntu/cambc-autumn/'; A = R + 'replays/.analysis/'

def one(arg):
    d, src, k, opp = arg
    meta = json.load(open(A + d + '/meta.json')); us = 0 if src.endswith('-12.repl26a') else 1
    team = {c['id']: c['team'] for c in meta['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    rd = json.load(gzip.open(A + d + '/rounds.json.gz')); idx = {r: i for i, r in enumerate(rd['round'])}
    hpf = {c['id']: (c['hp'], c['maxHp']) for c in rd['champions']}
    fights, cur = [], None
    for l in gzip.open(A + d + '/events.jsonl.gz', 'rt'):
        e = json.loads(l)
        if e['r'] > 300: break
        if e['k'] in ('attack', 'cast') and e.get('dmg') and any(v in team and team[v] != team[e['a']] for v, a in e['dmg']):
            if cur is None or e['r'] > cur['end'] + 3:
                if cur: fights.append(cur)
                i = idx.get(e['r'] - 1, 0)
                cur = {'start': e['r'], 'end': e['r'], 'init_ours': team[e['a']] == us, 'init_who': name[e['a']],
                       'du': 0, 'dt': 0, 'dmg_u': 0, 'dmg_t': 0,
                       'hp_u': round(sum(hpf[c][0][i] for c in team if team[c] == us) / max(1, sum(hpf[c][1][i] for c in team if team[c] == us)), 2),
                       'hp_t': round(sum(hpf[c][0][i] for c in team if team[c] != us) / max(1, sum(hpf[c][1][i] for c in team if team[c] != us)), 2)}
            cur['end'] = e['r']
            for v, a in e['dmg']:
                if v in team: cur['dmg_t' if team[v] != us else 'dmg_u'] += a
        elif e['k'] == 'death' and cur and e['v'] in team and 'camp' not in e and e['r'] <= cur['end'] + 1:
            cur['du' if team[e['v']] == us else 'dt'] += 1
    if cur: fights.append(cur)
    return {'map': meta['map']['name'], 'side': 'a' if us == 0 else 'b', 'k': k, 'opp': opp, 'win': meta['result']['winner'] == us,
            'fights': fights}

if __name__ == '__main__':
    idxj = json.load(open(A + 'index.json'))['games']; B = {}
    for l in open(sys.argv[1]):
        k, o, b = l.split(); B[b] = (int(k), o)
    args = [(g['dir'], g['source'], *B[os.path.dirname(g['source'])]) for g in idxj if g['ok'] and os.path.dirname(g['source']) in B]
    with Pool(32) as p, open(sys.argv[2], 'w') as out:
        for f in p.imap_unordered(one, args, chunksize=8): out.write(json.dumps(f) + '\n')
    print(len(args))
