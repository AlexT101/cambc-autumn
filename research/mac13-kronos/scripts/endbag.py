import json,gzip,glob,collections
rows=[]
for f in glob.glob('/home/ubuntu/wt/mac13-kronos/replays/.analysis/*/meta.json'):
    m=json.load(open(f))
    if 'bel-study512' not in m['source']: continue
    d=f.rsplit('/',1)[0]
    names={c['id']:c['name'] for c in m['champions']}
    o=json.load(gzip.open(d+'/rounds.json.gz'))
    w=m['result']['winner']; T=len(o['round'])
    lt=1-w
    bag={0:0,1:0}; pbag={0:0,1:0}
    for c in o['champions']:
        g=c['gems'][-1] if c['alive'][-1] else 0
        bag[c['team']]+=g
        if names[c['id']]=='Prism': pbag[c['team']]=g
    sc=m['result']['gems']
    rows.append((sc[lt], bag[lt], pbag[lt], sc[w], bag[w], T, m['result']['outcome']))
n=len(rows)
print('n',n)
# loser score+bag >= 1000 at the end?
over=[r for r in rows if r[0]+r[1]>=1000]; print('loser score+bags >=1000 at end:',len(over))
over2=[r for r in rows if r[0]+r[2]>=1000]; print('loser score+prism bag >=1000:',len(over2))
big=[r for r in rows if r[2]>=300]; print('loser prism bag>=300 at end:',len(big))
import statistics
print('median loser score',statistics.median(r[0] for r in rows),'median loser bags',statistics.median(r[1] for r in rows),'median loser prism bag',statistics.median(r[2] for r in rows))
print('loser score+bags quantiles',sorted(r[0]+r[1] for r in rows)[n//10::n//10])
