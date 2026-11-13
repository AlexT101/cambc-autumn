import json,gzip,glob,collections,statistics
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}; team={c['id']:c['team'] for c in m['champions']}
    w=m['result']['winner']; R=m['result']['rounds']
    starts={}; out=dict(win_tr=None, loser_cancels=0, winner_cancels=0, loser_long_starts=0, loser_long_cancel=0, loser_chan_at_end=None)
    for l in gzip.open(d+'/events.jsonl.gz'):
        e=json.loads(l)
        k=e['k']
        if k=='tribute_start': starts[e['a']]=e
        elif k=='tribute_cancel':
            s=starts.pop(e['a'],None)
            if team[e['a']]==w: out['winner_cancels']+=1
            else:
                out['loser_cancels']+=1
                if s and s['gems']>=100: out['loser_long_cancel']+=1
        elif k=='tribute_end':
            s=starts.pop(e['a'],None)
            if team[e['a']]==w and e['total']>=1000 and s: out['win_tr']=(names[e['a']], s['gems'], s['dur'], e['r']-s['r'])
        if k=='tribute_start' and team[e['a']]!=w and e['gems']>=100: out['loser_long_starts']+=1
    for a,s in starts.items():
        if team[a]!=w: out['loser_chan_at_end']=(names[a], s['gems'], s['dur'], R-s['r'])
    out['outcome']=m['result']['outcome']; out['R']=R
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for x in p.map(one,fs,chunksize=8) if x]
    print('games',len(R), collections.Counter(x['outcome'] for x in R))
    wt=[x['win_tr'] for x in R if x['win_tr']]; print('winning tributes found',len(wt), collections.Counter(t[0] for t in wt).most_common(6))
    g=sorted(t[1] for t in wt); n=len(g); print('winning tribute gems',[g[int(n*q)] for q in (.1,.25,.5,.75,.9)])
    big=[t for t in wt if t[1]>=200]; print('winning tributes >=200 gems',len(big))
    print('loser channelling at end',sum(1 for x in R if x['loser_chan_at_end']), collections.Counter(x['loser_chan_at_end'][0] for x in R if x['loser_chan_at_end']).most_common(4))
    lc=[x['loser_chan_at_end'] for x in R if x['loser_chan_at_end']]; 
    if lc: print(' loser channel gems median',statistics.median(t[1] for t in lc),'turns in',statistics.median(t[3] for t in lc),'dur',statistics.median(t[2] for t in lc))
    print('loser cancels/game',sum(x['loser_cancels'] for x in R)/len(R),'winner cancels/game',sum(x['winner_cancels'] for x in R)/len(R))
    print('loser long(>=100) starts/game',sum(x['loser_long_starts'] for x in R)/len(R),'long cancels',sum(x['loser_long_cancel'] for x in R)/len(R))
