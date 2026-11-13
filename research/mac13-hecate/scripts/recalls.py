"""Completed recalls: HP fraction and gems at start, why (shop after?), and rounds from recall start until next camp hit/hold."""
import sys, json, gzip, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
        mp = json.loads((d/meta['mapFile']).read_text())
    except Exception: return None
    name = {c['id']: c['name'] for c in meta['champions']}
    ch = {c['id']: c for c in R['champions']}; r0 = R['round'][0]; n = len(R['round'])
    tiles = set(tuple(t) for g in mp['groups'] for t in g['tiles'])
    work = collections.defaultdict(set)
    shop = collections.defaultdict(list)
    for e in ev:
        if e.get('k') in ('attack','cast') and ('camp' in e or e.get('cdmg')): work[e['a']].add(e['r'])
        if e.get('k') == 'shop': shop[e['a']].append((e['r'], -e.get('gold', 0)))
    starts = {}
    out = []
    for e in ev:
        k = e.get('k')
        if k == 'recall_start': starts[e['a']] = e
        elif k == 'recall_end':
            s = starts.get(e['a']); a = e['a']; C = ch[a]
            if not s: continue
            i = s['r'] - r0
            hpf = C['hp'][i] / C['maxHp'][i] if C['hp'][i] is not None else None
            # rounds until next work after landing
            back = None
            for j in range(e['r'] - r0 + 1, n):
                r = j + r0
                if r in work[a] or (C['x'][j], C['y'][j]) in tiles: back = r - s['r']; break
                if not C['alive'][j]: break
            spent = sum(g for (r, g) in shop[a] if e['r'] <= r <= e['r'] + 3)
            out.append(dict(name=name[a], hpf=hpf, gems=s.get('gems', 0), back=back, spent=spent, r=s['r']))
    return out, n, len(meta['champions'])
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []; rounds = 0; bodies = 0
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if not o: continue
            rows += o[0]; rounds += o[1] * o[2]
    print('recalls', len(rows), 'per game', len(rows)/len(dirs))
    full = [x for x in rows if x['hpf'] is not None and x['hpf'] >= 0.9]
    print('start hp>=0.9:', len(full)/len(rows), ' with gems>0:', sum(1 for x in rows if x['gems']>0)/len(rows))
    bk = [x['back'] for x in rows if x['back'] is not None]
    print('rounds from recall start to next work: mean', sum(bk)/len(bk), 'median', statistics.median(bk))
    print('total recall-cycle rounds share of body-rounds:', sum(bk)/rounds)
    print('spent gold at landing (mean):', sum(x['spent'] for x in rows)/len(rows), 'share spending >0:', sum(1 for x in rows if x['spent']>0)/len(rows))
    print('full-hp no-gems no-spend:', sum(1 for x in full if x['gems']==0 and x['spent']==0)/len(dirs), 'per game')
    by = collections.defaultdict(list)
    for x in rows: by[x['name']].append(x)
    for k, v in sorted(by.items(), key=lambda t: -len(t[1])):
        bb = [x['back'] for x in v if x['back'] is not None]
        print(k.ljust(14), len(v)/len(dirs), 'hp>=.9', round(sum(1 for x in v if x['hpf'] and x['hpf']>=.9)/len(v),2), 'gems>0', round(sum(1 for x in v if x['gems']>0)/len(v),2), 'back', round(sum(bb)/max(1,len(bb)),1), 'spend', round(sum(x['spent'] for x in v)/len(v)))
