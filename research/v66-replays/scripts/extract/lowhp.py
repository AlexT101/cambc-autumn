import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']; mp=mapj(m)
    sp=mp['spawn']
    def onsp(t,p): s=sp[t]; return s['minX']<=p[0]<=s['maxX'] and s['minY']<=p[1]<=s['maxY']
    out=[]
    N=len(R['round'])
    for c in R['champions']:
        t=c['team']; side='us' if t==us else 'them'
        i=1
        while i<N:
            if c['alive'][i] and c['alive'][i-1] and c['hp'][i]<0.3*c['maxHp'][i]<=c['hp'][i-1]:
                # outcome within 25 rounds
                res='survive'
                for j in range(i+1,min(N,i+40)):
                    if not c['alive'][j]: res='died'; break
                    if onsp(t,(c['x'][j],c['y'][j])): res='spawn'; break
                    if c['hp'][j]>=0.6*c['maxHp'][j]: res='healed'; break
                # enemies within 8 at i
                ne=0
                for e in R['champions']:
                    if e['team']!=t and e['alive'][i] and cheb((e['x'][i],e['y'][i]),(c['x'][i],c['y'][i]))<=8: ne+=1
                out.append((side,r['opp'],res,ne, c['gems'][i]))
                i+=5
            i+=1
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=[x for o in ex.map(one,games()) for x in o]
    c=defaultdict(Counter)
    for side,o,res,ne,g in res:
        c[(side,'all')][res]+=1; c[(side,o)][res]+=1; c[(side,'ne>=1' if ne else 'ne0')][res]+=1
    for k in sorted(c): 
        n=sum(c[k].values()); print(k,n,{a:'%.2f'%(b/n) for a,b in c[k].items()})
