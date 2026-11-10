"""simpan.py DIR: per turn with a sim under 70k fuel: sims (in, cost), finished/OOF, spend after the last sim."""
import zipfile,glob,sys,collections
turns=[]
overrun=[]
for f in glob.glob(sys.argv[1]+'/*/*.repl26a'):
    z=zipfile.ZipFile(f)
    for side in 'ab':
        try: s=z.read(f'team-{side}.stdout').decode(errors='replace')
        except KeyError: continue
        if '\nT ' not in s and not s.startswith('T '): continue
        cur={}  # handle -> turn
        oof=set()
        allt=[]
        last=None
        for l in s.splitlines():
            p=l.split()
            if not p: continue
            if p[0]=='T' and len(p)==3:
                last={'r':int(p[1]),'h':p[2],'sims':[],'end':None}; allt.append(last)
            elif p[0]=='S' and len(p)==5 and last: last['sims'].append((int(p[1]),int(p[2]),int(p[3]),int(p[4])))
            elif p[0]=='E' and len(p)==3 and last and last['h']==p[1] and last['end'] is None: last['end']=int(p[2])
            elif p[0]=='X' and len(p)>=3:
                oof.add((int(p[1]),p[2]))
                if len(p)>=4: overrun.append(100000-int(p[3]))
        for t in allt:
            t['oof']=(t['r'],t['h']) in oof
            turns.append(t)
oofT=[t for t in turns if t['oof']]; fin=[t for t in turns if not t['oof'] and t['end'] is not None]
print('turns with low sims',len(turns),'oof',len(oofT),'finished',len(fin))
def q(v,ps=(50,90,95,99)):
    v=sorted(v); return ' '.join(f'p{p}={v[min(len(v)-1,int(len(v)*p/100))]}' for p in ps) if v else '-'
aft=[t['sims'][-1][0]-t['sims'][-1][1]-t['end'] for t in fin]
print('finished: spend after last sim', q(aft))
lastexit=[t['sims'][-1][0]-t['sims'][-1][1] for t in oofT]
print('oof: fuel left at last sim exit', q(lastexit))
print('oof: sims per turn', q([len(t['sims']) for t in oofT]), ' sim cost', q([c for t in oofT for _,c,_,_ in t['sims']]))
for F in (5000,10000,15000,20000,25000,30000,40000):
    def below(t): return sum(max(0,min(i,F)-(i-c)) for i,c,_,_ in t['sims'])
    fo=[below(t) for t in oofT]; ff=[below(t) for t in fin]
    print(f'F={F}: oof turns w/ sim fuel below F {sum(1 for x in fo if x)/max(1,len(oofT)):.0%} mean {sum(fo)/max(1,len(fo)):.0f}; '
          f'finished turns firing {sum(1 for x in ff if x)} ({sum(1 for x in ff if x)/max(1,len(fin)):.1%} of low-sim finished)')

print('OOF turns (all)',len(overrun),'overrun (tail cost on resume)', q(overrun,(10,25,50,75,90)))
for k in (2000,5000,10000,20000,30000):
    print(f'  overrun <= {k}: {sum(1 for x in overrun if x<=k)/max(1,len(overrun)):.0%}')
