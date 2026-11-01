"""Q5: deaths right after a kill (trade-backs). For each death of team T within 20 rounds and 10 tiles after a kill
by T: a trade-back. Both teams from the extract; ours joined with the trace (deaths_tr.json: last turn's branch,
want_home) and with what the victim did over the rounds between the kill and its death (TT d counts)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
def one(g):
    G=Game(g); us=G.us; out=[]
    ds=sorted([e for e in G.deaths if e.get('at')],key=lambda e:e['s'])
    for j,e in enumerate(ds):
        t=G.team[e['v']]
        prior=[x for x in ds[:j] if x.get('by') is not None and G.team[x['by']]==t and e['r']-x['r']<=20 and C.cheb(x['at'],e['at'])<=10]
        out.append(dict(side='us' if t==us else 'them',tb=bool(prior),kr=prior[-1]['r'] if prior else None,victim_was_killer=bool(prior) and G.unit.get(prior[-1]['by'])==G.unit[e['v']],r=e['r'],v=e['v'],src=g['source'],dir=G.dir,camp=e.get('camp') is not None,gems=e.get('gems',0)))
    return out
if __name__=='__main__':
    res=[y for o in pmap(one,games()) for y in o]
    for s in('us','them'):
        Z=[x for x in res if x['side']==s]; tb=[x for x in Z if x['tb']]
        print(f"{s}: deaths {len(Z)}, trade-backs (died <=20r/10 tiles after own kill) {len(tb)} ({len(tb)/412:.2f}/game, {len(tb)/len(Z):.2f} of deaths); victim was the killer {sum(x['victim_was_killer'] for x in tb)/len(tb):.2f}; gems lost in them {sum(x['gems'] for x in tb)/412:.1f}/game")
    # trace join
    M=manifest(); D=json.load(open(CACHE+'/../deaths_tr.json'))
    tbset={(x['dir'],x['r']) for x in res if x['side']=='us' and x['tb']}
    G={g['source']:g['dir'] for g in C.games(distinct=False)}
    A=[d for d in D if (G.get(d['src']),d['r']) in tbset]; B=[d for d in D if (G.get(d['src']),d['r']) not in tbset]
    for nm,Z in(('trade-back',A),('other',B)):
        print(nm,len(Z),'last d',Counter(d['d'] for d in Z).most_common(6),'home',Counter(tuple(d['home']) if d['home'] else None for d in Z).most_common(6))
    # what victims did between the kill and the death (trace)
    TK={k:g for k,g in trace_keys()}
    byk=defaultdict(list)
    for x in res:
        if x['side']=='us' and x['tb']: byk[M.get(x['src'])].append(x)
    cnt=Counter(); n=0
    for k,L in byk.items():
        if k not in TK: continue
        T=tload(k)
        for x in L:
            for r in range(x['kr']+1,x['r']+1):
                tt=T['turns'].get((r,x['v']),{}).get('tt')
                if tt and tt.get('a')=='1': cnt[tt.get('d')]+=1; n+=1
    print('victims\' branches between the kill and their death:',{k:round(v/n,3) for k,v in cnt.most_common(10)})
