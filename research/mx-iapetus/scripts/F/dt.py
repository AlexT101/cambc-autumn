# For our deaths to an enemy Prism: the DT trace line (our read of that Prism) at our last turn before its first hit.
# Usage: dt.py BATCH RECORDS.json
import json,sys,os,zipfile,collections
B,REC=sys.argv[1],sys.argv[2]
G=json.load(open(REC)); C=collections.Counter(); ex=[]
for g in G:
    side='ab'[g['ct']]
    try: out=zipfile.ZipFile(os.path.join(B,g['src'])).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except Exception: continue
    dt=collections.defaultdict(dict)
    for l in out:
        p=l.split()
        if len(p)==11 and p[0]=='DT':
            try: dt[(int(p[1]),int(p[2]))][int(p[3][1:])]=dict(d=int(p[4][1:]),a=int(p[5][1:]),tb=int(p[6][2:]),nr=int(p[7][2:]),rs=int(p[8][2:]),bl=float(p[9][2:]),sn=int(p[10][2:]))
            except ValueError: pass
    for d in g['deaths']:
        if not d['ours'] or d['camp'] or d['byname']!='Prism': continue
        s=d.get('seq') or {}; dxs=d.get('dx') or {}
        per=collections.Counter()
        for rr,a,ab,am in d['dmg']:
            if str(a)==str(d['by']): per[rr]+=am
        if not per: continue
        rk=min(per); x=next((x for x in range(rk-1,rk-4,-1) if str(x) in dxs),None)
        if x is None or s.get(str(x))=='E': continue
        zero=dxs[str(x)][3]==0
        t=dt.get((x,d['v']),{}).get(d['by'])
        if t is None: C[('zero' if zero else 'read','prism not in DT (unseen or >7)')]+=1; continue
        C[('zero' if zero else 'read','d%d a%d tb%d nr%d rs%d'%(t['d'],t['a'],t['tb'],t['nr'],t['rs']))]+=1
        if zero: ex.append((g['src'],x,d['v'],d['by'],t,per[rk]))
for k,v in sorted(C.items(),key=lambda kv:-kv[1])[:40]: print(k,v)
for e in ex[:10]: print(e)
