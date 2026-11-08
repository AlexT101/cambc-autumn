import pickle,collections,itertools
rows=pickle.load(open('cfull.pkl','rb'))
D=lambda a,b:max(abs(a['x']-b['x']),abs(a['y']-b['y']))
def offset(me,en,P):
    h=me['hp']/me['maxHp']; g=me['gems']
    e5=[e for e in en if D(e,me)<=P['R']]
    R= bool(e5) and (g>=P['g'] or h<=P['h'])
    K= any(e['hp']/e['maxHp']<=P['kh'] for e in e5) and not (R and h<=P['kd'])
    C= any(e['gems']>=P['cg'] for e in en if D(e,me)<=P['cr'])
    return 6460*K + ((1000 if K else 2000) if R else 0) + 3000*C
best=[]
for R,g,h,kh,kd,cg,cr in itertools.product((5,),(10,),(0.4,),(0.33,0.35,0.36),(0.25,),(300,400,450,500),(3,4,5)):
    P=dict(R=R,g=g,h=h,kh=kh,kd=kd,cg=cg,cr=cr); hit=0
    for r in rows:
        me=r['me']; b=100-min(D(e,me) for e in r['s_en'])
        hit+= b+offset(me,r['s_en'],P)==r['v']
    best.append((hit/len(rows),P))
best.sort(key=lambda x:-x[0]); [print(round(a,4),p) for a,p in best[:5]]
P=best[0][1]
base=sum((100-min(D(e,r['me']) for e in r['s_en']))==r['v'] for r in rows)/len(rows)
print('contact writes exact, no offsets:',round(base,4))
