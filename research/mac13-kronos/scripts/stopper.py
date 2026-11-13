# stop-ender ('E') episodes: does the stopper die, is a channel cancelled, does the game end meanwhile.
import json,gzip,glob,collections,statistics,zipfile
from multiprocessing import Pool
def one(f):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: return None
    d=f.rsplit('/',1)[0]
    team={c['id']:c['team'] for c in m['champions']}; names={c['id']:c['name'] for c in m['champions']}
    w=m['result']['winner']
    o=json.load(gzip.open(d+'/rounds.json.gz')); T=len(o['round']); C={c['id']:c for c in o['champions']}
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz')]
    cancels=[(e['r'],team[e['a']],e['cause'],e['gems']) for e in ev if e['k']=='tribute_cancel' and e['cause'] in('stun','lock')]
    deaths=[(e['r'],e.get('a'),e) for e in ev if e['k']=='death']
    z=zipfile.ZipFile('/home/ubuntu/wt/mac13-kronos/'+m['source'])
    out=[]
    for side in (0,1):
        rounds=collections.defaultdict(list)
        for line in z.read('team-%s.stdout'%'ab'[side]).decode('latin1').splitlines():
            if line.startswith('D '):
                p=line.split()
                if p[3]=='E': rounds[int(p[2])].append(int(p[1]))
        for cid,rs in rounds.items():
            rs=sorted(set(rs)); eps=[]; s=rs[0]; prev=rs[0]
            for r in rs[1:]:
                if r>prev+2: eps.append((s,prev)); s=r
                prev=r
            eps.append((s,prev))
            c=C[cid]
            for a,b in eps:
                if a>=T: continue
                died=any(not c['alive'][r] for r in range(a,min(b+4,T)))
                canc=[x for x in cancels if a<=x[0]<=b+1 and x[1]!=team[cid]]
                big=sum(x[3] for x in canc)
                end=b>=T-3
                out.append((team[cid]==w,names[cid],b-a+1,died,len(canc)>0,big,end, c['gems'][a] if c['gems'][a] is not None else 0))
    return out
if __name__=='__main__':
    fs=glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json')
    with Pool(16) as p: R=[x for r in p.map(one,fs,chunksize=4) if r for x in r]
    print('E episodes',len(R),'per team-game',len(R)/2048)
    for wn in (True,False):
        S=[x for x in R if x[0]==wn]
        print('winner' if wn else 'loser',len(S),'died',round(sum(x[3] for x in S)/len(S),3),'cancelled a channel',round(sum(x[4] for x in S)/len(S),3),
              'game ended in episode',round(sum(x[6] for x in S)/len(S),3),'median len',statistics.median(x[2] for x in S),'own bag median',statistics.median(x[7] for x in S))
    print('died & no cancel',sum(x[3] and not x[4] for x in R),'cancel & survived',sum(x[4] and not x[3] for x in R),'both',sum(x[3] and x[4] for x in R),'neither',sum(not x[3] and not x[4] for x in R))
    print('died, by champ',collections.Counter(x[1] for x in R if x[3]).most_common(8))
    print('bag lost on E deaths: median',statistics.median([x[7] for x in R if x[3]] or [0]),'mean',statistics.mean([x[7] for x in R if x[3]] or [0]))
