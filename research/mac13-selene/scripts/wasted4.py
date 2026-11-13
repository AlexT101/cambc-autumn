import zipfile, re, sys, os, json, gzip
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
D=re.compile(rb'^[\s\0]*D (\d+) (\d+) (\S) (-?\d+) (-?\d+)\s*$', re.M)
A='replays/.analysis'
def one(g):
    try:
        d=os.path.join(A,g['dir']); R=json.load(gzip.open(os.path.join(d,'rounds.json.gz')))
        ev=[json.loads(l) for l in gzip.open(os.path.join(d,'events.jsonl.gz'),'rt')]
        z=zipfile.ZipFile(g['source'])
    except Exception: return None
    rix={r:i for i,r in enumerate(R['round'])}; C={c['id']:c for c in R['champions']}
    caps={}
    mp=json.load(open(os.path.join(d,json.load(open(os.path.join(d,'meta.json')))['mapFile'])))
    cg={c['id']:c['group'] for c in mp['camps']}
    hits={}
    for e in ev:
        if e['k'] in ('attack','cast') and e.get('cdmg'):
            for cc,a in e['cdmg']:
                if cc in cg: hits.setdefault((e['a'],cg[cc]),[]).append(e['r'])
    for e in ev:
        if e['k']=='capture': caps.setdefault(e['g'],[]).append((e['r'],e['team'],[s[0] for s in e['shares']]))
    eclr={}
    for e in ev:
        if e['k']=='group_clear' and e.get('by') in C: eclr.setdefault(e['g'],[]).append((e['r'],C[e['by']]['team']))
        if e['k']=='capture_hold': eclr.setdefault(e['g'],[]).append((e['r'],e['team']))
    mpg={g['id']:g for g in mp['groups']}
    seq={}
    for nm in z.namelist():
        if nm.endswith('.stdout'):
            for m in D.finditer(z.read(nm)):
                seq.setdefault(int(m.group(2)),[]).append((int(m.group(1)),m.group(3).decode(),int(m.group(4))))
    res=Counter()
    for cid,s in seq.items():
        if cid not in C: continue
        c=C[cid]; t=c['team']
        # segments of F turns with same fg
        segs=[]; cur=None
        for r,b,fg in s:
            if b!='F' or fg<0: continue
            if cur and cur[0]==fg and r-cur[2]<=40: cur[2]=r; cur[3].append(r)
            else: cur=[fg,r,r,[r]]; segs.append(cur)
        for fg,r0,r1,rs in segs:
            moved=0
            for r in rs:
                i=rix.get(r)
                if i and i>0 and c['x'][i] is not None and c['x'][i-1] is not None and (c['x'][i],c['y'][i])!=(c['x'][i-1],c['y'][i-1]): moved+=1
            out='other'
            for cr,ct,hold in caps.get(fg,[]):
                if r0<=cr<=r1+30:
                    helped=any(r0<=hr<=cr for hr in hits.get((cid,fg),[]))
                    if ct!=t and not helped:
                        st=[x for x,tt in eclr.get(fg,[]) if tt==ct and x<=cr]
                        s0=max(st) if st else cr
                        s0=min(st[-1:] or [cr]) if False else s0
                        # first enemy clear/hold in the run up to this capture
                        st2=[x for x,tt in eclr.get(fg,[]) if tt==ct and cr-12<=x<=cr]
                        s0=min(st2) if st2 else cr
                        late=0; far=[]
                        for r in rs:
                            i=rix.get(r)
                            if i is None or c['x'][i] is None: continue
                            gx=sum(tt[0] for tt in mpg[fg]['tiles'])/len(mpg[fg]['tiles']); gy=sum(tt[1] for tt in mpg[fg]['tiles'])/len(mpg[fg]['tiles'])
                            dd=max(abs(c['x'][i]-gx),abs(c['y'][i]-gy))
                            if r>=s0:
                                late+=1; far.append(dd)
                        res['en_turns_after_enemy_clear']+=late; res['en_turns_total']+=len(rs)
                        for dd in far: res['en_after_d<=8' if dd<=8 else 'en_after_d>8']+=1
                    out='ours_me' if cid in hold else (('ally_helped' if helped else 'ally_nohelp') if ct==t else ('enemy_helped' if helped else 'enemy_nohelp')); break
            res[out]+=moved; res[out+'_turns']+=len(rs); res['moved']+=moved
    return res
if __name__=='__main__':
    idx=json.load(open(A+'/index.json')); gs=[g for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,gs,chunksize=4):
            if c: tot.update(c)
    print({k:v for k,v in tot.items() if k.startswith('en_')})
    m=tot['moved']
    print('farm-segment steps by outcome of the target (within 12 rounds of segment end):')
    for k in ('ours_me','ally_helped','ally_nohelp','enemy_helped','enemy_nohelp','other'): print(k,'%.1f%% of steps'%(100*tot[k]/m), 'turns %d'%tot[k+'_turns'])
