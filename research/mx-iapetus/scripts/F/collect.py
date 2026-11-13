# Death audit stage 1: one record per death (both teams) with CAND's trace around it.
# Usage: collect.py BATCH_DIR EXTRACT_DIR CAND_NAME OUT.json
import json,gzip,sys,os,zipfile,collections
from multiprocessing import Pool
B,A,cand,OUT=sys.argv[1],sys.argv[2].rstrip('/')+'/',sys.argv[3],sys.argv[4]
GAP=3
def cheb(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
def one(r):
    src=os.path.basename(r['source']); f=os.path.join(B,src)
    if not os.path.exists(f) or cand not in r['teams']: return None
    ct=r['teams'].index(cand); side='ab'[ct]
    try: out=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except KeyError: return None
    dec={}; dx={}; last_trace=0
    for l in out:
        p=l.split()
        if len(p)==6 and p[0]=='D' and p[1].isdigit():
            try: dec[(int(p[1]),int(p[2]))]=p[3]; last_trace=int(p[1])
            except ValueError: pass
        elif len(p)==9 and p[0]=='DX':
            try: dx[(int(p[1]),int(p[2]))]=(float(p[4][2:]),int(p[5][1:]),*map(float,p[6][1:].split('/')),int(p[7][1:]),int(p[8][1:]))
            except ValueError: pass
    d=r['dir']
    R=json.load(gzip.open(A+d+'/rounds.json.gz')); ri={x:i for i,x in enumerate(R['round'])}
    ch={int(c['id']):c for c in R['champions']}
    m=json.load(open(A+d+'/meta.json')); name={c['id']:c['name'] for c in m['champions']}
    hit=collections.defaultdict(list); linked=collections.defaultdict(int); dmgby=collections.defaultdict(lambda:collections.Counter())
    deaths=[]
    for e in gzip.open(A+d+'/events.jsonl.gz','rt'):
        e=json.loads(e); k=e['k']
        if k in ('attack','cast') and 'dmg' in e:
            for v,a in e['dmg']:
                if v in ch and a>0 and ch[v]['team']!=ch[e['a']]['team']: hit[v].append(e['r']); dmgby[v][(e['r'],e['a'],e.get('ab','basic'))]+=a
        elif k=='camp_attack' and e.get('tgt') in ch: hit[e['tgt']].append(e['r']); dmgby[e['tgt']][(e['r'],'camp','camp')]+=e.get('dmg',0)
        elif k=='death':
            if e.get('linked') is not None: linked[(e['r'],e['linked'])]+=e.get('gems',0)
            else: deaths.append(e)
    recs=[]
    def st(i,c):
        return None if i is None else dict(x=ch[c]['x'][i],y=ch[c]['y'][i],hp=ch[c]['hp'][i],mx=ch[c]['maxHp'][i],g=ch[c]['gems'][i],al=ch[c]['alive'][i],chan=ch[c]['chan'][i],cd=(ch[c]['cd0'][i],ch[c]['cd1'][i]),turn=ch[c]['turn'][i],sees=ch[c]['sees'][i],stun=ch[c]['stun'][i])
    for e in deaths:
        v=e['v']; rd=e['r']; vt=int(ch[v]['team'])
        gems=e.get('gems',0)+linked.get((rd,v),0)
        hs=sorted(set(x for x in hit[v] if x<=rd)); r0=rd
        for x in reversed(hs):
            if r0-x<=GAP: r0=x
            else: break
        ours = vt==ct
        rec=dict(src=src,map=r['map'],win=int(r['winner']==ct),round=rd,ours=ours,v=v,vname=name[v],gems=gems,
                 by=e.get('by'),byname=name.get(e.get('by')),camp=e.get('camp') is not None,r0=r0,
                 traced=rd<=last_trace,assists=e.get('assists',[]))
        me=v if ours else e.get('by')
        if me is not None and me in ch and int(ch[me]['team'])==ct:
            rec['seq']={x:dec.get((x,me),'.') for x in range(rd-15,rd+1)}
            rec['dx']={x:dx.get((x,me)) for x in range(rd-15,rd+1) if (x,me) in dx}
        # state of every champion at r0-1 and rd-1 (end of round)
        rec['s0']={c:st(ri.get(r0-1),c) for c in ch}
        rec['s1']={c:st(ri.get(rd-1),c) for c in ch}
        rec['team']={c:int(ch[c]['team']) for c in ch}; rec['names']={c:name[c] for c in ch}
        rec['dmg']=[(rr,a,ab,am) for (rr,a,ab),am in sorted(dmgby[v].items(),key=lambda kv:(kv[0][0],str(kv[0][1]))) if rr>=r0-2]
        kb=e.get('by')
        W=[]
        for x in range(rd-15,rd+1):
            i=ri.get(x)
            if i is None or not ch[v]['alive'][i] or ch[v]['x'][i] is None: continue
            pv=(ch[v]['x'][i],ch[v]['y'][i])
            dk=None
            if kb in ch and ch[kb]['alive'][i] and ch[kb]['x'][i] is not None: dk=cheb(pv,(ch[kb]['x'][i],ch[kb]['y'][i]))
            en=[cheb(pv,(ch[o]['x'][i],ch[o]['y'][i])) for o in ch if int(ch[o]['team'])!=vt and ch[o]['alive'][i] and ch[o]['x'][i] is not None]
            W.append((x,int(kb in (ch[v]['sees'][i] or [])),dk,len(ch[v]['sees'][i] or []),round(ch[v]['hp'][i]),min(en) if en else None,pv))
        rec['win']=W
        recs.append(rec)
    return dict(src=src,win=int(r['winner']==ct),rounds=r['rounds'],deaths=recs,ct=ct)
if __name__=='__main__':
    idx=json.load(open(A+'index.json'))['games']
    with Pool(8) as p: res=[x for x in p.map(one,idx,chunksize=8) if x]
    json.dump(res,open(OUT,'w'))
    print(len(res),'games',sum(len(g['deaths']) for g in res),'deaths')
