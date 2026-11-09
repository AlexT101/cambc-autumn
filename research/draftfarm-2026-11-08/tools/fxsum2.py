import pickle, sys, numpy as np, collections
rows = pickle.load(open(sys.argv[1], 'rb'))
m = lambda xs: float(np.mean(xs))
def se(xs): xs=np.array(xs,float); return xs.std()/np.sqrt(len(xs))
for lim in (50,100,150,200,300):
    dg=[r['C'][f'gold{lim}u']-r['B'][f'gold{lim}u'] for r in rows]; dgo=[r['C'][f'gold{lim}o']-r['B'][f'gold{lim}o'] for r in rows]
    de=[r['C'][f'own{lim}u']-r['B'][f'own{lim}u'] for r in rows]; deo=[r['C'][f'own{lim}o']-r['B'][f'own{lim}o'] for r in rows]
    print(f'r{lim}: d gold ours {m(dg):+.1f}±{se(dg):.1f} theirs {m(dgo):+.1f}±{se(dgo):.1f}  d gems ours {m(de):+.2f}±{se(de):.2f} theirs {m(deo):+.2f}±{se(deo):.2f}')
for lim in (100,150):
    for who,flag in (('ours',True),('theirs',False)):
        d=[sum(1 for x in r['C']['deaths'] if x[0]<=lim and x[1]==flag)-sum(1 for x in r['B']['deaths'] if x[0]<=lim and x[1]==flag) for r in rows]
        print(f'd deaths<=r{lim} {who} {m(d):+.3f}±{se(d):.3f}')
# deaths by place and outnumbering (ours)
for G in ('C','B'):
    c=collections.Counter()
    for r in rows:
        for x in r[G]['deaths']:
            if x[0]<=150 and x[1]:
                place='own' if x[7]>0.15 else 'mid' if x[7]>-0.15 else 'their'
                c[place]+=1; c['outnum' if x[6]>x[5]+1 else 'even']+=1; c['bycamp' if not x[3] else 'bychamp']+=1
    print(G, {k:round(v/len(rows),3) for k,v in sorted(c.items())})
# mid caps overall
def caps(G,ours,lo,hi,lim=150): return sum(1 for c in G['caps'] if c[0]<=lim and c[2]==ours and lo<=G['gside'].get(c[1],0)<hi)
for nm,lo,hi in (('own',0.15,9),('mid',-0.15,0.15),('their',-9,-0.15)):
    a=[caps(r['C'],True,lo,hi)-caps(r['B'],True,lo,hi) for r in rows]; b=[caps(r['C'],False,lo,hi)-caps(r['B'],False,lo,hi) for r in rows]
    print(f'caps<=150 {nm}: d ours {m(a):+.3f}±{se(a):.3f} d theirs {m(b):+.3f}±{se(b):.3f}')
# oscillation: A->B->A within 10 rounds, per game, r<=100
def osc(D):
    n=0
    for h,d in D.items():
        seq=[]
        for r in sorted(d):
            if r>100: break
            g=d[r][1]
            if g>=0 and (not seq or seq[-1][0]!=g): seq.append((g,r))
        for i in range(2,len(seq)):
            if seq[i][0]==seq[i-2][0] and seq[i][1]-seq[i-2][1]<=10: n+=1
    return n
a=[osc(r['C'].get('D',{})) for r in rows]; b=[osc(r['B'].get('D',{})) for r in rows]
print('A-B-A flips within 10 rounds per game, r<=100: C', m(a), 'B', m(b))
# decision letters mix r<=100
for G in ('C','B'):
    c=collections.Counter()
    for r in rows:
        for h,d in r[G].get('D',{}).items():
            for rr,(dec,g,cl) in d.items():
                if rr<=100: c[dec]+=1
    t=sum(c.values()); print(G, {k:round(v/t,3) for k,v in c.most_common(10)})
