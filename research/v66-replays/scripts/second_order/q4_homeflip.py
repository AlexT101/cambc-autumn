"""want_home flip-flops (trace, trusted). A flip = a turn with TE home v=1 (stand_lost / stand_falls / outmatched)
and a retreat (d=R), whose champion is back on that turn's start tile within its next 2 turns while want_home said
stay (v=0 or not asked) in between. An episode = flips of one champion with at most 6 rounds between them;
loops = episodes of >= 3 flips. Reported: turns in loops, damage taken in them (TT dmg), what drew it back
(the TA site of the return step), the work it was at (TT fg / hold), and episodes per game."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def one(arg):
    key,g=arg; T=tload(key)
    seq=defaultdict(list)
    for (r,c),L in T['turns'].items():
        tt=L.get('tt')
        if tt and tt.get('a')=='1': seq[c].append((r,L))
    alive_turns=sum(len(v) for v in seq.values())
    eps=[]
    for c,S in seq.items():
        S.sort(key=lambda x:x[0]); flips=[]
        for j in range(len(S)-2):
            r,L=S[j]; tt=L['tt']
            h=[e for e in L['te'] if e['k']=='home' and e.get('v')=='1']
            if not h or tt.get('d')!='R' or h[-1].get('why') not in('stand_lost','stand_falls','outmatched'): continue
            p=tt.get('p')
            for k in (1,2):
                if j+k>=len(S): break
                r2,L2=S[j+k]
                h2=[e for e in L2['te'] if e['k']=='home' and e.get('v')=='1']
                if h2 or L2['tt'].get('d')=='R': break
                if L2['tt'].get('q')==p:
                    site=[a[1] for a in L2['ta'] if a[0] in('move_to_with_result','cast_with_result')]
                    flips.append((r,r2,h[-1].get('why'),site[-1] if site else None,L2['tt'].get('d'),tt.get('fg'),sum(float(S[j+x][1]['tt'].get('dmg',0) or 0) for x in range(0,k+1)),k+1))
                    break
        cur=[]
        for f in flips:
            if cur and f[0]-cur[-1][1]>6: eps.append((c,cur)); cur=[]
            cur.append(f)
        if cur: eps.append((c,cur))
    return dict(key=key,dir=g['dir'],opp=g['opp'],map=g['map'],alive=alive_turns,eps=[(c,e) for c,e in eps])
if __name__=='__main__':
    res=pmap(one,trace_keys()); json.dump(res,open(CACHE+'/../q4_homeflip.json','w'))
    A=sum(x['alive'] for x in res); nk=len(res)
    allf=[f for x in res for c,e in x['eps'] for f in e]
    loops=[(x,c,e) for x in res for c,e in x['eps'] if len(e)>=3]
    lt=sum(sum(f[7] for f in e) for x,c,e in loops)
    print(f'flips {len(allf)} ({len(allf)/nk:.1f}/game); turns in flips {100*sum(f[7] for f in allf)/A:.2f}% of alive turns; loops (>=3 flips) {len(loops)} ({len(loops)/nk:.2f}/game) in {len({x["key"] for x,c,e in loops})} games, {len({x["map"] for x,c,e in loops})} maps; turns in loops {100*lt/A:.2f}% of alive turns')
    print(' reasons',Counter(f[2] for f in allf).most_common(), '\n return sites',Counter(f[3] for f in allf).most_common(10),'\n return branch',Counter(f[4] for f in allf).most_common(8))
    print(' damage taken over a flip (start..return): zero in %.2f'%(sum(f[6]==0 for f in allf)/len(allf)))
    print(' loop length',Counter(min(len(e),10) for x,c,e in loops))
    print(' by opp per game',{o:round(sum(len(e) for x in res if x['opp']==o for c,e in x['eps'])/sum(1 for x in res if x['opp']==o),1) for o in ('Fish','Mite','UoS','PBG')})
    for x,c,e in sorted(loops,key=lambda z:-len(z[2]))[:8]: print('  ',x['key'],x['map'],'c',c,'rounds',e[0][0],'-',e[-1][1],'flips',len(e),Counter(f[2] for f in e).most_common(2),Counter(f[3] for f in e).most_common(2))
