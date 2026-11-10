import zipfile,re,glob,collections,sys
cost=collections.defaultdict(list); oofent=collections.defaultdict(list)
for d in glob.glob(sys.argv[1]+'/*/'):
    z=glob.glob(d+'*.repl26a')
    if not z: continue
    side=d.rstrip('/')[-1]
    open_={}
    for line in zipfile.ZipFile(z[0]).read(f'team-{side}.stdout').decode(errors='replace').replace('\x00','').splitlines():
        if line.startswith('ENT '):
            p=line.split(); 
            if len(p)==4: open_[p[2]]=int(p[3])
        elif line.startswith('EXT '):
            p=line.split()
            if len(p)==5 and p[2] in open_:
                e=open_.pop(p[2])
                if p[4]=='0' and e>=int(p[3]): cost[p[2]].append(e-int(p[3]))
                elif p[4]=='1': oofent[p[2]].append(e)
        elif line.startswith('OOF '):
            for k,e in open_.items(): oofent[k].append(e)
            open_={}
        elif line.startswith('CEN '): open_={}
print(len(cost), len(oofent))
for k in sorted(oofent, key=lambda k:-len(oofent[k])):
    c=sorted(cost[k]); 
    if not c: continue
    p5=c[len(c)//20]; p25=c[len(c)//4]; med=c[len(c)//2]
    o=oofent[k]
    print(f'{k:15} oof-open {len(o):4}  cost p5 {p5:6} p25 {p25:6} med {med:6} | oof entered below p5 {sum(x<p5 for x in o):4} below p25 {sum(x<p25 for x in o):4}')
