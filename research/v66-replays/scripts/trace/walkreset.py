import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
RESET={'vesper':0,'willow':1,'tavi':0}  # attack_reset slot
def one(kv):
    key,v=kv
    T,TV=load(key); o=Counter(); ex=[]
    for (r,c),L in T.items():
        tv=TV.get(c)
        if not tv or tv['t'] not in RESET or not L['TT']: continue
        tt=L['TT'][0]
        if tt.get('a')!='1' or tt.get('ok')=='0': continue
        q=xy(tt.get('q','-1,-1'))
        vis=[b for b in L['TB'] if b.get('s')=='e' and b.get('v')=='1' and b.get('al')=='1']
        if not vis or not q: continue
        tas=L['TA']
        mv=[a for a in tas if a['a']=='move_to_with_result' and a.get('ok')=='1']
        if not mv: continue
        # enemy within 3 of end tile (belief position at turn start)
        dn=min(cheb(q,xy(b['p'])) for b in vis)
        if dn>3: continue
        cd=tt.get('cd','0,0').split(',')
        slot=RESET[tv['t']]
        ready=cd[slot]=='0'
        att=[a for a in tas if a['a']=='attack' and a['x'].startswith('1,') and a.get('rc')=='0']
        rst=[a for a in tas if a['a']=='cast_with_result' and a['x'].split(',')[0]==str(slot) and a.get('rc')=='0']
        d=tt.get('d')
        k=(tv['t'],d,'reset_ready' if ready else 'reset_cd')
        o[k+('n',)]+=1
        o[k+('walk+reset+attack',)]+= bool(att and rst)
        o[k+('attack_any',)]+= bool(att)
        if ready and not att and d=='R' and len(ex)<6: ex.append((key,r,c,tv['t'],tt['p'],tt['q'],tt['hp'],[ (b['h'],b['t'],b['p'],b['hp']) for b in vis]))
    return o,ex
if __name__=='__main__':
    K=keys()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,K))
    T=Counter(); E=[]
    for o,e in res: T.update(o); E+=e
    ks=sorted({k[:3] for k in T}, key=lambda k:-T[k+('n',)])
    for k in ks[:14]:
        n=T[k+('n',)]; print(k,n,'walk+reset+attack %.2f any attack %.2f'%(T[k+('walk+reset+attack',)]/n,T[k+('attack_any',)]/n))
    for e in E: print(e)
