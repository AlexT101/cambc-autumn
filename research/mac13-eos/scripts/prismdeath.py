import gzip,json,sys,collections,zipfile,statistics as st
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}; team={int(c['id']):int(c['team']) for c in meta['champions']}
    w=meta['result']['winner']; ch={int(c['id']):c for c in R['champions']}
    try: z=zipfile.ZipFile(meta['source'])
    except Exception: return []
    br={}
    for f in ('team-a.stdout','team-b.stdout'):
        for line in z.read(f).decode(errors='replace').splitlines():
            if line.startswith('D '):
                p=line.split(); br[(int(p[1]),int(p[2]))]=p[3]
    out=[]; first=True
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death' or names[e['v']]!='Prism': continue
        v=e['v']; r=e['r']; i=max(1,r-1); t=team[v]
        ally=[max(abs(ch[a]['x'][i-1]-e['at'][0]),abs(ch[a]['y'][i-1]-e['at'][1])) for a in ch if a!=v and team[a]==t and ch[a]['alive'][i-1]]
        en=[max(abs(ch[a]['x'][i-1]-e['at'][0]),abs(ch[a]['y'][i-1]-e['at'][1])) for a in ch if team[a]!=t and ch[a]['alive'][i-1]]
        hp5=ch[v]['hp'][max(0,r-6)]/max(1,ch[v]['maxHp'][max(0,r-6)])
        by=e.get('by'); byn=names.get(by,'camp') if by is not None else 'camp'
        last=[br.get((rr,v),'?') for rr in range(r-3,r+1)]
        out.append(dict(r=r,lost=t!=w,gems=e['gems'],by=byn,na=sum(x<=8 for x in ally),ne=sum(x<=8 for x in en),hp5=hp5,last=''.join(last),firstp=first))
        first=False
    return out
if __name__=='__main__':
    dirs=[d for d in Path(sys.argv[1]).iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=[x for r in ex.map(g,dirs,chunksize=8) for x in r]
    print('prism deaths',len(res),'per game',len(res)/len(dirs))
    F=[x for x in res if x['firstp']]
    print('first prism death in a game (per side):',len(F),'team lost',round(sum(x['lost'] for x in F)/len(F),3),'median round',st.median(x['r'] for x in F),'median bag',st.median(x['gems'] for x in F))
    print('killers',collections.Counter(x['by'] for x in res).most_common(6))
    print('hp 5 rounds before >=0.8:',round(sum(x['hp5']>=0.8 for x in res)/len(res),2))
    print('(allies<=8,enemies<=8)',collections.Counter((min(x['na'],3),min(x['ne'],4)) for x in res).most_common(10))
    print('last branch',collections.Counter(x['last'][-2] for x in res).most_common(8))
    print('bag at death quartiles',[sorted(x['gems'] for x in res)[int(len(res)*q)] for q in (.25,.5,.75,.9)])
