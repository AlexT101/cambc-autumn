import sys; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
FF=json.load(open(sys.argv[1]+'/fights.json'))
sel=defaultdict(list)
for f in FF:
    if f['ku']+f['kt']>0 and f['pres']['us'] and f['pres']['them'] and f['start']<250 and len(f['pres']['us'])==len(f['pres']['them']):
        sel[f['key']].append(f)
def one(key):
    m=meta(key); us=[g for g in games() if g['dir']==key][0]['us']; R=rounds(key)
    team={c['id']:c['team'] for c in m['champions']}; NM={c['id']:c['name'] for c in m['champions']}
    ev=events(key); CH={c['id']:c for c in R['champions']}
    act=defaultdict(lambda:Counter())
    for e in ev:
        if 'a' in e and e['k'] in('attack','cast','move'):
            hitc=any(v in team and team[v]!=team[e['a']] for v,a in (e.get('dmg') or [])) or any(v in team and team[v]!=team[e['a']] for v in (e.get('stun') or []))
            k=('hit' if hitc else ('camp' if e.get('cdmg') else ('selfcast' if e['k']=='cast' else 'move')))
            act[(e['a'],e['r'])][k]+=1
            if e['k']=='move' or e.get('moved'):
                act[(e['a'],e['r'])]['moved']+=1
    o=Counter()
    for f in sel[key]:
        ids=set(x[5] for x in f['pres']['us'])|set(x[5] for x in f['pres']['them'])
        for c in ids:
            side='us' if team[c]==us else 'them'
            for rn in range(f['start'],f['end']+1):
                i=rn-1
                if i>=len(R['round']) or not CH[c]['alive'][i]: continue
                # nearest enemy distance at previous round end
                j=rn-2
                if j<0 or not CH[c]['alive'][j]: continue
                p=(CH[c]['x'][j],CH[c]['y'][j])
                dn=min([cheb(p,(CH[e]['x'][j],CH[e]['y'][j])) for e in CH if team[e]!=team[c] and CH[e]['alive'][j]] or [99])
                if dn>4: continue
                a=act[(c,rn)]
                cls='hit' if a['hit'] else ('camp' if a['camp'] else ('move_only' if a['moved'] else ('selfcast' if a['selfcast'] else 'idle')))
                o[(side,cls)]+=1; o[(side,NM[c],cls)]+=1
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,list(sel)))
    T=Counter()
    for o in res: T.update(o)
    for s in ('us','them'):
        n=sum(v for k,v in T.items() if len(k)==2 and k[0]==s)
        print(s,n,{k[1]:'%.2f'%(v/n) for k,v in T.items() if len(k)==2 and k[0]==s})
    for nm in ('Heart of Ruin','Marcella','Vendetta','Prism','Vesper Vale','Issac','Cassi','Willow'):
        for s in ('us','them'):
            n=sum(v for k,v in T.items() if len(k)==3 and k[0]==s and k[1]==nm)
            if n<100: continue
            print('  %-14s %-4s n=%5d '%(nm,s,n)+' '.join('%s %.2f'%(c,T[(s,nm,c)]/n) for c in ('hit','move_only','camp','idle','selfcast')))
