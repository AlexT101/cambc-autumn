"""For enemy captures with one of ours within 6 of the tiles at hold start: our nearest champion's branch then, and
whether the group has 2+ tiles (contestable while the holder stands on one)."""
import gzip,json,sys,collections,os,zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    try: z=zipfile.ZipFile(meta['source'])
    except Exception: return []
    br={}
    for f in ('team-a.stdout','team-b.stdout'):
        for line in z.read(f).decode(errors='replace').splitlines():
            if line.startswith('D '):
                p=line.split(); br[(int(p[1]),int(p[2]))]=p[3]
    tiles={x['id']:x['tiles'] for x in mp['groups']}; gems={x['id']:x['gems'] for x in mp['groups']}
    names={int(c['id']):c['name'] for c in meta['champions']}
    ch=R['champions']; out=[]
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='capture': continue
        t=e['team']; gid=e['g']; r=e['r']; i=max(0,r-7)
        best=99; who=None
        for c in ch:
            if int(c['team'])==t or not c['alive'][i]: continue
            dd=min(max(abs(c['x'][i]-x),abs(c['y'][i]-y)) for x,y in tiles[gid])
            if dd<best: best,who=dd,int(c['id'])
        if best<=6:
            out.append((br.get((r-6,who),'?'),len(tiles[gid])>1,gems[gid],names[who]))
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    G=2*len(dirs)
    print('within 6 at hold start, per team-game',len(res)/G,'multi-tile share',round(sum(x[1] for x in res)/len(res),2))
    print('our nearest body branch:',[(k,round(v/G,2)) for k,v in collections.Counter(x[0] for x in res).most_common(10)])
    print('by type:',[(k,round(v/G,2)) for k,v in collections.Counter(x[3] for x in res).most_common(8)])
