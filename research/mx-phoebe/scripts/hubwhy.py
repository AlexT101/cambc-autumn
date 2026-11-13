# For each hub capture, the Prism's 'G'-loop verdicts (PG lines: B bound, T takeover/carries refused, E enemy seen, W walk, V/N value, P/L picked) in the hold before payout.
# usage: hubwhy.py EXTRACT_DIR
import gzip, json, sys, re, zipfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
HUB = re.compile(rb'HUB (\d+) (\d+) g(\d+) at (\d+) (\d+) mode')
PG = re.compile(rb'PG (\d+) g(\d+) (\S)')
def one(d):
    d=Path(d)
    try:
        meta=json.loads((d/'meta.json').read_text()); mp=json.loads((d/meta['mapFile']).resolve().read_text())
        ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]; z=zipfile.ZipFile(meta['source'])
    except Exception: return None
    typ={c['id']:c['name'] for c in meta['champions']}; team={c['id']:c['team'] for c in meta['champions']}
    by_tile={tuple(t):g['id'] for g in mp['groups'] for t in g['tiles']}
    caps=[e for e in ev if e['k']=='capture']; out=Counter()
    for side,name in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        if meta['teams'][side]['name']!='phb-hub': continue
        pr=[c for c in typ if typ[c]=='Prism' and team[c]==side]
        if not pr: continue
        p=pr[0]; txt=z.read(name)
        pgs={}
        for m in PG.finditer(txt): pgs.setdefault(int(m[2]),[]).append((int(m[1]),m[3].decode()))
        seen=set()
        for m in HUB.finditer(txt):
            r=int(m[1]); bg=int(m[3]); gid=by_tile.get((int(m[4]),int(m[5])))
            cap=next((e for e in caps if e['g']==gid and r<=e['r']<=r+80 and e['team']==side),None)
            if not cap or (gid,cap['r']) in seen: continue
            seen.add((gid,cap['r']))
            gems=sum(x[1] for x in cap['shares']); pg=sum(x[1] for x in cap['shares'] if x[0]==p)
            k='K' if pg*2>=gems else 'B'
            codes=[c for rr,c in pgs.get(bg,[]) if cap['r']-7<=rr<cap['r']]
            out[(k,''.join(sorted(set(codes))) or 'none')]+=1
    return out
if __name__=='__main__':
    dirs=[str(p.parent) for p in Path(sys.argv[1]).glob('*/meta.json')]
    tot=Counter()
    with ProcessPoolExecutor(16) as ex:
        for r in ex.map(one,dirs,chunksize=8):
            if r: tot.update(r)
    for k in 'KB':
        items=sorted(((v,c) for (kk,c),v in tot.items() if kk==k),reverse=True)[:12]
        print(k, sum(v for v,c in items), items)
