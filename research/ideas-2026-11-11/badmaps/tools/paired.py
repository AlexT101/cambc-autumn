#!/usr/bin/env python3
"""paired.py TAG CAND BASE : CAND and BASE each played the same bodies on the same maps; paired by (map, side)."""
import json,glob,sys,math,os,collections
ROOT='/home/ubuntu/cambc-autumn'
def load(tag,bot,body):
    s=json.load(open(f'{ROOT}/replays/ab/bm11-{tag}-{bot}-{bot}-{body}/summary.json'))
    bs=glob.glob(f'{ROOT}/replays/batch-*-ab-bm11-{tag}-{bot}-{bot}-{body}-*')
    out={}
    for b in bs:
        r=json.load(open(b+'/results.json'))
        for m in r['matches']:
            if m.get('winner') is None: continue
            out[(os.path.basename(m['map']),tuple(m['order']))]=(int(m['winner']==0),m.get('oof_turns',[0,0])[0 if m['order'][0]==0 else 1],m['rounds'])
    return out
def wilson(w,n,z=1.96):
    if n==0: return (0,0)
    p=w/n; d=1+z*z/n; c=p+z*z/(2*n); h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return ((c-h)/d,(c+h)/d)
def report(tag,cand,base,subset=None,label='all fresh'):
    rows=[]
    tot=[0,0,0,0]  # n, cand wins, base wins, sum sq of per-map diff
    perbody={}
    unit=collections.defaultdict(lambda:[0,0,0])
    for body in ('Flp4','Mt3q'):
        try: c=load(tag,cand,body); b=load(tag,base,body)
        except FileNotFoundError as e: print('missing',e); continue
        keys=[k for k in c if k in b and (subset is None or k[0] in subset)]
        cw=sum(c[k][0] for k in keys); bw=sum(b[k][0] for k in keys); n=len(keys)
        for k in keys:
            u=unit[(body,k[0])]; u[0]+=c[k][0]-b[k][0]; u[1]+=1
        perbody[body]=(n,cw,bw,sum(1 for k in keys if c[k][0]!=b[k][0]))
    alln=sum(v[0] for v in perbody.values()); allc=sum(v[1] for v in perbody.values()); allb=sum(v[2] for v in perbody.values())
    def diffci(sel):
        ds=[u[0]/u[1] for (bd,m),u in unit.items() if sel(bd)]
        n=len(ds)
        if n<2: return (0,0,0)
        mu=sum(ds)/n; var=sum((d-mu)**2 for d in ds)/(n-1)
        return (100*mu,100*1.96*math.sqrt(var/n),n)
    out=[]
    for name,sel,(n,cw,bw) in (('both',lambda bd:True,(alln,allc,allb)),('Fish body',lambda bd:bd=='Flp4',perbody.get('Flp4',(0,0,0))[:3]),('Mite body',lambda bd:bd=='Mt3q',perbody.get('Mt3q',(0,0,0))[:3])):
        if n==0: continue
        lo,hi=wilson(cw,n); d,ci,nu=diffci(sel)
        out.append(f"| {cand} | {label} | {name} | {100*cw/n:.2f}% ({100*lo:.1f}-{100*hi:.1f}) of {n} | {100*bw/n:.2f}% | {d:+.2f} ±{ci:.2f} ({nu} maps) |")
    flips=sum(v[3] for v in perbody.values())
    return out,flips,alln
if __name__=='__main__':
    tag,cand,base=sys.argv[1:4]
    subset=None;label='all fresh'
    if len(sys.argv)>4:
        subset=set(l.strip() for l in open(sys.argv[4])); label=sys.argv[5] if len(sys.argv)>5 else 'subset'
    out,flips,n=report(tag,cand,base,subset,label)
    print('| cand | maps | body | cand win% (95% CI) of n | base win% | paired diff, pts (95% CI over maps) |'); print('|---|---|---|---|---|---|')
    print('\n'.join(out)); print(f'flipped games: {flips} of {n} ({100*flips/max(1,n):.1f}%)')
