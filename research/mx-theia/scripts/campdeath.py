# Prism deaths to camps: bag, round, D branches over the 8 rounds before, health 8 rounds before, an enemy within 8.
import json,gzip,collections,sys,os,re,zipfile
ROOT=sys.argv[1]
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
idx=json.load(open(ROOT+'/index.json')); rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
br=collections.Counter(); n=0; enemy=0; hp8=[]; bags=[]
for dn,row in rows.items():
    d=os.path.join(ROOT,dn); meta=json.load(open(d+'/meta.json')); names={x['id']:x['name'] for x in meta['champions']}
    ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    cd=[e for e in ev if e['k']=='death' and names.get(e['v'])=='Prism' and e.get('by') is None]
    if not cd: continue
    R=json.load(gzip.open(d+'/rounds.json.gz')); rd={r:i for i,r in enumerate(R['round'])}; CH={c['id']:c for c in R['champions']}
    z=zipfile.ZipFile(os.path.join('/home/ubuntu/wt/mx-theia',row['source'])); D={}
    for fn in ('team-a.stdout','team-b.stdout'):
        for m in D_RE.finditer(z.read(fn)): D[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    for e in cd:
        n+=1; v=CH[e['v']]; i=rd.get(e['r']-1)
        if i is None: continue
        bags.append(e.get('gems',0))
        j=max(0,i-8); hp8.append(v['hp'][j]/v['maxHp'][j])
        p=(v['x'][i],v['y'][i])
        enemy+=any(c['team']!=v['team'] and c['alive'][i] and cheb((c['x'][i],c['y'][i]),p)<=8 for c in R['champions'])
        for r in range(e['r']-8,e['r']+1): br[D.get((r,e['v']),'?')]+=1
print('Prism camp deaths',n,'mean bag %.0f'%(sum(bags)/len(bags)),'enemy within 8 at r-1: %.2f'%(enemy/n))
print('hp fraction 8 rounds before: buckets',sorted(collections.Counter(round(h,1) for h in hp8).items()))
print('branches over the 8 rounds before',br.most_common(10))
