"""Per champion-game rows from decoded live scrims: owned emblems/shards, gold, earned at checkpoints; shop log."""
import json, gzip, os, sys, pickle, collections
from multiprocessing import Pool
H = os.path.expanduser('~/tmp-offload/')
FAM = ['Monster','Power','Durability','Treasure','Jungle','Home','Bruiser','Tribute','Capture','Prospector','Hunter','Skirmish','Greed','Collectors']
CP = [50,100,150,200,300,400,500,600,800,1000,1200,1500]
def load(ana):
    out = {}
    for g in json.load(open(ana + '/index.json'))['games']:
        if not g.get('ok', True): continue
        for s in [g['source']] + [x['source'] for x in g.get('sources', [])]:
            out[os.path.basename(s).split('.')[0]] = ana + '/' + g['dir']
    return out
def one(args):
    mid, g, d = args
    meta = json.load(open(d + '/meta.json'))
    R = json.load(gzip.open(d + '/rounds.json.gz')); rr = R['round']
    us = 0 if g['side'] == 'a' else 1
    shops = collections.defaultdict(list); caps = collections.defaultdict(list)
    for l in gzip.open(d + '/events.jsonl.gz'):
        e = json.loads(l)
        if e['k'] == 'shop' and 'items' in e: shops[e['a']].append((e['r'], e['items']))
        elif e['k'] == 'capture':
            for cid, gm, gd in e['shares']: caps[cid].append((e['r'], gm, gd, len(e['shares'])))
    rows = []
    for c in R['champions']:
        ch = next(x for x in meta['champions'] if x['id'] == c['id'])
        row = dict(mid=mid, dir=os.path.basename(d), ver=g['version'], opp=g['opp_name'][0], map=g['map'], side=g['side'], ours=c['team'] == us,
                   team_win=meta['result']['winner'] == c['team'], name=ch['name'], id=c['id'], rounds=len(rr), cp={}, shops=shops[c['id']], caps=caps[c['id']],
                   our_picks=g['our_picks'], opp_picks=g['opp_picks'])
        for r in CP:
            if r > len(rr): break
            i = r - 1
            it = c['items'][i]; owned = {}
            for k in range(0, len(it), 2): owned[it[k]] = it[k+1]
            emb = collections.Counter(); sh = 0
            for iid, n in owned.items():
                fam, rest = divmod(iid, 6)
                if rest % 2: emb[(FAM[fam], rest // 2)] += n; sh += n * (25 if fam == 12 else 5)
                else: sh += n
            row['cp'][r] = dict(earned=c['earned'][i], gold=c['gold'][i], gems=c['gems'][i], alive=c['alive'][i], emb=dict(emb), shards=sh,
                                maxhp=c['maxHp'][i] if isinstance(c['maxHp'], list) else None)
        rows.append(row)
    return rows
if __name__ == '__main__':
    jobs = []
    for gj, ana in ((H + 'bigl/games.json', H + 'bigl/ana'), (H + 'emblem/games9091.json', H + 'emblem/ana')):
        if not os.path.exists(ana + '/index.json'): print('skip', ana); continue
        L = load(ana)
        for mid, g in json.load(open(gj)).items():
            if mid in L: jobs.append((mid, g, L[mid]))
    with Pool(12) as p: res = p.map(one, jobs, chunksize=8)
    rows = [r for x in res for r in x]
    pickle.dump(rows, open(H + 'emblem/live_items.pkl', 'wb')); print(len(jobs), len(rows))
