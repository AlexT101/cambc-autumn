"""Q4 trace: farm target switching. Per champion, the sequence of TE farm_pick g over alive turns (trusted).
switch = g differs from the previous pick (both >=0); return = the pick goes back to a group left within the last
20 turns (A->B->...->A); turns_away = turns between leaving A and returning to it. Also mode pairs at a switch."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(arg):
    key,g=arg; T=tload(key)
    seq=defaultdict(list)
    for (r,c),L in T['turns'].items():
        tt=L.get('tt')
        if not tt or tt.get('a')!='1': continue
        fp=[e for e in L['te'] if e['k']=='farm_pick']
        if fp: seq[c].append((r,int(fp[-1]['g']),fp[-1]['m'],tt.get('d'),tt.get('t')))
    picks=sw=ret=away=0; pairs=Counter(); ex=[]; bytype=Counter(); bytype_sw=Counter()
    for c,S in seq.items():
        S.sort()
        last_left={}  # group -> index when left
        for j in range(1,len(S)):
            r,gg,m,d,t=S[j]; pr=S[j-1]
            picks+=1; bytype[t]+=1
            if gg<0 or pr[1]<0 or r-pr[0]>3: continue
            if gg!=pr[1]:
                sw+=1; bytype_sw[t]+=1; pairs[(pr[2],m)]+=1
                last_left[pr[1]]=j
                if gg in last_left and j-last_left[gg]<=20:
                    ret+=1; away+=j-last_left[gg]
                    if len(ex)<5: ex.append((key,c,t,S[last_left[gg]-1][0],r,[x[1] for x in S[last_left[gg]-1:j+1]]))
    return dict(picks=picks,sw=sw,ret=ret,away=away,pairs=dict((f'{a}>{b}',v) for (a,b),v in pairs.items()),ex=ex,bt=dict(bytype),bts=dict(bytype_sw))
if __name__=='__main__':
    res=pmap(one,trace_keys())
    P=sum(x['picks'] for x in res); S=sum(x['sw'] for x in res); R=sum(x['ret'] for x in res); A=sum(x['away'] for x in res)
    print(f'farm picks {P}, switches {S} ({100*S/P:.1f} per 100 picks), returns to a group left <=20 turns ago {R} ({100*R/P:.2f}/100 picks), turns away in those {A} ({100*A/P:.2f}% of pick turns)')
    pr=Counter()
    for x in res: pr.update(x['pairs'])
    print(pr.most_common(12))
    bt=Counter(); bs=Counter()
    for x in res: bt.update(x['bt']); bs.update(x['bts'])
    print({k:round(100*bs[k]/bt[k],1) for k in bt})
    for x in res[:60]:
        for e in x['ex'][:1]: print(e)
