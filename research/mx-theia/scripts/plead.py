# Prism Focus lead at round T (default 250, both Prisms alive and no Prism death yet): its parts (capture gems,
# kill gems, gems tributed, item count) and how the lead predicts the win.
import json,gzip,sys,os,collections,statistics
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; T=int(sys.argv[2]) if len(sys.argv)>2 else 250
def one(d):
    d=os.path.join(ROOT,d)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    P={team[i]:i for i,n in names.items() if n=='Prism'}
    if len(P)!=2: return None
    if any(e['k']=='death' and e['r']<=T and names.get(e['v'])=='Prism' for e in ev): return None
    rd={r:i for i,r in enumerate(R['round'])}
    if T not in rd: return None
    t=rd[T]; CH={c['id']:c for c in R['champions']}
    out={}
    for tm,pid in P.items():
        cap=sum(s[1] for e in ev if e['k']=='capture' and e['r']<=T for s in e['shares'] if s[0]==pid)
        kill=sum(e.get('gemsTo',0) for e in ev if e['k']=='death' and e['r']<=T and e.get('by')==pid)
        trib=sum(e['gems'] for e in ev if e['k']=='tribute_end' and e['r']<=T and e['a']==pid)
        team_cap=sum(s[1] for e in ev if e['k']=='capture' and e['r']<=T and e['team']==tm for s in e['shares'])
        c=CH[pid]
        out[tm]=dict(foc=c['foc'][t],gems=c['gems'][t],cap=cap,kill=kill,trib=trib,items=len(c['items'][t]),team_cap=team_cap,earned=c['earned'][t])
    return dict(w=meta['result']['winner'],P=out)
def main():
    idx=json.load(open(ROOT+'/index.json')); dirs=sorted({g['dir'] for g in idx['games']})
    with ProcessPoolExecutor(32) as ex: G=[x for x in ex.map(one,dirs,chunksize=8) if x]
    print('games with both Prisms alive through r%d: %d'%(T,len(G)))
    keys=('foc','gems','cap','kill','trib','items','team_cap','earned')
    for k in keys:
        W=[g['P'][g['w']][k] for g in G]; L=[g['P'][1-g['w']][k] for g in G]
        print('%-8s W %.0f L %.0f  W higher %.2f'%(k,statistics.mean(W),statistics.mean(L),sum(a>b for a,b in zip(W,L))/len(G)))
    # win rate by focus ratio bucket of team 0
    b=collections.defaultdict(lambda:[0,0])
    for g in G:
        r=g['P'][0]['foc']/max(1,g['P'][1]['foc']); k=round(min(2,max(0.5,r)),1)
        b[k][0]+=g['w']==0; b[k][1]+=1
    print('win rate by focus ratio (team A / team B):',{k:'%.2f n%d'%(v[0]/v[1],v[1]) for k,v in sorted(b.items())})
if __name__=='__main__': main()
