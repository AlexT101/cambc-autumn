# Games with a 1.5x gem lead (tributed+carried) at r300: leader vs trailer, r<=300.
import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]; w=m['result']['winner']
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round'])
    if T<=300: return None
    r=300; tot=[0,0]
    for c in o['champions']:
        if c['alive'][r]: tot[c['team']]+=c['gems'][r] or 0
    for t in (0,1): tot[t]+=o['gems'][t][r]
    L=1 if tot[1]>tot[0] else 0
    if max(tot)<1.5*max(1,min(tot)): return None
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    st={t:collections.Counter() for t in (0,1)}
    for c in o['champions']:
        t=c['team']; st[t]['deadrounds']+=sum(1 for x in c['alive'][:301] if not x)
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        if e['r']>300: break
        if e['k']=='death':
            v=e['v']; st[team[v]]['deaths']+=1
            if e['r']<=150: st[team[v]]['deaths150']+=1
            if names[v]=='Prism': st[team[v]]['prismdeath']+=1
            st[team[v]]['gemslost']+=e.get('gems',0)
            k=e.get('by')
            if isinstance(k,int) and k in team and team[k]!=team[v]: st[team[k]]['kills']+=1
            else: st[team[v]]['otherdeath']+=1
        elif e['k']=='capture':
            t=e['team']; st[t]['captures']+=1; st[t]['capgems']+=sum(x[1] for x in e['shares'])
            if e['r']<=150: st[t]['capgems150']+=sum(x[1] for x in e['shares'])
    return (L,w==L,st[L],st[1-L])
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    print('games',len(R),'leader wins',sum(x[1] for x in R))
    keys=sorted(set(k for x in R for k in list(x[2])+list(x[3])))
    for k in keys: print(k,'leader',round(statistics.mean(x[2][k] for x in R),2),'trailer',round(statistics.mean(x[3][k] for x in R),2))
