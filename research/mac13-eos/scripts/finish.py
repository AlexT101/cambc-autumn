"""The finish: first round a team's score + carried >= 1000; its score, Prism bag, others' bags; rounds to the end;
who won. Also Prism bag trajectory vs score. py finish.py EXTRACT_DIR"""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    w=meta['result']['winner']; n=len(R['round']); sc=R['gems']; ch=R['champions']
    names={int(c['id']):c['name'] for c in meta['champions']}
    res=[]
    for t in (0,1):
        mine=[c for c in ch if int(c['team'])==t]
        for i in range(n):
            car=sum(c['gems'][i] for c in mine if c['alive'][i])
            if sc[t][i]+car>=1000:
                pr=[c['gems'][i] for c in mine if names[int(c['id'])]=='Prism' and c['alive'][i]]
                res.append(dict(team=t,won=t==w,r=i+1,end=n,score=sc[t][i],prism=pr[0] if pr else None,others=car-(pr[0] if pr else 0),
                                other_reach=None))
                break
    # also: team that reached first
    if len(res)==2: first=min(res,key=lambda x:x['r'])['team']
    elif res: first=res[0]['team']
    else: first=None
    for x in res: x['first']=x['team']==first
    return res
if __name__=='__main__':
    root=Path(sys.argv[1]); dirs=[d for d in root.iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    F=[x for x in res if x['first']]
    print('first reachers',len(F),'win',round(sum(x['won'] for x in F)/len(F),3))
    P=[x for x in F if x['prism'] is not None]
    print('with Prism alive at that moment',len(P),'win',round(sum(x['won'] for x in P)/len(P),3))
    import statistics as st
    for lab,S in [('won',[x for x in P if x['won']]),('lost',[x for x in P if not x['won']])]:
        print(lab,len(S),'score med',st.median(x['score'] for x in S),'prism bag med',st.median(x['prism'] for x in S),'others med',st.median(x['others'] for x in S),
              'rounds to end med',st.median(x['end']-x['r'] for x in S),'mean',round(st.mean(x['end']-x['r'] for x in S),1))
    # conversion time by prism bag size
    for lo,hi in [(0,300),(300,500),(500,700),(700,900),(900,3000)]:
        S=[x for x in P if lo<=x['prism']<hi]
        if S: print('prism bag',lo,hi,len(S),'win',round(sum(x['won'] for x in S)/len(S),3),'rounds to end med',st.median(x['end']-x['r'] for x in S),'score med',st.median(x['score'] for x in S))
