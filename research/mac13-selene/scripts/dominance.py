import json, gzip, sys, os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import statistics as st
ROOT=sys.argv[1]
def game(d):
    try:
        meta=json.load(open(os.path.join(d,'meta.json')))
        R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
    except Exception: return None
    team={c['id']:c['team'] for c in meta['champions']}
    prisms=[c['id'] for c in meta['champions'] if c['name']=='Prism']
    if len(prisms)!=2 or team[prisms[0]]==team[prisms[1]]: return None
    ch=R['champions']; idx={c['id']:i for i,c in enumerate(ch)}
    rounds=R['round']; n=len(rounds)
    A,B=ch[idx[prisms[0]]],ch[idx[prisms[1]]]
    deaths={}
    for e in ev:
        if e['k']=='death' and e['v'] in prisms: deaths.setdefault(e['v'],[]).append((e['r'],e.get('by')))
    win=meta['result']['winner']
    out=[]
    # dominance episodes: P strong, Q weak, both alive, strong gems>=40 and >=2x weak+?
    for P,Q,pid,qid in ((A,B,prisms[0],prisms[1]),(B,A,prisms[1],prisms[0])):
        i=0
        while i<n:
            ok=lambda j: P['alive'][j] and Q['alive'][j] and P['x'][j] is not None and Q['x'][j] is not None and P['gems'][j]>=40 and P['gems'][j]>=2*Q['gems'][j]+10
            if ok(i):
                s=i
                while i<n and ok(i): i+=1
                e=i
                L=e-s
                d0=max(abs(P['x'][s]-Q['x'][s]),abs(P['y'][s]-Q['y'][s]))
                dmin=min(max(abs(P['x'][j]-Q['x'][j]),abs(P['y'][j]-Q['y'][j])) for j in range(s,e))
                r0,r1=rounds[s],rounds[min(e,n-1)]
                kill=any(r0<=r<=r1+1 and by==pid for r,by in deaths.get(qid,[]))
                pdie=any(r0<=r<=r1+1 for r,by in deaths.get(pid,[]))
                # how did it end
                end='gameend' if e>=n else ('qdead' if not Q['alive'][e] else ('pdead' if not P['alive'][e] else ('pbank' if P['gems'][e]<P['gems'][e-1]-20 else 'qgrow')))
                qz=sum(1 for j in range(s,e) if Q['gems'][j]>Q['gems'][s]+10)
                out.append(dict(qgain=Q['gems'][e-1]-Q['gems'][s],pgain=P['gems'][e-1]-P['gems'][s],L=L,d0=d0,dmin=dmin,kill=kill,pdie=pdie,end=end,pw=int(team[pid]==win),g=P['gems'][s],qg=Q['gems'][s],r=r0))
            else: i+=1
    return out
def main():
    dirs=[os.path.join(ROOT,x) for x in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT,x)) and x!='maps']
    rows=[];ng=0
    with ProcessPoolExecutor(24) as ex:
        for r in ex.map(game,dirs,chunksize=8):
            if r is not None: ng+=1; rows+=r
    big=[r for r in rows if r['L']>=3]
    print('2-prism games',ng,'episodes(L>=3)',len(big), 'per game',len(big)/ng)
    print('median L',st.median(r['L'] for r in big),'mean L',st.mean(r['L'] for r in big))
    print('ends',Counter(r['end'] for r in big))
    print('strong kills weak',sum(r['kill'] for r in big)/len(big),' strong dies',sum(r['pdie'] for r in big)/len(big))
    print('strong team wins',st.mean(r['pw'] for r in big))
    print('d0 dist',Counter(min(r['d0']//4*4,24) for r in big))
    print('dmin dist',Counter(min(r['dmin']//2*2,20) for r in big))
    for lo,hi in ((0,6),(6,10),(10,16),(16,99)):
        s=[r for r in big if lo<=r['dmin']<hi]
        if s: print('dmin',lo,hi,len(s),'kill',round(sum(r['kill'] for r in s)/len(s),3),'win',round(st.mean(r['pw'] for r in s),3))
    for lo,hi in ((0,6),(6,10),(10,16),(16,99)):
        s=[r for r in big if lo<=r['dmin']<hi]
        print('dmin',lo,hi,'mean L',round(st.mean(r['L'] for r in s),1),'weak gain',round(st.mean(r['qgain'] for r in s),1),'strong gain',round(st.mean(r['pgain'] for r in s),1),'start bags',round(st.mean(r['g'] for r in s)),round(st.mean(r['qg'] for r in s)),'ends',Counter(r['end'] for r in s).most_common())
if __name__=='__main__': main()
