import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
RANGED={'Vesper Vale','Prism','Cassi','Willow','Tavi','Stellar'}
def one(r):
    d=r['dir']; m=meta(d); R=rounds(d); us=r['us']
    team={c['id']:c['team'] for c in m['champions']}; NM={c['id']:c['name'] for c in m['champions']}
    CH={c['id']:c for c in R['champions']}
    act=defaultdict(Counter)
    TK=defaultdict(float)
    for e in events(d):
        if e['k'] in ('attack','cast'):
            for v,a in (e.get('dmg') or []):
                if v in team and team[v]!=team[e['a']]: TK[(v,e['r'])]+=a
    for e in events(d):
        if 'a' in e and e['k'] in('attack','cast','move'):
            if any(v in team and team[v]!=team[e['a']] for v,a in (e.get('dmg') or [])) or any(v in team and team[v]!=team[e['a']] for v in (e.get('stun') or [])): act[(e['a'],e['r'])]['hit']+=1
            elif e.get('cdmg'): act[(e['a'],e['r'])]['camp']+=1
            if e['k']=='move': act[(e['a'],e['r'])]['move']+=1
            if e['k']=='cast' and e.get('ab')=='Dash': act[(e['a'],e['r'])]['dash']+=1
    o=Counter()
    for c,ch in CH.items():
        if NM[c] not in RANGED: continue
        side='us' if team[c]==us else 'them'
        for i in range(1,len(R['round'])):
            j=i-1
            if not ch['alive'][i] or not ch['alive'][j]: continue
            # mid-game only to avoid item effects? keep all
            if R['turn'] if False else False: pass
            if ch['turn'][i]!=1 and ch['turn'][i]!=2: continue
            p=(ch['x'][j],ch['y'][j])
            ens=[e for e in CH if team[e]!=team[c] and CH[e]['alive'][j] and e in ch['sees'][i]] if False else [e for e in ch['sees'][i] if CH[e]['alive'][j]]
            if not ens: continue
            dn=min(cheb(p,(CH[e]['x'][j],CH[e]['y'][j])) for e in ens)
            if dn>3: continue
            a=act[(c,R['round'][i])]
            cls='hit' if a['hit'] else ('camp' if a['camp'] else ('move' if a['move'] else 'none'))
            hp=ch['hp'][j]/ch['maxHp'][j]
            near=min(ens,key=lambda e:cheb(p,(CH[e]['x'][j],CH[e]['y'][j])))
            mel='ranged' if NM[near] in RANGED else 'melee'
            o[(side,'vs',mel,dn,cls)]+=1
            if cls in ('hit','move'):
                rn=R['round'][i]
                o[(side,'tk',cls)]+=TK[(c,rn)]+TK[(c,rn+1)]; o[(side,'tkn',cls)]+=1
                o[(side,'tkd',cls)]+= int(any(not ch['alive'][k] for k in range(i,min(len(R['round']),i+3))))
            o[(side,NM[c],cls)]+=1; o[(side,'ALL',cls)]+=1
            if cls=='move':
                q=(ch['x'][i],ch['y'][i])
                dn2=min(cheb(q,(CH[e]['x'][j],CH[e]['y'][j])) for e in ens)
                o[(side,'dir','away' if dn2>dn else ('toward' if dn2<dn else 'same'))]+=1
                o[(side,'dir_from',dn,'away' if dn2>dn else ('toward' if dn2<dn else 'same'))]+=1
                o[(side,'moved_then_dmg')]+= 0
            o[(side,'ALL',cls,'hp<0.4' if hp<0.4 else 'hp>=0.4')]+=1
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,games()))
    T=Counter()
    for o in res: T.update(o)
    for nm in ['ALL']+sorted(RANGED):
        for s in ('us','them'):
            n=sum(T[(s,nm,c)] for c in ('hit','camp','move','none'))
            if n<200: continue
            print('%-12s %-4s n=%6d '%(nm,s,n)+' '.join('%s %.2f'%(c,T[(s,nm,c)]/n) for c in ('hit','move','camp','none')))
    for s in ('us','them'):
        for cl in ('hit','move'): print(s,cl,'dmg taken this+next round %.0f, died within 2 rounds %.3f'%(T[(s,'tk',cl)]/T[(s,'tkn',cl)],T[(s,'tkd',cl)]/T[(s,'tkn',cl)]))
    for s in ('us','them'):
        for mel in ('melee','ranged'):
            for dd in (1,2,3):
                n=sum(T[(s,'vs',mel,dd,c)] for c in ('hit','camp','move','none'))
                if n: print(s,'nearest',mel,'dist',dd,n,'hit %.2f move %.2f'%(T[(s,'vs',mel,dd,'hit')]/n,T[(s,'vs',mel,dd,'move')]/n))
    for s in ('us','them'):
        n=sum(T[(s,'dir',k)] for k in ('away','toward','same')); print(s,'move direction',{k:'%.2f'%(T[(s,'dir',k)]/n) for k in ('away','toward','same')})
        for dd in (1,2,3):
            n=sum(T[(s,'dir_from',dd,k)] for k in ('away','toward','same')); print('   from dist',dd,n,{k:'%.2f'%(T[(s,'dir_from',dd,k)]/n) for k in ('away','toward','same')})
    for s in ('us','them'):
        for h in ('hp<0.4','hp>=0.4'):
            n=sum(T[(s,'ALL',c,h)] for c in ('hit','camp','move','none')); print(s,h,n,' '.join('%s %.2f'%(c,T[(s,'ALL',c,h)]/n) for c in ('hit','move','camp','none')))
