"""Q1: snowball after a death (extract, both teams symmetric).
Per round state = alive pick units per team at the end of the previous round (C&I = one unit).
diff = own alive - enemy alive. For each team and diff bucket: deaths per 100 alive unit-rounds,
captures and captured gems per 100 alive unit-rounds, capture resets (contested / walked off), gold earned.
Event windows: the 60 rounds after a team's first death vs the 60 before (or from r1), and the time to its
second death vs the other team's deaths in that window."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from so import *
import statistics as st
PH=lambda r: 0 if r<300 else (1 if r<800 else 2)
def one(g):
    G=Game(g); us=G.us; N=G.N
    alive=[[G.alive_units(t,i) for i in range(N)] for t in (0,1)]
    # per round events
    dth=defaultdict(lambda:[0,0]); cap=defaultdict(lambda:[0,0]); capg=defaultdict(lambda:[0,0])
    rst=defaultdict(lambda:[[0,0],[0,0]])  # [team][contested]
    for e in G.ev:
        if e['k']=='death' and e.get('linked') is None: dth[e['r']][G.team[e['v']]]+=1
        elif e['k']=='capture': cap[e['r']][e['team']]+=1; capg[e['r']][e['team']]+=sum(s[1] for s in e['shares'])
        elif e['k']=='capture_reset': rst[e['r']][e['team']][1 if e.get('contested') else 0]+=1
    earned=[[sum(G.ch[c]['earned'][i] for c in G.team if G.team[c]==t) for i in range(N)] for t in (0,1)]
    # bucket accumulators: key (side 'us'/'them', diff, phase) -> [unit_rounds, deaths, caps, capgems, reset_walk, reset_cont, gold]
    acc=defaultdict(lambda:[0]*7)
    for i in range(1,N):
        r=G.rnd[i]
        for t in (0,1):
            a=alive[t][i-1]; d=a-alive[1-t][i-1]; d=max(-2,min(2,d))
            k=('us' if t==us else 'them',d,PH(r))
            A=acc[k]; A[0]+=a; A[1]+=dth[r][t]; A[2]+=cap[r][t]; A[3]+=capg[r][t]; A[4]+=rst[r][t][0]; A[5]+=rst[r][t][1]
            A[6]+=earned[t][i]-earned[t][i-1]
    # event windows
    ev=[]
    for t in (0,1):
        ds=sorted(e['r'] for e in G.deaths if G.team[e['v']]==t)
        if not ds: continue
        D=ds[0]
        def cnt(arr,lo,hi,tt): return sum(arr[r][tt] for r in range(lo,hi))
        lo=max(1,D-60)
        w=dict(side='us' if t==us else 'them', D=D, opp=G.opp, map=G.mapname, won=G.won, dir=G.dir,
               own_d_after=cnt(dth,D+1,D+61,t), oth_d_after=cnt(dth,D+1,D+61,1-t),
               own_d_before=cnt(dth,lo,D,t), oth_d_before=cnt(dth,lo,D,1-t), before_len=D-lo,
               own_cap_after=cnt(cap,D+1,D+61,t), oth_cap_after=cnt(cap,D+1,D+61,1-t),
               own_cap_before=cnt(cap,lo,D,t), oth_cap_before=cnt(cap,lo,D,1-t),
               own_capg_after=cnt(capg,D+1,D+61,t), oth_capg_after=cnt(capg,D+1,D+61,1-t),
               own_capg_before=cnt(capg,lo,D,t), oth_capg_before=cnt(capg,lo,D,1-t),
               second=(ds[1]-D) if len(ds)>1 else None,
               other_first=min([e['r'] for e in G.deaths if G.team[e['v']]==1-t] or [10**6]))
        ev.append(w)
    return dict(acc={str(k):v for k,v in acc.items()}, ev=ev, opp=G.opp, map=G.mapname)
if __name__=='__main__':
    res=pmap(one, games())
    json.dump(res,open(CACHE+'/../q1.json','w'))
    tot=defaultdict(lambda:[0]*7); byopp=defaultdict(lambda:[0]*7)
    for x in res:
        for k,v in x['acc'].items():
            k=eval(k)
            for j in range(7): tot[k][j]+=v[j]; tot[(k[0],k[1],'all')][j]+=v[j]; byopp[(x['opp'],k[0],k[1])][j]+=v[j]
    print('per 100 alive unit-rounds: deaths, captures, cap gems, resets walked/contested; gold per unit-round')
    for ph in (0,1,2,'all'):
        print('phase',ph)
        for d in (-2,-1,0,1,2):
            row=[]
            for side in ('us','them'):
                A=tot[(side,d,ph)]
                if A[0]<200: row.append(f'{side}: n/a'); continue
                row.append(f"{side}: ur={A[0]:7d} death={100*A[1]/A[0]:.2f} cap={100*A[2]/A[0]:.2f} capg={100*A[3]/A[0]:5.1f} rw={100*A[4]/A[0]:.2f} rc={100*A[5]/A[0]:.2f} gold={A[6]/A[0]:.2f}")
            print(f'  diff {d:+d}  '+' | '.join(row))
    print('death hazard by opponent (diff -1 / 0 / +1)')
    for o in ('Fish','Mite','UoS','PBG'):
        s=[]
        for side in ('us','them'):
            s.append(side+' '+' '.join(f"{100*byopp[(o,side,d)][1]/max(1,byopp[(o,side,d)][0]):.2f}" for d in (-1,0,1)))
        print(' ',o,' | '.join(s))
    E=[w for x in res for w in x['ev']]
    for side in ('us','them'):
        W=[w for w in E if w['side']==side and w['D']<w['other_first']]  # this team died first
        n=len(W)
        f=lambda k: sum(w[k] for w in W)/n
        print(f"\n{side} died first: n={n} median D={st.median(w['D'] for w in W)}")
        print(f"  next 60 rounds: own deaths {f('own_d_after'):.2f}, other team deaths {f('oth_d_after'):.2f}")
        print(f"  captures own/other after {f('own_cap_after'):.2f}/{f('oth_cap_after'):.2f} (before, per 60: {sum(w['own_cap_before'] for w in W)/sum(w['before_len'] for w in W)*60:.2f}/{sum(w['oth_cap_before'] for w in W)/sum(w['before_len'] for w in W)*60:.2f})")
        print(f"  cap gems own/other after {f('own_capg_after'):.1f}/{f('oth_capg_after'):.1f} (before per 60: {sum(w['own_capg_before'] for w in W)/sum(w['before_len'] for w in W)*60:.1f}/{sum(w['oth_capg_before'] for w in W)/sum(w['before_len'] for w in W)*60:.1f})")
        sec=[w['second'] for w in W if w['second'] is not None]
        print(f"  second own death: median gap {st.median(sec)} ; within 60: {sum(s<=60 for s in sec)/n:.2f}; first death median round {st.median(w['D'] for w in W)}; win {sum(w['won']==(side=='us') for w in W)/n:.2f}")
        # same with the time-matched comparison: the other side when it dies first
