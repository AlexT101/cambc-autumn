import pickle,os,collections,numpy as np
D=pickle.load(open(os.path.expanduser('~/tmp-offload/bigl/deaths.pkl'),'rb'))
D=[d for d in D if not d['linked']]
ng=collections.Counter()
for d in D: ng[(d['dir'],d['win'])]=1
nL=sum(1 for k in ng if not k[1]); nW=sum(1 for k in ng if k[1])
print('games with deaths: L',nL,'W',nW)
def cat(d):
    if d['killer']=='camp': return 'camp'
    if d['chan']==2: return 'tributing'
    if d['chan']==1: return 'recalling'
    if d['near_ally']>5: return 'isolated'
    if d['en']>d['al']+1: return 'outnumbered'
    return 'even fight'
for res,ng_ in (('L',nL),('W',nW)):
    for side in (True,False):
        ds=[d for d in D if d['win']==(res=='W') and d['ours']==side]
        c=collections.Counter(cat(d) for d in ds); bags=collections.defaultdict(float)
        for d in ds: bags[cat(d)]+=d['bag']
        print(f"{res} {'our' if side else 'opp'} deaths/game {len(ds)/ng_:.2f}  gems/game {sum(d['bag'] for d in ds)/ng_:.0f}: "+'  '.join(f'{k} {v/ng_:.2f}({bags[k]/ng_:.0f}g)' for k,v in c.most_common()))
print()
# where: distance from own spawn
for res in ('L','W'):
    for side in (True,False):
        ds=[d for d in D if d['win']==(res=='W') and d['ours']==side and d['killer']!='camp']
        sd=np.array([d['spawn_d'] for d in ds]); ed=np.array([d['enemy_spawn_d'] for d in ds])
        own_half=np.mean(sd<ed)
        print(f"{res} {'our' if side else 'opp'}: died on own half {own_half:.2f}, median own-spawn dist {np.median(sd):.0f}; hp<30% before {np.mean([d['hp']<0.3 for d in ds]):.2f}; full hp(>80%) {np.mean([d['hp']>0.8 for d in ds]):.2f}; bag>=50 {np.mean([d['bag']>=50 for d in ds]):.2f}; unseen 10r before {np.mean([d['seen_before']>=8 for d in ds]):.2f}")
print()
# by phase, our deaths per game in losses vs wins
for lo,hi in ((0,200),(200,400),(400,600),(600,800),(800,1200),(1200,2001)):
    s=[]
    for res,ng_ in (('L',nL),('W',nW)):
        for side in (True,False):
            s.append(sum(1 for d in D if d['win']==(res=='W') and d['ours']==side and lo<=d['r']<hi)/ng_)
    print(f'r{lo}-{hi}: L our {s[0]:.2f} opp {s[1]:.2f} | W our {s[2]:.2f} opp {s[3]:.2f}')
print()
# victim type, our deaths in losses
for res,ng_ in (('L',nL),('W',nW)):
    c=collections.Counter(d['victim'] for d in D if d['win']==(res=='W') and d['ours']); print(res,'our victims/game',{k:round(v/ng_,2) for k,v in c.most_common()})
    c=collections.Counter(d['killer'] for d in D if d['win']==(res=='W') and d['ours']); print(res,'killers of ours/game',{k:round(v/ng_,2) for k,v in c.most_common()})
