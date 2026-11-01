"""Our pressured holds (trace-joined, trusted rounds). Hold/pressure as q1_holds.py. For each, the holders'
want_home answers during the hold (TE home v=1 reasons), the outcome, whether the holder died within 15 rounds
of the hold's end, whether the enemy captured the group within 15, rounds left to payout when we walked
(capture_reset left), and the stand fight summary of the deciding turn."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def one(arg):
    key,g=arg; G=Game(g); T=tload(key); us=G.us; tr=T['trust']
    gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}
    gval={gg['id']:gg['gems'] for gg in G.mp['groups']}
    caps=defaultdict(list); dr=defaultdict(list)
    for e in G.ev:
        if e['k']=='capture': caps[e['g']].append((e['r'],e['team']))
        if e['k']=='death': dr[e['v']].append(e['r'])
    out=[]; open_={}
    for e in G.ev:
        if e['r']>tr: break
        k=e['k']
        if k=='capture_hold' and e['team']==us: open_[e['g']]=e['r']
        elif k in('capture','capture_reset') and e['team']==us and e['g'] in open_:
            r0=open_.pop(e['g']); r1=e['r']; tiles=gt[e['g']]
            pr=None
            for r in range(r0,r1):
                i=G.idx.get(r)
                if i is None: continue
                ds=[min(C.cheb(G.pos(c,i),q) for q in tiles) for c in G.team if G.team[c]!=us and G.pos(c,i)]
                if ds and min(ds)<=3:
                    own=sum(1 for c in G.team if G.team[c]==us and G.pos(c,i) and min(C.cheb(G.pos(c,i),q) for q in tiles)<=6)
                    pr=(r,own,sum(1 for d in ds if d<=6)); break
            if not pr: continue
            holders=set()
            for r in range(r0,r1+1):
                i=G.idx.get(r)
                if i is None: continue
                for c in G.team:
                    if G.team[c]==us and G.pos(c,i) in tiles: holders.add(c)
            homes=[]
            for r in range(r0,r1+1):
                for c in holders:
                    for x in T['turns'].get((r,c),{}).get('te',[]):
                        if x['k']=='home' and x.get('v')=='1': homes.append((r,c,x.get('why'),x.get('t'),x.get('hp')))
            if k=='capture': oc='paid'
            elif e.get('contested'): oc='contested'
            else:
                i=G.idx.get(r1)
                lv=[c for c in holders if G.pos(c,i-1) in tiles and G.pos(c,i) not in tiles]
                oc='died' if lv and not G.ch[lv[0]]['alive'][i] else 'walked'
            hd=any(r1<=x<=r1+15 for c in holders for x in dr[c])
            stolen=any(r1<=cr<=r1+15 and ct!=us for cr,ct in caps[e['g']])
            out.append(dict(key=key,g=e['g'],gems=gval[e['g']],r0=r0,r1=r1,pr=pr,oc=oc,left=e.get('left') if k=='capture_reset' else 0,homes=homes,hd=hd,stolen=stolen,opp=G.opp,map=G.mapname))
    return out
if __name__=='__main__':
    res=[x for o in pmap(one,trace_keys()) for x in o]
    json.dump(res,open(CACHE+'/../q1_holdtrace.json','w'))
    print('pressured holds (trusted):',len(res),Counter(x['oc'] for x in res))
    W=[x for x in res if x['oc']=='walked']
    first=Counter(x['homes'][-1][2] if x['homes'] else 'none' for x in W)
    print('walked: last want_home reason',first)
    for lab,f in (('outnumbered',lambda p:p[1]<p[2]),('equal',lambda p:p[1]==p[2]),('more',lambda p:p[1]>p[2])):
        Z=[x for x in res if f(x['pr'])]
        st_=[x for x in Z if x['oc']!='walked']; wk=[x for x in Z if x['oc']=='walked']
        print(f"{lab}: n={len(Z)}; stayed {len(st_)}: paid {sum(x['oc']=='paid' for x in st_)/max(1,len(st_)):.2f}, holder died<=15 {sum(x['hd'] for x in st_)/max(1,len(st_)):.2f} | walked {len(wk)}: holder died<=15 {sum(x['hd'] for x in wk)/max(1,len(wk)):.2f}, stolen {sum(x['stolen'] for x in wk)/max(1,len(wk)):.2f}, left<=2 {sum((x['left'] or 9)<=2 for x in wk)/max(1,len(wk)):.2f}")
    print('walked with left<=2:',sum((x['left'] or 9)<=2 for x in W),'of',len(W),'gems at stake (group gems) per game:',sum(x['gems'] for x in W)/len(set(x['key'] for x in res)))
    print('stand fight summaries of the walking decision (lost:tku:tkt:falls:allies:enemies) top:',Counter(x['homes'][-1][3] for x in W if x['homes'] and x['homes'][-1][3]).most_common(10))
    for x in [x for x in W if (x['left'] or 9)<=2][:8]: print(x['key'],x['g'],x['r0'],x['r1'],x['pr'],x['left'],x['homes'][-1:],x['stolen'],x['hd'])
