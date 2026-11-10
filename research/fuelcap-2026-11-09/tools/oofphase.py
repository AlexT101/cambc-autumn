import zipfile,glob,sys,collections
c=collections.Counter(); cb=collections.Counter(); tot=0
for f in glob.glob(sys.argv[1]+'/*/*.repl26a'):
    z=zipfile.ZipFile(f)
    for side in 'ab':
        try: s=z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        ph=None
        for l in s.splitlines():
            p=l.split()
            if p[:1]==['OOF'] and len(p)>=3: ph=p[2]
            elif p[:1]==['X'] and len(p)>=5 and ph:
                o=100000-int(p[3]); b='<=5k' if o<=5000 else '5-20k' if o<=20000 else '>20k'
                c[(b,ph)]+=1; cb[b]+=1; ph=None
for b in ('<=5k','5-20k','>20k'):
    print(b,cb[b],' '.join(f'{ph}:{n}' for (bb,ph),n in c.most_common() if bb==b)[:400])
