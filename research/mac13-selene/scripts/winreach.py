# In death windows (k>=1 enemy bodies dead), for each our alive body: nearest live (state 1) enemy-half group by Chebyshev,
# and whether a dead enemy's respawn (death+61) + crow distance from enemy spawn > now + dist + 15 (stay estimate).
import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json'))); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
    except Exception: return None
    G={g['id']:g for g in mp['groups']}
    cen={g['id']:(sum(t[0] for t in g['tiles'])/len(g['tiles']),sum(t[1] for t in g['tiles'])/len(g['tiles'])) for g in mp['groups']}
    sp=mp['spawn']; sc=[((s['minX']+s['maxX'])/2,(s['minY']+s['maxY'])/2) for s in sp]
    D=lambda a,b: max(abs(a[0]-b[0]),abs(a[1]-b[1]))
    n=len(R['round']); rows=R['groups']; j=0; cur={}
    deathr={}  # (cid)-> round died
    res=Counter()
    for i,r in enumerate(R['round']):
        while j<len(rows) and rows[j][0]<=r: cur[rows[j][1]]=rows[j][2]; j+=1
        for t in (0,1):
            o=1-t
            deadE=[c for c in R['champions'] if c['team']==o and not c['alive'][i]]
            if not deadE: continue
            nE=sum(1 for c in R['champions'] if c['team']==o)
            for c in R['champions']:
                if c['team']!=t or not c['alive'][i] or c['x'][i] is None: continue
                p=(c['x'][i],c['y'][i]); best=None
                for g,s in cur.items():
                    if s!=1 or G[g]['side']!=o: continue
                    dd=D(p,cen[g])
                    # respawn: find death round of each dead enemy
                    absent=0
                    for e in deadE:
                        k=i
                        while k>0 and not e['alive'][k-1]: k-=1
                        back=R['round'][k]+61+D(sc[o],cen[g])
                        if back> r+dd+15: absent+=1
                    if absent==0: continue
                    if best is None or dd<best[0]: best=(dd,absent/nE)
                res['bodyrounds']+=1
                if best:
                    b=best[0]; res['has']+=1
                    res['d<=10' if b<=10 else 'd<=20' if b<=20 else 'd>20']+=1
    return res
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps'][:300]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=4):
            if r: tot.update(r)
    b=tot['bodyrounds']; print('window body-rounds',b, {k:'%.1f%%'%(100*v/b) for k,v in tot.items() if k!='bodyrounds'})
if __name__=='__main__': main()
