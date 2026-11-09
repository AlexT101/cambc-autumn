import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,None)
    team={c['id']:c['team'] for c in meta['champions']}
    # per champion: running bag sources since last tribute/death
    src=collections.defaultdict(lambda: collections.Counter())
    big=collections.Counter(); n300=collections.Counter()
    gtype={}
    for g in json.load(open(os.path.dirname(d)+'/maps/'+meta['map']['hash']+'.json'))['groups'] if os.path.exists(os.path.dirname(d)+'/maps/'+meta['map']['hash']+'.json') else []:
        gtype[g['id']]=g['types']
    for e in ev:
        kk=e['k']
        if kk=='capture':
            for sh in e.get('shares',[]):
                cid,gems=sh[0],sh[1]
                t=gtype.get(e['g'],[])
                lab='mono' if 'Monolith' in t else 'golem' if 'Golem' in t else 'cap'
                src[cid][lab]+=gems
        elif kk=='death':
            if e.get('by') is not None and e.get('gemsTo'):
                src[e['by']]['kill']+=e['gemsTo']
            src[e['v']].clear()
        elif kk=='tribute_end':
            a=e['a']; side='us' if team[a]==T else 'op'
            if e.get('gems',0)>=300:
                n300[side]+=1
                for lab,v in src[a].items(): big[(side,lab)]+=v
            src[a].clear()
    return (k,(big,n300))
if __name__=='__main__':
    jobs=L.jl()+L.jloc(sys.argv[1],1)
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(lambda:[collections.Counter(),collections.Counter()])
    for k,r in res:
        if r: G[k][0].update(r[0]); G[k][1].update(r[1])
    for k,(big,n) in G.items():
        for side in ('us','op'):
            tot=sum(v for (s,l),v in big.items() if s==side)
            print(k,side,'300+ tributes',n[side],' sources: '+' '.join(f'{l}:{v/max(1,tot):.2f}' for (s,l),v in sorted(big.items()) if s==side))
