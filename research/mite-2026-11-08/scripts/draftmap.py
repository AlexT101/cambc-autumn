import json,gzip,os,collections
R='/home/ubuntu/cambc-autumn/replays/fish-scorecard/mite-1107/'
ix={o['mid']:o for o in json.load(open('mite_index.json'))}
rows={}
for p in ('A','B'):
    for f in os.listdir(R+p+'/actor'):
        d=json.load(gzip.open(R+p+'/actor/'+f)); m=d['map']; o=ix[d['match']]
        c=collections.Counter(x['type'] for x in m['camps'])
        key=o['mhash']
        rows[key]=dict(picks=tuple(o['picks']),n=o['rounds'],w=m['width'],h=m['height'],wolf=c[0],elk=c[1],gem=c[2],gold=c[3],mono=c[4],golem=c[5],
                       altars=len(m['altars']),groups=len(m['groups']),bush=len(m['bushes']),walls=len(m['walls']),holes=len(m['holes']),sym=m['symmetry'])
print(len(rows),'maps')
byo=collections.defaultdict(list)
for k,r in rows.items(): byo[r['picks']].append(r)
for o,v in sorted(byo.items(),key=lambda x:-len(x[1])):
    avg=lambda f: round(sum(r[f] for r in v)/len(v),1)
    print(len(v),o); print('    ',{f:avg(f) for f in ('w','gem','gold','wolf','elk','golem','mono','altars','groups','bush')}, collections.Counter(r['n'] for r in v))
json.dump(list(rows.values()),open('draftmap.json','w'))
