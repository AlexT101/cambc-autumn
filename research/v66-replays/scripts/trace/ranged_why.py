import sys; sys.path.insert(0,sys.argv[1])
from tlib import *
from concurrent.futures import ProcessPoolExecutor
RANGED={'vesper','prism','cassi','willow','tavi','stellar'}
def one(kv):
    key,v=kv
    T,TV=load(key); o=Counter(); ex=[]
    for (r,c),L in T.items():
        tv=TV.get(c)
        if not tv or tv['t'] not in RANGED or not L['TT']: continue
        tt=L['TT'][0]
        if tt.get('a')!='1' or tt.get('ok')=='0': continue
        p=xy(tt['p'])
        vis=[b for b in L['TB'] if b.get('s')=='e' and b.get('v')=='1' and b.get('al')=='1']
        if not vis: continue
        dn=min(cheb(p,xy(b['p'])) for b in vis)
        if dn>3: continue
        tas=L['TA']
        att=[a for a in tas if a['a'] in('attack',) and a['x'].startswith('1,') and a.get('rc')=='0'] + [a for a in tas if a['a']=='cast_with_result' and a['x'].split(',')[1]=='1' and a.get('rc')=='0']
        mv=[a for a in tas if a['a']=='move_to_with_result' and a.get('ok')=='1']
        dash=[a for a in tas if a['a']=='cast_with_result' and a.get('s','').startswith('dash')]
        cls='hit' if att else ('move' if (mv or dash) else 'none')
        o[('cls',cls)]+=1
        if cls!='hit':
            site=(mv or dash or [{}])[0].get('s','-') if cls=='move' else '-'
            home=[e for e in L['TE'] if e.get('k')=='home']
            hw=home[-1].get('why') if home else '-'
            hv=home[-1].get('v') if home else '-'
            o[('d',tt.get('d'),site)]+=1
            o[('home',hv,hw)]+=1
            o[('hp', 'lt35' if float(tt['hp'])<0.35*float(tt['mh']) else 'ge35')]+=1
            o[('cd',tt.get('cd'))]+=0
            ts=L['TS']
            if ts: o[('ts', 'free' if 'free' in ts[0] else 'search')]+=1
            if len(ex)<3 and cls=='move' and float(tt['hp'])>=0.6*float(tt['mh']): ex.append((key,r,c,tv['t'],tt.get('d'),site,hv,hw,tt['hp'],tt['p'],tt['q'],dn))
    return o,ex
if __name__=='__main__':
    K=keys()
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,K))
    T=Counter(); E=[]
    for o,e in res: T.update(o); E+=e
    print('games',len(K))
    n=sum(v for k,v in T.items() if k[0]=='cls'); print({k[1]:'%.2f'%(v/n) for k,v in T.items() if k[0]=='cls'},n)
    nm=n-T[('cls','hit')]
    for grp in ('d','home','hp','ts'):
        print(grp,[(k[1:],v,'%.2f'%(v/nm)) for k,v in sorted(T.items(),key=lambda kv:-kv[1]) if k[0]==grp][:14])
    for e in E[:12]: print(e)
