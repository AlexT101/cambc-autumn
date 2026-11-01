import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
RANGED={'vesper','prism','cassi','willow','tavi','stellar'}
DASH={'vesper','vendetta','hor','issac','ren'}
def reach(t,rr,r):
    base=(3 if t in RANGED else 1)+1
    # dash ready?
    try:
        a,b=[int(x) for x in rr.split(',')]
    except: a=b=10**9
    slot={'vesper':1,'vendetta':1,'hor':1,'issac':1,'ren':1}.get(t)
    if slot is not None and (a if slot==0 else b)<=r+1: base+=2
    return base
def one(kv):
    key,v=kv
    T,TV=load(key); o=Counter()
    for (r,c),L in T.items():
        tv=TV.get(c)
        if not tv or tv['t'] not in RANGED or not L['TT']: continue
        tt=L['TT'][0]
        if tt.get('a')!='1' or tt.get('d')!='R': continue
        p=xy(tt['p']); q=xy(tt['q'])
        vis=[b for b in L['TB'] if b.get('s')=='e' and b.get('v')=='1' and b.get('al')=='1']
        if not vis or p==q: continue
        dn=min(cheb(p,xy(b['p'])) for b in vis)
        if dn>3: continue
        att=any(a['a']=='attack' and a['x'].startswith('1,') and a.get('rc')=='0' for a in L['TA'])
        still=[b for b in vis if cheb(q,xy(b['p']))<=reach(b['t'],b.get('rr','9,9'),r)]
        hp=float(tt['hp'])/float(tt['mh'])
        k=('futile' if still else 'escapes')
        o[(k,)]+=1; o[(k,'attacked' if att else 'no_attack')]+=1
        o[(k,'hp<35' if hp<0.35 else 'hp>=35')]+=1
    return o
if __name__=='__main__':
    K=keys()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,K))
    T=Counter()
    for o in res: T.update(o)
    n=T[('futile',)]+T[('escapes',)]
    print('ranged retreat moves with an enemy within 3:',n)
    for k in ('futile','escapes'): print(k,T[(k,)],'%.2f'%(T[(k,)]/n),'attacked',T[(k,'attacked')],'no_attack',T[(k,'no_attack')],'hp>=35',T[(k,'hp>=35')])
