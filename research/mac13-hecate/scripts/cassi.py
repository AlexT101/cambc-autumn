import sys, json, gzip, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def one(d):
    d = Path(d)
    try:
        meta = json.loads((d/'meta.json').read_text()); R = json.load(gzip.open(d/'rounds.json.gz'))
        mp = json.loads((d/meta['mapFile']).read_text())
    except Exception: return None
    ch = {c['id']: c for c in R['champions']}; name = {c['id']: c['name'] for c in meta['champions']}
    r0 = R['round'][0]; out = []
    tiles = set(tuple(t) for g in mp['groups'] for t in g['tiles'])
    ev = [json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    camp_hits = set((e['a'], e['r']) for e in ev if e.get('k') in ('attack','cast') and ('camp' in e or e.get('cdmg')))
    for e in ev:
        if e.get('k') != 'death' or e.get('by') not in ch: continue
        v, k = e['v'], e['by']
        if name[v] not in ('Cassi','Issac') or name[k] != 'Prism' or e.get('linked'): continue
        V = ch[v]; K = ch[k]; i = e['r'] - r0
        prof = []
        for j in range(max(0, i-8), i):
            if V['x'][j] is None or K['x'][j] is None: prof.append(None); continue
            prof.append(max(abs(V['x'][j]-K['x'][j]), abs(V['y'][j]-K['y'][j])))
        j = i - 1
        pair = [c for c in R['champions'] if c['team']==V['team'] and name[c['id']] in ('Cassi','Issac') and c['id']!=v]
        pd = max(abs(pair[0]['x'][j]-V['x'][j]), abs(pair[0]['y'][j]-V['y'][j])) if pair and pair[0]['x'][j] is not None else None
        sees = [k in V.get('sees',[[]]*len(R['round']))[jj] if V.get('sees') else None for jj in range(max(0,i-4), i)]
        seen_by_v = [ (v in K['seenBy'][jj]) for jj in range(max(0,i-4), i)]
        act = 'hold' if (V['x'][j],V['y'][j]) in tiles else ('camp' if (v, e['r']-1) in camp_hits else 'other')
        out.append(dict(r=e['r'], body=name[v], hp=V['hp'][j], maxhp=V['maxHp'][j], kfoc=K['foc'][j], prof=prof, pair_dist=pd, saw=seen_by_v, act=act, gems=e.get('gems',0)))
    return out
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o: rows += o
    print('pair bodies killed by Prism (direct hit body)', len(rows), collections.Counter(x['body'] for x in rows))
    burst = [x for x in rows if x['hp'] and x['kfoc'] and x['hp'] <= 2.5*x['kfoc']]
    print('hp at death-1 within enemy Prism 2.5xFocus burst:', len(burst)/len(rows))
    print('max hp vs burst: share max<=burst', sum(1 for x in rows if x['maxhp'] <= 2.5*x['kfoc'])/len(rows))
    print('activity at death-1', collections.Counter(x['act'] for x in rows))
    print('pair distance', sorted(collections.Counter(min(x['pair_dist'] or 0, 12) for x in rows).items()))
    prof = collections.defaultdict(list)
    for x in rows:
        for t, dd in enumerate(x['prof']):
            if dd is not None: prof[t - len(x['prof'])].append(dd)
    print('dist to killer by offset', {t: round(sum(v)/len(v),1) for t, v in sorted(prof.items())})
    print('saw killer in last 4 rounds', sum(1 for x in rows if any(x['saw']))/len(rows))
    print('dist at death-1', sorted(collections.Counter(x['prof'][-1] for x in rows if x['prof'] and x['prof'][-1] is not None).items()))
