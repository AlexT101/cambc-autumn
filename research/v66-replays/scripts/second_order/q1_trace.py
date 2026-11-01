"""Q1 trace side: our decisions by manpower state (trusted rounds only).
Per our alive champion turn: diff = our alive units - theirs at the end of the previous round (extract),
`fresh` = one of ours died within the last 60 rounds. Rates of TT d branches and TE home reasons (v=1).
Capture resets of ours: who left the tiles and why (trace d, home reason)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(arg):
    key,g=arg
    G=Game(g); T=tload(key); us=G.us; tr=T['trust']
    alive=[[G.alive_units(t,i) for i in range(G.N)] for t in (0,1)]
    ours=[e['r'] for e in G.deaths if G.team[e['v']]==us]
    cnt=defaultdict(Counter)
    for (r,c),L in T['turns'].items():
        tt=L.get('tt')
        if not tt or tt.get('a')!='1' or r not in G.idx: continue
        i=G.idx[r]
        if i==0: continue
        d=max(-2,min(2,alive[us][i-1]-alive[1-us][i-1]))
        fresh=any(0<r-x<=60 for x in ours)
        k=(d,fresh)
        C_=cnt[k]; C_['turns']+=1; C_['d_'+tt.get('d','?')]+=1
        for e in L['te']:
            if e['k']=='home' and e.get('v')=='1': C_['home_'+e.get('why','?')]+=1
            if e['k']=='home' and e.get('v')=='0': C_['stay_'+e.get('why','?')]+=1
    # capture resets by us
    gt={gg['id']:set(map(tuple,gg['tiles'])) for gg in G.mp['groups']}
    resets=[]
    for e in G.ev:
        if e['k']!='capture_reset' or e['team']!=us or e['r']>tr: continue
        r=e['r']; i=G.idx.get(r)
        if i is None or i==0: continue
        tiles=gt[e['g']]
        leavers=[c for c in G.team if G.team[c]==us and G.pos(c,i-1) in tiles and G.pos(c,i) not in tiles]
        if e.get('contested'): cause='contested'
        elif not leavers: cause='other'
        else:
            c=leavers[0]
            if not G.ch[c]['alive'][i]: cause='died'
            else:
                L=T['turns'].get((r,c),{}); tt=L.get('tt',{})
                why=[x.get('why') for x in L.get('te',[]) if x['k']=='home' and x.get('v')=='1']
                br=[x.get('why') for x in L.get('te',[]) if x['k']=='branch']
                cause='left:'+tt.get('d','?')+(':'+why[0] if why else '')+(':'+br[0] if br else '')
        d=max(-2,min(2,alive[us][i-1]-alive[1-us][i-1]))
        resets.append((cause,d,e.get('left'),key,r,e['g']))
    return dict(cnt={str(k):dict(v) for k,v in cnt.items()}, resets=resets, opp=G.opp, map=G.mapname)
if __name__=='__main__':
    res=pmap(one, trace_keys())
    json.dump(res,open(CACHE+'/../q1_trace.json','w'))
    tot=defaultdict(Counter)
    for x in res:
        for k,v in x['cnt'].items(): tot[eval(k)].update(v)
    keys=['d_F','d_R','d_C','d_A','d_P','d_B','d_K','d_H','d_Q','d_X','d_G','home_low','home_outmatched','home_stand_lost','home_stand_falls','home_willow_threat','home_camp','stay_stand_ok']
    print('per 100 alive turns; key=(diff, our death within 60)')
    print('%-12s %7s '%('state','turns')+' '.join('%9s'%k for k in keys))
    for d in (-2,-1,0,1,2):
        for fr in (False,True):
            C_=tot[(d,fr)]
            if C_['turns']<500: continue
            print('%-12s %7d '%(f'{d:+d},{int(fr)}',C_['turns'])+' '.join('%9.2f'%(100*C_[k]/C_['turns']) for k in keys))
    R=[r for x in res for r in x['resets']]
    print('\nour capture resets (trusted):',len(R))
    print(Counter(r[0] for r in R).most_common(25))
    for d in (-2,-1,0,1,2):
        Z=[r for r in R if r[1]==d]; print(d,len(Z),Counter(r[0].split(':')[0]+':'+(r[0].split(':')[1] if ':' in r[0] else '') for r in Z).most_common(6))
