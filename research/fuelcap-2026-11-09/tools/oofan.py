"""oofan.py GAMESDIR [--top N]: OOF turns (OOFT/OOFS): by (reset -> last mark), with the sites in the segment."""
import zipfile, glob, collections, sys
d=sys.argv[1]; top=int(sys.argv[sys.argv.index('--top')+1]) if '--top' in sys.argv else 40
P=collections.defaultdict(lambda: [0,0,collections.Counter(),'' ]); total=0
for f in glob.glob(f"{d}/**/*.repl26a", recursive=True):
    z=zipfile.ZipFile(f)
    for side in 'ab':
        try: s=z.read(f'team-{side}.stdout').decode(errors='replace').replace('\x00','')
        except KeyError: continue
        cur=None
        for line in s.splitlines():
            w=line.split()
            if len(w)==6 and w[0]=='OOFT' and w[5].isdigit():
                total+=1; cur=P[(w[2],w[3],w[4])]; cur[0]+=1
                if int(w[5])>cur[1]: cur[1]=int(w[5]); cur[3]=f.split('/')[-2]+':r'+w[1]
            elif len(w)==4 and w[0]=='OOFS' and cur is not None and w[3].isdigit(): cur[2][w[1]]+=int(w[3])
            else: cur=None if (w and w[0]!='OOFS') else cur
print('OOF turns traced', total)
for k,v in sorted(P.items(), key=lambda kv:-kv[1][0])[:top]:
    tot=sum(v[2].values()) or 1
    print(f"{v[0]:>6} left{v[1]:>7} {k[2]} {k[0]} -> {k[1]}  @{v[3]}")
    print("        "+"  ".join(f"{s}:{100*c//tot}%" for s,c in v[2].most_common(6)))
