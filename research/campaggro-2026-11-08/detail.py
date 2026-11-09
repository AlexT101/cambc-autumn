"""Context of safe strict monolith opportunities (live): enemy distance, on own spawn, channel, hp; who woke what."""
import json, gzip, os, sys, collections
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(__file__)); from occur import cheb, RANGE
def game(args):
    d, our = args
    meta = json.load(open(d + '/meta.json')); mp = json.load(open(os.path.join(d, meta['mapFile'])))
    R = json.load(gzip.open(d + '/rounds.json.gz')); ch = R['champions']
    camps = {c['id']: c for c in mp['camps']}; groups = {g['id']: g for g in mp['groups']}
    spawn = mp['spawn']
    onsp = lambda t, p: spawn[t]['minX'] <= p[0] <= spawn[t]['maxX'] and spawn[t]['minY'] <= p[1] <= spawn[t]['maxY']
    mons = [(g, camps[c]) for g, G in groups.items() for c in G['camps'] if camps[c]['type'] == 'Monolith']
    rows = collections.defaultdict(list); gs = {}
    for row in R['groups']: rows[row[0]].append(row)
    out = collections.Counter()
    for i in range(len(R['round'])):
        for row in rows.get(R['round'][i], []): gs[row[1]] = row
        for g, m in mons:
            st = gs.get(g)
            if st is None or st[2] != 1 or st[6] != 0: continue
            mm = (m['x'], m['y'])
            alive = [(c, (c['x'][i], c['y'][i])) for c in ch if c['alive'][i] and c['x'][i] is not None]
            mine = [p for c, p in alive if c['team'] == our]; th = [(c, p) for c, p in alive if c['team'] != our]
            if not mine or not th: continue
            dT = min(cheb(p, mm) for p in mine)
            wake = min(cheb(p, (camps[c]['x'], camps[c]['y'])) for p in mine for c in groups[g]['camps'])
            if wake > 4: continue
            c, p = min(th, key=lambda cp: cheb(cp[1], mm)); dE = cheb(p, mm)
            if dE > 5 or dE >= dT: continue
            out[("pair", dE, dT)] += 1
            out[('dE', dE)] += 1; out[('wake', wake)] += 1
            out[('onspawn', onsp(c['team'], p))] += 1; out[('chan', c['chan'][i])] += 1
            out[('hpfrac', round(c['hp'][i] / c['maxHp'][i], 1))] += 1
            out[('ourdist', dT)] += 1; out[('side', mp['groups'][g]['side'] == our)] += 1
            out[('map', meta['map']['hash'])] += 1
    return out
if __name__ == '__main__':
    ana = sys.argv[1]; G = json.load(open(sys.argv[2])); jobs = []
    for g in json.load(open(ana + '/index.json'))['games']:
        mid = os.path.basename(g['source']).split('.')[0]
        if mid in G: jobs.append((ana + '/' + g['dir'], 0 if G[mid]['side'] == 'a' else 1))
    tot = collections.Counter()
    with Pool(32) as p:
        for r in p.imap_unordered(game, jobs, chunksize=4): tot.update(r)
    for k in sorted(tot, key=str):
        if k[0] != 'map': print(k, tot[k])
    print('maps', sorted(((v, k[1]) for k, v in tot.items() if k[0] == 'map'), reverse=True)[:12])
