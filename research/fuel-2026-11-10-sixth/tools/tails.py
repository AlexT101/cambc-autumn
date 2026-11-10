import sys, zipfile, re, glob, collections
root=sys.argv[1]; late_want=sys.argv[2] if len(sys.argv)>2 else '0'
by=collections.defaultdict(list); allv=[]
for d in glob.glob(root+'/*/'):
    z=glob.glob(d+'*.repl26a')
    if not z: continue
    side=d.rstrip('/')[-1]
    for line in zipfile.ZipFile(z[0]).read(f'team-{side}.stdout').decode(errors='replace').splitlines():
        if not line.startswith('CEN ') or ' oof1' not in line: continue
        m=re.match(r'CEN (\S+) \S+ \S+ late(\d) oof1 .*? post (\d+) dpost (\d+) .*?stack (\S+)', line)
        if not m: continue
        try:
            if int(m.group(1).strip('\x00'))<2: continue
        except: pass
        if m.group(2)!=late_want: continue
        st=m.group(5).split('/'); key='/'.join(st[-2:])
        v=int(m.group(4)); by[key].append(v); allv.append(v)
allv.sort(); n=len(allv); print('n',n,'mean',sum(allv)/n)
for q in (0.1,0.25,0.5,0.75,0.9,0.95): print(q, allv[int(q*(n-1))])
print('by total dpost')
for k,v in sorted(by.items(), key=lambda kv:-sum(kv[1]))[:30]:
    v.sort(); print(f'{k:45} n {len(v):4} sum {sum(v):8} med {v[len(v)//2]:6} max {v[-1]}')
