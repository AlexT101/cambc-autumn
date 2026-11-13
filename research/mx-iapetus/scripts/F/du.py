# Our deaths to an enemy Prism unseen at our last turn before its first hit: our belief of it (DU trace).
# Usage: du.py BATCH RECORDS.json
import json,sys,os,zipfile,collections
B,REC=sys.argv[1],sys.argv[2]
G=json.load(open(REC)); C=collections.Counter(); W=[]
for g in G:
    side='ab'[g['ct']]
    try: out=zipfile.ZipFile(os.path.join(B,g['src'])).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except Exception: continue
    du=collections.defaultdict(dict)
    for l in out:
        p=l.split()
        if len(p)==10 and p[0]=='DU':
            try: du[(int(p[1]),int(p[2]))][int(p[3][1:])]=dict(t=int(p[4][1:]),n=int(p[5][1:]),w=float(p[6][1:]),r=int(p[7][1:]),m=float(p[8][1:]),inr=int(p[9][2:]))
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
        u=du.get((x,d['v']),{}).get(d['by'])
        if u is None: C['visible (no DU)']+=1; continue
        hp=dxs[str(x)][0]
        if not u['t']: C['untracked']+=1
        elif not u['inr']: C['tracked, possible out of reach']+=1
        else:
            k='tracked in reach, w>=0.5' if u['w']>=0.5 else 'tracked in reach, w<0.5 (dropped)'
            C[k]+=1; W.append((u['w'],u['m']/max(hp,1)))
            if u['w']<0.5: C['   dropped, w*blow/hp>=0.5' if u['w']*u['m']/max(hp,1)>=0.5 else '   dropped, w*blow/hp<0.5']+=1
for k,v in sorted(C.items()): print(k,v)
