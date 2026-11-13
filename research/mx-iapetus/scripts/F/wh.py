# Why our bodies were retreating before deaths: want_home's reason (WH trace) at the first R turn of the run
# that led into the fatal exchange, by killer kind. Also every R-run start in the games, for the base rate.
# Usage: wh.py BATCH RECORDS.json
import json,sys,os,zipfile,collections
B,REC=sys.argv[1],sys.argv[2]
G=json.load(open(REC)); C=collections.Counter(); ALL=collections.Counter(); n=0
for g in G:
    side='ab'[g['ct']]
    try: out=zipfile.ZipFile(os.path.join(B,g['src'])).read(f'team-{side}.stdout').decode(errors='replace').splitlines()
    except Exception: continue
    n+=1; wh={}; dec={}
    for l in out:
        p=l.split()
        if len(p)==5 and p[0]=='WH': wh.setdefault((int(p[1]),int(p[2])),p[3])
        elif len(p)==6 and p[0]=='D' and p[1].isdigit(): dec[(int(p[1]),int(p[2]))]=p[3]
    for (r,h),c in dec.items():
        if c=='R' and dec.get((r-1,h))!='R': ALL[wh.get((r,h),'none')]+=1
    for d in g['deaths']:
        if not d['ours'] or d['camp']: continue
        s=d.get('seq') or {}
        x=next((x for x in range(d['r0']-1,d['r0']-6,-1) if s.get(str(x),'.')!='.'),None)
        if x is None or s.get(str(x))!='R': continue
        y=x
        while s.get(str(y-1))=='R': y-=1
        k='Prism' if d['byname']=='Prism' else 'other'
        C[(k,wh.get((y,d['v']),'none'))]+=1
print('games',n)
for k,v in sorted(C.items()): print(k,round(v/n,3))
print('all R-run starts by reason (per game):',{k:round(v/n,2) for k,v in ALL.most_common()})
