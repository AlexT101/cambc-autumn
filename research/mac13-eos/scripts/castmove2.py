"""Prism quiet-unused ready casts while hitting a camp: the group's remaining hp vs the cast's damage; enemies seen in prior 8 rounds."""
import gzip,json,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}; team={int(c['id']):int(c['team']) for c in meta['champions']}
    gid={c['id']:c['group'] for c in json.load(open(d/meta['mapFile']))['camps']} if False else None
    import os
    mp=json.load(open(os.path.join(d,meta['mapFile']))); camp2g={c['id']:c['group'] for c in mp['camps']}
    ghp={}
    for row in R['groups']:
        ghp[(row[0],row[1])]=row[7]
    campatk={}; castr=set()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']=='cast': castr.add((e['r'],e['a'],e['slot']))
        if e['k']=='attack' and e.get('camp') is not None: campatk[(e['r'],e['a'])]=e['camp']
    out=collections.Counter()
    import zipfile
    br={}
    try:
        z=zipfile.ZipFile(meta['source'])
        for f in ('team-a.stdout','team-b.stdout'):
            for line in z.read(f).decode(errors='replace').splitlines():
                if line.startswith('D '):
                    p=line.split(); br[(int(p[1]),int(p[2]))]=p[3]
    except Exception: pass
    for c in R['champions']:
        cid=int(c['id'])
        if names[cid]!='Prism': continue
        for s in (0,1):
            cd=c['cd%d'%s]
            for i in range(1,len(cd)):
                r=i+1
                if not(c['alive'][i] and cd[i-1]==0 and (r,cid) in campatk and (r,cid,s) not in castr): continue
                seen=c['sees'][i] or []
                if any(team.get(x if not isinstance(x,list) else x[0])!=team[cid] for x in seen): continue
                recent=any(any(team.get(x if not isinstance(x,list) else x[0])!=team[cid] for x in (c['sees'][j] or [])) for j in range(max(0,i-8),i))
                g_=camp2g.get(campatk[(r,cid)]); hp=ghp.get((r,g_), ghp.get((r-1,g_)))
                dmg=(1.5 if s==0 else 1.0)*c['foc'][i]
                out['n']+=1; out['recent_enemy']+=recent
                if hp is not None and hp>dmg and not recent: out[('br',br.get((r,cid),'?'))]+=1
                if hp is not None:
                    out['hp_known']+=1; out['hp_gt_dmg']+=hp>dmg; out['hp_gt_2dmg']+=hp>2*dmg
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()][:400]
    T=collections.Counter()
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8): T.update(r)
    print({k:v for k,v in T.items()}, 'per game', T['n']/400, 'hp>dmg share', round(T['hp_gt_dmg']/max(1,T['hp_known']),2), 'enemy seen in prior 8r', round(T['recent_enemy']/T['n'],2))
