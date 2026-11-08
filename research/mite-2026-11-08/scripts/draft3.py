import json,collections,datetime
ix=json.load(open('mite_index.json'))
def ts(mid): return int(mid.replace('-','')[:12],16)/1000
H=lambda o: datetime.datetime.utcfromtimestamp(ts(o['mid'])).strftime('%m-%d %H')
wins={'05 00-03':('11-05 00','11-05 03'),'05 08-14':('11-05 08','11-05 14'),'05 17-23':('11-05 17','11-05 23'),'06 21-07 04':('11-06 21','11-07 04'),'07 05-14':('11-07 05','11-07 14')}
def purity(S,keyf):
    cells=collections.defaultdict(collections.Counter)
    for o in S:
        for k in range(len(o['picks'])):
            key=keyf(o,k)
            if key is None: continue
            cells[key][o['picks'][k]]+=1
    n=sum(sum(c.values()) for c in cells.values() if sum(c.values())>=2)
    hit=sum(c.most_common(1)[0][1] for c in cells.values() if sum(c.values())>=2)
    return hit,n,len(cells)
for name,(a,b) in wins.items():
    S=[o for o in ix if a<=H(o)<=b]
    r0=purity(S,lambda o,k:(o['mhash'],tuple(o['picks'][:k])))
    r1=purity(S,lambda o,k:(o['mhash'],tuple(o['picks'][:k]),tuple(o['opicks'][:k])))
    r2=purity(S,lambda o,k:(o['mhash'],o['side'],tuple(o['picks'][:k])))
    r3=purity(S,lambda o,k:(o['mhash'],tuple(o['picks'][:k]),o['opp']))
    print(f"{name}: games {len(S)}  map {r0[0]/r0[1]:.3f}  map+oppprefix {r1[0]/r1[1]:.3f}  map+side {r2[0]/r2[1]:.3f}  map+oppteam {r3[0]/r3[1]:.3f}")
    print('   orders:',collections.Counter(tuple(o['picks']) for o in S).most_common(4))
