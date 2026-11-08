# Fight-free openings (no champion kill before T): captured gems by T, ours vs theirs; opening steals of 10+ gem
# groups on the other half; first kill and net kills by T against win rate.
import pickle,os,collections,numpy as np
B=os.path.expanduser('~/tmp-offload/bigl/')
F=pickle.load(open(B+'feats.pkl','rb')); D=[d for d in pickle.load(open(B+'deaths.pkl','rb')) if not d['linked'] and d['killer']!='camp']
C=pickle.load(open(B+'clears.pkl','rb')); Fd={r['dir']:r for r in F if not r['dup']}
fk=collections.defaultdict(lambda:9999); by=collections.defaultdict(list)
for d in D: fk[d['dir']]=min(fk[d['dir']],d['r']); by[d['dir']].append(d)
for T in (200,300):
    rs=[r for r in Fd.values() if fk[r['dir']]>T]; dd=np.array([r['capr'][0][:T+1].sum()-r['capr'][1][:T+1].sum() for r in rs])
    print(f'fight-free to r{T}: {len(rs)} games, capture diff {dd.mean():+.1f} (CI ±{1.96*dd.std()/np.sqrt(len(rs)):.1f})')
for T in (80,150):
    g=collections.defaultdict(lambda:[0,0])
    for c in C:
        if c['r1']<T and c['gems']>=10 and c['clearer'] not in ('slept',None):
            if c['side']==c['us'] and c['clearer']!=c['us']: g[c['dir']][0]+=1
            if c['side']==1-c['us'] and c['clearer']==c['us']: g[c['dir']][1]+=1
    print(f'by r{T}: they take an our-half group in {np.mean([g[d][0]>0 for d in Fd]):.3f} of games, we take theirs in {np.mean([g[d][1]>0 for d in Fd]):.3f}')
c=collections.defaultdict(list)
for r in F:
    ds=sorted(by.get(r['dir'],[]),key=lambda d:d['r']); c['none' if not ds else ('we first' if not ds[0]['ours'] else 'they first')].append(r['win'])
print({k:(round(100*np.mean(v)),len(v)) for k,v in c.items()})
for T in (150,250,400):
    c=collections.defaultdict(list)
    for r in F:
        ds=by.get(r['dir'],[]); net=sum(1 for d in ds if d['r']<T and not d['ours'])-sum(1 for d in ds if d['r']<T and d['ours']); c[max(-3,min(3,net))].append(r['win'])
    print(f'net kills by r{T}:',' '.join(f'{k:+d}: {100*np.mean(v):.0f}% ({len(v)})' for k,v in sorted(c.items())))
