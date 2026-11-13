# Prism duels by initiative: each Prism-to-Prism unit cast (tgt = the other Prism) that opens an engagement (no such
# cast between them in the 30 rounds before); who died within 30 rounds; split by the opener's Focus ratio.
import json,gzip,sys,os,collections,re,zipfile
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
def one(item):
    dn,row=item; d=os.path.join(ROOT,dn)
    try:
        meta=json.load(open(d+'/meta.json')); ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
        z=zipfile.ZipFile(os.path.join('/home/ubuntu/wt/mx-theia',row['source'])); D={}
        for fn in ('team-a.stdout','team-b.stdout'):
            for m in D_RE.finditer(z.read(fn)): D[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    except Exception: return []
    names={c['id']:c['name'] for c in meta['champions']}; P=[i for i,n in names.items() if n=='Prism']
    if len(P)!=2: return []
    CH={c['id']:c for c in R['champions']}; rd={r:i for i,r in enumerate(R['round'])}
    deaths=[(e['r'],e['v']) for e in ev if e['k']=='death' and e['v'] in P]
    out=[]; last=-999
    for e in ev:
        if e['k']=='cast' and e['a'] in P and e.get('tgt') in P and e['tgt']!=e['a']:
            if e['r']-last>30:
                a,b=e['a'],e['tgt']; t=rd.get(e['r']-1)
                if t is None: continue
                fa,fb=CH[a]['foc'][t],CH[b]['foc'][t]
                da=any(e['r']<=r<=e['r']+30 and v==a for r,v in deaths); db=any(e['r']<=r<=e['r']+30 and v==b for r,v in deaths)
                out.append(dict(br=D.get((e['r'],a),'?'),tch=CH[b]['chan'][t],r=e['r'],ratio=fa/max(1,fb),opener_died=da,target_died=db,hpa=CH[a]['hp'][t]/CH[a]['maxHp'][t],hpb=CH[b]['hp'][t]/CH[b]['maxHp'][t]))
            last=e['r']
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); rws={}
    for g in idx['games']: rws.setdefault(g['dir'],g)
    dirs=list(rws.items())
    with ProcessPoolExecutor(32) as ex: rows=[x for l in ex.map(one,dirs,chunksize=8) for x in l]
    print('engagement openers',len(rows))
    b=collections.defaultdict(collections.Counter)
    for r in rows:
        k='<0.8' if r['ratio']<0.8 else '0.8-1.25' if r['ratio']<=1.25 else '>1.25'
        b[k]['n']+=1; b[k]['opener_died']+=r['opener_died']; b[k]['target_died']+=r['target_died']
    for k in ('<0.8','0.8-1.25','>1.25'):
        c=b[k]; print('opener focus ratio %-9s n %5d opener died %.2f target died %.2f'%(k,c['n'],c['opener_died']/c['n'],c['target_died']/c['n']))
    weak=[r for r in rows if r['ratio']<0.8]
    print('weak openers: branch',collections.Counter(r['br'] for r in weak).most_common(8),'round<400',sum(r['r']<400 for r in weak),'target channelling',collections.Counter(r['tch'] for r in weak).most_common(4))
    for br,c in collections.Counter(r['br'] for r in weak).most_common(6):
        s=[r for r in weak if r['br']==br]; print('  ',br,len(s),'opener died %.2f'%(sum(r['opener_died'] for r in s)/len(s)),'median round',sorted(r['r'] for r in s)[len(s)//2])
    early=[r for r in rows if r['r']<400 and 0.8<=r['ratio']<=1.25]
    print('parity openers before r400: n %d opener died %.2f target died %.2f'%(len(early),sum(r['opener_died'] for r in early)/max(1,len(early)),sum(r['target_died'] for r in early)/max(1,len(early))))
if __name__=='__main__': pass
