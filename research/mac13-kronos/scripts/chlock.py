# At the start of each giant (200+) winning enemy channel: the losers' living champions, their locks,
# and whether each could reach lock range (Chebyshev - 2) within the channel. Also lock placements a game.
import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}
    w=m['result']['winner']
    starts={}; win=None; places=collections.Counter(); cancels_by_lock=0
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    lockrounds=collections.defaultdict(set)
    for e in ev:
        if e['k']=='lock_place': places[team[e['a']]]+=1; lockrounds[e['r']].add(team[e['a']])
    for e in ev:
        if e['k']=='tribute_start': starts[e['a']]=e
        elif e['k']=='tribute_end':
            s=starts.pop(e['a'],None)
            if team[e['a']]==w and e['total']>=1000 and s and s['gems']>=200: win=(e['a'],s['r'],e['r'],s['gems'])
        elif e['k']=='tribute_cancel': starts.pop(e['a'],None)
    if not win: return ('nowin',places)
    a,r0,r1,g=win
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round']); r1=min(r1,T-1)
    P=[c for c in o['champions'] if c['id']==a][0]
    px,py=P['x'][r0],P['y'][r0]; dur=r1-r0
    alive=0; withlock=0; reachlock=0; reachany=0
    for c in o['champions']:
        if c['team']==w: continue
        if not c['alive'][r0] or c['x'][r0] is None: continue
        alive+=1
        dd=max(abs(c['x'][r0]-px),abs(c['y'][r0]-py))
        lk=c['cons'][r0][2]>0
        withlock+=lk
        ok=dd-2 <= dur*0.8
        reachany+=ok; reachlock+=ok and lk
    return ('win',places,dur,alive,withlock,reachany,reachlock)
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=4) if x]
    pl=[v for x in R for v in (x[1][0],x[1][1])]
    print('games',len(R),'lock placements per team-game',statistics.mean(pl))
    W=[x for x in R if x[0]=='win']
    print('giant winning channels',len(W),'median dur',statistics.median(x[2] for x in W))
    print('losers alive at start (mean)',statistics.mean(x[3] for x in W),'with lock',statistics.mean(x[4] for x in W))
    print('channels with >=1 alive loser able to reach lock range in 80% of the channel',sum(x[5]>0 for x in W))
    print('... of which one carried a lock',sum(x[6]>0 for x in W))
    print('channels with no alive lock carrier',sum(x[4]==0 for x in W))
