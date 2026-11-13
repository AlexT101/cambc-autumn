# Champion deaths by champions: where (map side by spawn distance), how many allies/enemies within 8,
# victim's nearest ally distance; plus territory occupancy: share of alive rounds each team spends by side.
import json,gzip,glob,collections,sys,os,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
dirs=[g['dir'] for g in idx['games']]
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json'))
        mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(d+'/rounds.json.gz'))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    except Exception:
        return None
    sp=mp['spawn']
    cen=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in sp]
    def side(p,team):
        da=cheb(p,cen[team]); de=cheb(p,cen[1-team])
        return de/(da+de) if da+de>0 else .5  # 1 at own spawn
    CH=R['champions']; idmap={c['id']:i for i,c in enumerate(CH)}
    team_of={c['id']:c['team'] for c in CH}
    win=meta['result']['winner']
    out=collections.Counter()
    rows=[]
    for e in ev:
        if e['k']!='death' or e.get('by') is None: continue
        v=e['v']; t=team_of[v]; r=e['r']; i=max(0,min(len(R['round'])-1,r-2))
        at=e['at'] if e.get('at') else None
        if at is None: continue
        al=0;enm=0;nearest=99
        for c in CH:
            k=idmap[c['id']]
            if c['id']==v or not c['alive'][i] or c['x'][i] is None: continue
            dd=cheb(at,(c['x'][i],c['y'][i]))
            if c['team']==t:
                al+= dd<=8; nearest=min(nearest,dd)
            else: enm+= dd<=8
        rows.append((int(t==win),r,side(at,t),al,enm,nearest,en[meta['champions'][idmap[v]]['type']],e.get('gems',0) or 0))
    # occupancy by side buckets, rounds 1-600 sampled every 5
    occ={0:collections.Counter(),1:collections.Counter()}
    for i in range(0,min(len(R['round']),600),5):
        for c in CH:
            if not c['alive'][i] or c['x'][i] is None: continue
            s=side((c['x'][i],c['y'][i]),c['team'])
            b='own' if s>0.6 else 'enemy' if s<0.4 else 'mid'
            occ[int(c['team']==win)][b]+=1
    return rows,occ
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,dirs,chunksize=4) if r]
    rows=[x for r in res for x in r[0]]
    occ={0:collections.Counter(),1:collections.Counter()}
    for r in res:
        for k in (0,1): occ[k].update(r[1][k])
    print('deaths by champion',len(rows),'games',len(res))
    for w in (1,0):
        rs=[x for x in rows if x[0]==w]
        print('WIN side' if w else 'LOSE side', 'deaths/game', len(rs)/len(res))
        sides=collections.Counter('own' if x[2]>0.6 else 'enemy' if x[2]<0.4 else 'mid' for x in rs)
        print('  where', dict(sides))
        print('  allies<=8 dist', collections.Counter(min(x[3],3) for x in rs))
        print('  enemies<=8 dist', collections.Counter(min(x[4],4) for x in rs))
        print('  nearest ally', collections.Counter(min(x[5]//4*4,16) for x in rs))
        print('  gems lost', sum(x[7] for x in rs)/len(res))
        o=occ[w]; tot=sum(o.values()); print('  occupancy', {k:round(v/tot,3) for k,v in o.items()})
    # by type
    bt=collections.Counter((x[6],x[0]) for x in rows)
    for t in sorted(set(x[6] for x in rows)): print(t, 'W', bt[(t,1)], 'L', bt[(t,0)])
