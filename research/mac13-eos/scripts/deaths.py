"""Deaths: first death of the game and death context by phase. py deaths.py EXTRACT_DIR"""
import gzip,json,os,sys,collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
def g(d):
    meta=json.loads((d/'meta.json').read_text()); R=json.load(gzip.open(d/'rounds.json.gz'))
    names={int(c['id']):c['name'] for c in meta['champions']}; team={int(c['id']):int(c['team']) for c in meta['champions']}
    w=meta['result']['winner']; ch={int(c['id']):c for c in R['champions']}
    out=[]
    for l in gzip.open(d/'events.jsonl.gz','rt'):
        e=json.loads(l)
        if e['k']!='death': continue
        v=e['v']; r=e['r']; i=max(1,r-1)
        t=team[v]
        pairname={'Cassi':'Issac','Issac':'Cassi'}.get(names[v],'')
        ally=[max(abs(ch[a]['x'][i-1]-e['at'][0]),abs(ch[a]['y'][i-1]-e['at'][1])) for a in ch if a!=v and team[a]==t and ch[a]['alive'][i-1] and names[a]!=pairname]
        en=[max(abs(ch[a]['x'][i-1]-e['at'][0]),abs(ch[a]['y'][i-1]-e['at'][1])) for a in ch if team[a]!=t and ch[a]['alive'][i-1]]
        by=e.get('by'); byn=names.get(by,'camp') if by is not None else 'camp'
        out.append(dict(r=r,vic=names[v],by=byn,lost=t!=w,gems=e['gems'],na=sum(x<=8 for x in ally), ne=sum(x<=8 for x in en), near=min(ally) if ally else 99))
    return out
if __name__=='__main__':
    root=Path(sys.argv[1]); dirs=[d for d in root.iterdir() if (d/'meta.json').exists()]
    with ProcessPoolExecutor(32) as ex: res=list(ex.map(g,dirs,chunksize=8))
    first=[r[0] for r in res if r]
    print('first death victim', collections.Counter(f['vic'] for f in first).most_common(8))
    print('first death: victim team loses', round(sum(f['lost'] for f in first)/len(first),3), 'median round', sorted(f['r'] for f in first)[len(first)//2])
    print('first death killer', collections.Counter(f['by'] for f in first).most_common(6))
    print('first death (allies<=8, enemies<=8)', collections.Counter((min(f['na'],3),min(f['ne'],4)) for f in first).most_common(12))
    allD=[x for r in res for x in r]
    print('all deaths per game', len(allD)/len(res))
    for lo,hi in [(0,200),(200,400),(400,700),(700,2001)]:
        s=[x for x in allD if lo<=x['r']<hi]
        print(lo,hi,round(len(s)/len(res),2), collections.Counter(x['vic'] for x in s).most_common(5), 'outnumbered', round(sum(x['ne']>x['na']+1 for x in s)/max(1,len(s)),2), 'no ally<=8', round(sum(x['near']>8 for x in s)/max(1,len(s)),2), 'by Prism', round(sum(x['by']=='Prism' for x in s)/max(1,len(s)),2))
