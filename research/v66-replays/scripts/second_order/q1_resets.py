"""Capture holds abandoned (both teams, extract) and what followed.
A reset = capture_reset event. walked = not contested and the leaver lived; died; contested.
After a reset of team T on group g: did the other team capture g within 15 rounds (stolen), did T re-capture it
within 30, did the leaver die within 15 rounds, nearest enemy distance to the group tiles at reset (end of round).
Trace join (ours): leaver's want_home reason (q1_trace.json)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
def one(g):
    G=Game(g); us=G.us
    gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}
    caps=defaultdict(list)
    for e in G.ev:
        if e['k']=='capture': caps[e['g']].append((e['r'],e['team']))
    holds=defaultdict(list)
    for e in G.ev:
        if e['k']=='capture_hold': holds[(e['g'],e['team'])].append(e['r'])
    dr=defaultdict(list)
    for e in G.ev:
        if e['k']=='death': dr[e['v']].append(e['r'])
    out=[]
    for e in G.ev:
        if e['k']!='capture_reset': continue
        t=e['team']; r=e['r']; i=G.idx.get(r)
        if not i: continue
        tiles=gt[e['g']]
        leavers=[c for c in G.team if G.team[c]==t and G.pos(c,i-1) in tiles and G.pos(c,i) not in tiles]
        lv=leavers[0] if leavers else None
        died=lv is not None and not G.ch[lv]['alive'][i]
        cause='contested' if e.get('contested') else ('died' if died else ('walked' if lv is not None else 'other'))
        # held for how long: last capture_hold of team on g before r
        h=[x for x in holds[(e['g'],t)] if x<=r]; held=r-h[-1] if h else None
        stolen=any(r<=cr<=r+15 and ct!=t for cr,ct in caps[e['g']])
        recap=any(r<cr<=r+30 and ct==t for cr,ct in caps[e['g']])
        ld=lv is not None and any(r<=x<=r+15 for x in dr[lv])
        en=[G.pos(c,i) for c in G.team if G.team[c]!=t]
        dist=min([min(C.cheb(p,q) for q in tiles) for p in en if p] or [99])
        out.append(dict(side='us' if t==us else 'them',cause=cause,left=e.get('left'),held=held,stolen=stolen,recap=recap,leaver_died=ld,dist=dist,r=r,g=e['g'],dir=G.dir,opp=G.opp,map=G.mapname,lv=lv))
    return out
if __name__=='__main__':
    gs=games(); res=[x for o in pmap(one,gs) for x in o]
    json.dump(res,open(CACHE+'/../q1_resets.json','w'))
    ng=len(gs)
    for side in ('us','them'):
        Z=[x for x in res if x['side']==side]
        print(side,'resets per game %.2f'%(len(Z)/ng), Counter(x['cause'] for x in Z))
        for cause in ('walked','contested','died'):
            W=[x for x in Z if x['cause']==cause]
            if not W: continue
            print(f"  {cause:9s} n={len(W)} per game {len(W)/ng:.2f}: stolen<=15 {sum(x['stolen'] for x in W)/len(W):.2f} recaptured<=30 {sum(x['recap'] for x in W)/len(W):.2f} leaver died<=15 {sum(x['leaver_died'] for x in W)/len(W):.2f}  enemy within 4 {sum(x['dist']<=4 for x in W)/len(W):.2f} within 8 {sum(x['dist']<=8 for x in W)/len(W):.2f}; left median {st.median([x['left'] for x in W if x['left'] is not None])}")
    # by opponent
    for o in ('Fish','Mite','UoS','PBG'):
        a=[x for x in res if x['opp']==o]; n=sum(1 for g in gs if g['opp']==o)
        print(o, 'walked us %.2f them %.2f per game; stolen after our walk %.2f'%(sum(x['side']=='us' and x['cause']=='walked' for x in a)/n, sum(x['side']=='them' and x['cause']=='walked' for x in a)/n,
              sum(x['stolen'] for x in a if x['side']=='us' and x['cause']=='walked')/max(1,sum(x['side']=='us' and x['cause']=='walked' for x in a))))
    # trace join: our walked resets with reason
    T=json.load(open(CACHE+'/../q1_trace.json'))
