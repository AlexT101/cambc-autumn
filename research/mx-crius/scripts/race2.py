"""Both sides: the first round each team could win with one tribute (tributed + one champion's bag >= 1000). Who
reaches it, and the win rate of the team that has it, by its bag size, the other team's tributed then, and the channel
length it needs (ceil(bag/10)) against rounds left (unknown in play; here the actual remaining rounds)."""
import json,gzip,glob,os,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
CH=json.load(open(A+'/enums.json'))['champions']
def one(d):
    m=json.load(open(d+'/meta.json')); w=m['result']['winner']; end=m['result']['rounds']
    typ={c['id']:CH[c['type']] for c in m['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); rr=R['round']
    first=[None,None]
    for i,r in enumerate(rr):
        for t in (0,1):
            if first[t] is not None: continue
            T=R['gems'][t][i]
            bags=[(c['gems'][i] or 0,c['id']) for c in R['champions'] if c['team']==t]
            b,cid=max(bags)
            if T+b>=1000 and b>0: first[t]=(r,b,typ[cid],T,R['gems'][1-t][i])
    return w,first,end
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(A+'/*/meta.json')]
    with ProcessPoolExecutor(48) as ex: S=list(ex.map(one,ds,chunksize=8))
    rows=[]
    for w,first,end in S:
        for t in (0,1):
            if first[t] is None: continue
            r,b,ty,T,E=first[t]
            other=first[1-t]
            rows.append(dict(won=w==t,b=b,ty=ty,T=T,E=E,firstone=other is None or other[0]>r,both=other is not None,r=r,end=end))
    n=len(rows); print('team-sides reaching one-tribute-wins',n,'of',2*len(S),'win %.1f%%'%(100*sum(x['won'] for x in rows)/n))
    def tab(lab,f,bins):
        print(lab)
        for lo,hi in bins:
            xs=[x for x in rows if lo<=f(x)<hi]
            if xs: print('  [%s,%s) n=%5d win %.1f%%'%(lo,hi,len(xs),100*sum(x['won'] for x in xs)/len(xs)))
    tab('by bag',lambda x:x['b'],[(0,50),(50,150),(150,300),(300,500),(500,700),(700,2000)])
    tab('by enemy tributed then',lambda x:x['E'],[(0,300),(300,600),(600,800),(800,900),(900,1000)])
    tab('by round',lambda x:x['r'],[(0,400),(400,700),(700,1000),(1000,1500),(1500,2001)])
    xs=[x for x in rows if x['firstone']]; print('reached it first: n=%d win %.1f%%'%(len(xs),100*sum(x['won'] for x in xs)/len(xs)))
    xs=[x for x in rows if x['ty']=='Prism' and x['b']>=300]; print('Prism bag>=300: n=%d win %.1f%%'%(len(xs),100*sum(x['won'] for x in xs)/len(xs)))
