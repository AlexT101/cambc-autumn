import sys,math; sys.path.insert(0,sys.argv[1])
from common import *
from concurrent.futures import ProcessPoolExecutor
FF=json.load(open(sys.argv[1]+'/fights.json'))
def P(side): return sum(x[1] for x in side)*sum(x[4] for x in side)
sel=defaultdict(list)
for f in FF:
    if f['ku']+f['kt']>0 and f['pres']['us'] and f['pres']['them'] and f['start']<250 and len(f['pres']['us'])==len(f['pres']['them']):
        sel[f['key']].append((f['start'],f['end'],{x[5] for x in f['pres']['us']}|{x[5] for x in f['pres']['them']}))
def one(key):
    m=meta(key); us=[g for g in games() if g['dir']==key][0]['us']
    NM={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    o=Counter()
    ev=events(key)
    for s,e_,ids in sel[key]:
        for e in ev:
            if s<=e['r']<=e_+1 and e['k'] in ('attack','cast') and e.get('a') in ids:
                side='us' if team[e['a']]==us else 'them'
                d=sum(a for v,a in (e.get('dmg') or []) if v in team and team[v]!=team[e['a']])
                if d<=0 and not e.get('stun'): continue
                kind=e['k'] if e['k']=='attack' else 'cast:'+str(e.get('ab'))
                o[(side,NM[e['a']],kind,'dmg')]+=d; o[(side,NM[e['a']],kind,'n')]+=1
                o[(side,'ALL','dmg')]+=d
                st=[v for v in (e.get('stun') or []) if v in team and team[v]!=team[e['a']]]
                o[(side,'ALL','stuns')]+=len(st)
                # target type
                for v,a in (e.get('dmg') or []):
                    if v in team and team[v]!=team[e['a']]: o[(side,'target',NM[v])]+=a
    return o
if __name__=='__main__':
    with ProcessPoolExecutor(40) as ex: res=list(ex.map(one,list(sel)))
    T=Counter()
    for o in res: T.update(o)
    print('fights',sum(len(v) for v in sel.values()))
    for s in ('us','them'): print(s,'total dmg',round(T[(s,'ALL','dmg')]),'stuns',T[(s,'ALL','stuns')])
    rows=sorted([(k,v) for k,v in T.items() if len(k)==4 and k[3]=='dmg'],key=lambda kv:-kv[1])
    for (s,nm,kind,_),v in rows[:30]: print('  %-4s %-14s %-18s dmg %7.0f n %5d'%(s,nm,kind,v,T[(s,nm,kind,'n')]))
    for s in ('us','them'):
        print(s,'damage received by type', sorted(((nm,round(v)) for (ss,t,nm),v in T.items() if ss==('them' if s=='us' else 'us') and t=='target'),key=lambda x:-x[1])[:8])
