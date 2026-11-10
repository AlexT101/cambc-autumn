import sys, zipfile, re, glob, collections
root=sys.argv[1]; L=[]; lines=collections.Counter()
for d in glob.glob(root+'/*/'):
    z=glob.glob(d+'*.repl26a')
    if not z: continue
    side=d.rstrip('/')[-1]
    out=zipfile.ZipFile(z[0]).read(f'team-{side}.stdout').decode(errors='replace')
    for m in re.finditer(r'OOF (\S+) (\S+) left (\d+)', out):
        r=int(m.group(1).strip('\x00'))
        if r<2: continue
        L.append((100000-int(m.group(3)), m.group(2)))
L.sort()
n=len(L); print('n',n)
for q in (0.1,0.25,0.5,0.75,0.9,0.95,0.99): print(q, L[int(q*(n-1))][0])
print('mean', sum(x for x,_ in L)/n)
c=collections.defaultdict(list)
for x,p in L: c[p].append(x)
for p,v in sorted(c.items(), key=lambda kv:-sum(kv[1])): print(p, len(v), sum(v)//len(v), sorted(v)[len(v)//2])
