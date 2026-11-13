"""Still farm turns: the farm group's state and distance. py fstill.py EXTRACT_DIR"""
import gzip,json,sys,collections,zipfile,os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
GS=['unknown','camps','empty','respawning']
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    try: z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    team={int(c['id']):int(c['team']) for c in meta['champions']}; names={int(c['id']):c['name'] for c in meta['champions']}
    br={}
    for f in ('team-a.stdout','team-b.stdout'):
        for line in z.read(f).decode(errors='replace').splitlines():
            if line.startswith('D '):
                p=line.split()
                if len(p)>=6: br[(int(p[1]),int(p[2]))]=(p[3],int(p[4]),int(p[5]))
    dealt=set()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k'] in ('attack','camp_attack','cast'): dealt.add((e['r'],e.get('a')))
    # group state per round (forward fill)
    rows=collections.defaultdict(list)
    for r in R['groups']: rows[r[1]].append(r)
    def gstate(gid,rnd):
        st=None
        for r in rows.get(gid,[]):
            if r[0]<=rnd: st=r
            else: break
        return st
    tiles={x['id']:x['tiles'] for x in mp['groups']}
    out=collections.Counter()
    ch={int(c['id']):c for c in R['champions']}; n=len(R['round'])
    for cid,c in ch.items():
        s=mp['spawn'][team[cid]]
        for i in range(1,n):
            if not c['alive'][i]: continue
            b=br.get((i+1,cid))
            if not b or b[0]!='F': continue
            on=s['minX']<=c['x'][i]<=s['maxX'] and s['minY']<=c['y'][i]<=s['maxY']
            if not(c['x'][i]==c['x'][i-1] and c['y'][i]==c['y'][i-1] and not on and (i+1,cid) not in dealt): continue
            fg=b[1]
            if fg<0 or fg not in tiles: out[(names[cid],'nogroup')]+=1; continue
            st=gstate(fg,i+1)
            dd=min(max(abs(c['x'][i]-x),abs(c['y'][i]-y)) for x,y in tiles[fg])
            state=GS[st[2]] if st else '?'
            if state=='camps': state+=('-awake' if st[6] else '-asleep')
            out[(names[cid],state,'on' if dd==0 else 'd<=4' if dd<=4 else 'far')]+=1
    return out
if __name__=='__main__':
    root=Path(sys.argv[1]); dirs=[d for d in root.iterdir() if (d/'meta.json').exists()][:300]
    T=collections.Counter(); G=0
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=4):
            if r: T.update(r); G+=1
    print('games',G)
    agg=collections.Counter()
    for (nm,*k),v in T.items(): agg[tuple(k)]+=v
    for k,v in agg.most_common(15): print(k, round(v/G,1),'per game')
    for k,v in T.most_common(15): print(k, round(v/G,1))
