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
    r0 = R['round'][0]; sc = R['gems']; win = 0 if sc[0][-1] >= sc[1][-1] else 1
    sp = mp['spawn']
    def cen(t): s = sp[t]; return ((s['minX']+s['maxX'])/2, (s['minY']+s['maxY'])/2)
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e = json.loads(l)
        if e.get('k') != 'death' or e.get('by') not in ch: continue
        v, k = e['v'], e['by']
        if ch[k]['team'] == ch[v]['team']: continue
        i = max(0, e['r'] - r0 - 1); kt = ch[k]['team']; vt = 1 - kt
        x, y = ch[v]['x'][i], ch[v]['y'][i]
        if x is None: return None
        dk = max(abs(x-cen(kt)[0]), abs(y-cen(kt)[1])); dv = max(abs(x-cen(vt)[0]), abs(y-cen(vt)[1]))
        side = 'victim-half' if dv < dk else 'killer-half'
        nk = sum(1 for c in R['champions'] if c['team']==kt and c['alive'][i] and c['x'][i] is not None and max(abs(c['x'][i]-x), abs(c['y'][i]-y)) <= 8)
        nv = sum(1 for c in R['champions'] if c['team']==vt and c['alive'][i] and c['x'][i] is not None and max(abs(c['x'][i]-x), abs(c['y'][i]-y)) <= 8)
        return dict(r=e['r'], won=(kt == win), side=side, diff=nk-nv, victim=name[v], killer=name[k], gems=e.get('gems',0))
    return dict(r=None, won=None)
if __name__ == '__main__':
    dirs = [p for p in Path(sys.argv[1]).iterdir() if (p/'meta.json').exists()]
    rows = []
    with ProcessPoolExecutor(24) as ex:
        for o in ex.map(one, dirs, chunksize=8):
            if o and o['r']: rows.append(o)
    print('games with a kill', len(rows), 'first-kill team wins', sum(x['won'] for x in rows)/len(rows))
    rs = sorted(x['r'] for x in rows); print('first kill round quartiles', rs[len(rs)//4], rs[len(rs)//2], rs[3*len(rs)//4])
    print('side', collections.Counter(x['side'] for x in rows)); print('numbers diff (killer-victim within 8)', sorted(collections.Counter(x['diff'] for x in rows).items()))
    print('victims', collections.Counter(x['victim'] for x in rows).most_common(6)); print('killers', collections.Counter(x['killer'] for x in rows).most_common(6))
    for v in ('Prism','Cassi','Issac','Willow'):
        s = [x for x in rows if x['victim']==v]; print(v, len(s), 'killer team wins', round(sum(x['won'] for x in s)/max(1,len(s)),2))
