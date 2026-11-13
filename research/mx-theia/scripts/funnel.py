# Ally captures (non-Prism, gems, Prism alive) within 12 of the Prism that the Prism did not share: what the Prism's
# D branch was at the capture round and at hold start, whether an enemy was within 8 of the capturer.
import json,gzip,collections,sys,os,re,zipfile
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
en=json.load(open(ROOT+'/enums.json'))['champions']
idx=json.load(open(ROOT+'/index.json'))
rows={}
for g in idx['games']: rows.setdefault(g['dir'],g)
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
def one(item):
    dname,row=item; d=os.path.join(ROOT,dname)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile'])))
        ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]; R=json.load(gzip.open(d+'/rounds.json.gz'))
        src=os.path.join('/home/ubuntu/wt/mx-theia',row['source'])
        z=zipfile.ZipFile(src)
        D={}
        for fn in ('team-a.stdout','team-b.stdout'):
            for m in D_RE.finditer(z.read(fn)):
                D[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    except Exception as ex: return None
    typ={c['id']:en[c['type']] for c in meta['champions']}; team_of={c['id']:c['team'] for c in meta['champions']}
    CH={c['id']:c for c in R['champions']}
    prism={t:[c for c in CH if typ[c]=='Prism' and team_of[c]==t] for t in (0,1)}
    groups={g['id']:g for g in mp['groups']}
    out=collections.Counter()
    hold_start={}
    for e in ev:
        if e['k']=='capture_hold': hold_start[(e['g'],e['team'])]=e['r']
        if e['k']!='capture' or e['team'] not in (0,1) or e['r']>600: continue
        t=e['team']
        if not prism[t]: continue
        pid=prism[t][0]; p=CH[pid]; i=max(0,e['r']-1)
        if any(s[0]==pid for s in e['shares']) or not p['alive'][i] or p['x'][i] is None: continue
        G=groups.get(e['g'])
        if not G or 'Monolith' in G['types'] or G['gems']==0: continue
        dd=min(max(abs(p['x'][i]-x),abs(p['y'][i]-y)) for x,y in G['tiles'])
        if dd>12: continue
        gems=sum(s[1] for s in e['shares'])
        hs=hold_start.get((e['g'],t),e['r']-6)
        br=D.get((hs,pid),'?')
        cap=e['shares'][0][0]; c=CH[cap]; j=max(0,hs-1)
        enemy=any(CH[x]['team']!=t and CH[x]['alive'][j] and CH[x]['x'][j] is not None and c['x'][j] is not None and max(abs(CH[x]['x'][j]-c['x'][j]),abs(CH[x]['y'][j]-c['y'][j]))<=8 for x in CH)
        out[('n',)]+=1; out[('gems',)]+=gems
        out[('prism_branch',br)]+=gems
        out[('enemy8',enemy)]+=gems
        out[('captype',typ[cap])]+=gems
        out[('near6',dd<=6)]+=gems
    return out
if __name__=='__main__':
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,list(rows.items()),chunksize=4) if r]
    T=collections.Counter()
    for r in res: T.update(r)
    n=len(res); print('games',n,'captures/game %.1f gems/game %.1f'%(T[('n',)]/n,T[('gems',)]/n))
    for k in ('prism_branch','enemy8','captype','near6'):
        print(k,{kk[1]:round(v/n,1) for kk,v in sorted(T.items(),key=lambda x:-x[1]) if kk[0]==k})
