"""Captures in [swing, swing+W] of no-death swings: by group type mix and map side, winner vs loser."""
import json, gzip, glob, os, sys, collections, statistics as st
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]; W=25
def kind(G,camps):
    ts=set(camps[c]['type'] for c in G['camps'])
    for k in ('Monolith','Golem','Elk','Wolf'):
        if k in ts: return k
    return 'cluster'
def one(d):
    meta=json.load(open(d+'/meta.json')); w=meta['result']['winner']; L=1-w
    mp=json.load(open(os.path.join(d,meta['mapFile']))); camps={c['id']:c for c in mp['camps']}; groups={g['id']:g for g in mp['groups']}
    team={c['id']:c['team'] for c in meta['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rounds=R['round']; n=len(rounds)
    val=[[R['gems'][t][i] for i in range(n)] for t in (0,1)]
    for c in R['champions']:
        for i in range(n): val[c['team']][i]+=c['gems'][i] or 0
    sw=0
    for i in range(n):
        if val[L][i]-val[w][i]>=0: sw=i
    sr=rounds[sw]; caps=[]; dead=False
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l); r=e['r']
        if r<=sr: continue
        if r>sr+W: break
        if e['k']=='death' and team[e['v']]==L: dead=True
        if e['k']=='capture':
            G=groups.get(e['g']); 
            if not G: continue
            gm=sum(s[1] for s in e['shares']); t=e['team']
            side='own' if G['side']==t else 'mid' if G['side']==-1 else 'enemy'
            caps.append(('W' if t==w else 'L',kind(G,camps),side,gm))
    return None if dead else (sr,caps)
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    with ProcessPoolExecutor(32) as ex: S=[s for s in ex.map(one,ds,chunksize=8) if s]
    N=len(S); print('no-death swings',N)
    agg=collections.defaultdict(float); cnt=collections.defaultdict(float)
    for sr,caps in S:
        for who,k,side,gm in caps: agg[(who,k,side)]+=gm/N; cnt[(who,k,side)]+=1/N
    for key in sorted(agg, key=lambda k:(k[1],k[2],k[0])): print('%s %-8s %-6s gems/game %.1f caps/game %.2f'%(key[0],key[1],key[2],agg[key],cnt[key]))
    early=[x for x in S if x[0]<200]
    print('early (<200) n',len(early))
