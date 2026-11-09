import beh, json, sys, os, collections
from multiprocessing import Pool
import lockcut_run as L
def run(j):
    k,d,T=j
    try: meta,rd,ev=beh.load(d)
    except Exception: return (k,[],[])
    team={c['id']:c['team'] for c in meta['champions']}
    us=[e['gems'] for e in ev if e['k']=='tribute_start' and team[e['a']]==T]
    op=[e['gems'] for e in ev if e['k']=='tribute_start' and team[e['a']]!=T]
    return (k,us,op)
if __name__=='__main__':
    jobs=L.jl()+L.jloc(sys.argv[1],1)
    with Pool(32) as p: res=p.map(run,jobs,chunksize=8)
    G=collections.defaultdict(lambda:[[],[],0])
    for k,us,op in res: G[k][0]+=us; G[k][1]+=op; G[k][2]+=1
    bins=[0,40,100,150,200,300,1000]
    for k,(us,op,n) in G.items():
        for lab,x in (('us',us),('op',op)):
            h=[sum(1 for g in x if bins[i]<=g<bins[i+1])/n for i in range(len(bins)-1)]
            print(f'{k:14} {lab} starts/game by bag '+' '.join(f'[{bins[i]},{bins[i+1]}):{h[i]:.2f}' for i in range(len(h))))
