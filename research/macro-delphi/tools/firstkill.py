import json,gzip,glob,sys,collections,statistics as st
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def one(d):
    M=json.load(open(d+'/meta.json')); w=M['result']['winner']
    names={c['id']:c['name'] for c in M['champions']}
    team={c['id']:c['team'] for c in M['champions']}
    ks=[]
    for l in gzip.open(d+'/events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='death' and e.get('by') is not None and team.get(e['by'])!=team[e['v']]:
            ks.append((e['r'],team[e['by']],names[e['v']],e['gems']))
    if not ks: return None
    r,kt,vn,g=ks[0]
    # kill diff in first 300 rounds
    k300=collections.Counter(t for rr,t,_,_ in ks if rr<=300)
    return dict(r=r,won=(kt==w),vic=vn,gems=g, k300=(k300[w]-k300[1-w]))
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    res=[o for o in ProcessPoolExecutor(32).map(one,dirs) if o]
    print(len(res),'games with a kill; first-kill team wins %.1f%%'%(100*sum(r['won'] for r in res)/len(res)), 'median round', st.median(r['r'] for r in res))
    for lo,hi in ((0,100),(100,200),(200,400),(400,2001)):
        s=[r for r in res if lo<=r['r']<hi]
        if s: print(' first kill in [%d,%d): n=%d, killer team wins %.1f%%'%(lo,hi,len(s),100*sum(r['won'] for r in s)/len(s)))
    pv=[r for r in res if r['vic']=='Prism']; print(' first victim Prism: n=%d killer wins %.1f%%'%(len(pv),100*sum(r['won'] for r in pv)/len(pv)))
    c=collections.Counter(max(-3,min(3,r['k300'])) for r in res); print(' winner-minus-loser kills by r300:',sorted(c.items()))
if __name__=='__main__': main()
