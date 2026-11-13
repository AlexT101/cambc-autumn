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
    gtiles={g['id']:g['tiles'] for g in mp['groups']}
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
                    out='ours_me' if cid in hold else (('ally_helped' if helped else 'ally_nohelp') if ct==t else ('enemy_helped' if helped else 'enemy_nohelp')); break
            for r in rs:
                i=rix.get(r)
                if i is None or c['x'][i] is None: continue
                tl=gtiles[fg]
                me=min(max(abs(c['x'][i]-a),abs(c['y'][i]-b)) for a,b in tl)
                al=[min(max(abs(v['x'][i]-a),abs(v['y'][i]-b)) for a,b in tl) for v in R['champions'] if v['team']==t and v['id']!=cid and v['alive'][i] and v['x'][i] is not None]
                if al: res[out+('_ally_nearer' if min(al)<me else '_me_nearer')]+=1
            res[out]+=moved; res[out+'_turns']+=len(rs); res['moved']+=moved
    return res
if __name__=='__main__':
    idx=json.load(open(A+'/index.json')); gs=[g for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,gs,chunksize=4):
            if c: tot.update(c)
    print({k:(tot[k+'_ally_nearer'],tot[k+'_me_nearer']) for k in ('ours_me','ally_helped','ally_nohelp','enemy_nohelp','other')})
    m=tot['moved']
    print('farm-segment steps by outcome of the target (within 12 rounds of segment end):')
    for k in ('ours_me','ally_helped','ally_nohelp','enemy_helped','enemy_nohelp','other'): print(k,'%.1f%% of steps'%(100*tot[k]/m), 'turns %d'%tot[k+'_turns'])
