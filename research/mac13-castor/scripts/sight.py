import json,gzip,glob,collections,sys,os
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(d):
    meta=json.load(open(d+'/meta.json'))
    R=json.load(gzip.open(d+'/rounds.json.gz'))
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    rid={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    out=collections.Counter()
    # per death by a champion: killer id
    for e in ev:
        if e['k']!='death': continue
        v=e.get('v'); k=e.get('by', e.get('killer'))
        if v is None or k is None or k not in C: continue
        if C[k]['team']==C[v]['team']: continue
        i=rid.get(e['r'])
        if i is None: continue
        out['deaths']+=1
        team=C[v]['team']
        allies=[c for c in R['champions'] if c['team']==team and c['id']!=v]
        for lag in (1,3,5,8):
            lo=max(0,i-lag)
            self_saw=any(k in C[v]['sees'][j] for j in range(lo,i))
            ally_saw=any(k in a['sees'][j] for a in allies for j in range(lo,i))
            if not self_saw and ally_saw: out[f'ally_only_{lag}']+=1
            if not self_saw and not ally_saw: out[f'nobody_{lag}']+=1
            if self_saw: out[f'self_{lag}']+=1
    # generic: fraction of champion-rounds where an enemy within 8 (chebyshev) is unseen by self but seen by an ally
    for c in R['champions']:
        allies=[a for a in R['champions'] if a['team']==c['team'] and a['id']!=c['id']]
        enem=[a for a in R['champions'] if a['team']!=c['team']]
        for i in range(0,len(R['round']),3):
            if not c['alive'][i] or c['x'][i] is None: continue
            for e in enem:
                if not e['alive'][i] or e['x'][i] is None: continue
                dd=max(abs(c['x'][i]-e['x'][i]),abs(c['y'][i]-e['y'][i]))
                if dd>8: continue
                out['near']+=1
                s=e['id'] in c['sees'][i]; a=any(e['id'] in x['sees'][i] for x in allies)
                out['near_self' if s else ('near_allyonly' if a else 'near_none')]+=1
    return out
if __name__=='__main__':
    ds=[os.path.dirname(p) for p in glob.glob(ROOT+'/*/meta.json')]
    tot=collections.Counter()
    with ProcessPoolExecutor(48) as ex:
        for o in ex.map(one,ds,chunksize=4): tot+=o
    print(dict(tot))
