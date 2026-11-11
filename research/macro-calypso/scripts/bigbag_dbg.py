import gzip, json, sys, collections, zipfile
from pathlib import Path
an=Path(sys.argv[1]); batch=Path(sys.argv[2])
idx=json.load(open(an/'index.json'))
cnt=collections.Counter(); ex=[]
for row in idx['games']:
    d=an/row['dir']; src=Path(row['source'])
    ev=[json.loads(l) for l in gzip.open(d/'events.jsonl.gz','rt')]
    R=json.load(gzip.open(d/'rounds.json.gz')); ch=R['champions']; team={c['id']:c['team'] for c in ch}
    deaths=[e for e in ev if e['k']=='death' and e.get('gems',0)>=200 and 'linked' not in e]
    if not deaths: continue
    z=zipfile.ZipFile(batch/src.name)
    lines={}
    for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
        for l in z.read(f).decode(errors='replace').splitlines():
            p=l.split()
            if len(p)>=4 and p[0]=='D': lines.setdefault((int(p[2])),[]).append((int(p[1]),p[3]))
    for e in deaths:
        v=e['v']; L=[x for x in lines.get(v,[]) if e['r']-8<=x[0]<=e['r']]
        seq=''.join(b for r,b in L)
        cnt[seq[-3:] if seq else '?']+=1
        ex.append((row['dir'][:8],e['r'],e['gems'],seq))
print(cnt.most_common(20))
for x in ex[:25]: print(x)
