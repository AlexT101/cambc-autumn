"""All our capture resets where the holder walked off on a want_home retreat (q1_trace.json resets, trusted).
For each: rounds left, the deciding TE home (why, stand summary tku), nearest enemy's distance to the tiles at the
end of the previous round, whether an enemy stood on a tile within `left` rounds after (truth), stolen within 15,
recaptured by us within 30, the leaver's death within 15, group gems; and the gem value when the group would have
paid (enemy absent from the tiles through the payout and tku > left)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
Q=json.load(open(CACHE+'/../q1_trace.json'))
RS=defaultdict(list)
for x in Q:
    for r in x['resets']:
        if r[0].startswith('left:R:'): RS[r[3]].append(r)
M={k:g for k,g in trace_keys()}
def one(key):
    G=Game(M[key]); T=tload(key); us=G.us
    gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}; gv={gg['id']:gg['gems'] for gg in G.mp['groups']}
    caps=defaultdict(list); dr=defaultdict(list)
    for e in G.ev:
        if e['k']=='capture': caps[e['g']].append((e['r'],e['team']))
        if e['k']=='death': dr[e['v']].append(e['r'])
    out=[]
    for cause,d,left,_,r,g in RS[key]:
        i=G.idx[r]; tiles=gt[g]; left=left or 0
        lv=[c for c in G.team if G.team[c]==us and G.pos(c,i-1) in tiles and G.pos(c,i) not in tiles][0]
        h=[x for x in T['turns'].get((r,lv),{}).get('te',[]) if x['k']=='home' and x.get('v')=='1']
        h=h[-1] if h else {}
        tku=None
        if h.get('t'):
            try: tku=int(h['t'].split(':')[1])
            except: pass
        en=[min(C.cheb(G.pos(c,i-1),q) for q in tiles) for c in G.team if G.team[c]!=us and G.pos(c,i-1)]
        dmin=min(en) if en else 99
        came=False
        for rr in range(r,r+left+1):
            j=G.idx.get(rr)
            if j is not None and any(G.pos(c,j) in tiles for c in G.team if G.team[c]!=us): came=True
        hp=float(h.get('hp',0) or 0); mh=G.ch[lv]['maxHp'][i-1]
        out.append(dict(key=key,r=r,g=g,c=lv,name=G.name[lv],why=cause.split(':')[2],left=left,tku=tku,dmin=dmin,came=came,hpf=hp/mh if mh else None,
            stolen=any(r<=cr<=r+15 and ct!=us for cr,ct in caps[g]),recap=any(r<cr<=r+30 and ct==us for cr,ct in caps[g]),
            died=any(r<=x<=r+15 for x in dr[lv]),gems=gv[g],diff=d,opp=G.opp,map=G.mapname))
    return out
if __name__=='__main__':
    res=[y for o in pmap(one,sorted(RS)) for y in o]
    json.dump(res,open(CACHE+'/../q1_holdwalk2.json','w'))
    nk=len(trace_keys()); n=len(res)
    print(f'want_home walk-offs from holds: {n} in {nk} traced games ({n/nk:.2f}/game, trusted rounds only)')
    print(' reasons',Counter(x['why'] for x in res),' left',sorted(Counter(x['left'] for x in res).items()))
    print(f" enemy stood on a tile within `left` rounds: {sum(x['came'] for x in res)/n:.2f}; stolen<=15 {sum(x['stolen'] for x in res)/n:.2f}; recaptured<=30 {sum(x['recap'] for x in res)/n:.2f}; leaver died<=15 {sum(x['died'] for x in res)/n:.2f}")
    for why in ('stand_lost','outmatched','stand_falls','low'):
        Z=[x for x in res if x['why']==why]
        if not Z: continue
        tk=[x for x in Z if x['tku']]
        print(f" {why:11s} n={len(Z)} left<=2 {sum(x['left']<=2 for x in Z)/len(Z):.2f} enemy came {sum(x['came'] for x in Z)/len(Z):.2f} stolen {sum(x['stolen'] for x in Z)/len(Z):.2f} died {sum(x['died'] for x in Z)/len(Z):.2f} median hp {st.median([x['hpf'] for x in Z if x['hpf'] is not None]):.2f}"
              +(f" tku median {st.median([x['tku'] for x in tk])}, tku>left+1 {sum(x['tku']>x['left']+1 for x in tk)/len(tk):.2f}" if tk else ''))
    W=[x for x in res if not x['came'] and (x['tku'] is None or x['tku']>x['left']+1) and x['why']!='low']
    print(f" would have paid by both tests (no enemy on a tile through payout, own sim survives): {len(W)} ({len(W)/n:.2f}), {sum(x['gems'] for x in W)/nk:.1f} group gems/game; of which stolen after {sum(x['stolen'] for x in W)/len(W):.2f}; leaver died<=15 anyway {sum(x['died'] for x in W)/len(W):.2f}")
    print(' by opp',{o:round(sum(1 for x in W if x['opp']==o)/sum(1 for k,g in trace_keys() if g['opp']==o),2) for o in ('Fish','Mite','UoS','PBG')})
    pm=Counter(x['map'] for x in W); print(' maps with any:',len(pm),'of',len({g['map'] for k,g in trace_keys()}),'top',pm.most_common(6))
    print(' champion',Counter(x['name'] for x in W).most_common())
    for x in W[:12]: print('  ',x['key'],'r',x['r'],'g',x['g'],x['name'],x['why'],'left',x['left'],'tku',x['tku'],'dmin',x['dmin'],'stolen',x['stolen'],'died',x['died'])
