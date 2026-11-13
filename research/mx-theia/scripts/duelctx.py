# First Prism death of a game by the enemy Prism: the D branches of victim and killer from 10 rounds before
# contact (first round within 8) to death; who closed the gap; whether the victim saw the killer at contact.
import json,gzip,collections,sys,os,re,zipfile
from concurrent.futures import ProcessPoolExecutor
ROOT=sys.argv[1]
D_RE=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$',re.M)
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(item):
    dname,row=item; d=os.path.join(ROOT,dname)
    try:
        meta=json.load(open(d+'/meta.json')); mp=json.load(open(os.path.join(d,meta['mapFile']))); bush={tuple(b) for b in mp['bushes']}; ev=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
        R=json.load(gzip.open(d+'/rounds.json.gz')); z=zipfile.ZipFile(os.path.join('/home/ubuntu/wt/mx-theia',row['source']))
        D={}
        for fn in ('team-a.stdout','team-b.stdout'):
            for m in D_RE.finditer(z.read(fn)): D[(int(m.group(1)),int(m.group(2)))]=m.group(3).decode()
    except Exception: return None
    names={c['id']:c['name'] for c in meta['champions']}; CH={c['id']:c for c in R['champions']}; rd={r:i for i,r in enumerate(R['round'])}
    e=next((e for e in ev if e['k']=='death' and names.get(e['v'])=='Prism'),None)
    if not e or names.get(e.get('by'))!='Prism': return None
    v,k=CH[e['v']],CH[e['by']]; i=rd.get(e['r']-1)
    if i is None: return None
    j=i
    while j>0 and v['alive'][j-1] and k['alive'][j-1] and cheb((v['x'][j-1],v['y'][j-1]),(k['x'][j-1],k['y'][j-1]))<=8: j-=1
    pk=(k['x'][j],k['y'][j]); pv=(v['x'][j],v['y'][j])
    base=sum(1 for t in range(len(R['round'])) if k['alive'][t] and (k['x'][t],k['y'][t]) in bush)/max(1,sum(k['alive']))
    out=dict(kbush=pk in bush,vbush=pv in bush,base=base,r=e['r'],vb=[],kb=[],vclose=0,kclose=0,saw=k['id'] in (v['sees'][j] or []),foc=(k['foc'][j],v['foc'][j]))
    for t in range(max(1,j-10),i+1):
        if not (v['alive'][t] and k['alive'][t] and v['alive'][t-1] and k['alive'][t-1]): continue
        d0=cheb((v['x'][t-1],v['y'][t-1]),(k['x'][t-1],k['y'][t-1]))
        dv=cheb((v['x'][t],v['y'][t]),(k['x'][t-1],k['y'][t-1]))-d0  # victim's move alone
        dk=cheb((v['x'][t-1],v['y'][t-1]),(k['x'][t],k['y'][t]))-d0
        out['vclose']+=-dv; out['kclose']+=-dk
        rr=R['round'][t]
        out['vb'].append(('pre' if t<j else 'in',D.get((rr,v['id']),'?'))); out['kb'].append(('pre' if t<j else 'in',D.get((rr,k['id']),'?')))
    return out
if __name__=='__main__':
    idx=json.load(open(ROOT+'/index.json')); rows={}
    for g in idx['games']: rows.setdefault(g['dir'],g)
    with ProcessPoolExecutor(48) as ex: res=[r for r in ex.map(one,list(rows.items()),chunksize=4) if r]
    print('first prism deaths by prism',len(res))
    print('victim saw killer at contact',sum(r['saw'] for r in res))
    print('at contact: killer in a bush %.2f, victim in a bush %.2f; killer Prism bush share of its alive rounds %.2f'%(sum(r['kbush'] for r in res)/len(res),sum(r['vbush'] for r in res)/len(res),sum(r['base'] for r in res)/len(res)))
    print('gap closed by victim moves %.1f, by killer moves %.1f (mean per case, 10 rounds pre-contact to death)'%(sum(r['vclose'] for r in res)/len(res),sum(r['kclose'] for r in res)/len(res)))
    for who in ('vb','kb'):
        for ph in ('pre','in'):
            c=collections.Counter(b for r in res for p,b in r[who] if p==ph); n=sum(c.values())
            print(who,ph,{b:round(x/n,3) for b,x in c.most_common(10)})
    lead=[r for r in res if r['foc'][0]>=1.25*r['foc'][1]]
    print('killer focus >=1.25x victim at contact',len(lead))
    c=collections.Counter(b for r in lead for p,b in r['vb'] if p=='pre'); n=sum(c.values()); print(' victim pre branches',{b:round(x/n,3) for b,x in c.most_common(10)})
    print(' gap closed by victim %.1f killer %.1f'%(sum(r['vclose'] for r in lead)/len(lead),sum(r['kclose'] for r in lead)/len(lead)))
