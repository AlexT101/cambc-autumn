import json,gzip,glob,sys,collections
from concurrent.futures import ProcessPoolExecutor
A=sys.argv[1]
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(d):
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); C={c['id']:c for c in R['champions']}
    P={team[c]:c for c in C if names[c]=='Prism'}
    if len(P)<2: return None
    a,b=P[0],P[1]
    out=collections.Counter(); last=-99
    n=len(R['round'])
    for i in range(n):
        if not (C[a]['alive'][i] and C[b]['alive'][i]): continue
        dd=cheb((C[a]['x'][i],C[a]['y'][i]),(C[b]['x'][i],C[b]['y'][i]))
        if dd<=8 and (b in C[a]['sees'][i] or a in C[b]['sees'][i]):
            if i-last>20:
                for x,y in ((a,b),(b,a)):
                    rat=C[x]['foc'][i]/max(1,C[y]['foc'][i])
                    bin_='<0.5' if rat<0.5 else '<0.8' if rat<0.8 else '<1.25' if rat<1.25 else '<2' if rat<2 else '>2'
                    died=any(not C[x]['alive'][j] for j in range(i,min(n,i+15)))
                    killed=any(not C[y]['alive'][j] for j in range(i,min(n,i+15)))
                    out[bin_,'n']+=1; out[bin_,'died']+=died; out[bin_,'killed']+=killed
            last=i
    return out
def main():
    dirs=[x[:-10] for x in glob.glob(A+'/*/meta.json')]
    agg=collections.Counter()
    for o in ProcessPoolExecutor(32).map(one,dirs):
        if o: agg.update(o)
    for b in ('<0.5','<0.8','<1.25','<2','>2'):
        n=agg[b,'n']; print(b,n,'died %.2f killed %.2f'%(agg[b,'died']/n,agg[b,'killed']/n))
if __name__=='__main__': main()
