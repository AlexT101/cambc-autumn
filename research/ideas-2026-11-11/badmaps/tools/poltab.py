import pickle,sys
def tab(rows,label):
    print(label,'n',len(rows))
    bb=[(1,9),(10,17),(18,24),(25,39),(40,999)]; db=[(0,3),(4,6),(7,10),(11,16),(17,99)]
    print('   bag\\dist   '+'  '.join(f"{a}-{b}".rjust(11) for a,b in db))
    for a,b in bb:
        s=[]
        for c,e in db:
            g=[r for r in rows if a<=r['bag']<=b and c<=r['d']<=e]
            t=sum(1 for r in g if r['next']=='tribute'); dd=sum(1 for r in g if r['next']=='death')
            s.append(f"{100*t/max(1,len(g)):3.0f}%/{100*dd/max(1,len(g)):2.0f}% {len(g):4d}".rjust(11))
        print(f"   {a:3d}-{b:3d}   "+'  '.join(s))
    small=[r for r in rows if r['bag']<25]; 
    print('   bags<25: death before next capture/tribute %.1f%% (n=%d); bags>=25: %.1f%%'%(100*sum(r['next']=='death' for r in small)/max(1,len(small)),len(small),100*sum(r['next']=='death' for r in rows if r['bag']>=25)/max(1,sum(1 for r in rows if r['bag']>=25))))
if __name__=='__main__':
    out=pickle.load(open(sys.argv[1],'rb')); np=lambda r:r['typ']!='Prism'
    for opp in ('Inte','Mite'):
        tab([r for r in out if r['us'] and np(r) and r['opp']==opp],f'OURS non-Prism vs {opp}')
        tab([r for r in out if not r['us'] and np(r) and r['opp']==opp],f'OPPONENT {opp} non-Prism')
