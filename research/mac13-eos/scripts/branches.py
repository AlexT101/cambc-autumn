"""Turn share by decision branch (D trace lines), and for 'still' turns (alive, same tile as last round, off spawn,
no damage dealt) which branch. Winner vs loser. py branches.py EXTRACT_DIR"""
import gzip,json,sys,collections,zipfile,re,os
LO=int(os.environ.get('LO','1')); HI=int(os.environ.get('HI','99999'))
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    mp=json.load(open(os.path.join(d,meta['mapFile'])))
    w=meta['result']['winner']; src=meta['source']
    try: z=zipfile.ZipFile(src)
    except Exception: return None
    team={int(c['id']):int(c['team']) for c in meta['champions']}
    names={int(c['id']):c['name'] for c in meta['champions']}
    br={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for line in z.read(f).decode(errors='replace').splitlines():
            if line.startswith('D '):
                p=line.split()
                if len(p)>=4: br[(int(p[1]),int(p[2]))]=p[3]
    dealt=set()
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k'] in ('attack','camp_attack','cast'): dealt.add((e['r'],e.get('a')))
    ch={int(c['id']):c for c in R['champions']}
    n=len(R['round'])
    tot=collections.Counter(); still=collections.Counter()
    for cid,c in ch.items():
        t=team[cid]; s=mp['spawn'][t]; role=('W' if t==w else 'L')
        for i in range(max(1,LO),min(n,HI)):
            if not c['alive'][i]: continue
            b=br.get((i+1,cid),'?')
            tot[(role,b)]+=1
            on=s['minX']<=c['x'][i]<=s['maxX'] and s['minY']<=c['y'][i]<=s['maxY']
            if c['x'][i]==c['x'][i-1] and c['y'][i]==c['y'][i-1] and not on and (i+1,cid) not in dealt and c['chan'][i] in (0,1):
                still[(role,b,names[cid])]+=1
    return tot,still
if __name__=='__main__':
    root=Path(sys.argv[1])
    dirs=[d for d in root.iterdir() if (d/'meta.json').exists()]
    T=collections.Counter(); S=collections.Counter(); G=0
    with ProcessPoolExecutor(32) as ex:
        for r in ex.map(g,dirs,chunksize=8):
            if r: T.update(r[0]); S.update(r[1]); G+=1
    print('games',G)
    for role in 'WL':
        tt=sum(v for (r,b),v in T.items() if r==role)
        print(role,'branch share of alive turns:',' '.join(f'{b}:{v/tt:.3f}' for (r,b),v in sorted(T.items(),key=lambda kv:-kv[1]) if r==role))
        ss=collections.Counter()
        for (r,b,nm),v in S.items():
            if r==role: ss[b]+=v
        print(role,'still (no move, no damage, off spawn, not channelling) share of alive turns:',round(sum(ss.values())/tt,3),' '.join(f'{b}:{v/tt:.3f}' for b,v in ss.most_common(10)))
    sn=collections.Counter()
    for (r,b,nm),v in S.items(): sn[(nm,b)]+=v
    print('still by type/branch (per game):',' '.join(f'{nm}/{b}:{v/G:.1f}' for (nm,b),v in sn.most_common(20)))
