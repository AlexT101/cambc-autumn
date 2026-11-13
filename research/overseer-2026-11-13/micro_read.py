import zipfile,glob,collections,sys
tot=collections.defaultdict(lambda:[0]*9)
for f in glob.glob(sys.argv[1]+'/*/*.repl26a'):
    side=f.split('/')[-2][-1]; m=f.split('/')[-2][:-2]
    for l in zipfile.ZipFile(f).read(f'team-{side}.stdout').decode(errors='replace').splitlines():
        if l.startswith('MICROBAD'): print('BAD', m)
        if l.startswith('MICRO2 '):
            v=l.split()
            if len(v)==10 and all(x.isdigit() for x in v[1:]):
                t=tot[m]
                for i,x in enumerate(map(int,v[1:])): t[i]+=x
for m,t in sorted(tot.items()):
    n,h,c,s,v3,hs,w,cl,wr=t
    print(f"{m:28s} n {n} hit {h/n:.2f} cast {c/n:.0f} score {s/n:.0f} v3(first) {v3/n:.0f} v3(hit) {hs/n:.0f} | own writes {w} clear {cl/max(1,w):.0f} write {wr/max(1,w):.0f}")
