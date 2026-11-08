import json,os,sys,collections
G='/home/ubuntu/tmp-offload/gaps/'
games=json.load(open(G+'games.json'))
out=[]
for d in os.listdir(G+'analysis'):
    try: m=json.load(open(G+'analysis/'+d+'/meta.json'))
    except Exception: continue
    mid=os.path.basename(m['source']).split('.')[0]
    g=games.get(mid)
    if not g: continue
    for side,key in ((0,'name_a'),(1,'name_b')):
        if g[key]=='Mite':
            out.append(dict(dir=d,mid=mid,side=side,opp=g['name_b' if side==0 else 'name_a'],src=g['src'],kind=g['kind'],
              map=m['map']['name'],mhash=m['map']['hash'],w=m['map']['width'],h=m['map']['height'],
              picks=m['draft']['picks'][side],opicks=m['draft']['picks'][1-side],rounds=m['draft']['rounds'],
              winner=m.get('winner'),meta_keys=list(m.keys())))
json.dump(out,open('mite_index.json','w'))
print(len(out), collections.Counter((o['src'],o['kind']) for o in out))
print(out[0]['meta_keys'])
print(collections.Counter(o['opp'] for o in out).most_common(15))
