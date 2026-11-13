# During the Prism's own capture holds (hold start to payout, Prism among the shares, r<=LIMIT): rounds it dealt
# camp damage, cast anything, or was idle; and whether another live group's camp was within 5 of it (work it could do).
import json,gzip,sys,os,collections
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; LIMIT=int(sys.argv[2]) if len(sys.argv)>2 else 600
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; CH={c['id']:c for c in R['champions']}; rd={r:i for i,r in enumerate(R['round'])}
    P={i for i,n in names.items() if n=='Prism'}
    tiles={g['id']:g['tiles'] for g in mp['groups']}
    act=collections.defaultdict(set); cast=collections.defaultdict(set)
    alive_g={}  # group -> alive (woken/respawned) approximate: respawn sets alive, clear sets dead
    for g in tiles: alive_g[g]=True
    hold={}; out=collections.Counter()
    for e in ev:
        if e['r']>LIMIT: break
        k=e['k']
        if k in ('attack','cast') and e['a'] in P:
            if e.get('cdmg'): act[e['a']].add(e['r'])
            if k=='cast': cast[e['a']].add(e['r'])
        if k=='group_clear': alive_g[e['g']]=False
        if k=='group_respawn': alive_g[e['g']]=True
        if k=='capture_hold' and e['team'] in (0,1): hold[(e['g'],e['team'])]=e['r']
        if k=='capture' and e['team'] in (0,1):
            h=hold.pop((e['g'],e['team']),None)
            for s in e['shares']:
                if s[0] in P and h is not None:
                    c=CH[s[0]]
                    for r in range(h,e['r']):
                        t=rd.get(r)
                        if t is None: continue
                        p=(c['x'][t],c['y'][t]); out['rounds']+=1
                        work=r in act[s[0]]; out['work']+=work; out['cast']+=r in cast[s[0]]
                        near=any(alive_g[g] and g!=e['g'] and min(cheb(p,tt) for tt in tl)<=5 for g,tl in tiles.items() if tl)
                        out['near']+=near; out['idle_near']+=near and not work
                        rdy=c['cd1'][t]==0; out['cd1']+=rdy; out['cd0']+=c['cd0'][t]==0; out['rdy_near']+=rdy and near
                        if r==h: out['starts']+=1; out['start_rdy']+=rdy; out['start_rdy_near']+=rdy and near
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: res=[x for x in ex.map(one,dirs,chunksize=8) if x]
    T=collections.Counter()
    for r in res: T.update(r)
    n=T['rounds']; print('ground slot ready %.2f unit slot ready %.2f; ground ready and a live group within 5 %.2f; at hold start: ready %.2f, ready+near %.2f (holds/game %.1f)'%(T['cd1']/n,T['cd0']/n,T['rdy_near']/n,T['start_rdy']/T['starts'],T['start_rdy_near']/T['starts'],T['starts']/len(res)))
    print('Prism hold rounds/game %.1f; camp damage %.2f, casts %.2f, a live other group within 5 %.2f, idle with one within 5 %.2f'%(n/len(res),T['work']/n,T['cast']/n,T['near']/n,T['idle_near']/n))
