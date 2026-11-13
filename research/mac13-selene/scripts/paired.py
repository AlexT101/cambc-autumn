import re,sys
def res(f):
    d={}
    for l in open(f):
        m=re.match(r'\[(\d+)/\d+\] (\S+) A=(\d) B=(\d): bot (\d) wins',l)
        if m: d[(m.group(2),m.group(3))]=m.group(5)=='1'
    return d
r=res(sys.argv[1]); w=res(sys.argv[2])
k=[x for x in r if x in w]
import math
a=sum(r[x] for x in k); b=sum(w[x] for x in k); n=len(k)
dis=sum(1 for x in k if r[x]!=w[x])
print('paired',n,'cand %.2f base %.2f diff %.2f +- %.2f'%(100*a/max(1,n),100*b/max(1,n),100*(a-b)/max(1,n),196*math.sqrt(max(1,dis))/max(1,n)))
