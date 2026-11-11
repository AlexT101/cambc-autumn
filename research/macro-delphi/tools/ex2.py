import json,gzip,glob,sys,collections,zipfile
A=sys.argv[1]; ROOT='/home/ubuntu/wt/macro-o4/'; want=int(sys.argv[2])
def cheb(a,b):
    if None in a or None in b: return 99
    return max(abs(a[0]-b[0]),abs(a[1]-b[1]))
found=0
for d in sorted(glob.glob(A+'/*/meta.json')):
    d=d[:-10]
    M=json.load(open(d+'/meta.json'))
    names={c['id']:c['name'] for c in M['champions']}; team={c['id']:c['team'] for c in M['champions']}
    R=json.load(gzip.open(d+'/rounds.json.gz')); ri={r:i for i,r in enumerate(R['round'])}
    C={c['id']:c for c in R['champions']}
    evs=[json.loads(l) for l in gzip.open(d+'/events.jsonl.gz','rt')]
    for e in evs:
        if e['k']!='death' or names.get(e.get('by'))!='Prism' or names[e['v']]!='Prism': continue
        v=e['v'];k=e['by'];r=e['r'];i=ri.get(r-4)
        if i is None or k not in C[v]['sees'][i]: continue
        found+=1
        if found!=want: continue
        src=M['sources'][0]['source']; z=zipfile.ZipFile(ROOT+src); D={}
        for t,f in ((0,'team-a.stdout'),(1,'team-b.stdout')):
            for line in z.read(f).decode(errors='replace').splitlines():
                p=line.split()
                if len(p)>=4 and p[0]=='D': D[(int(p[2]),int(p[1]))]=p[3]
        print(src, 'map',M['map'],'death r',r,'victim',v,names[v],'killer',k, 'gems',e['gems'])
        for rr in range(r-8,r+1):
            j=ri[rr]
            row=[]
            for c in sorted(C):
                cc=C[c]
                if not cc['alive'][j]: row.append('%d%s:dead'%(c,names[c][:2])); continue
                row.append('%d%s%s(%d,%d)hp%d f%d cd%s/%s %s'%(c,names[c][:2],'AB'[team[c]],cc['x'][j],cc['y'][j],cc['hp'][j],cc['foc'][j],cc['cd0'][j],cc['cd1'][j],D.get((c,rr),'.')))
            print(rr,' | '.join(row))
        for e2 in evs:
            if r-8<=e2['r']<=r and e2['k'] in ('cast','attack','death') and (e2.get('a') in (k,v,e.get('linked')) or e2.get('v')==v or e2.get('tgt') in (v,)):
                print('  ',json.dumps(e2)[:200])
        sys.exit()
