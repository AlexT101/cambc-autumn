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
    gt={g['id']:g['tiles'] for g in mp['groups']}
    grows=R['groups']
    hist={}
    for row in grows: hist.setdefault(row[1],[]).append((row[0],row[2]))
    def gstate(g,r):
        st=None
        for rr,s_ in hist.get(g,[]):
            if rr<=r: st=s_
            else: break
        return st
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
        nxt={}
        for k in range(len(s)-1): nxt[s[k][0]]=(s[k+1][1], s[k+1][2])
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
            if out=='other':
                nb=nxt.get(r1,('end',-1)); key='ab_next_'+(nb[0] if nb[0]!='F' else ('F_switch' if nb[1]!=fg else 'F_same'))
                res[key]+=moved
                if key=='ab_next_F_switch':
                    stt=gstate(fg,r1); res['sw_state_%s'%stt]+=moved
                    if stt==3:
                        prev=[(cr,ct,hold) for cr,ct,hold in caps.get(fg,[]) if cr<=r1]
                        if prev:
                            cr,ct,hold=prev[-1]
                            who='self' if cid in hold else ('ally' if ct==t else 'enemy')
                            res['sw_resp_by_'+who]+=moved; res['sw_resp_age_'+who]+=moved*(r1-cr)
                            res['sw_resp_start_after_cap_'+who]+=moved*(1 if r0>cr else 0)
                    # distance to the abandoned target at the switch
                    i=rix.get(r1)
                    if i is not None and c['x'][i] is not None:
                        tl=gt[fg]; dd=min(max(abs(c['x'][i]-a),abs(c['y'][i]-b)) for a,b in tl)
                        res['sw_d<=8' if dd<=8 else 'sw_d>8']+=moved
            res[out]+=moved; res[out+'_turns']+=len(rs); res['moved']+=moved
    return res
if __name__=='__main__':
    idx=json.load(open(A+'/index.json')); gs=[g for g in idx['games'] if 'mirdbg' in g['source']][:400]
    tot=Counter()
    with ProcessPoolExecutor(24) as ex:
        for c in ex.map(one,gs,chunksize=4):
            if c: tot.update(c)
    print(sorted(((k,round(100*v/tot['other'],1)) for k,v in tot.items() if (k.startswith('sw_resp_by') or k.startswith('sw_resp_start'))), key=lambda kv:-kv[1]))
    m=tot['moved']
    print('farm-segment steps by outcome of the target (within 12 rounds of segment end):')
    for k in ('ours_me','ally_helped','ally_nohelp','enemy_helped','enemy_nohelp','other'): print(k,'%.1f%% of steps'%(100*tot[k]/m), 'turns %d'%tot[k+'_turns'])
