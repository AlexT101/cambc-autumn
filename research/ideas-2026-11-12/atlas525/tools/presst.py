import glob,zipfile,collections,sys
for d in sys.argv[1:]:
    n=0; press=0; sim=0; hits=0; tags=collections.Counter(); sc_press=collections.Counter(); sc_all=collections.Counter(); oof_pr=0; oofs=0; turns=0; pr_rounds=0
    for f in glob.glob(d+'/*.repl26a'):
        side='a' if f.endswith('-12.repl26a') else 'b'
        s=zipfile.ZipFile(f).read(f'team-{side}.stdout').decode('utf-8','replace').replace('\x00','')
        n+=1; pt=set(); prr=set(); oofr=[]
        L=s.splitlines()
        for l in L:
            if l.startswith('PRESS '):
                p=l.split(); press+=1; sim+=('sim' in p[7:]); pt.add((p[1],p[2])); prr.add(int(p[1]))
                for c in p[7]: tags[c]+=1
            elif l.startswith('PRESSHIT'): hits+=1
            elif l.startswith('OOF '):
                r=int(l.split()[1]);
                if r>5: oofr.append(r)
            elif l.startswith('D '): turns+=1
        for l in L:
            if l.startswith('SHORTCUT '):
                p=l.split()
                if len(p)>=4:
                    sc_all[p[3]]+=1
                    if (p[1],p[2]) in pt: sc_press[p[3]]+=1
        oofs+=len(oofr); oof_pr+=sum(r in prr or r-1 in prr for r in oofr); pr_rounds+=len(prr)
    print(d.split('atlprof-')[1], f'games {n} press-turns/game {press/n:.1f} sim {sim/max(press,1):.2f} hit/press {hits/max(press,1):.2f} tags', {k:round(v/n,1) for k,v in tags.items()})
    print('  OOF/game', round(oofs/n,2), 'OOF in a press round (or next)', round(oof_pr/n,2), 'press rounds/game', round(pr_rounds/n,1))
    print('  shortcuts on press turns /game', {k:round(v/n,2) for k,v in sc_press.most_common(8)})
