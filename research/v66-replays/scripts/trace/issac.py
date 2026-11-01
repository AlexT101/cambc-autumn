import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
RANGED={'vesper','prism','cassi','willow','tavi','stellar'}
def one(kv):
    key,v=kv
    T,TV=load(key); o=Counter()
    for (r,c),L in T.items():
        tv=TV.get(c)
        if not tv or not L['TT']: continue
        tt=L['TT'][0]
        if tt.get('a')!='1' or tt.get('ok')=='0': continue
        rng=3 if tv['t'] in RANGED else 1
        p=xy(tt['p'])
        vis=[b for b in L['TB'] if b.get('s')=='e' and b.get('v')=='1' and b.get('al')=='1']
        inr=[b for b in vis if cheb(p,xy(b['p']))<=rng]
        if not inr: continue
        tas=L['TA']
        hit_h=set()
        for a in tas:
            if a['a']=='attack' and a['x'].startswith('1,') and a.get('rc')=='0': hit_h.add(a['x'].split(',')[1])
            if a['a']=='cast_with_result' and a['x'].split(',')[1]=='1' and a.get('rc')=='0': hit_h.add(a['x'].split(',')[2])
        types={b['t'] for b in inr}
        cls='ranged' if rng==3 else 'melee'
        if types=={'issac'}:
            b=inr[0]; hp=float(b['hp'].split('/')[0])
            cas=[x for x in vis if x['t']=='cassi']
            cl='issac_only_inrange:' + ('cassi_lower_visible' if cas and float(cas[0]['hp'].split('/')[0])<hp else ('cassi_higher_visible' if cas else 'cassi_unseen'))
        else:
            cl='other'
        o[(cls,cl,'n')]+=1; o[(cls,cl,'hit')]+= bool(hit_h)
        o[(cls,cl,'d='+tt.get('d','?'))]+=1
    return o
if __name__=='__main__':
    K=keys()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,K))
    T=Counter()
    for o in res: T.update(o)
    for k in sorted({k[:2] for k in T}):
        n=T[k+('n',)]; print(k,n,'hit %.2f'%(T[k+('hit',)]/n), sorted([(kk[2],round(v/n,2)) for kk,v in T.items() if kk[:2]==k and kk[2].startswith('d=')],key=lambda x:-x[1])[:5])
