# Capture gems by group side (our half / their half / shared) in losses vs wins; plus deaths by phase.
import pickle,json,os,collections,numpy as np,sys
R=pickle.load(open(os.path.expanduser('~/tmp-offload/bigl/feats.pkl'),'rb'))
ana=os.path.expanduser('~/tmp-offload/bigl/ana')
mapcache={}
def groups(r):
    meta=json.load(open(f"{ana}/{r['dir']}/meta.json"))
    f=meta['mapFile']
    if f not in mapcache: mapcache[f]=json.load(open(os.path.join(ana,'maps',os.path.basename(f))))
    return {g['id']:g for g in mapcache[f]['groups']}
out=collections.defaultdict(list)
for r in R:
    G=groups(r); us=0 if r['side']=='a' else 1
    acc=collections.Counter()
    for k,v in r['capg'].items():
        g,who=k.split(':'); s=G[int(g)]['side']
        where='shared' if s==-1 else ('ours' if s==us else 'theirs')
        acc[(where,who)]+=v
    out['L' if not r['win'] else 'W'].append(acc)
for k in ('L','W'):
    a=out[k]; print(k,len(a))
    for where in ('ours','shared','theirs'):
        print(f'  {where:7s} me {np.mean([x[(where,"me")] for x in a]):7.1f}  op {np.mean([x[(where,"op")] for x in a]):7.1f}')
