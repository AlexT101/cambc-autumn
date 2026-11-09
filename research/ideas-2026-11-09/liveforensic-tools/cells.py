import os
# Live-loss forensics (EXPERIMENTS "Why v90-v93 lose live"): pickles and extractions live in ~/tmp-offload/liveforensic.
import sys, json, math, collections
sys.path.insert(0,'/home/ubuntu/cambc-autumn/tools')
import ladder_scrims as L
mc=json.load(open('/home/ubuntu/tmp-offload/handoff/gate/mapclass.json'))
V=[86,87,88,89,90,91,93,95]
cells=collections.defaultdict(dict)
for v in V:
    for r in L.games(v):
        if r.get('refset')!='r2': continue
        k=(r['map'],r['side'],'fish' if 'Fish' in r['opp_name'] else 'mite')
        cells[k][v]=r
def fp(r): return (r['result'],r['rounds'],r['our_gems'],r['opp_gems'],r['our_gold'],r['opp_gold'],r['our_kills'],r['opp_kills'])
import pickle
pickle.dump((dict(cells),mc),open(os.path.expanduser('~/tmp-offload/liveforensic/')+'cells.pkl','wb'))
print(len(cells))
for v in V:
    rs=[c[v] for c in cells.values() if v in c]
    w=sum(r['result']=='win' for r in rs); print(v,len(rs),w,round(100*w/len(rs),1))
# identity matrix
print('identical games')
for a in V:
    print(a,[sum(1 for c in cells.values() if a in c and b in c and fp(c[a])==fp(c[b])) for b in V])
print('flip net (row minus col) ')
for a in V:
    row=[]
    for b in V:
        pa=pb=0
        for c in cells.values():
            if a in c and b in c:
                wa=c[a]['result']=='win'; wb=c[b]['result']=='win'
                pa+=wa and not wb; pb+=wb and not wa
        row.append(f"{pa-pb:+d}/{pa+pb}")
    print(a,row)
